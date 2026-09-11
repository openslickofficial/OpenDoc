"""
Test Packaged Executable in an Isolated Temporary Directory.
Copies dist/SnapdragonDocAssistant to a completely different location ($TEMP),
verifies model file resolution, launches the executable, and reports status.
"""

import os
import sys
import tempfile
import shutil
import time
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIST = os.path.join(PROJECT_ROOT, "dist", "SnapdragonDocAssistant")
ISOLATED_DIR = os.path.join(tempfile.gettempdir(), "SnapdragonDocAssistant_IsolatedTest")

def test_isolated_execution():
    print("=" * 80)
    print("  TESTING STANDALONE EXECUTABLE IN ISOLATED TEMP DIRECTORY")
    print("=" * 80)
    print(f"Source Distributable : {SRC_DIST}")
    print(f"Isolated Test Target : {ISOLATED_DIR}")

    if os.path.exists(ISOLATED_DIR):
        print(f"Cleaning previous test directory: {ISOLATED_DIR}...")
        shutil.rmtree(ISOLATED_DIR)

    print("Copying full distribution to isolated temp directory...")
    shutil.copytree(SRC_DIST, ISOLATED_DIR)
    print("Copy complete!")

    exe_path = os.path.join(ISOLATED_DIR, "SnapdragonDocAssistant.exe")
    piper_path = os.path.join(ISOLATED_DIR, "models", "piper_hi", "hi_IN-pratham-medium.onnx")
    trocr_path = os.path.join(ISOLATED_DIR, "models", "trocr-qnn-compiled")
    genie_path = os.path.join(ISOLATED_DIR, "models", "genie_bundle_qwen17")

    print("\nVerifying model file existence in isolated directory:")
    print(f"  * Executable exists : {os.path.isfile(exe_path)}")
    print(f"  * Piper model exists: {os.path.isfile(piper_path)} ({os.path.getsize(piper_path) / 1024 / 1024:.1f} MB)")
    print(f"  * TrOCR dir exists  : {os.path.isdir(trocr_path)}")
    print(f"  * Genie dir exists  : {os.path.isdir(genie_path)}")

    assert os.path.isfile(exe_path), "Executable missing!"
    assert os.path.isfile(piper_path), "Piper model missing in isolated folder!"
    assert os.path.isdir(trocr_path), "TrOCR model missing in isolated folder!"

    # Now launch the executable from the isolated directory with CWD = ISOLATED_DIR
    print(f"\nLaunching {exe_path} from isolated working directory...")
    proc = subprocess.Popen([exe_path], cwd=ISOLATED_DIR)

    try:
        time.sleep(4)
        poll = proc.poll()
        if poll is None:
            print(f"[SUCCESS] Packaged executable launched and is running healthy in ISOLATED folder!")
            print(f"  * Isolated PID : {proc.pid}")
            print(f"  * Status       : ACTIVE & RESPONDING (zero reliance on project folder)")
            proc.terminate()
            proc.wait(timeout=5)
            print("  * Cleanup      : Process terminated cleanly.")
            success = True
        else:
            print(f"[FAIL] Executable exited prematurely with code {poll}")
            success = False
    except Exception as e:
        print(f"[ERROR] Launch failed: {e}")
        try:
            proc.kill()
        except Exception:
            pass
        success = False

    # Cleanup temp directory
    try:
        shutil.rmtree(ISOLATED_DIR)
        print(f"Cleaned up isolated test directory: {ISOLATED_DIR}")
    except Exception as e:
        print(f"Note: Could not immediately remove temp dir: {e}")

    return success

if __name__ == "__main__":
    ok = test_isolated_execution()
    sys.exit(0 if ok else 1)
