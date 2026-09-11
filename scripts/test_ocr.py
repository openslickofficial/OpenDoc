#!/usr/bin/env python3
"""
Test Suite for Snapdragon X NPU Document Assistant OCR.
Executes extract_text() against all 3 test documents:
1. printed_paragraph.png - Dense printed document paragraph.
2. form_document.png - Form-style document with structured fields.
3. skewed_document.png - Skewed/tilted scan testing automatic deskew & alignment.

Reports:
- Extracted text transcription
- Execution Provider used (QNNExecutionProvider on NPU vs CPUExecutionProvider fallback)
- Latency in milliseconds
- Skew angle corrected
"""

import os
import sys
import time

# Ensure project root is in python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Configure console for UTF-8
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.ocr_module import extract_text

# Terminal Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(title: str):
    print(f"\n{CYAN}{BOLD}{'=' * 75}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 75}{RESET}")


def run_ocr_test(image_path: str, test_label: str) -> dict:
    if not os.path.isfile(image_path):
        print(f"Error: Test image not found at {image_path}")
        return {"status": "FAIL", "error": "File not found"}

    file_size_kb = os.path.getsize(image_path) / 1024.0
    print(f"\n{BOLD}Document: {os.path.basename(image_path)} ({file_size_kb:.1f} KB){RESET}")
    print(f"Category: {test_label}")

    t0 = time.perf_counter()
    result = extract_text(image_path)
    total_time = (time.perf_counter() - t0) * 1000.0

    provider = result.get("provider_used", "UNKNOWN")
    latency = result.get("latency_ms", total_time)
    skew = result.get("skew_angle_corrected", 0.0)
    lines = result.get("lines_processed", 1)
    text = result.get("text", "").strip()

    # Provider highlighting
    if "QNN" in provider:
        provider_str = f"{GREEN}{BOLD}{provider} (Hexagon NPU Accelerated){RESET}"
    else:
        provider_str = f"{YELLOW}{BOLD}{provider} (CPU Dev Fallback){RESET}"

    print(f"  * Execution Provider : {provider_str}")
    print(f"  * Inference Latency  : {BOLD}{latency:.2f} ms{RESET}")
    print(f"  * Deskew Correction  : {skew:.2f} deg tilt compensated")
    print(f"  * Lines Processed    : {lines}")
    print(f"  * Recognized Characters: {len(text)}")
    print(f"\n{BOLD}--- Extracted Text Transcription ---{RESET}")
    if text:
        for line in text.splitlines():
            print(f"  | {line}")
    else:
        print("  | [Warning: No text transcribed]")
    print(f"{BOLD}{'-' * 36}{RESET}")

    return {
        "image": os.path.basename(image_path),
        "provider": provider,
        "latency_ms": latency,
        "skew_deg": skew,
        "lines": lines,
        "chars": len(text),
        "status": "PASS" if len(text) > 0 else "FAIL",
    }


def main():
    print_header("Snapdragon X Elite Document OCR Verification Pipeline")
    test_dir = os.path.join(PROJECT_ROOT, "test_images")

    test_cases = [
        ("printed_paragraph.png", "Dense Printed English Paragraph"),
        ("form_document.png", "Form Document with Labeled Key-Value Fields"),
        ("skewed_document.png", "Rotated Document (Deskew & Normalization Validation)"),
    ]

    results = []
    for filename, label in test_cases:
        path = os.path.join(test_dir, filename)
        res = run_ocr_test(path, label)
        results.append(res)

    # Print summary table
    print_header("OCR PIPELINE EXECUTION SUMMARY")
    print(f"{'Image Filename':<26} {'Provider':<24} {'Latency':<12} {'Deskew':<10} {'Status':<8}")
    print("-" * 75)
    for r in results:
        status_colored = f"{GREEN}PASS{RESET}" if r["status"] == "PASS" else f"\033[91mFAIL{RESET}"
        print(
            f"{r['image']:<26} "
            f"{r['provider']:<24} "
            f"{r['latency_ms']:>7.1f} ms   "
            f"{r['skew_deg']:>5.1f}°    "
            f"{status_colored}"
        )
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
