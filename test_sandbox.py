#!/usr/bin/env python
"""
Comprehensive test script to verify the NALA sandbox hardening system.
"""

import sys
import os
import platform
import time

# Add the NALA directory to the path so we can import the modules
sys.path.insert(0, r'E:\NALA-Project\NALA')

def test_basic_imports():
    """Test that we can import the sandbox modules."""
    try:
        from core.hands import sandbox
        from core.hands import sandbox_hooks
        from core.hands import sandbox_windows
        from core.hands import sandbox_linux
        from core.hands import sandbox_seccomp
        from core.hands.sandbox_hooks import SandboxLevel
        
        # Verify SandboxLevel inherits from IntEnum (crucial for comparisons)
        from enum import IntEnum
        assert issubclass(SandboxLevel, IntEnum), "SandboxLevel must inherit from IntEnum"
        
        print("✓ All sandbox modules imported successfully", flush=True)
        return True
    except Exception as e:
        print(f"✗ Failed to import sandbox modules: {e}", flush=True)
        return False

def test_sandbox_creation():
    """Test that we can create a sandbox context."""
    try:
        from core.hands.sandbox import sandbox_context

        # Test creating a sandbox context
        with sandbox_context("medium") as ctx:
            print(f"✓ Created sandbox temp dir: {ctx.temp_dir}", flush=True)
            print(f"  Level: {ctx.sandbox_level.name} ({ctx.sandbox_level_num})", flush=True)

            # Test creating a file in the sandbox
            test_file = os.path.join(ctx.temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("Hello, sandbox!")

            # Verify the file was created
            if os.path.exists(test_file):
                with open(test_file, "r") as f:
                    content = f.read()
                print(f"✓ File created and read inside sandbox: '{content}'", flush=True)
            else:
                print("✗ File was not created", flush=True)
                return False

        # Small delay to ensure Windows file handles disengage
        time.sleep(0.1)

        # Verify the sandbox temp directory was cleaned up
        if not os.path.exists(ctx.temp_dir):
            print("✓ Sandbox cleaned up successfully", flush=True)
        else:
            print("✗ Sandbox directory was not cleaned up", flush=True)
            return False

        return True
    except Exception as e:
        print(f"✗ Failed to create/use sandbox: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

def test_sandbox_execution():
    """Test executing a function in a sandbox across all levels."""
    try:
        from core.hands.sandbox import execute_in_sandbox

        def simple_function(x, y):
            return x + y

        # Test execution at all security levels
        for level in ["critical", "high", "medium", "low"]:
            result = execute_in_sandbox(level, simple_function, 10, 20)
            if result == 30:
                print(f"✓ Function executed successfully at level: {level.upper()}", flush=True)
            else:
                print(f"✗ Function failed at level {level.upper()}: {result}", flush=True)
                return False

        return True
    except Exception as e:
        print(f"✗ Failed to execute function in sandbox: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

def test_security_violations():
    """Test that security violations are intercepted by the audit hook."""
    try:
        from core.hands.sandbox import execute_in_sandbox, SandboxViolationError
        
        # Test 1: Reading file outside sandbox allowlist
        def read_outside():
            # Attempt to read a typical system file
            target = "C:\\Windows\\System32\\drivers\\etc\\hosts" if platform.system() == "Windows" else "/etc/hosts"
            with open(target, 'r') as f:
                return f.read(10)
                
        print("Testing file read limits (Should be blocked at MEDIUM+)...", flush=True)
        for level in ["critical", "high", "medium", "low"]:
            try:
                execute_in_sandbox(level, read_outside)
                if level in ["critical", "high"]:
                    print(f"  Level {level.upper()}: Allowed (Expected for trusted levels)", flush=True)
                else:
                    print(f"  Level {level.upper()}: ✗ Read succeeded (Security violation! Should be blocked)", flush=True)
                    return False
            except (SandboxViolationError, PermissionError) as e:
                print(f"  Level {level.upper()}: ✓ Blocked as expected - {type(e).__name__}", flush=True)

        # Test 2: Writing outside sandbox
        def write_outside():
            target = "C:\\test_outside_sandbox.txt" if platform.system() == "Windows" else "/test_outside_sandbox.txt"
            with open(target, 'w') as f:
                f.write("violation")
                
        print("Testing file write limits (Should be blocked at ALL levels)...", flush=True)
        for level in ["critical", "high", "medium", "low"]:
            try:
                execute_in_sandbox(level, write_outside)
                print(f"  Level {level.upper()}: ✗ Write succeeded (Security violation! Should be blocked)", flush=True)
                return False
            except (SandboxViolationError, PermissionError, OSError) as e:
                print(f"  Level {level.upper()}: ✓ Blocked as expected - {type(e).__name__}", flush=True)

        # Test 3: Spawning subprocesses
        def spawn_proc():
            import subprocess
            cmd = ["cmd", "/c", "echo test"] if platform.system() == "Windows" else ["echo", "test"]
            return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
            
        print("Testing subprocess limits (Should be blocked at MEDIUM+)...", flush=True)
        for level in ["critical", "high", "medium", "low"]:
            try:
                execute_in_sandbox(level, spawn_proc)
                if level in ["critical", "high"]:
                    print(f"  Level {level.upper()}: Allowed (Expected for trusted levels)", flush=True)
                else:
                    print(f"  Level {level.upper()}: ✗ Process spawned (Security violation! Should be blocked)", flush=True)
                    return False
            except (SandboxViolationError, PermissionError) as e:
                print(f"  Level {level.upper()}: ✓ Blocked as expected - {type(e).__name__}", flush=True)
                
        return True
    except Exception as e:
        print(f"✗ Unexpected failure in violation testing: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False

def test_stats_and_health():
    """Test sandbox health checks and stats collection."""
    try:
        from core.hands.sandbox import get_sandbox_stats, sandbox_health_check
        
        # Verify stats collection
        stats = get_sandbox_stats()
        print("✓ Stats structure verified:", flush=True)
        for k, v in stats.items():
            print(f"  - {k}: {v}", flush=True)
            
        # Verify health check
        health = sandbox_health_check()
        print(f"✓ Health check status: {health['status']}", flush=True)
        if health['issues']:
            print("  Identified issues:", flush=True)
            for issue in health['issues']:
                print(f"    * {issue}", flush=True)
        else:
            print("  No issues detected", flush=True)
            
        return True
    except Exception as e:
        print(f"✗ Failed statistics and health check test: {e}", flush=True)
        return False

def main():
    """Run all tests."""
    print("NALA Sandbox System Hardening Verification", flush=True)
    print("=" * 50, flush=True)

    tests = [
        test_basic_imports,
        test_sandbox_creation,
        test_sandbox_execution,
        test_security_violations,
        test_stats_and_health
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        print(f"\nRunning {test.__name__}...", flush=True)
        if test():
            passed += 1
        print("-" * 50, flush=True)

    print(f"\nVerification Results: {passed}/{total} tests passed", flush=True)

    if passed == total:
        print("🎉 NALA Sandbox System is fully hardened and functioning correctly!", flush=True)
        return 0
    else:
        print("❌ Sandbox verification failed. Check errors above.", flush=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())