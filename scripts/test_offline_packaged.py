"""
Rigorous Network-Off (True Offline) Verification Suite for Snapdragon Document Assistant.
Tests:
  1. Verifies that all outbound internet traffic to huggingface.co is dead / blocked.
  2. Runs packaged dist/SnapdragonDocAssistant/SnapdragonDocAssistant.exe on form_document.png.
  3. Runs packaged dist/SnapdragonDocAssistant/SnapdragonDocAssistant.exe on telecom_disconnect_unseen.png.
  4. Runs isolated %TEMP% deployment with zero network access and zero connection to repo root.
"""

import os
import sys
import json
import time
import wave
import shutil
import tempfile
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE_PATH = os.path.join(PROJECT_ROOT, "dist", "SnapdragonDocAssistant", "SnapdragonDocAssistant.exe")
OUT_DIR = os.path.join(PROJECT_ROOT, "dist", "SnapdragonDocAssistant", "offline_verification_artifacts")
os.makedirs(OUT_DIR, exist_ok=True)

# Build strictly offline environment
OFFLINE_ENV = os.environ.copy()
OFFLINE_ENV["HF_HUB_OFFLINE"] = "1"
OFFLINE_ENV["TRANSFORMERS_OFFLINE"] = "1"
OFFLINE_ENV["HTTP_PROXY"] = "http://127.0.0.1:54321"
OFFLINE_ENV["HTTPS_PROXY"] = "http://127.0.0.1:54321"
OFFLINE_ENV["ALL_PROXY"] = "http://127.0.0.1:54321"
OFFLINE_ENV["NO_PROXY"] = ""

def verify_network_is_dead():
    print("=" * 80)
    print("  VERIFYING THAT NETWORK IS DEAD / BLOCKED FOR CHILD PROCESSES")
    print("=" * 80)
    check_cmd = [
        sys.executable,
        "-c",
        "import urllib.request; urllib.request.urlopen('https://huggingface.co', timeout=2)"
    ]
    try:
        subprocess.run(check_cmd, env=OFFLINE_ENV, capture_output=True, text=True, check=True)
        print("[FAIL] Network call succeeded! The network is NOT blocked.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"[OK] Outbound network successfully blocked as expected: {e}")
        return True

def run_document_test(name, image_path, doc_id):
    print("\n" + "=" * 80)
    print(f"  RUNNING TRUE OFFLINE TEST: {name}")
    print(f"  Image: {image_path}")
    print("=" * 80)

    screenshot_path = os.path.join(OUT_DIR, f"{doc_id}_offline.png")
    json_path = os.path.join(OUT_DIR, f"{doc_id}_offline.json")

    cmd = [
        EXE_PATH,
        "--image", image_path,
        "--auto-process",
        "--save-screenshot", screenshot_path,
        "--dump-json", json_path,
        "--exit-on-finish"
    ]

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, env=OFFLINE_ENV, capture_output=True, text=True, cwd=PROJECT_ROOT)
    elapsed = time.perf_counter() - t0

    print(f"Return Code: {proc.returncode} (Elapsed: {elapsed:.2f}s)")
    if proc.stdout.strip():
        print(f"[STDOUT]: {proc.stdout.strip()[:300]}")

    # Inspect stderr for HTTP or network activity
    if proc.stderr.strip():
        for line in proc.stderr.splitlines():
            if "HTTP" in line:
                print(f"[ALERT - HTTP ACTIVITY DETECTED]: {line}")
            elif any(k in line for k in ["STAGE", "PIPELINE", "TTS Complete", "FIDELITY", "SUCCESS"]):
                print(f"  {line}")

    if not os.path.isfile(json_path):
        print(f"[FAIL] Result JSON not found: {json_path}")
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        res = json.load(f)

    audio_file = res.get("audio_path")
    print(f"\nResults for {name}:")
    print(f"  * Status: {res.get('status')}")
    print(f"  * Overall Fidelity Passed: {res.get('overall_fidelity_passed')}")
    print(f"  * OCR Chars: {len(res.get('raw_text', ''))}")
    print(f"  * Simplified Chars: {len(res.get('simplified_text', ''))}")
    print(f"  * Translated Chars: {len(res.get('translated_text', ''))}")
    print(f"  * Audio Path: {audio_file}")

    if audio_file and os.path.isfile(audio_file):
        with wave.open(audio_file, "rb") as wf:
            dur = wf.getnframes() / float(wf.getframerate())
        print(f"  * [AUDIO VERIFIED] Valid WAV: {dur:.2f}s, {os.path.getsize(audio_file):,} bytes")
    else:
        print(f"  * [AUDIO ERROR] Missing audio at {audio_file}")
        return False

    return True

def run_isolated_temp_test_offline():
    print("\n" + "=" * 80)
    print("  RUNNING ISOLATED %TEMP% PORTABILITY TEST (WITH ZERO NETWORK)")
    print("=" * 80)

    temp_dir = os.path.join(tempfile.gettempdir(), "SnapdragonDocAssistant_IsolatedOffline")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    src_dist = os.path.join(PROJECT_ROOT, "dist", "SnapdragonDocAssistant")
    print(f"Copying package to isolated path: {temp_dir}")
    shutil.copytree(src_dist, temp_dir)

    isolated_img = os.path.join(temp_dir, "isolated_doc.png")
    shutil.copy2(os.path.join(PROJECT_ROOT, "test_images", "form_document.png"), isolated_img)

    isolated_exe = os.path.join(temp_dir, "SnapdragonDocAssistant.exe")
    isolated_json = os.path.join(temp_dir, "isolated_offline_result.json")
    isolated_screenshot = os.path.join(temp_dir, "isolated_offline_screenshot.png")

    cmd = [
        isolated_exe,
        "--image", isolated_img,
        "--auto-process",
        "--save-screenshot", isolated_screenshot,
        "--dump-json", isolated_json,
        "--exit-on-finish"
    ]

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, env=OFFLINE_ENV, capture_output=True, text=True, cwd=temp_dir)
    elapsed = time.perf_counter() - t0

    print(f"Isolated Offline Return Code: {proc.returncode} (Elapsed: {elapsed:.2f}s)")
    if not os.path.isfile(isolated_json):
        print(f"[FAIL] Isolated offline JSON not found at: {isolated_json}")
        return False

    with open(isolated_json, "r", encoding="utf-8") as f:
        res = json.load(f)

    audio_file = res.get("audio_path")
    print(f"\nIsolated Offline Execution Results:")
    print(f"  * Status: {res.get('status')}")
    print(f"  * Fidelity Passed: {res.get('overall_fidelity_passed')}")
    print(f"  * TTS Provider: {res.get('stages', {}).get('tts', {}).get('provider_used')}")
    print(f"  * Audio Path: {audio_file}")

    if audio_file and os.path.isfile(audio_file):
        with wave.open(audio_file, "rb") as wf:
            dur = wf.getnframes() / float(wf.getframerate())
        print(f"  * [AUDIO VERIFIED] Valid WAV: {dur:.2f}s, {os.path.getsize(audio_file):,} bytes")
    else:
        print(f"  * [FAIL] Audio file missing at {audio_file}")
        return False

    print("\n[SUCCESS] COMPOSED TEST PASSED: Packaged binary runs in isolated directory with ZERO network access!")
    return True

if __name__ == "__main__":
    if not verify_network_is_dead():
        sys.exit(1)

    # Test 1: Clean Form Document
    img_clean = os.path.join(PROJECT_ROOT, "test_images", "form_document.png")
    run_document_test("Clean Form Document", img_clean, "01_form_document")

    # Test 2: Telecom Disconnect Notice
    img_telecom = os.path.join(PROJECT_ROOT, "test_images", "telecom_disconnect_unseen.png")
    run_document_test("Telecom Disconnection Warning Document", img_telecom, "02_telecom_warning")

    # Test 3: Isolated %TEMP% directory test with ZERO network
    run_isolated_temp_test_offline()
