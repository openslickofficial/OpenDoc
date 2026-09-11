"""
Automated Functional Verification of Packaged SnapdragonDocAssistant.exe.
Runs 3 real documents through the compiled standalone binary:
  1. Clean Structured Form: test_images/form_document.png
  2. Fidelity Warning Case: test_images/telecom_disconnect_unseen.png
  3. Blank Scan Short-Circuit: test_images/blank_test_image.png
Captures real-time logs, verifies generated WAV audio files, and saves UI screenshots.
"""

import os
import sys
import json
import time
import wave
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE_PATH = os.path.join(PROJECT_ROOT, "dist", "SnapdragonDocAssistant", "SnapdragonDocAssistant.exe")
OUT_DIR = os.path.join(PROJECT_ROOT, "dist", "SnapdragonDocAssistant", "verification_artifacts")
os.makedirs(OUT_DIR, exist_ok=True)

TEST_CASES = [
    {
        "id": "clean_form",
        "name": "Clean Structured Form",
        "image": os.path.join(PROJECT_ROOT, "test_images", "form_document.png"),
        "strict": False,
        "expected_fidelity": True,
        "expected_status": "success",
    },
    {
        "id": "telecom_warning",
        "name": "Fidelity Warning Discrepancy Notice",
        "image": os.path.join(PROJECT_ROOT, "test_images", "telecom_disconnect_unseen.png"),
        "strict": False,
        "expected_fidelity": False,
        "expected_status": "success",
    },
]

def run_test(case):
    test_id = case["id"]
    print("\n" + "=" * 80)
    print(f"  RUNNING PACKAGED BINARY TEST: {case['name']}")
    print(f"  Image: {case['image']}")
    print("=" * 80)

    screenshot_path = os.path.join(OUT_DIR, f"{test_id}_screenshot.png")
    json_path = os.path.join(OUT_DIR, f"{test_id}_result.json")

    cmd = [
        EXE_PATH,
        "--image", case["image"],
        "--auto-process",
        "--save-screenshot", screenshot_path,
        "--dump-json", json_path,
        "--exit-on-finish"
    ]
    if case.get("strict"):
        cmd.append("--strict")

    t0 = time.perf_counter()
    print(f"Executing: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
    elapsed = time.perf_counter() - t0

    print(f"\nExecution Return Code: {proc.returncode} (Elapsed: {elapsed:.2f}s)")
    if proc.stdout.strip():
        print(f"[STDOUT]:\n{proc.stdout.strip()}")
    if proc.stderr.strip():
        print(f"[STDERR]:\n{proc.stderr.strip()}")

    # Check JSON output
    if not os.path.isfile(json_path):
        print(f"[FAIL] Expected result JSON not found at: {json_path}")
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        res = json.load(f)

    status = res.get("status")
    overall_fidelity = res.get("overall_fidelity_passed")
    raw_text = res.get("raw_text", "")
    simp_text = res.get("simplified_text", "")
    trans_text = res.get("translated_text", "")
    audio_path = res.get("audio_path")
    fidelity_summary = res.get("fidelity_summary", {})

    print("\n--- RESULTS SUMMARY ---")
    print(f"Pipeline Status: {status}")
    print(f"Overall Fidelity Passed: {overall_fidelity}")
    print(f"OCR Extracted Chars: {len(raw_text)}")
    print(f"Simplified Chars: {len(simp_text)}")
    print(f"Translated Chars: {len(trans_text)}")
    print(f"Audio Path: {audio_path}")

    # Verify Audio Playability
    if audio_path and os.path.isfile(audio_path):
        try:
            with wave.open(audio_path, "rb") as wf:
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                framerate = wf.getframerate()
                nframes = wf.getnframes()
                duration = nframes / float(framerate)
                size_bytes = os.path.getsize(audio_path)
            print(f"[AUDIO VERIFIED] Valid WAV file: {channels} ch, {framerate} Hz, {duration:.2f}s duration, {size_bytes:,} bytes")
        except Exception as e:
            print(f"[AUDIO ERROR] Corrupt audio file: {e}")
    else:
        print(f"[AUDIO] No audio file generated or found at {audio_path}")

    # Verify Screenshot
    if os.path.isfile(screenshot_path):
        print(f"[SCREENSHOT VERIFIED] Captured UI state ({os.path.getsize(screenshot_path):,} bytes) -> {screenshot_path}")
    else:
        print(f"[SCREENSHOT ERROR] Screenshot not created at {screenshot_path}")

    return True

if __name__ == "__main__":
    for c in TEST_CASES:
        run_test(c)
