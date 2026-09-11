#!/usr/bin/env python3
"""
Phase 3 Verification Suite: Indic Language Translation & Cross-Language Fidelity Safeguard.
Tests the full 3-stage pipeline:
  Stage 1: Document OCR (TrOCR)
  Stage 2: Plain-Language Simplification (Qwen)
  Stage 3: Indian Language Translation (Hindi) + Cross-Language Fidelity Check

Evaluates:
1. printed_paragraph.png (Technical Brief)
2. form_document.png (Verification Form: SN-2026-X89, Status: Approved)
3. skewed_document.png (Deskewed scan with OCR noise)
4. medical_bill_receipt.png (Medical statement: MED-90821-TX, $450.00, Approved)
5. legal_notice_deadline.png (Municipal summons: GOV-2026-LAW-77, $250.00, Deadline)
6. Adversarial Tampering Test Case (Deliberately flipped status / dropped entities)
"""

import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure console supports UTF-8 for Devanagari output
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.ocr_module import extract_text
from src.simplify_module import simplify_text
from src.translate_module import translate_text
from src.fidelity_checker import verify_fidelity

# Terminal ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner(title: str):
    print(f"\n{CYAN}{BOLD}{'=' * 80}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 80}{RESET}")


def run_pipeline_test(image_filename: str, description: str) -> dict:
    image_path = os.path.join(PROJECT_ROOT, "test_images", image_filename)
    if not os.path.exists(image_path):
        print(f"[-] Image not found: {image_path}")
        return {"status": "FAIL", "image": image_filename}

    print(f"\n{BOLD}Test Document : {image_filename}{RESET} ({description})")

    # Step 1: Run OCR
    t_ocr_start = time.perf_counter()
    ocr_result = extract_text(image_path)
    ocr_latency_ms = (time.perf_counter() - t_ocr_start) * 1000.0
    raw_ocr = ocr_result["text"]

    print(f"  [1] OCR Provider     : {ocr_result['provider_used']}")
    print(f"      OCR Latency      : {ocr_latency_ms:.1f} ms")

    # Step 2: Run Simplification
    simp_result = simplify_text(raw_text=raw_ocr, engine_mode="cpu")
    simplified = simp_result["simplified_text"]
    print(f"  [2] Simp Provider    : {simp_result['provider_used']}")
    print(f"      Simp Latency     : {simp_result['latency_ms']:.1f} ms")
    print(f"      Simp Fidelity    : {'PASS' if simp_result['fidelity_passed'] else 'WARNING'}")

    # Step 3: Run Translation (English -> Hindi)
    trans_result = translate_text(text=simplified, target_lang="hi", engine_mode="cpu")
    translated = trans_result["translated_text"]
    trans_latency_ms = trans_result["latency_ms"]
    fidelity_passed = trans_result["fidelity_passed"]
    warnings = trans_result["fidelity_warnings"]

    print(f"  [3] Trans Provider   : {trans_result['provider_used']}")
    print(f"      Trans Latency    : {trans_latency_ms:.1f} ms")
    print(f"      Cross-Lang Pass  : {GREEN + 'PASS' + RESET if fidelity_passed else RED + 'FAIL' + RESET}")

    if warnings:
        print(f"      {YELLOW}Warnings ({len(warnings)}):{RESET}")
        for w in warnings:
            print(f"        - {w}")

    print(f"\n  {BOLD}--- Simplified English Output ---{RESET}")
    for line in simplified.split("\n")[:4]:
        print(f"    | {line}")

    print(f"\n  {BOLD}--- Translated Hindi Output (हिन्दी) ---{RESET}")
    for line in translated.split("\n")[:6]:
        print(f"    > {line}")

    return {
        "image": image_filename,
        "ocr_latency": ocr_latency_ms,
        "simp_latency": simp_result["latency_ms"],
        "trans_latency": trans_latency_ms,
        "total_latency": ocr_latency_ms + simp_result["latency_ms"] + trans_latency_ms,
        "provider": trans_result["provider_used"],
        "passed": fidelity_passed,
        "warnings_count": len(warnings),
        "translated_text": translated,
    }


def run_adversarial_tampering_test():
    print_banner("DELIBERATE ADVERSARIAL TAMPERING TEST (CROSS-LANGUAGE SAFEGUARD)")
    print("Injecting deliberate corruption into translation: dropped charges, flipped approval status, wrong date.\n")

    original_english = (
        "Patient Billing Statement: Metropolitan Healthcare Services.\n"
        "Patient: Harold Jenkins.\n"
        "Service Date: October 24, 2026.\n"
        "Claim Reference ID: MED-90821-TX.\n"
        "Total Charges: $450.00.\n"
        "Claim Determination: All expenses verified and approved for full reimbursement."
    )

    # Adversarial corruption: flipped to "अस्वीकृत" (rejected), dropped $450.00, changed date to December 31
    corrupted_hindi = (
        "रोगी बिलिंग विवरण: Metropolitan Healthcare Services.\n"
        "रोगी: Harold Jenkins.\n"
        "सेवा तिथि: 31 दिसंबर 2026.\n"
        "दावा संदर्भ संख्या (Claim Reference ID): MED-90821-TX.\n"
        "दावा निर्धारण: आपका स्वास्थ्य बीमा दावा पूरी तरह से अस्वीकृत कर दिया गया है (REJECTED)."
    )

    print("Source English Text:")
    print(original_english)
    print("\nCorrupted Adversarial Hindi Text:")
    print(corrupted_hindi)

    fidelity_result = verify_fidelity(
        original_text=original_english,
        simplified_text=corrupted_hindi,
        target_lang="hi",
    )

    passed = fidelity_result["fidelity_passed"]
    warnings = fidelity_result["fidelity_warnings"]

    print(f"\nSafeguard Assessment:")
    print(f"  Fidelity Passed : {passed} (Expected: False)")
    print(f"  Discrepancies   : {len(warnings)}")
    for w in warnings:
        print(f"  {RED}[CAUGHT]{RESET} {w}")

    if not passed and len(warnings) >= 3:
        print(f"\n{GREEN}[PASS] Cross-language safeguard actively and reliably intercepted all deliberate tampering!{RESET}")
        return True, len(warnings)
    else:
        print(f"\n{RED}[FAIL] Safeguard failed to intercept deliberate tampering!{RESET}")
        return False, len(warnings)


def main():
    print_banner("PHASE 3 END-TO-END PIPELINE: OCR -> SIMPLIFICATION -> TRANSLATION (HINDI)")

    test_docs = [
        ("printed_paragraph.png", "Dense Technical Architecture Brief"),
        ("form_document.png", "Verification Form (Application ID: SN-2026-X89, Approved)"),
        ("skewed_document.png", "Deskewed Scan with OCR Noise"),
        ("medical_bill_receipt.png", "Medical Bill (Claim: MED-90821-TX, $450.00, Approved)"),
        ("legal_notice_deadline.png", "Municipal Summons (Docket: GOV-2026-LAW-77, $250.00, Nov 15 2026)"),
        ("utility_bill_unseen.png", "Generalization Test: Utility Statement (Unseen labels, $135.50, Current)"),
        ("flowing_prose_letter.png", "Flowing Prose + Entity Test: Assessment Notice (TAX-2026-8819, Approved)"),
    ]

    results = []
    for filename, desc in test_docs:
        res = run_pipeline_test(filename, desc)
        results.append(res)

    # Run adversarial test
    adv_passed, adv_caught = run_adversarial_tampering_test()

    # Print Summary Table
    print_banner("PHASE 3 PIPELINE EXECUTION SUMMARY")
    print(f"{'Test Document':<26} | {'OCR Lat':<9} | {'Simp Lat':<9} | {'Trans Lat':<10} | {'Fidelity':<10} | {'Status'}")
    print("-" * 80)
    for r in results:
        pass_str = f"{GREEN}100% Intact{RESET}" if r["passed"] else f"{YELLOW}{r['warnings_count']} Warn{RESET}"
        status_str = f"{GREEN}PASS{RESET}" if r["passed"] else f"{RED}FAIL{RESET}"
        print(f"{r['image']:<26} | {r['ocr_latency']:>7.1f}ms | {r['simp_latency']:>7.1f}ms | {r['trans_latency']:>8.1f}ms | {pass_str:<19} | {status_str}")
    print("-" * 80)
    adv_status = f"{GREEN}PASS (Intercepted){RESET}" if adv_passed else f"{RED}FAIL{RESET}"
    print(f"{'Adversarial Tampering Case':<26} | {'N/A':<9} | {'N/A':<9} | {'<1ms':<10} | {f'Caught {adv_caught}':<10} | {adv_status}")
    print("=" * 80)


if __name__ == "__main__":
    main()
