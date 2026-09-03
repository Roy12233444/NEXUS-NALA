"""
Windows Job Object Sandbox for NALA Transcendent Reasoning Engine
================================================================

Implements Phase 2A hardening via Windows Job Objects via ctypes for kernel-level
resource enforcement on Windows platforms.
"""

import logging
import ctypes
import ctypes.wintypes as wintypes
from typing import Optional, Any

logger = logging.getLogger(__name__)


def _apply_windows_job_object(context: Any) -> Optional[Any]:
    """
    Apply Windows Job Object resource limits to the current process.
    Returns the job handle on success, None on failure.

    This method is only called on Windows platforms.

    Args:
        context: SandboxContext object containing sandbox level and configuration

    Returns:
        Windows Job Object handle or None if failed
    """
    if not hasattr(context, 'sandbox_level_num'):
        logger.warning("Invalid context passed to _apply_windows_job_object")
        return None

    # --- Win32 Constants ---
    JOB_OBJECT_LIMIT_PROCESS_TIME = 0x00000002
    JOB_OBJECT_LIMIT_JOB_TIME = 0x00000004
    JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
    JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION = 0x00000400

    JobObjectExtendedLimitInformation = 9  # info class for SetInformationJobObject

    # --- C‑structure definitions ---
    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount",  ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount",   ctypes.c_uint64),
            ("WriteTransferCount",  ctypes.c_uint64),
            ("OtherTransferCount",  ctypes.c_uint64),
        ]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),   # 100‑nanosecond units
            ("PerJobUserTimeLimit",     ctypes.c_int64),
            ("LimitFlags",             ctypes.c_uint32),
            ("MinimumWorkingSetSize",  ctypes.c_size_t),
            ("MaximumWorkingSetSize",  ctypes.c_size_t),
            ("ActiveProcessLimit",     ctypes.c_uint32),
            ("Affinity",               ctypes.c_size_t),
            ("PriorityClass",          ctypes.c_uint32),
            ("SchedulingClass",        ctypes.c_uint32),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo",                IO_COUNTERS),
            ("ProcessMemoryLimit",    ctypes.c_size_t),
            ("JobMemoryLimit",        ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed",     ctypes.c_size_t),
        ]

    # --- Load kernel32.dll and bind functions ---
    try:
        _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except Exception as e:
        logger.error(f"Failed to load kernel32.dll: {e}")
        return None

    # HANDLE CreateJobObjectW(LPSECURITY_ATTRIBUTES, LPCWSTR)
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.CreateJobObjectW.argtypes = [
        ctypes.c_void_p,   # lpJobAttributes (NULL = default security)
        wintypes.LPCWSTR,  # lpName (NULL = anonymous)
    ]

    # BOOL AssignProcessToJobObject(HANDLE, HANDLE)
    _kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    _kernel32.AssignProcessToJobObject.argtypes = [
        wintypes.HANDLE,  # hJob
        wintypes.HANDLE,  # hProcess
    ]

    # BOOL SetInformationJobObject(HANDLE, JOBOBJECTINFOCLASS, LPVOID, DWORD)
    _kernel32.SetInformationJobObject.restype = wintypes.BOOL
    _kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,   # hJob
        ctypes.c_int,      # JobObjectInformationClass
        ctypes.c_void_p,   # lpJobObjectInformation
        wintypes.DWORD,    # cbJobObjectInformationLength
    ]

    # HANDLE GetCurrentProcess()
    _kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    _kernel32.GetCurrentProcess.argtypes = []

    # --- Create the Job Object ---
    job_handle = _kernel32.CreateJobObjectW(None, None)
    if not job_handle:
        err = ctypes.get_last_error()
        logger.error(f"CreateJobObjectW failed: error={err}")
        return None

    try:
        # Prepare the extended limit information
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        # CPU limit: convert seconds to 100‑nanosecond intervals
        # Using default_cpu_limit from context if available, otherwise 5.0 seconds
        cpu_limit = getattr(context, 'default_cpu_limit', 5.0)
        cpu_limit_100ns = int(cpu_limit * 10_000_000)
        info.BasicLimitInformation.PerProcessUserTimeLimit = cpu_limit_100ns
        info.BasicLimitInformation.PerJobUserTimeLimit = cpu_limit_100ns  # same as per process
        # Active process limit: allow more for BASIC, none for RESTRICTED/ISOLATED
        max_procs = 4 if context.sandbox_level_num == 1 else 1
        info.BasicLimitInformation.ActiveProcessLimit = max_procs
        # Build limit flags
        limit_flags = (
            JOB_OBJECT_LIMIT_PROCESS_TIME |
            JOB_OBJECT_LIMIT_JOB_TIME |
            JOB_OBJECT_LIMIT_ACTIVE_PROCESS |
            JOB_OBJECT_LIMIT_JOB_MEMORY |
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE |
            JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
        )
        info.BasicLimitInformation.LimitFlags = limit_flags
        # Job memory limit
        # Using default_memory_limit from context if available, otherwise 512 MB
        memory_limit = getattr(context, 'default_memory_limit', 512 * 1024 * 1024)
        info.JobMemoryLimit = memory_limit

        # Apply the limits to the job object
        ok = _kernel32.SetInformationJobObject(
            job_handle,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info)
        )
        if not ok:
            err = ctypes.get_last_error()
            raise OSError(f"SetInformationJobObject failed: error={err}")

        # Assign the current process to the job
        proc_handle = _kernel32.GetCurrentProcess()
        ok = _kernel32.AssignProcessToJobObject(job_handle, proc_handle)
        if not ok:
            err = ctypes.get_last_error()
            raise OSError(f"AssignProcessToJobObject failed: error={err}")

        return job_handle

    except Exception as e:
        logger.error(f"Windows Job Object setup failed: {e}")
        # Clean up the job handle if we created one
        if job_handle:
            try:
                _kernel32.CloseHandle(job_handle)
            except Exception:
                pass
        return None


# For backward compatibility and ease of import
__all__ = [
    "_apply_windows_job_object"
]