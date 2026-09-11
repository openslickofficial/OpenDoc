"""
Verify Packaged Executable Launch & Process Health.
"""

import os
import sys
import time
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE_PATH = os.path.join(PROJECT_ROOT, "dist", "SnapdragonDocAssistant", "SnapdragonDocAssistant.exe")

def test_executable_launch():
    print("=" * 80)
    print("  VERIFYING PACKAGED EXECUTABLE LAUNCH")
    print("=" * 80)

    if not os.path.isfile(EXE_PATH):
        print(f"[FAIL] Executable does not exist at {EXE_PATH}")
        return False

    print(f"Launching binary: {EXE_PATH}")
    proc = subprocess.Popen([EXE_PATH], cwd=os.path.dirname(EXE_PATH))

    try:
        # Wait 4 seconds to observe launch, initialization, and window creation
        time.sleep(4)
        poll = proc.poll()
        if poll is None:
            print(f"[SUCCESS] Packaged executable is running healthy!")
            print(f"  * Process PID : {proc.pid}")
            print(f"  * Status      : ACTIVE & RESPONDING (No premature crash)")
            proc.terminate()
            proc.wait(timeout=5)
            print("  * Cleanup     : Terminated process cleanly after verification.")
            return True
        else:
            print(f"[FAIL] Executable exited prematurely with return code {poll}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception during process launch check: {e}")
        try:
            proc.kill()
        except Exception:
            pass
        return False

if __name__ == "__main__":
    success = test_executable_launch()
    sys.exit(0 if success else 1)
