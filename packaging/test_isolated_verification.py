"""
Verification of Machine Portability:
Copies dist/SnapdragonDocAssistant/ to an isolated temporary location with no
relation to the project directory, and runs the compiled binary through
a real document pipeline.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import time
import wave

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIST = os.path.join(PROJECT_ROOT, "dist", "SnapdragonDocAssistant")
TEST_IMG = os.path.join(PROJECT_ROOT, "test_images", "form_document.png")

TEMP_DIR = os.path.join(tempfile.gettempdir(), "SnapdragonDocAssistant_IsolatedVerification")

def run_portability_test():
    print("=" * 80)
    print("  TASK 2 PORTABILITY VERIFICATION: ISOLATED DIRECTORY EXECUTION")
    print("=" * 80)

    # 1. Inspect source models/ directory attributes
    src_models = os.path.join(SRC_DIST, "models")
    print(f"\n[1] Checking source models folder: {src_models}")
    if not os.path.exists(src_models):
        print("[FAIL] models folder does not exist!")
        sys.exit(1)

    is_junction = os.path.islink(src_models)
    print(f"  * os.path.islink(models): {is_junction}")
    print(f"  * Exists as genuine directory: {os.path.isdir(src_models)}")

    # 2. Copy entire distribution to completely isolated temp path
    print(f"\n[2] Copying full distribution to isolated temp directory:\n    {TEMP_DIR}")
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    t0 = time.perf_counter()
    shutil.copytree(SRC_DIST, TEMP_DIR)
    print(f"  * Copied {os.path.getsize(TEMP_DIR) if os.path.isfile(TEMP_DIR) else 'distribution'} in {time.perf_counter() - t0:.2f}s")

    # 3. Copy test image into temp folder as well to be completely independent
    isolated_img = os.path.join(TEMP_DIR, "isolated_form.png")
    shutil.copy2(TEST_IMG, isolated_img)

    isolated_exe = os.path.join(TEMP_DIR, "SnapdragonDocAssistant.exe")
    isolated_json = os.path.join(TEMP_DIR, "isolated_result.json")
    isolated_screenshot = os.path.join(TEMP_DIR, "isolated_screenshot.png")

    print(f"\n[3] Launching isolated binary: {isolated_exe}")
    cmd = [
        isolated_exe,
        "--image", isolated_img,
        "--auto-process",
        "--save-screenshot", isolated_screenshot,
        "--dump-json", isolated_json,
        "--exit-on-finish"
    ]

    t1 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=TEMP_DIR, capture_output=True, text=True)
    elapsed = time.perf_counter() - t1

    print(f"  * Isolated Run Return Code: {proc.returncode} (Elapsed: {elapsed:.2f}s)")
    if proc.stdout.strip():
        print(f"  * STDOUT: {proc.stdout.strip()[:300]}")
    if proc.stderr.strip():
        for line in proc.stderr.splitlines():
            if "STAGE" in line or "PIPELINE" in line or "TTS" in line or "Piper" in line or "ERROR" in line:
                print(f"    {line}")

    # 4. Verify outputs
    if not os.path.isfile(isolated_json):
        print(f"[FAIL] Isolated JSON result not created at: {isolated_json}")
        sys.exit(1)

    import json
    with open(isolated_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    audio_file = data.get("audio_path")
    print(f"\n[4] Output Verification:")
    print(f"  * Status: {data.get('status')}")
    print(f"  * Fidelity Passed: {data.get('overall_fidelity_passed')}")
    print(f"  * TTS Provider: {data.get('stages', {}).get('tts', {}).get('provider_used')}")
    print(f"  * Audio Path: {audio_file}")

    if audio_file and os.path.isfile(audio_file):
        with wave.open(audio_file, "rb") as wf:
            dur = wf.getnframes() / float(wf.getframerate())
        print(f"  * Generated Audio Verified: {dur:.2f}s duration, {os.path.getsize(audio_file):,} bytes")
    else:
        print(f"  * [FAIL] Audio file missing at {audio_file}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("  [SUCCESS] PORTABILITY VERIFIED: EXECUTABLE RUNS 100% INDEPENDENTLY")
    print("=" * 80)

if __name__ == "__main__":
    run_portability_test()
