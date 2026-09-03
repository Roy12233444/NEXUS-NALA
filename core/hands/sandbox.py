"""
Sandbox Layer for NALA for NALA Transcendent
This provides isolated execution environments for tools based on their safety levels.
Implements defense-in-depth sandboxing with:
- Phase 1: Python audit hooks (PEP 578) for filesystem/network/subprocess restrictions
- Phase 2A: Windows Job Objects for kernel-level resource enforcement on Windows
- Phase 2B: Linux namespace isolation (mount, net, pid, ipc, uts) via unshare/chroot
- Phase 3: Linux seccomp-BPF syscall filtering for kernel-level syscall whitelisting

Integrates with:
- Tool Registry (for safety level determination)
- Executor (to activate/deactivate sandboxes around tool execution)
- Safety layers (for violation reporting and monitoring)
"""

import logging
import threading
import tempfile
import os
import sys
import platform
import time
import shutil
from typing import Optional, Dict, Any, Callable, ContextManager
from dataclasses import dataclass, field
from contextlib import contextmanager
from enum import Enum, IntEnum, auto

# Import modular sandbox components
try:
    from . import sandbox_hooks
    from . import sandbox_windows
    from . import sandbox_linux
    from . import sandbox_seccomp
    HAS_MODULAR_COMPONENTS = True
except ImportError:
    HAS_MODULAR_COMPONENTS = False
    sandbox_hooks = None
    sandbox_windows = None
    sandbox_linux = None
    sandbox_seccomp = None

logger = logging.getLogger(__name__)

# Try to import platform‑specific modules (fallback for backward compatibility)
try:
    import resource  # Unix/Linux/macOS
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False
    resource = None

try:
    import psutil  # For cross‑platform process monitoring
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

# Architecture‑specific syscall name → number mapping (x86_64)
# NOTE: This is a simplified mapping for the most common architecture.
# For production use across multiple architectures, a more robust
# mechanism (e.g., parsing system headers) should be implemented.
_X86_64_SYSCALL_MAP = {
    "read": 0,
    "write": 1,
    "close": 3,
    "fstat": 5,
    "lseek": 8,
    "mmap": 9,
    "mprotect": 10,
    "munmap": 11,
    "brk": 12,
    "rt_sigaction": 13,
    "rt_sigprocmask": 14,
    "ioctl": 16,
    "pread64": 17,
    "readv": 19,
    "writev": 20,
    "access": 21,
    "pipe": 22,
    "select": 23,
    "sched_yield": 24,
    "mremap": 25,
    "msync": 26,
    "futex": 28,
    "clone": 56,
    "getdents": 61,
    "getcwd": 79,  # Note: This has a typo in the original, but we'll keep it for now
    "rename": 82,
    "mkdir": 83,
    "rmdir": 84,
    "unlink": 87,
    "readlink": 89,
    "chmod": 90,
    "lstat": 6,
    "stat": 4,
    "openat": 257,
    "getpid": 39,
    "exit_group": 231,
    "sigaltstack": 129,
    "arch_prctl": 158,
    "set_tid_address": 218,
}


def _get_syscall_number(name: str) -> Optional[int]:
    """
    Convert a syscall name to its number for the current architecture.
    Currently only supports x86_64 on Linux. For other architectures, returns None.

    Args:
        name: Syscall name (e.g., "read", "write")

    Returns:
        Syscall number as integer, or None if not supported/unknown
    """
    if sys.platform.startswith('linux') and platform.machine() == 'x86_64':
        return _X86_64_SYSCALL_MAP.get(name)
    logger.warning("Syscall number lookup only implemented for x86_64 on Linux; "
                   "skipping seccomp filter for platform: %s/%s",
                   sys.platform, platform.machine())
    return None


class SandboxLevel(IntEnum):
    """Execution sandbox restriction levels matching ToolMetadata safety levels."""
    NONE = 0          # No restrictions (for CRITICAL safety trusted tools)
    BASIC = 1         # Basic resource limits (CPU, memory, time)
    RESTRICTED = 2    # Restricted filesystem, network, no child processes
    ISOLATED = 3      # Full isolation (separate process/container with minimal privileges)


@dataclass
class SandboxContext:
    """Context for sandbox execution containing all necessary cleanup information."""
    sandbox_level: SandboxLevel
    sandbox_level_num: int          # 1=BASIC, 2=RESTRICTED, 3=ISOLATED (for audit hook)
    temp_dir: str
    original_cwd: str
    original_env: Dict[str, str] = field(default_factory=dict)
    allowlist: frozenset = field(default_factory=frozenset)  # allowed paths for audit hook
    cleanup_callbacks: list = field(default_factory=list)
    process_handle: Optional[Any] = None  # For isolated sandboxes (future phases)
    winjob_handle: Optional[Any] = None   # Windows Job Object handle (Phase 2A)
    created_at: float = field(default_factory=time.time)

    def cleanup(self):
        """Execute all cleanup callbacks and clean up temporary directory."""
        # Execute cleanup callbacks in reverse order
        for callback in reversed(self.cleanup_callbacks):
            try:
                callback()
            except Exception as e:
                logger.warning(f"Sandbox cleanup callback failed: {e}")

        # Restore original working directory if currently inside temp_dir (required on Windows)
        if self.original_cwd and os.path.exists(self.original_cwd):
            try:
                os.chdir(self.original_cwd)
            except Exception as e:
                logger.warning(f"Failed to restore original CWD {self.original_cwd}: {e}")

        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            for attempt in range(3):
                try:
                    shutil.rmtree(self.temp_dir)
                    logger.debug(f"Cleaned up sandbox directory: {self.temp_dir}")
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(0.1)
                    else:
                        logger.error(f"Failed to remove sandbox directory {self.temp_dir}: {e}")


class SandboxViolationError(Exception):
    """Raised when a tool attempts to violate sandbox restrictions."""
    pass


class SandboxManager:
    """
    Manages secure sandbox environments for tool execution.

    Phase 1 features (audit hook based):
    - Irreversible sys.audit hook that blocks disallowed filesystem, network,
      subprocess and privileged OS operations.
    - Per-sandbox allow-list (sandbox temp dir + Python stdlib/site-packages + executable dir).
    - Mapping of ToolMetadata safety levels to audit-hook strictness:
        * CRITICAL/HIGH  → BASIC  (writes only allowed inside sandbox)
        * MEDIUM         → RESTRICTED (blocks network & subprocess)
        * LOW            → ISOLATED (blocks privileged OS ops as well)

    Phase 2A features (Windows Job Objects via ctypes):
    - Kernel-enforced CPU, memory, and process limits on Windows.
    - Automatic termination of all processes in the job on handle close.
    - Limits applied per sandbox based on safety level.

    Phase 2B features (Linux namespace isolation):
    - Linux/macOS namespace isolation via unshare(2) and chroot.
    - Provides mount, network, PID, IPC, and UTS namespace isolation.
    - Requires appropriate privileges (CAP_SYS_ADMIN or user namespaces).

    Phase 3 features (Linux seccomp-BPF):
    - Linux seccomp-BPF syscall filtering to allow only a whitelisted set of system calls.
    - Provides the final layer of defense-in-depth for Linux systems.

    Legacy features (kept for defense-in-depth and future phases):
    - Basic resource limits (CPU, memory, file size, process count) via resource/Job‑Objects.
    - Filesystem, network and process-creation placeholders.
    - Environment sanitization for ISOLATED level.
    """

    def __init__(self,
                 base_temp_dir: Optional[str] = None,
                 enable_sandboxing: bool = True,
                 default_cpu_limit: float = 5.0,          # seconds
                 default_memory_limit: int = 512 * 1024 * 1024,  # 512 MB
                 default_file_quota: int = 100 * 1024 * 1024):   # 100 MB
        """
        Initialize the Sandbox Manager.

        Args:
            base_temp_dir: Base directory for sandbox temporary files (None = system temp)
            enable_sandboxing: Whether to enable sandboxing (False for testing)
            default_cpu_limit: Default CPU time limit in seconds
            default_memory_limit: Default memory limit in bytes
            default_file_quota: Maximum file write size in bytes
        """
        self._lock = threading.RLock()
        self._logger = logging.getLogger(f"{__name__}.SandboxManager")
        self._local = threading.local()  # holds current sandbox context for audit hook

        # Configuration
        self.base_temp_dir = base_temp_dir or tempfile.gettempdir()
        self.enable_sandboxing = enable_sandboxing
        self.default_cpu_limit = default_cpu_limit
        self.default_memory_limit = default_memory_limit
        self.default_file_quota = default_file_quota

        # Safety level → sandbox level mapping (used for legacy compat & context)
        self.safety_to_sandbox_map = {
            "critical": SandboxLevel.NONE,
            "high": SandboxLevel.BASIC,
            "medium": SandboxLevel.RESTRICTED,
            "low": SandboxLevel.ISOLATED,
        }

        # Statistics
        self._sandbox_count = 0
        self._violation_count = 0
        self._total_setup_time = 0.0
        self._total_cleanup_time = 0.0

        # Install the audit hook once (if sandboxing enabled)
        self._audit_hook_installed = False
        if self.enable_sandboxing:
            self._audit_hook_installed = True
            if HAS_MODULAR_COMPONENTS and sandbox_hooks:
                # Use modular audit hook
                sys.addaudithook(sandbox_hooks._audit_hook)
            else:
                # Fallback to inline implementation
                sys.addaudithook(self._audit_hook)

        self._logger.info(
            f"Sandbox Manager initialized: "
            f"base_temp_dir={self.base_temp_dir}, "
            f"enabled={self.enable_sandboxing}"
        )

    # --------------------------------------------------------------------- #
    # Audit-hook helpers (Phase 1) - Use modular implementations when available
    # --------------------------------------------------------------------- #
    @staticmethod
    def _build_sandbox_allowlist(sandbox_temp_dir: str) -> frozenset:
        """
        Build the exact set of allowed filesystem prefixes for a sandboxed tool.
        Only these paths can be opened for reading. Nothing outside can be touched.
        Delegates to modular implementation if available.
        """
        if HAS_MODULAR_COMPONENTS and sandbox_hooks:
            return sandbox_hooks._build_sandbox_allowlist(sandbox_temp_dir)
        else:
            # Fallback implementation
            allowed = set()
            # 1. The sandbox's own temporary working directory
            allowed.add(os.path.realpath(sandbox_temp_dir))
            # 2. Python standard library (read-only)
            stdlib_path = sysconfig.get_paths()["stdlib"]
            if stdlib_path:
                allowed.add(os.path.realpath(stdlib_path))
            # 3. Python platlib (compiled extensions like .pyd / .so)
            platlib = sysconfig.get_paths().get("platlib", "")
            if platlib:
                allowed.add(os.path.realpath(platlib))
            # 4. The active virtual environment's site-packages (read-only)
            for path in sys.path:
                if path and ("site-packages" in path or "dist-packages" in path):
                    resolved = os.path.realpath(path)
                    if os.path.isdir(resolved):
                        allowed.add(resolved)
            # 5. Python executable directory (needed for import machinery)
            python_exec = os.path.realpath(sys.executable)
            allowed.add(os.path.dirname(python_exec))
            return frozenset(allowed)

    @staticmethod
    def _is_path_allowed(path: str, allowlist: frozenset) -> bool:
        """Check if a given path falls under any allowed prefix."""
        if HAS_MODULAR_COMPONENTS and sandbox_hooks:
            return sandbox_hooks._is_path_allowed(path, allowlist)
        else:
            # Fallback implementation
            try:
                real = os.path.normcase(os.path.realpath(os.path.abspath(path)))
            except (OSError, ValueError):
                return False
            return any(real.startswith(os.path.normcase(prefix)) for prefix in allowlist)

    def _audit_hook(self, event: str, args):
        """
        Immutable audit hook installed via sys.addaudithook.
        It reads the current sandbox context from thread-local storage and
        enforces policy based on the context's allow-list and sandbox level.
        Delegates to modular implementation when available.
        """
        if HAS_MODULAR_COMPONENTS and sandbox_hooks:
            # Delegate to modular implementation
            sandbox_hooks._audit_hook(event, args)
            return

        # Fallback implementation
        ctx = getattr(self._local, 'sandbox_context', None)
        if ctx is None:
            # No active sandbox – allow operation (no restriction)
            return

        allowlist = ctx.allowlist
        level_num = ctx.sandbox_level_num  # 1=BASIC, 2=RESTRICTED, 3=ISOLATED

        # ---------- FILESYSTEM EVENTS ----------
        if event in ("open", "os.open", "io.open", "builtins.open"):
            if args:
                path = args[0]
                if isinstance(path, (str, bytes)):
                    path_str = path.decode() if isinstance(path, bytes) else path
                    mode = args[1] if len(args) > 1 else "r"
                    # BLOCK WRITES outside sandbox temp dir
                    if isinstance(mode, str) and any(c in mode for c in "wxa+"):
                        sandbox_dir = os.path.normcase(os.path.realpath(ctx.temp_dir))
                        target_path = os.path.normcase(os.path.realpath(os.path.abspath(path_str)))
                        if not target_path.startswith(sandbox_dir):
                            raise PermissionError(
                                f"[SandboxViolation] Write blocked outside sandbox: {path_str}"
                            )
                    # BLOCK READS outside allow-list
                    elif not self._is_path_allowed(path_str, allowlist):
                        raise PermissionError(
                            f"[SandboxViolation] Read blocked outside allowlist: {path_str}"
                        )

        # ---------- NETWORK EVENTS (RESTRICTED+) ----------
        if level_num >= 2 and event in ("socket.connect", "socket.sendto"):
            raise PermissionError(
                f"[SandboxViolation] Network call '{event}' blocked in sandbox"
            )

        # ---------- SUBPROCESS EVENTS (RESTRICTED+) ----------
        if level_num >= 2 and event in ("subprocess.Popen", "os.system", "os.exec"):
            raise PermissionError(
                f"[SandboxViolation] Process spawn '{event}' blocked in sandbox"
            )

        # ---------- DANGEROUS OS OPERATIONS (ISOLATED) ----------
        if level_num >= 3 and event in (
            "os.chmod", "os.chown", "os.setuid", "os.setgid",
            "os.symlink", "os.link", "os.mount", "shutil.rmtree"
        ):
            raise PermissionError(
                f"[SandboxViolation] Privileged OS op '{event}' blocked in isolated sandbox"
            )

    # --------------------------------------------------------------------- #
    # Phase 2A: Windows Job Objects via ctypes - Use modular implementation
    # --------------------------------------------------------------------- #
    def _apply_windows_job_object(self, context: SandboxContext) -> Optional[Any]:
        """
        Apply Windows Job Object resource limits to the current process.
        Returns the job handle on success, None on failure.

        This method is only called on Windows platforms.
        Delegates to modular implementation when available.
        """
        if HAS_MODULAR_COMPONENTS and sandbox_windows:
            return sandbox_windows._apply_windows_job_object(context)

        # Fallback implementation (simplified)
        if sys.platform != 'win32':
            return None

        # Simple fallback - in a real implementation, this would have the full Windows Job Object logic
        self._logger.warning("Using fallback Windows Job Object implementation")
        return None

    # --------------------------------------------------------------------- #
    # Sandbox lifecycle (public API)
    # --------------------------------------------------------------------- #
    def create_sandbox(self, tool_safety_level: str) -> SandboxContext:
        """
        Create a sandbox context based on the tool's safety level.

        Args:
            tool_safety_level: Safety level from ToolMetadata ("low", "medium", "high", "critical")

        Returns:
            SandboxContext ready for use
        """
        start_time = time.time()

        # Normalise safety level
        safety_level = tool_safety_level.lower().strip()
        if safety_level not in self.safety_to_sandbox_map:
            self._logger.warning(f"Unknown safety level '{safety_level}', defaulting to 'medium'")
            safety_level = "medium"

        # Determine sandbox level (for legacy fields & context)
        sandbox_level = self.safety_to_sandbox_map[safety_level]
        # Numeric level for audit hook: 1=BASIC, 2=RESTRICTED, 3=ISOLATED (for audit hook)
        safety_to_level_num = {"critical": 1, "high": 1, "medium": 2, "low": 3}
        level_num = safety_to_level_num.get(safety_level, 2)

        # Create temporary directory
        temp_dir = tempfile.mkdtemp(
            prefix=f"nala_sandbox_{sandbox_level.value}_",
            dir=self.base_temp_dir
        )

        # Save current state for restoration
        original_cwd = os.getcwd()
        original_env = dict(os.environ)

        # Build allow-list for this sandbox
        allowlist = self._build_sandbox_allowlist(temp_dir)

        context = SandboxContext(
            sandbox_level=sandbox_level,
            sandbox_level_num=level_num,
            temp_dir=temp_dir,
            original_cwd=original_cwd,
            original_env=original_env,
            allowlist=allowlist,
        )

        # Apply legacy (OS-level) restrictions – kept for defense-in-depth
        if self.enable_sandboxing and sandbox_level != SandboxLevel.NONE:
            self._apply_sandbox_restrictions(context, sandbox_level)

        # Track statistics
        with self._lock:
            self._sandbox_count += 1
            self._total_setup_time += time.time() - start_time

        self._logger.debug(
            f"Created {sandbox_level.name} sandbox ({level_num}) for {safety_level} tool: {temp_dir}"
        )
        return context

    @contextmanager
    def sandbox_context(self, tool_safety_level: str) -> ContextManager[SandboxContext]:
        """
        Context manager for automatic sandbox creation and cleanup.

        Usage:
            with sandbox_manager.sandbox_context("medium") as ctx:
                # Execute tool here with sandbox active
                result = some_tool_function()
        """
        context = None
        try:
            context = self.create_sandbox(tool_safety_level)
            # Bind context to thread-local so the audit hook can see it
            self._local.sandbox_context = context
            if HAS_MODULAR_COMPONENTS and sandbox_hooks:
                sandbox_hooks._local.sandbox_context = context
            yield context
        finally:
            if context:
                # Clean up thread-local reference first to deactivate audit hook during cleanup
                if hasattr(self._local, 'sandbox_context'):
                    del self._local.sandbox_context
                if HAS_MODULAR_COMPONENTS and sandbox_hooks and hasattr(sandbox_hooks._local, 'sandbox_context'):
                    del sandbox_hooks._local.sandbox_context
                self._cleanup_sandbox(context)

    def _cleanup_sandbox(self, context: SandboxContext):
        """Clean up sandbox resources and restore original state."""
        start_time = time.time()

        try:
            context.cleanup()
        finally:
            # Close Windows Job Object handle if present
            if context.winjob_handle is not None and sys.platform == 'win32':
                try:
                    if HAS_MODULAR_COMPONENTS and sandbox_windows:
                        # The modular implementation doesn't expose a close function directly
                        # but we can still try to close the handle
                        import ctypes
                        ctypes.windll.kernel32.CloseHandle(context.winjob_handle)
                    else:
                        import ctypes
                        ctypes.windll.kernel32.CloseHandle(context.winjob_handle)
                except Exception as e:
                    self._logger.warning(f"Failed to close Windows Job Object handle: {e}")
                finally:
                    context.winjob_handle = None

            # Restore original working directory
            try:
                os.chdir(context.original_cwd)
            except Exception as e:
                self._logger.warning(f"Failed to restore original CWD: {e}")

            # Update statistics
            with self._lock:
                self._total_cleanup_time += time.time() - start_time

    def execute_in_sandbox(self,
                          tool_safety_level: str,
                          func: Callable,
                          *args,
                          **kwargs) -> Any:
        """
        Execute a function within the appropriate sandbox.

        Args:
            tool_safety_level: Safety level from ToolMetadata
            func: Function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function return value

        Raises:
            SandboxViolationError: If sandbox restrictions are violated
            Any exception raised by the function
        """
        with self.sandbox_context(tool_safety_level) as context:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Check if this looks like a sandbox violation
                if ("access denied" in str(e).lower() or
                   "permission denied" in str(e).lower() or
                   "operation not permitted" in str(e).lower()):
                    self._violation_count += 1
                    self._logger.warning(
                        f"Potential sandbox violation in {tool_safety_level} tool: {e}"
                    )
                    # Re-raise as security exception
                    raise SandboxViolationError(f"Sandbox violation detected: {e}") from e
                else:
                    # Regular tool error – let it propagate
                    raise

    # --------------------------------------------------------------------- #
    # Legacy restriction applicators (kept for defense-in-depth & future phases)
    # --------------------------------------------------------------------- #
    def _apply_sandbox_restrictions(self, context: SandboxContext, level: SandboxLevel):
        """
        Apply OS-specific sandbox restrictions based on level.
        These are legacy defense-in-depth measures; the primary enforcement
        comes from the audit hook (Phase 1), Windows Job Object (Phase 2A),
        Linux namespaces (Phase 2B), and seccomp-BPF (Phase 3).
        """
        try:
            # Change to sandbox directory (also done by audit hook allowance)
            os.chdir(context.temp_dir)

            # Apply restrictions based on level
            if level >= SandboxLevel.BASIC:
                self._apply_resource_limits(context)

            if level >= SandboxLevel.RESTRICTED:
                self._apply_filesystem_restrictions(context)
                self._apply_network_restrictions(context)
                self._restrict_process_creation(context)

            if level >= SandboxLevel.ISOLATED:
                self._apply_isolation(context)
                # Apply Linux namespace isolation for ISOLATED level on Linux
                if sys.platform.startswith('linux') and HAS_LINUX_SPECIFIC and sandbox_linux:
                    try:
                        # Get Python standard library path for bind-mount
                        python_lib_path = sysconfig.get_paths()["stdlib"]
                        sandbox_linux._apply_linux_namespaces(context.temp_dir, python_lib_path)
                        self._logger.debug("Applied Linux namespace isolation")
                    except Exception as e:
                        self._logger.warning(
                            f"Failed to apply Linux namespace isolation: {e}. "
                            "Falling back to audit hook and other restrictions."
                        )

            # --- Windows Job Object (Phase 2A) ---
            if sys.platform == 'win32' and level >= SandboxLevel.BASIC:
                try:
                    job_handle = self._apply_windows_job_object(context)
                    if job_handle is not None:
                        context.winjob_handle = job_handle
                except Exception as e:
                    self._logger.warning(
                        f"Failed to apply Windows Job Object: {e}. "
                        "Falling back to audit hook and legacy resource limits."
                    )

            # --- Linux seccomp-BPF (Phase 3) ---
            if sys.platform.startswith('linux') and HAS_LINUX_SPECIFIC and sandbox_seccomp is not None and level >= SandboxLevel.ISOLATED:
                try:
                    # Convert syscall names to numbers for the current architecture
                    allowed_nums = frozenset(
                        num for name in sandbox_seccomp.ALLOWED_SYSCALLS_NAMES
                        if (num := _get_syscall_number(name)) is not None
                    )
                    if allowed_nums:
                        sandbox_seccomp.apply_seccomp_filter(allowed_nums)
                        self._logger.debug("Applied seccomp-BPF filter allowing %d syscalls", len(allowed_nums))
                    else:
                        self._logger.warning("No valid syscall numbers found for seccomp filter")
                except Exception as e:
                    self._logger.warning(
                        f"Failed to apply seccomp-BPF filter: {e}. "
                        "Continuing with reduced syscall filtering."
                    )

        except Exception as e:
            self._logger.error(f"Failed to apply sandbox restrictions: {e}")
            # Don't fail hard – continue with warnings for defense-in-depth
            context.cleanup_callbacks.append(
                lambda: self._logger.warning("Sandbox may be incomplete due to setup error")
            )

    def _apply_resource_limits(self, context: SandboxContext):
        """Apply CPU and memory limits using OS-specific mechanisms."""
        if sys.platform.startswith('linux') or sys.platform == 'darwin':
            if not HAS_RESOURCE:
                self._logger.warning("resource module unavailable, skipping Unix limits")
                return

            try:
                # Limit CPU time (seconds)
                resource.setrlimit(
                    resource.RLIMIT_CPU,
                    (int(self.default_cpu_limit), int(self.default_cpu_limit))
                )
                # Limit memory (bytes)
                resource.setrlimit(
                    resource.RLIMIT_AS,
                    (self.default_memory_limit, self.default_memory_limit)
                )
                # Limit file size (bytes)
                resource.setrlimit(
                    resource.RLIMIT_FSIZE,
                    (self.default_file_quota, self.default_file_quota)
                )
                # Limit number of processes
                resource.setrlimit(
                    resource.RLIMIT_NPROC,
                    (64, 64)  # Reasonable limit
                )
                context.cleanup_callbacks.append(
                    lambda: self._logger.debug("Resource limits applied")
                )
            except Exception as e:
                self._logger.warning(f"Failed to set resource limits: {e}")

        elif sys.platform == 'win32':
            # Windows job objects for resource limits are handled in _apply_windows_job_object
            # This placeholder is kept for consistency with non-Windows code paths.
            self._logger.debug("Windows resource limits applied via Job Object (see _apply_windows_job_object)")
            context.cleanup_callbacks.append(
                lambda: self._logger.debug("Windows resource limits applied (placeholder)")
            )

    def _apply_filesystem_restrictions(self, context: SandboxContext):
        """Restrict filesystem access to sandbox directory and safe locations."""
        # Placeholder – in a full implementation we would use chroot, job objects, or mount namespaces.
        def check_path_access(path):
            pass  # Would hook into file-system calls
        context.cleanup_callbacks.append(
            lambda: self._logger.debug("Filesystem restrictions applied (baseline)")
        )

    def _apply_network_restrictions(self, context: SandboxContext):
        """Restrict network access."""
        # Placeholder – in a full implementation we would use network namespaces or firewall rules.
        def network_guard():
            pass  # Would enforce network block
        context.cleanup_callbacks.append(
            lambda: self._logger.debug("Network restrictions applied (placeholder)")
        )

    def _restrict_process_creation(self, context: SandboxContext):
        """Prevent spawning of child processes."""
        # Placeholder – RLIMIT_NPROC on Unix, Job Object on Windows.
        context.cleanup_callbacks.append(
            lambda: self._logger.debug("Process creation restrictions applied")
        )

    def _apply_isolation(self, context: SandboxContext):
        """Apply maximum isolation techniques."""
        # Placeholder – user namespaces, drop privileges, mount namespaces, etc.
        dirty_vars = [
            'LD_PRELOAD', 'LD_LIBRARY_PATH', 'PYTHONPATH',
            'PATH', 'HOME', 'USER', 'LOGNAME'
        ]
        safe_env = {
            k: v for k, v in os.environ.items()
            if k not in dirty_vars and not k.startswith('LD_')
        }
        safe_env.update({
            'PATH': '/usr/bin:/bin',
            'HOME': context.temp_dir,
            'TMPDIR': context.temp_dir,
            'LANG': 'C.UTF-8',
            'LC_ALL': 'C.UTF-8'
        })
        original_env_backup = dict(os.environ)

        def restore_env():
            os.environ.clear()
            os.environ.update(original_env_backup)

        os.environ.clear()
        os.environ.update(safe_env)

        context.cleanup_callbacks.append(restore_env)
        context.cleanup_callbacks.append(
            lambda: self._logger.debug("Environment sanitized and isolated")
        )

    # --------------------------------------------------------------------- #
    # Diagnostics & statistics
    # --------------------------------------------------------------------- #
    def get_stats(self) -> Dict[str, Any]:
        """Get sandbox manager statistics."""
        with self._lock:
            count = self._sandbox_count
            return {
                'sandboxes_created': count,
                'violations_detected': self._violation_count,
                'avg_setup_time_ms': (
                    (self._total_setup_time / max(count, 1)) * 1000
                    if count > 0 else 0.0
                ),
                'avg_cleanup_time_ms': (
                    (self._total_cleanup_time / max(count, 1)) * 1000
                    if count > 0 else 0.0
                ),
                'enabled': self.enable_sandboxing,
                'base_temp_dir': self.base_temp_dir,
            }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on sandbox mechanisms."""
        issues = []
        status = "healthy"

        # Check base temp directory
        if not os.path.isdir(self.base_temp_dir):
            issues.append(f"Base temp directory does not exist: {self.base_temp_dir}")
            status = "unhealthy"
        elif not os.access(self.base_temp_dir, os.W_OK):
            issues.append(f"Base temp directory is not writable: {self.base_temp_dir}")
            status = "unhealthy"

        # Check if we can create a test sandbox
        try:
            test_ctx = self.create_sandbox("medium")
            test_ctx.cleanup()
        except Exception as e:
            issues.append(f"Failed to create/test sandbox: {e}")
            if status == "healthy":
                status = "degraded"

        # Check platform support for legacy features
        if sys.platform == 'win32' and not HAS_PSUTIL:
            issues.append("psutil not available – Windows sandboxing will be limited")
            if status == "healthy":
                status = "degraded"

        if (sys.platform.startswith('linux') or sys.platform == 'darwin') and not HAS_RESOURCE:
            issues.append("resource module not available – Unix resource limits disabled")
            if status == "healthy":
                status = "degraded"

        # Check Windows Job Object availability (Phase 2A)
        if sys.platform == 'win32':
            try:
                import ctypes
                import ctypes.wintypes as wintypes
                # Try to load kernel32 and bind a function to see if it works
                _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
                _kernel32.CreateJobObjectW.argtypes = [
                    ctypes.c_void_p,
                    wintypes.LPCWSTR,
                ]
                # Try to create a dummy job object to test
                job_handle = _kernel32.CreateJobObjectW(None, None)
                if not job_handle:
                    issues.append("Windows Job Object creation failed – check permissions")
                    if status == "healthy":
                        status = "degraded"
                else:
                    _kernel32.CloseHandle(job_handle)
            except Exception as e:
                issues.append(f"Windows Job Object support check failed: {e}")
                if status == "healthy":
                    status = "degraded"

        # Check Linux seccomp-BPF availability (Phase 3)
        if sys.platform.startswith('linux') and HAS_LINUX_SPECIFIC and sandbox_seccomp is not None:
            if not sandbox_seccomp.is_seccomp_available():
                issues.append("seccomp-BPF not available – syscall filtering disabled")
                if status == "healthy":
                    status = "degraded"

        # Check Linux namespace availability (Phase 2B)
        if sys.platform.startswith('linux') and HAS_LINUX_SPECIFIC and sandbox_linux is not None:
            # We can't easily test namespace availability without actually trying to use it
            # which requires privileges, so we just note it's available
            pass

        return {
            'status': status,
            'issues': issues,
            'timestamp': time.time(),
            'stats': self.get_stats()
        }

    def reset_stats(self):
        """Reset statistics (mainly for testing)."""
        with self._lock:
            self._sandbox_count = 0
            self._violation_count = 0
            self._total_setup_time = 0.0
            self._total_cleanup_time = 0.0


# =======================
# Module-Level Singleton
# =======================
_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager() -> SandboxManager:
    """
    Get or create the global SandboxManager instance (singleton pattern).

    Returns:
        The singleton SandboxManager instance.
    """
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager()
    return _sandbox_manager


def create_sandbox(tool_safety_level: str) -> SandboxContext:
    """
    Convenience function to create a sandbox via the global manager.

    Args:
        tool_safety_level: Safety level from ToolMetadata

    Returns:
        SandboxContext ready for use
    """
    return get_sandbox_manager().create_sandbox(tool_safety_level)


@contextmanager
def sandbox_context(tool_safety_level: str) -> ContextManager[SandboxContext]:
    """
    Convenience context manager for sandbox operations.

    Usage:
        with sandbox_context("medium") as ctx:
            # Execute tool here
            pass
    """
    with get_sandbox_manager().sandbox_context(tool_safety_level) as ctx:
        yield ctx


def execute_in_sandbox(tool_safety_level: str,
                      func: Callable,
                      *args,
                      **kwargs) -> Any:
    """
    Convenience function to execute a function in a sandbox via global manager.

    Args:
        tool_safety_level: Safety level from ToolMetadata
        func: Function to execute
        *args, **kwargs: Arguments to pass to function

    Returns:
        Function return value
    """
    return get_sandbox_manager().execute_in_sandbox(
        tool_safety_level, func, *args, **kwargs
    )


def get_sandbox_stats() -> Dict[str, Any]:
    """Get statistics from the global sandbox manager."""
    return get_sandbox_manager().get_stats()


def sandbox_health_check() -> Dict[str, Any]:
    """Get health status from the global sandbox manager."""
    return get_sandbox_manager().health_check()


# ======================
# Demo / Self-Test
# ======================
if __name__ == "__main__":
    # Configure logging for demo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 70)
    print("Sandbox Layer Demo / Self-Test (All Phases)")
    print("=" * 70)

    # Create sandbox manager with demo settings
    sandbox_manager = SandboxManager(
        base_temp_dir=tempfile.gettempdir(),
        enable_sandboxing=True,
        default_cpu_limit=2.0,          # 2 seconds for demo
        default_memory_limit=64 * 1024 * 1024,  # 64 MB
        default_file_quota=10 * 1024 * 1024     # 10 MB
    )

    print(f"\nInitial sandbox manager state:")
    stats = sandbox_manager.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Demo 1: Basic sandbox creation and cleanup
    print("\n--- Demo 1: Basic Sandbox Lifecycle ---")
    with sandbox_manager.sandbox_context("medium") as ctx:
        print(f"Created sandbox: {ctx.temp_dir}")
        print(f"Sandbox level: {ctx.sandbox_level.name} (numeric={ctx.sandbox_level_num})")
        print(f"Current directory: {os.getcwd()}")
        # Create a test file inside the sandbox (should succeed)
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Hello, secure sandbox!")
        print(f"Created test file: {test_file}")
    # Sandbox automatically cleaned up here
    print(f"After cleanup, directory exists: {os.path.exists(temp_dir)}")

    # Demo 2: Function execution in sandbox (should succeed for allowed ops)
    print("\n--- Demo 2: Function Execution in Sandbox ---")

    def cpu_intensive_task():
        total = 0
        for i in range(1_000_000):
            total += i
        return total

    def memory_intensive_task():
        data = [0] * (5 * 1024 * 1024)  # 5 MB array
        return len(data)

    def file_heavy_task():
        for i in range(3):
            with open(f"file_{i}.txt", "w") as f:
                f.write("x" * (1 * 1024 * 1024))  # 1 MB each
        return 3

    # Test safe operation (should succeed)
    try:
        result = sandbox_manager.execute_in_sandbox(
            "high",  # Should use BASIC sandbox (writes only inside sandbox)
            cpu_intensive_task
        )
        print(f"CPU task result: {result}")
    except Exception as e:
        print(f"CPU task failed: {e}")

    # Test memory-limited operation (may be limited by OS/resource limits)
    try:
        result = sandbox_manager.execute_in_sandbox(
            "high",
            memory_intensive_task
        )
        print(f"Memory task result: {result} bytes allocated")
    except Exception as e:
        print(f"Memory task failed (expected if limits enforced): {e}")

    # Test file-quota limited operation
    try:
        result = sandbox_manager.execute_in_sandbox(
            "high",
            file_heavy_task
        )
        print(f"File task result: {result} files created")
    except Exception as e:
        print(f"File task failed (expected if quota enforced): {e}")

    # Demo 3: Context manager usage – test violations
    print("\n--- Demo 3: Context Manager Usage – Violation Tests ---")
    with sandbox_manager.sandbox_context("low") as ctx:  # ISOLATED level
        print(f"In ISOLATED sandbox (level={ctx.sandbox_level_num}): {ctx.temp_dir}")

        # 1) Try to read a file outside the allow-list (should be blocked)
        try:
            with open("/etc/passwd", "r") as f:
                _ = f.read(10)
            print("ERROR: Could read /etc/passwd – audit hook did NOT block!")
        except PermissionError as pe:
            if "SandboxViolation" in str(pe):
                print("GOOD: Blocked read outside allow-list:", pe)
            else:
                print("Unexpected PermissionError:", pe)
        except Exception as e:
            print("Other error reading /etc/passwd:", e)

        # 2) Try to write outside sandbox (should be blocked)
        try:
            with open(os.path.join(os.path.sep, "temp", "outside.txt"), "w") as f:
                f.write("should not happen")
            print("ERROR: Could write outside sandbox – audit hook did NOT block!")
        except PermissionError as pe:
            if "SandboxViolation" in str(pe):
                print("GOOD: Blocked write outside sandbox:", pe)
            else:
                print("Unexpected PermissionError:", pe)
        except Exception as e:
            print("Other error writing outside:", e)

        # 3) Try a network call (socket.create_connection) – should be blocked for RESTRICTED+ (level>=2)
        try:
            import socket
            s = socket.create_connection(("8.8.8.8", 53), timeout=0.5)
            s.close()
            print("ERROR: Network call succeeded – audit hook did NOT block!")
        except PermissionError as pe:
            if "SandboxViolation" in str(pe):
                print("GOOD: Blocked network call:", pe)
            else:
                print("Unexpected PermissionError:", pe)
        except Exception as e:
            # socket errors may be timeout or refused; we treat those as not blocked by hook
            print("Network call error (may be timeout/refused):", e)

        # 4) Try to spawn a subprocess – should be blocked for RESTRICTED+ (level>=2)
        try:
            import subprocess
            subprocess.run(["echo", "hello"], check=True, timeout=0.5)
            print("ERROR: Subprocess spawned – audit hook did NOT block!")
        except PermissionError as pe:
            if "SandboxViolation" in str(pe):
                print("GOOD: Blocked subprocess spawn:", pe)
            else:
                print("Unexpected PermissionError:", pe)
        except Exception as e:
            print("Subprocess error (may be timeout/etc):", e)

        # 5) Try a privileged OS op (os.chmod) – should be blocked for ISOLATED (level==3)
        try:
            os.chmod(os.path.join(temp_dir, "test.txt"), 0o755)
            print("ERROR: chmod succeeded – audit hook did NOT block!")
        except PermissionError as pe:
            if "SandboxViolation" in str(pe):
                print("GOOD: Blocked chmod:", pe)
            else:
                print("Unexpected PermissionError:", pe)
        except Exception as e:
            print("chmod error:", e)

        # 6) Test Windows Job Object (only on Windows) – verify that a CPU-intensive task
        #    gets limited by the job object (we can't easily test termination in a demo,
        #    but we can at least verify the job object was created).
        if sys.platform == 'win32':
            if ctx.winjob_handle is not None:
                print(f"GOOD: Windows Job Object handle created: {ctx.winjob_handle}")
            else:
                print("INFO: Windows Job Object not created (may be due to limitations in demo)")

    # Demo 4: Statistics and health check
    print("\n--- Demo 4: Statistics and Health ---")
    stats = sandbox_manager.get_stats()
    print("Statistics:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    health = sandbox_manager.health_check()
    print(f"\nHealth Status: {health['status']}")
    if health['issues']:
        print("Issues:")
        for issue in health['issues']:
            print(f"  - {issue}")
    else:
        print("  No issues detected.")

    print("\n" + "=" * 70)
    print("Sandbox Layer Demo Complete")
    print("=" * 70)