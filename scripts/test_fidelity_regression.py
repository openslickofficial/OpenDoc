#!/usr/bin/env python3
"""
Comprehensive Regression Test Suite for Rebuilt Fidelity-Check Safeguard.
Evaluates:
1. All 5 Phase 1 & 2 Documents:
   - printed_paragraph.png
   - form_document.png
   - skewed_document.png
   - medical_bill_receipt.png
   - legal_notice_deadline.png
2. Phase 3 Generalization & Prose Documents:
   - utility_bill_unseen.png
   - flowing_prose_letter.png
3. Telecom Disconnection Notice (Silent Data Corruption Case):
   - telecom_disconnect_unseen.png
   - Confirms the rebuilt fidelity checker actively CAUGHT the corruption!
4. Deliberate Adversarial Tampering Case:
   - Confirms active interception of flipped status, altered dates, and dropped amounts.
"""

import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ocr_module import extract_text
from src.simplify_module import simplify_text
from src.translate_module import translate_text
from src.fidelity_checker import verify_fidelity, extract_all_entities

# ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner(title: str):
    print(f"\n{CYAN}{BOLD}{'=' * 82}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 82}{RESET}")


def run_document_test(image_filename: str, description: str, expected_to_pass: bool = True) -> dict:
    image_path = os.path.join(PROJECT_ROOT, "test_images", image_filename)
    if not os.path.exists(image_path):
        print(f"[-] Image not found: {image_path}")
        return {"image": image_filename, "status": "FILE_NOT_FOUND"}

    print(f"\n{BOLD}Document : {image_filename}{RESET} ({description})")

    # Step 1: OCR
    t0 = time.perf_counter()
    ocr_res = extract_text(image_path)
    ocr_lat = (time.perf_counter() - t0) * 1000.0
    raw_ocr = ocr_res["text"]
    ocr_ambiguities = ocr_res.get("ambiguity_warnings", [])

    print(f"  [1] OCR      : {ocr_lat:.1f} ms | Lines: {ocr_res['lines_processed']} | Provider: {ocr_res['provider_used']}")
    if ocr_ambiguities:
        print(f"      {YELLOW}OCR Ambiguity Warnings ({len(ocr_ambiguities)}):{RESET}")
        for a in ocr_ambiguities:
            print(f"        * {YELLOW}{a}{RESET}")

    # Step 2: Simplification
    t1 = time.perf_counter()
    simp_res = simplify_text(raw_ocr, engine_mode="cpu")
    simp_lat = simp_res["latency_ms"]
    simplified = simp_res["simplified_text"]
    simp_fidelity = simp_res["fidelity_passed"]
    simp_warnings = simp_res["fidelity_warnings"]

    print(f"  [2] Simplify : {simp_lat:.1f} ms | Provider: {simp_res['provider_used']}")
    print(f"      Simp Fidelity Check: {GREEN + 'PASSED' + RESET if simp_fidelity else YELLOW + 'FLAGGED (' + str(len(simp_warnings)) + ' warnings)' + RESET}")
    if simp_warnings:
        for w in simp_warnings:
            print(f"        - {YELLOW}{w}{RESET}")

    # Step 3: Translation to Hindi
    t2 = time.perf_counter()
    trans_res = translate_text(simplified, target_lang="hi", engine_mode="cpu")
    trans_lat = trans_res["latency_ms"]
    translated = trans_res["translated_text"]
    trans_fidelity = trans_res["fidelity_passed"]
    trans_warnings = trans_res["fidelity_warnings"]

    print(f"  [3] Translate: {trans_lat:.1f} ms | Provider: {trans_res['provider_used']}")
    print(f"      Cross-Lang Fidelity: {GREEN + 'PASSED' + RESET if trans_fidelity else YELLOW + 'FLAGGED (' + str(len(trans_warnings)) + ' warnings)' + RESET}")
    if trans_warnings:
        for w in trans_warnings:
            print(f"        - {YELLOW}{w}{RESET}")

    overall_passed = simp_fidelity and trans_fidelity
    test_success = (overall_passed == expected_to_pass)

    return {
        "image": image_filename,
        "description": description,
        "ocr_lat": ocr_lat,
        "simp_lat": simp_lat,
        "trans_lat": trans_lat,
        "ocr_ambiguities": len(ocr_ambiguities),
        "simp_fidelity": simp_fidelity,
        "trans_fidelity": trans_fidelity,
        "overall_passed": overall_passed,
        "expected_to_pass": expected_to_pass,
        "test_success": test_success,
        "warnings_count": len(simp_warnings) + len(trans_warnings),
    }


def run_adversarial_test() -> dict:
    print_banner("DELIBERATE ADVERSARIAL TAMPERING TEST")
    authentic_source = (
        "Patient Billing Statement: Metropolitan Healthcare Services.\n"
        "Patient: Harold Jenkins.\n"
        "Service Date: October 24 2026.\n"
        "Claim Reference ID: MED-90821-TX.\n"
        "Total Charges: $450.00.\n"
        "Claim Determination Status: APPROVED FOR FULL REIMBURSEMENT."
    )

    tampered_rewrite = (
        "Patient Billing Statement for Harold Jenkins.\n"
        "Claim Reference ID: MED-90821-TX.\n"
        "The service date was recorded as December 31, 2026.\n"
        "Claim Determination Status: REJECTED."
    )

    print(f"{BOLD}Source Document Text:{RESET}\n{authentic_source}")
    print(f"\n{BOLD}Tampered Rewrite (Dropped $450, Changed Date, Flipped Approval):{RESET}\n{tampered_rewrite}")

    res = verify_fidelity(authentic_source, tampered_rewrite)
    passed = res["fidelity_passed"]
    warnings = res["fidelity_warnings"]

    print(f"\nSafeguard Assessment:")
    print(f"  Fidelity Passed : {passed} (Expected: False)")
    print(f"  Caught Warnings : {len(warnings)}")
    for w in warnings:
        print(f"    {RED}[CAUGHT]{RESET} {w}")

    test_success = (not passed) and len(warnings) >= 3
    return {
        "test_name": "Adversarial Tampering",
        "passed": passed,
        "warnings_count": len(warnings),
        "test_success": test_success,
    }


def main():
    print_banner("FULL REGRESSION TEST SUITE (REBUILT FIDELITY CHECKER)")

    test_docs = [
        # Category 1: Structured Form Documents (AnchorPreservedTranslationEngine - Must 100% Pass)
        ("form_document.png", "Verification Form (SN-2026-X89, Approved)", True),
        ("skewed_document.png", "Deskewed Document Scan", True),
        ("medical_bill_receipt.png", "Medical Statement (MED-90821-TX, $450.00, Approved)", True),
        ("legal_notice_deadline.png", "Municipal Summons (GOV-2026-LAW-77, $250.00, Deadline)", True),
        ("utility_bill_unseen.png", "Residential Utility Statement (UTIL-99412-CA, $135.50)", True),

        # Category 2: Continuous Prose via 0.5B Proxy LLM (Strict checker catches omitted figures)
        ("printed_paragraph.png", "Technical Brief (Continuous Prose - Proxy drops '11')", False),
        ("flowing_prose_letter.png", "Flowing Prose Letter (OCR $320->8 32,000, Proxy drops '32')", False),

        # Category 3: Telecom Disconnection Notice (Silent Data Corruption - MUST be caught/flagged!)
        ("telecom_disconnect_unseen.png", "Telecom Disconnection Notice (Corrupted $889.50/2028)", False),
    ]

    results = []
    for filename, desc, expect_pass in test_docs:
        r = run_document_test(filename, desc, expect_pass)
        results.append(r)

    adv_res = run_adversarial_test()

    # Summary Table
    print_banner("REGRESSION TEST RESULTS SUMMARY")
    print(f"{'Document':<28} | {'OCR':<7} | {'Simp':<7} | {'Trans':<7} | {'Fidelity':<12} | {'Expected':<10} | {'Test Result'}")
    print("-" * 88)
    for r in results:
        fid_status = f"{GREEN}100% Pass{RESET}" if r["overall_passed"] else f"{YELLOW}FLAGGED ({r['warnings_count']}){RESET}"
        exp_status = "PASS" if r["expected_to_pass"] else "FLAGGED"
        res_str = f"{GREEN}PASS (Accurate){RESET}" if r["test_success"] else f"{RED}FAIL (Regression){RESET}"
        print(
            f"{r['image']:<28} | "
            f"{r['ocr_lat']:>5.0f}ms | "
            f"{r['simp_lat']:>5.0f}ms | "
            f"{r['trans_lat']:>5.0f}ms | "
            f"{fid_status:<21} | "
            f"{exp_status:<10} | "
            f"{res_str}"
        )

    print("-" * 88)
    adv_fid = f"{RED}FLAGGED ({adv_res['warnings_count']}){RESET}"
    adv_outcome = f"{GREEN}PASS (Intercepted){RESET}" if adv_res["test_success"] else f"{RED}FAIL{RESET}"
    print(f"{'Adversarial Tampering Case':<28} | {'N/A':<7} | {'N/A':<7} | {'N/A':<7} | {adv_fid:<21} | {'FLAGGED':<10} | {adv_outcome}")
    print("=" * 88 + "\n")


if __name__ == "__main__":
    main()
