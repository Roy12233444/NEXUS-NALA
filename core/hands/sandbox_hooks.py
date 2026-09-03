"""
Sandbox Hooks for NALA Transcendent Reasoning Engine
====================================================

Implements Phase 1 hardening via irreversible Python audit hooks (PEP 578)
for syscall interception and filesystem/network/subprocess restrictions.
"""

import logging
import threading
import os
import sys
import time
import tempfile
import shutil
import sysconfig
from typing import Optional, Dict, Any, Callable, FrozenSet
from dataclasses import dataclass, field
from contextlib import contextmanager
from enum import Enum, IntEnum, auto

logger = logging.getLogger(__name__)

# Thread-local storage for sandbox context (used by audit hook)
_local = threading.local()


class SandboxLevel(IntEnum):
    """Execution sandbox restriction levels."""
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
    original_env: dict = field(default_factory=dict)
    allowlist: FrozenSet[str] = field(default_factory=frozenset)  # allowed paths for audit hook
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


def _build_sandbox_allowlist(sandbox_temp_dir: str) -> FrozenSet[str]:
    """
    Build the exact set of allowed filesystem prefixes for a sandboxed tool.
    Only these paths can be opened for reading. Nothing outside can be touched.
    """
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
    # 4. The active virtual environment's site‑packages (read‑only)
    for path in sys.path:
        if path and ("site-packages" in path or "dist-packages" in path):
            resolved = os.path.realpath(path)
            if os.path.isdir(resolved):
                allowed.add(resolved)
    # 5. Python executable directory (needed for import machinery)
    python_exec = os.path.realpath(sys.executable)
    allowed.add(os.path.dirname(python_exec))
    return frozenset(allowed)


def _is_path_allowed(path: str, allowlist: FrozenSet[str]) -> bool:
    """Check if a given path falls under any allowed prefix."""
    try:
        real = os.path.normcase(os.path.realpath(os.path.abspath(path)))
    except (OSError, ValueError):
        return False
    return any(real.startswith(os.path.normcase(prefix)) for prefix in allowlist)


def _audit_hook(event: str, args):
    """
    Immutable audit hook installed via sys.addaudithook.
    It reads the current sandbox context from thread‑local storage and
    enforces policy based on the context's allow‑list and sandbox level.
    """
    ctx = getattr(_local, 'sandbox_context', None)
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
                # BLOCK READS outside allow‑list
                elif not _is_path_allowed(path_str, allowlist):
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


# Note: The actual SandboxManager implementation that uses these hooks
# resides in sandbox.py. This file contains only the hook mechanisms.

_tool_callbacks: list = []

def register_tool_callback(callback: Callable) -> None:
    """Register a callback to receive tool execution events from sandbox."""
    if callback not in _tool_callbacks:
        _tool_callbacks.append(callback)

def unregister_tool_callback(callback: Callable) -> None:
    """Remove a previously registered tool callback."""
    if callback in _tool_callbacks:
        _tool_callbacks.remove(callback)

def notify_tool_event(
    tool_name: str,
    success: bool,
    retries: int,
    latency_ms: float,
    is_anomalous: bool = False,
    is_blocked: bool = False,
    args: object = None
) -> None:
    """Notify all registered tool callbacks of a tool execution event."""
    for cb in list(_tool_callbacks):
        try:
            cb(tool_name, success, retries, latency_ms, is_anomalous=is_anomalous, is_blocked=is_blocked, args=args)
        except Exception as e:
            logger.warning(f"Tool event callback failed: {e}")


__all__ = [
    "_audit_hook",
    "_build_sandbox_allowlist",
    "_is_path_allowed",
    "SandboxViolationError",
    "SandboxLevel",
    "SandboxContext",
    "register_tool_callback",
    "unregister_tool_callback",
    "notify_tool_event",
]