"""
Deliberate Failure-Path Testing Suite for Snapdragon Document Assistant Pipeline.
Explicitly tests all 3 error handling behaviors:
1. Short-circuit on blank/blurry/near-empty OCR image.
2. Loud failure on simplification/translation engine crash (no silent degradation).
3. Graceful degradation on TTS failure (text outputs preserved, audio omitted).
"""

import os
import sys
import time
import numpy as np
import cv2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import PipelineConfig
from src.pipeline import process_document
import src.pipeline as pipeline_mod

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def print_banner(title: str):
    print("\n" + "=" * 78)
    print(f"  {BOLD}{title}{RESET}")
    print("=" * 78)


def test_failure_path_1_blank_image() -> bool:
    """
    Test 1: OCR produces near-empty or garbage output.
    Pipeline must short-circuit immediately with 'status: failed'
    without wasting 30+ seconds on downstream LLM/TTS stages.
    """
    print_banner("TEST 1: OCR NEAR-EMPTY / BLANK IMAGE SHORT-CIRCUIT")
    blank_img_path = os.path.join(PROJECT_ROOT, "test_images", "blank_test_image.png")

    # Generate a completely blank white image (800x400)
    blank_mat = np.full((400, 800, 3), 255, dtype=np.uint8)
    cv2.imwrite(blank_img_path, blank_mat)
    print(f"Created synthetic blank image: {blank_img_path}")

    t0 = time.perf_counter()
    result = process_document(blank_img_path)
    elapsed_s = time.perf_counter() - t0

    print(f"Result Status : {result['status']}")
    print(f"Total Latency : {result['total_latency_ms']:.2f} ms ({elapsed_s:.2f} s)")
    print(f"Error Message : {result.get('error')}")
    print(f"Stages Run    : {list(result.get('stages', {}).keys())}")

    # Assertions
    assert result["status"] == "failed", f"Expected status 'failed', got {result['status']}"
    assert "simplify" not in result["stages"], "Simplification should NOT have run!"
    assert "translate" not in result["stages"], "Translation should NOT have run!"
    assert "tts" not in result["stages"], "TTS should NOT have run!"
    assert result["audio_path"] is None, "Audio path must be None"
    assert "insufficient readable text" in result["error"].lower() or "short-circuit" in result["error"].lower()

    print(f"{GREEN}{BOLD}[PASS]{RESET} Pipeline short-circuited in {elapsed_s:.2f}s without wasting downstream compute!")
    return True


def test_failure_path_2_simplification_crash() -> bool:
    """
    Test 2: Simplification engine crashes / fails.
    Pipeline must fail loudly with a clear error message rather than
    silently passing raw OCR or corrupted output downstream.
    """
    print_banner("TEST 2: SIMPLIFICATION CRASH / FAIL LOUDLY")
    test_img = os.path.join(PROJECT_ROOT, "test_images", "form_document.png")

    # Monkeypatch simplify_text to simulate an unexpected model crash
    original_simplify = pipeline_mod.simplify_text

    def mock_crashed_simplify(*args, **kwargs):
        raise RuntimeError("Hexagon NPU context memory allocation failed: Out of Memory (OOM)")

    pipeline_mod.simplify_text = mock_crashed_simplify

    try:
        t0 = time.perf_counter()
        result = process_document(test_img)
        elapsed_s = time.perf_counter() - t0

        print(f"Result Status : {result['status']}")
        print(f"Total Latency : {result['total_latency_ms']:.2f} ms ({elapsed_s:.2f} s)")
        print(f"Error Message : {result.get('error')}")
        print(f"Stages Run    : {list(result.get('stages', {}).keys())}")

        # Assertions
        assert result["status"] == "failed", f"Expected status 'failed', got {result['status']}"
        assert "translate" not in result["stages"], "Translation should NOT run if simplification crashed!"
        assert "tts" not in result["stages"], "TTS should NOT run if simplification crashed!"
        assert "Hexagon NPU context memory allocation failed" in result["error"]
        assert result["audio_path"] is None

        print(f"{GREEN}{BOLD}[PASS]{RESET} Pipeline failed loudly with clear exception trace, halting corrupted downstream propagation!")
        return True
    finally:
        pipeline_mod.simplify_text = original_simplify


def test_failure_path_3_tts_failure_graceful_degradation() -> bool:
    """
    Test 3: TTS synthesis engine fails (e.g. audio device missing, disk full).
    Pipeline must NOT discard upstream OCR, simplification, or translation!
    Must return 'status: partial_success' with text outputs intact and audio_path=None.
    """
    print_banner("TEST 3: TTS FAILURE GRACEFUL DEGRADATION (TEXT PRESERVATION)")
    test_img = os.path.join(PROJECT_ROOT, "test_images", "form_document.png")

    # Monkeypatch synthesize_speech to simulate a speech synthesizer failure
    original_synthesize = pipeline_mod.synthesize_speech

    def mock_crashed_tts(*args, **kwargs):
        raise OSError("Audio device or SAPI5 audio render channel unavailable")

    pipeline_mod.synthesize_speech = mock_crashed_tts

    try:
        t0 = time.perf_counter()
        result = process_document(test_img)
        elapsed_s = time.perf_counter() - t0

        print(f"Result Status      : {result['status']}")
        print(f"Total Latency      : {result['total_latency_ms']:.2f} ms ({elapsed_s:.2f} s)")
        print(f"Error Message      : {result.get('error')}")
        print(f"Stages Run         : {list(result.get('stages', {}).keys())}")
        print(f"Raw OCR Text       : {bool(result.get('raw_text'))} ({len(result.get('raw_text', ''))} chars)")
        print(f"Simplified English : {bool(result.get('simplified_text'))} ({len(result.get('simplified_text', ''))} chars)")
        print(f"Hindi Translation  : {bool(result.get('translated_text'))} ({len(result.get('translated_text', ''))} chars)")
        print(f"Audio Path         : {result.get('audio_path')}")

        # Assertions
        assert result["status"] == "partial_success", f"Expected 'partial_success', got {result['status']}"
        assert result["audio_path"] is None, "Audio path must be None on TTS failure"
        assert len(result["raw_text"]) > 10, "Raw OCR text must NOT be lost!"
        assert len(result["simplified_text"]) > 10, "Simplified English text must NOT be lost!"
        assert len(result["translated_text"]) > 10, "Translated Hindi text must NOT be lost!"
        assert "Audio device or SAPI5" in str(result["error"])

        print(f"{GREEN}{BOLD}[PASS]{RESET} Upstream OCR, simplification, and translation fully preserved despite TTS failure!")
        return True
    finally:
        pipeline_mod.synthesize_speech = original_synthesize


def main():
    print_banner("DELIBERATE PIPELINE ERROR HANDLING & FAILURE-PATH TEST SUITE")

    t1_pass = test_failure_path_1_blank_image()
    t2_pass = test_failure_path_2_simplification_crash()
    t3_pass = test_failure_path_3_tts_failure_graceful_degradation()

    print_banner("ERROR HANDLING TEST SUMMARY")
    print(f"1. OCR Near-Empty Short-Circuit        : {GREEN}PASS{RESET}" if t1_pass else f"1. OCR Short-Circuit: {RED}FAIL{RESET}")
    print(f"2. Simplification Crash (Fail Loudly)  : {GREEN}PASS{RESET}" if t2_pass else f"2. Simplification Crash: {RED}FAIL{RESET}")
    print(f"3. TTS Degradation (Text Preservation) : {GREEN}PASS{RESET}" if t3_pass else f"3. TTS Degradation: {RED}FAIL{RESET}")

    all_passed = t1_pass and t2_pass and t3_pass
    print("\nOVERALL ERROR SUITE STATUS: " + (f"{GREEN}{BOLD}ALL 3 TESTS PASSED{RESET}" if all_passed else f"{RED}{BOLD}FAILURES DETECTED{RESET}"))
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
