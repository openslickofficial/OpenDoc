#!/usr/bin/env python3
"""
Phase 2 Verification Suite: Plain-Language Simplification & Fidelity-Check Safeguard.
Tests simplify_text() across:
1. Phase 1 Documents (including real OCR noise & artifacts):
   - printed_paragraph.png
   - form_document.png
   - skewed_document.png
2. Phase 2 Documents (rich dates, amounts, status):
   - medical_bill_receipt.png
   - legal_notice_deadline.png
3. Deliberate Adversarial Tampering Test Case:
   - Proves the fidelity-check safeguard actively detects and catches
     dropped amounts, changed dates, and flipped status language.
"""

import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure console supports UTF-8
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.ocr_module import extract_text
from src.simplify_module import simplify_text
from src.fidelity_checker import verify_fidelity

# Terminal ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner(title: str):
    print(f"\n{CYAN}{BOLD}{'=' * 75}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 75}{RESET}")


def run_pipeline_test(image_filename: str, description: str) -> dict:
    image_path = os.path.join(PROJECT_ROOT, "test_images", image_filename)
    if not os.path.exists(image_path):
        print(f"[-] Image not found: {image_path}")
        return {"status": "FAIL", "image": image_filename}

    print(f"\n{BOLD}Test Document : {image_filename}{RESET} ({description})")

    # Step 1: Run Phase 1 OCR
    t0 = time.perf_counter()
    ocr_result = extract_text(image_path)
    ocr_text = ocr_result.get("text", "").strip()
    ocr_time = (time.perf_counter() - t0) * 1000.0

    print(f"  [OCR] Lines: {ocr_result['lines_processed']} | Latency: {ocr_time:.1f} ms | Provider: {ocr_result['provider_used']}")
    print(f"{BOLD}--- Raw OCR Transcription (Phase 1 Output) ---{RESET}")
    for line in ocr_text.splitlines():
        print(f"  | {line}")
    print(f"{BOLD}{'-' * 45}{RESET}")

    # Step 2: Run Phase 2 Simplification
    t1 = time.perf_counter()
    simp_result = simplify_text(ocr_text)
    simp_time = (time.perf_counter() - t1) * 1000.0

    provider = simp_result["provider_used"]
    simp_text = simp_result["simplified_text"]
    passed = simp_result["fidelity_passed"]
    warnings = simp_result["fidelity_warnings"]
    entities = simp_result["entities_detected"]

    print(f"  [Simplify] Latency: {simp_time:.1f} ms | Provider: {provider}")
    print(f"{BOLD}--- Plain-Language Simplification (Phase 2 Output) ---{RESET}")
    for line in simp_text.splitlines():
        print(f"  > {line}")
    print(f"{BOLD}{'-' * 45}{RESET}")

    # Step 3: Report Fidelity Check Status
    status_str = f"{GREEN}{BOLD}PASSED (100% Factual Fidelity){RESET}" if passed else f"{YELLOW}{BOLD}FLAGGED ({len(warnings)} Warnings){RESET}"
    print(f"  [Fidelity Safeguard]: {status_str}")

    ent_counts = [f"{k}: {len(v)}" for k, v in entities.items() if len(v) > 0]
    print(f"  [Entities Tracked]  : {', '.join(ent_counts) if ent_counts else 'None'}")

    if warnings:
        print(f"  {YELLOW}{BOLD}Fidelity Warnings Raised:{RESET}")
        for w in warnings:
            print(f"    * {YELLOW}{w}{RESET}")
    else:
        print(f"  * Zero factual anchor discrepancies detected.")

    return {
        "image": image_filename,
        "ocr_latency": ocr_time,
        "simp_latency": simp_time,
        "provider": provider,
        "fidelity_passed": passed,
        "warning_count": len(warnings),
    }


def run_adversarial_tampering_test():
    """
    Deliberate Adversarial Test:
    Takes authentic document text, deliberately injects 3 major flaws:
    1. Dropping a $450.00 monetary amount
    2. Changing a critical date (October 24 2026 -> December 31 2026)
    3. Flipping a legal status from APPROVED to REJECTED
    Verifies that the fidelity checker catches and flags all 3 discrepancies!
    """
    print_banner("DELIBERATE ADVERSARIAL TAMPERING TEST")
    print("Goal: Prove that the fidelity-check safeguard catches omissions, altered dates, and flipped status.\n")

    authentic_ocr = (
        "Metropolitan Healthcare Services\n"
        "Patient: Harold Jenkins\n"
        "Service Date: October 24 2026\n"
        "Claim Reference ID: MED-90821-TX\n"
        "Total Billed Charges: $ 450.00\n"
        "Claim Determination Status: APPROVED FOR REIMBURSEMENT"
    )

    # Deliberately tampered text
    tampered_text = (
        "Metropolitan Healthcare Services has processed the claim for Harold Jenkins.\n"
        "Claim Reference ID: MED-90821-TX.\n"
        "The service date was recorded as December 31, 2026.\n"
        "Your health insurance status is: REJECTED."
        # Notice: $450.00 was completely dropped! Date was changed! Status flipped to REJECTED!
    )

    print(f"{BOLD}Authentic Source Text:{RESET}")
    for l in authentic_ocr.splitlines():
        print(f"  | {l}")

    print(f"\n{BOLD}Tampered / Adversarial Rewrite:{RESET}")
    for l in tampered_text.splitlines():
        print(f"  x {l}")

    # Run fidelity verification
    check_result = verify_fidelity(authentic_ocr, tampered_text)

    print(f"\n{BOLD}Fidelity Check Result:{RESET}")
    print(f"  Fidelity Passed : {check_result['fidelity_passed']} (Expected: False)")
    print(f"  Discrepancies Caught: {len(check_result['fidelity_warnings'])}")

    for warn in check_result["fidelity_warnings"]:
        print(f"  {RED}{BOLD}[CAUGHT]{RESET} {warn}")

    # Assertions to guarantee validation
    assert not check_result["fidelity_passed"], "Adversarial test failed: fidelity checker failed to flag tampered text!"
    assert any("polarity flipped" in w.lower() or "rejected" in w.lower() for w in check_result["fidelity_warnings"]), "Failed to catch status flip!"
    assert any("450" in w for w in check_result["fidelity_warnings"]), "Failed to catch dropped amount!"
    assert any("october" in w.lower() or "date" in w.lower() for w in check_result["fidelity_warnings"]), "Failed to catch altered date!"

    print(f"\n{GREEN}{BOLD}[PASS] Safeguard actively and reliably caught all 3 deliberate tampering flaws!{RESET}")


def main():
    print_banner("Phase 2: Document Simplification & Fidelity Safeguard Test Suite")

    test_docs = [
        ("printed_paragraph.png", "Technical Document with OCR Artifacts"),
        ("form_document.png", "Structured Form with Application ID & Status"),
        ("skewed_document.png", "Deskewed Document Scan with Punctuation Noise"),
        ("medical_bill_receipt.png", "Medical Billing Receipt with Date, Claim ID, $450, & Approval"),
        ("legal_notice_deadline.png", "Municipal Legal Summons with Docket ID, Deadline, & $250 Fine"),
    ]

    results = []
    for img, desc in test_docs:
        res = run_pipeline_test(img, desc)
        results.append(res)

    # Run the adversarial validation
    run_adversarial_tampering_test()

    # Final Execution Summary Table
    print_banner("PHASE 2 PIPELINE EXECUTION SUMMARY")
    print(f"{'Test Document':<28} {'OCR Latency':<13} {'Simp Latency':<13} {'Fidelity':<14} {'Status':<8}")
    print("-" * 75)
    for r in results:
        fid_str = f"{GREEN}100% Intact{RESET}" if r["fidelity_passed"] else f"{YELLOW}{r['warning_count']} Flagged{RESET}"
        status_str = f"{GREEN}PASS{RESET}" if r["fidelity_passed"] else f"{YELLOW}WARN{RESET}"
        print(
            f"{r['image']:<28} "
            f"{r['ocr_latency']:>7.1f} ms    "
            f"{r['simp_latency']:>7.1f} ms    "
            f"{fid_str:<23} "
            f"{status_str}"
        )
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
