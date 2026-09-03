"""
seccomp-bpf syscall filter for NALA Sandbox (Phase 3)
=====================================================

Implements Linux seccomp-BPF (BPF-based syscall filtering) to allow only a
whitelisted set of system calls. Any syscall not in the whitelist is blocked
(killed) at the kernel level, providing the final layer of defense-in-depth.

Based on the NALA sandbox hardening plan, section 3.4.
"""

import logging
import sys
import ctypes
import ctypes.util
import errno
from typing import FrozenSet, Iterable

logger = logging.getLogger(__name__)

# seccomp is Linux‑only
if not sys.platform.startswith('linux'):
    logger.warning("sandbox_seccomp.py is intended for Linux only; noop on %s", sys.platform)
    # Provide stubs to avoid import errors on non‑Linux platforms
    def apply_seccomp_filter(allowed_syscalls: FrozenSet[int]) -> None:
        """Stub for non‑Linux platforms."""
        logger.warning("seccomp‑BPF not available on %s", sys.platform)
        return

    def is_seccomp_available() -> bool:
        """Always False on non‑Linux platforms."""
        return False

    # For completeness, provide the name list (though unused off‑Linux)
    ALLOWED_SYSCALLS_NAMES = frozenset([
        "read", "write", "close", "fstat", "lseek", "mmap", "mprotect",
        "munmap", "brk", "rt_sigaction", "rt_sigprocmask", "ioctl",
        "pread64", "readv", "writev", "access", "pipe", "select",
        "sched_yield", "mremap", "msync", "futex", "clone",
        "getdents", "getcwd", "rename", "mkdir", "rmdir", "unlink",
        "readlink", "chmod", "lstat", "stat", "openat", "getpid",
        "exit_group", "sigaltstack", "arch_prctl", "set_tid_address",
    ])
else:
    # ----- seccomp Constants (from linux/seccomp.h and sys/prctl.h) -----
    # prctl options
    PR_SET_SECCOMP = 22
    PR_GET_SECCOMP = 21

    # seccomp modes
    SECCOMP_MODE_DISABLED = 0   # seccomp is not in use
    SECCOMP_MODE_STRICT   = 1   # only read, write, exit, sigreturn allowed
    SECCOMP_MODE_FILTER   = 2   # user‑defined filter

    # seccomp filter flags
    SECCOMP_FILTER_FLAG_TSYNC = 1 << 0   # synchronous (wait for all threads)

    # seccomp return actions (upper 16 bits)
    SECCOMP_RET_KILL_PROCESS = 0x80000000  # kill the entire process
    SECCOMP_RET_KILL_THREAD  = 0x00000000  # kill only the thread (not used)
    SECCOMP_RET_TRAP = 0x00030000          # deliver SIGSYS to triggering thread
    SECCOMP_RET_ERRNO = 0x00050000         # return errno from lower 16 bits
    SECCOMP_RET_TRACE = 0x7ff00000         # notify via ptrace (unused here)
    SECCOMP_RET_LOG   = 0x7ffc0000         # log the attempt (audit)
    SECCOMP_RET_ALLOW = 0x7fffffff         # allow the syscall

    # ----- Data Structures for BPF Program -----
    # struct sock_filter {
    #   unsigned short code;   // opcode
    #   unsigned char  jt;     // jump true
    #   unsigned char  jf;     // jump false
    #   unsigned long k;       // constant
    # };
    class sock_filter(ctypes.Structure):
        _fields_ = [
            ("code", ctypes.c_ushort),
            ("jt",   ctypes.c_ubyte),
            ("jf",   ctypes.c_ubyte),
            ("k",    ctypes.c_ulong),
        ]

    # struct sock_fprog {
    #   unsigned short len;    // number of filters
    #   struct sock_filter *filter;
    # };
    class sock_fprog(ctypes.Structure):
        _fields_ = [
            ("len",   ctypes.c_ushort),
            ("filter", ctypes.POINTER(sock_filter)),
        ]

    # ----- Libc Binding for prctl -----
    _libc_name = ctypes.util.find_library("c")
    if not _libc_name:
        raise OSError("Cannot find libc")
    _libc = ctypes.CDLL(_libc_name, use_errno=True)

    # int prctl(int option, unsigned long arg2, unsigned long arg3,
    #           unsigned long arg4, unsigned long arg5);
    _libc.prctl.restype = ctypes.c_int
    _libc.prctl.argtypes = [
        ctypes.c_int,   # option
        ctypes.c_ulong, # arg2
        ctypes.c_ulong, # arg3
        ctypes.c_ulong, # arg4
        ctypes.c_ulong, # arg5
    ]

    # ----- Architecture‑specific Syscall Numbers -----
    # NOTE: This module works with syscall numbers (integers), not names.
    # The caller (e.g., SandboxManager) must convert the names from
    # ALLOWED_SYSCALLS_NAMES to numbers for the current architecture.
    # We provide the names as a reference constant.
    ALLOWED_SYSCALLS_NAMES = frozenset([
        "read", "write", "close", "fstat", "lseek", "mmap", "mprotect",
        "munmap", "brk", "rt_sigaction", "rt_sigprocmask", "ioctl",
        "pread64", "readv", "writev", "access", "pipe", "select",
        "sched_yield", "mremap", "msync", "futex", "clone",
        "getdents", "getcwd", "rename", "mkdir", "rmdir", "unlink",
        "readlink", "chmod", "lstat", "stat", "openat", "getpid",
        "exit_group", "sigaltstack", "arch_prctl", "set_tid_address",
    ])

    # ----- Helper to Build BPF Program from Syscall Numbers -----
    def _build_seccomp_bpf(allowed_syscalls: FrozenSet[int]) -> sock_fprog:
        """
        Build a sock_fprog BPF program that allows only the given syscalls.
        Assumes the syscall number is at offset 0 in the seccomp data.

        Returns a sock_fprog containing the filter array.
        """
        # Convert to list for deterministic ordering
        allowed_list = list(allowed_syscalls)
        n_allowed = len(allowed_list)

        # We'll allocate an array of sock_filter structs
        # Total filters: 1 (load) + n_allowed (jeq) + 1 (kill) + 1 (allow) = n_allowed + 3
        total_filters = n_allowed + 3
        filters = (sock_filter * total_filters)()

        # 0: Load syscall number (offset 0, word)
        #   BPF_LD | BPF_W | BPF_ABS
        filters[0].code = 0x24   # 0x24 = BPF_LD(0x00) | BPF_W(0x04) | BPF_ABS(0x20)
        filters[0].jt   = 0
        filters[0].jf   = 0
        filters[0].k    = 0      # offset 0

        # 1..n_allowed: JEQ for each allowed syscall
        for idx, sysnum in enumerate(allowed_list, start=1):
            # BPF_JEQ | BPF_K
            filters[idx].code = 0x15   # 0x15 = BPF_JEQ(0x10) | BPF_K(0x00)
            # jt = jump if true: skip to the ALLOW instruction
            # jf = jump if false: fall through to next check (0)
            # The ALLOW instruction is at index: 1 (load) + n_allowed (jeqs) + 1 (kill) + 1 (allow) = n_allowed + 3
            # Current instruction index = idx (0‑based in the filters array)
            # Next instruction index = idx + 1
            # Target index (ALLOW) = n_allowed + 3
            # Offset = target - (next) = (n_allowed + 3) - (idx + 1) = n_allowed + 2 - idx
            offset_to_allow = n_allowed + 2 - idx
            filters[idx].jt = offset_to_allow & 0xFF   # Ensure it fits in a byte (unsigned, but we treat as signed offset)
            filters[idx].jf = 0
            filters[idx].k  = sysnum

        # n_allowed + 1: KILL (default)
        kill_idx = n_allowed + 1
        filters[kill_idx].code = 0x06   # BPF_RET | BPF_K
        filters[kill_idx].jt   = 0
        filters[kill_idx].jf   = 0
        filters[kill_idx].k    = SECCOMP_RET_KILL_PROCESS

        # n_allowed + 2: ALLOW (should never be reached if any syscall matched, but safe)
        allow_idx = n_allowed + 2
        filters[allow_idx].code = 0x06   # BPF_RET | BPF_K
        filters[allow_idx].jt   = 0
        filters[allow_idx].jf   = 0
        filters[allow_idx].k    = SECCOMP_RET_ALLOW

        # Create the sock_fprog
        prog = sock_fprog()
        prog.len = ctypes.ushort(total_filters)
        prog.filter = ctypes.cast(filters, ctypes.POINTER(sock_filter))
        return prog

    # ----- Public API -----
    def apply_seccomp_filter(allowed_syscalls: FrozenSet[int]) -> None:
        """
        Install a seccomp‑BPF filter that only allows the given syscalls.
        Any other syscall will result in the process being killed.

        Args:
            allowed_syscalls: A frozenset of integers (syscall numbers) to allow.

        Raises:
            OSError: If prctl fails to attach the filter.
        """
        if not allowed_syscalls:
            logger.warning("apply_seccomp_filter called with empty syscall set"
                           "– this will block all syscalls (likely fatal)")

        try:
            prog = _build_seccomp_bpf(allowed_syscalls)
        except Exception as e:
            logger.error("Failed to build BPF program: %s", e)
            raise

        # Prepare arguments for prctl
        #   PR_SET_SECCOMP, SECCOMP_MODE_FILTER | SECCOMP_FLAG_TSYNC, &prog, sizeof(prog), 0
        arg2 = ctypes.ulong(SECCOMP_MODE_FILTER | SECCOMP_FILTER_FLAG_TSYNC)
        arg3 = ctypes.addressof(prog.filter)
        arg4 = ctypes.ulong(ctypes.sizeof(prog))
        arg5 = ctypes.ulong(0)

        # Call prctl
        ret = _libc.prctl(PR_SET_SECCOMP, arg2, arg3, arg4, arg5)
        if ret != 0:
            err = ctypes.get_errno()
            logger.error("prctl(PR_SET_SECCOMP) failed: errno=%s", err)
            raise OSError(errno.errorcode.get(err, err), f"prctl(PR_SET_SECCOMP) failed: {errno.errorcode.get(err, str(err))}")
        else:
            logger.debug("seccomp‑BPF filter applied successfully (allowing %d syscalls)", len(allowed_syscalls))

    def is_seccomp_available() -> bool:
        """
        Check if the current kernel supports seccomp‑BPF via prctl.
        Returns True if prctl(PR_GET_SECCOMP, ...) does not return ENOSYS.
        """
        # Try to get the current seccomp mode; if we get ENOSYS, the syscall is missing.
        mode = ctypes.c_int()
        ret = _libc.prctl(PR_GET_SECCOMP, ctypes.byref(mode), 0, 0, 0)
        if ret == 0:
            return True
        err = ctypes.get_errno()
        if err == errno.ENOSYS:
            return False
        # Some other error – assume not available to be safe
        logger.warning("prctl(PR_GET_SECCOMP) failed with errno=%s", err)
        return False

# Exported symbols
__all__ = [
    "apply_seccomp_filter",
    "is_seccomp_available",
    "ALLOWED_SYSCALLS_NAMES",
]

if __name__ == "__main__":
    # Simple self‑test when run directly
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if sys.platform.startswith('linux'):
        if is_seccomp_available():
            logger.info("seccomp‑BPF is available on this system")
            # Example: try to apply a minimal filter (just exit, read, write)
            # Note: This is for demonstration only – do not use in production without proper testing!
            try:
                # These numbers are x86_64; adjust for your architecture if needed
                test_allowed = frozenset([0, 1, 2, 60])  # read, write, close, exit
                apply_seccomp_filter(test_allowed)
                logger.info("Test seccomp filter applied (this process will now be restricted)")
            except Exception as e:
                logger.error("Failed to apply test seccomp filter: %s", e)
        else:
            logger.warning("seccomp‑BPF not available on this system")
    else:
        logger.info("Running on non‑Linux platform (%s); seccomp‑BPF skipped", sys.platform)