"""
Linux/macOS Namespace Isolation for NALA Sandbox Layer
======================================================

Implements Phase 2B: Linux/macOS namespace isolation via ctypes.
Provides true OS-level isolation using clone namespaces and chroot.

Based on the NALA sandbox hardening plan, sections 3.3.1-3.3.2.
"""

import ctypes
import ctypes.util
import errno
import os
import sys
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Check platform support for Linux namespaces
if not sys.platform.startswith('linux'):
    logger.warning("sandbox_linux.py is intended for Linux only; noop on %s", sys.platform)

    def _apply_linux_namespaces(temp_dir: str, python_lib_path: str) -> None:
        """Stub for non-Linux platforms."""
        logger.warning("Linux namespaces not available on %s", sys.platform)
        return
else:
    # Linux Namespace Clone Flags (from sched.h)
    CLONE_NEWNS   = 0x00020000   # Mount namespace
    CLONE_NEWNET  = 0x40000000   # Network namespace
    CLONE_NEWPID  = 0x20000000   # PID namespace
    CLONE_NEWIPC  = 0x08000000   # IPC namespace
    CLONE_NEWUTS  = 0x04000000   # UTS namespace
    CLONE_NEWUSER = 0x10000000   # User namespace (not used in the base plan but often needed for unprivileged)

    # Combined flag for ISOLATED sandbox (as per the hardening plan)
    NALA_ISOLATED_NS_FLAGS = (
        CLONE_NEWNS   |
        CLONE_NEWNET  |
        CLONE_NEWPID  |
        CLONE_NEWIPC  |
        CLONE_NEWUTS
    )

    # Libc bindings
    _libc_name = ctypes.util.find_library("c")
    if not _libc_name:
        raise OSError("Cannot find libc")
    _libc = ctypes.CDLL(_libc_name, use_errno=True)

    # int unshare(int flags)
    _libc.unshare.restype  = ctypes.c_int
    _libc.unshare.argtypes = [ctypes.c_int]

    # int chroot(const char *path)
    _libc.chroot.restype  = ctypes.c_int
    _libc.chroot.argtypes = [ctypes.c_char_p]

    # int mount(const char *source, const char *target, const char *filesystemtype,
    #           unsigned long mountflags, const void *data)
    _libc.mount.restype  = ctypes.c_int
    _libc.mount.argtypes = [
        ctypes.c_char_p, ctypes.c_char_p,
        ctypes.c_char_p, ctypes.c_ulong,
        ctypes.c_void_p
    ]

    # Mount flags
    MS_BIND    = 4096
    MS_RDONLY  = 1
    MS_NOSUID  = 2
    MS_NOEXEC  = 8
    MS_NODEV   = 4

    def _apply_linux_namespaces(temp_dir: str, python_lib_path: str) -> None:
        """
        Use unshare(2) to detach into isolated namespaces.
        Then bind-mount only necessary read-only libraries into the temp jail.
        Finally, chroot into temp_dir.

        Requires Linux kernel >= 3.8. Falls back gracefully if EPERM.

        Args:
            temp_dir: Path to the sandbox temporary directory (will be chrooted to).
            python_lib_path: Path to the Python standard library directory (for bind-mount).

        Raises:
            PermissionError: If unshare fails with EPERM (insufficient privileges).
            OSError: For other system call failures.
        """
        # Step 1: Detach into new namespaces
        ret = _libc.unshare(NALA_ISOLATED_NS_FLAGS)
        if ret != 0:
            err = ctypes.get_errno()
            if err == errno.EPERM:
                raise PermissionError(
                    "unshare(2) failed: EPERM. Degrading to RESTRICTED (audit hook only). "
                    "Run with CAP_SYS_ADMIN or enable user namespaces for full isolation."
                )
            raise OSError(f"unshare(2) failed: errno={err}")

        # Step 2: Bind-mount Python standard library into the jail as read-only
        jail_lib = os.path.join(temp_dir, "lib")
        try:
            os.makedirs(jail_lib, exist_ok=True)
        except OSError as e:
            raise OSError(f"Failed to create jail lib directory: {e}")

        src = python_lib_path.encode('utf-8')
        dest = os.path.join(jail_lib, "").encode('utf-8')
        ret = _libc.mount(
            src,
            dest,
            b"none",
            MS_BIND | MS_RDONLY | MS_NOSUID | MS_NODEV,
            None
        )
        if ret != 0:
            err = ctypes.get_errno()
            raise OSError(f"mount(bind) for stdlib failed: errno={err}")

        # Step 3: Bind-mount essential /dev nodes
        for dev in ("null", "urandom", "zero"):
            src_dev = f"/dev/{dev}".encode('utf-8')
            dest_dir = os.path.join(temp_dir, "dev")
            try:
                os.makedirs(dest_dir, exist_ok=True)
            except OSError as e:
                raise OSError(f"Failed to create dev directory: {e}")
            dest_dev = os.path.join(dest_dir, dev).encode('utf-8')
            try:
                open(dest_dev.decode('utf-8'), 'a').close()
            except OSError as e:
                raise OSError(f"Failed to create {dev} device node: {e}")

            ret = _libc.mount(
                src_dev,
                dest_dev,
                b"none",
                MS_BIND | MS_NOSUID,
                None
            )
            if ret != 0:
                err = ctypes.get_errno()
                raise OSError(f"mount(bind) for /dev/{dev} failed: errno={err}")

        # Step 4: chroot into the jail
        ret = _libc.chroot(temp_dir.encode('utf-8'))
        if ret != 0:
            err = ctypes.get_errno()
            raise OSError(f"chroot(2) failed: errno={err}")

        # Step 5: Change the current working directory to the new root
        try:
            os.chdir("/")
        except OSError as e:
            raise OSError(f"Failed to change directory to jail root: {e}")