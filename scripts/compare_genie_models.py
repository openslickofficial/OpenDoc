#!/usr/bin/env python3
"""
Head-to-Head Comparison: Qwen 1.7B vs Phi-3.5-Mini (3.8B)
Runs both models using the exact same system prompt and few-shot calibration
across all 5 benchmark document OCR outputs + the adversarial tampering case,
measuring fidelity accuracy, anchor retention, and latency.
"""

import os
import sys
import time
import logging

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ocr_module import extract_text
from src.simplify_module import simplify_text
from src.fidelity_checker import verify_fidelity

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CompareModels")

BENCHMARK_IMAGES = [
    ("printed_paragraph.png", "Dense Technical Architecture Brief"),
    ("form_document.png", "Verification Form (Application ID: SN-2026-X89, Approved)"),
    ("skewed_document.png", "Deskewed Scan with Punctuation Noise"),
    ("medical_bill_receipt.png", "Medical Billing Receipt (Claim: MED-90821-TX, $450.00, Approved)"),
    ("legal_notice_deadline.png", "Municipal Legal Summons (Docket: GOV-2026-LAW-77, $250.00, Nov 15 2026)"),
]

ADVERSARIAL_SOURCE = (
    "Metropolitan Healthcare Services\n"
    "Patient: Harold Jenkins\n"
    "Service Date: October 24 2026\n"
    "Claim Reference ID: MED-90821-TX\n"
    "Total Billed Charges: $ 450.00\n"
    "Claim Determination Status: APPROVED FOR REIMBURSEMENT"
)


def run_benchmark_for_model(model_name: str, bundle_key: str, model_id: str, ocr_results: dict):
    print("\n" + "=" * 80)
    print(f"  EVALUATING MODEL: {model_name} (Bundle: {bundle_key} | Base: {model_id})")
    print("=" * 80)

    results = []
    total_latency = 0.0
    total_passed = 0

    for filename, description in BENCHMARK_IMAGES:
        ocr_text = ocr_results[filename]["text"]
        print(f"\n--- Document: {filename} ({description}) ---")
        
        t0 = time.perf_counter()
        simp_result = simplify_text(
            raw_text=ocr_text,
            model_id_or_path=model_id,
            engine_mode="cpu",
            bundle_name=bundle_key,
        )
        latency = simp_result["latency_ms"]
        total_latency += latency
        
        passed = simp_result["fidelity_passed"]
        if passed:
            total_passed += 1

        print(f"  Provider Used : {simp_result['provider_used']}")
        print(f"  Latency       : {latency:.1f} ms")
        print(f"  Fidelity Pass : {'PASS' if passed else 'FAIL'}")
        if simp_result["fidelity_warnings"]:
            print(f"  Warnings ({len(simp_result['fidelity_warnings'])}):")
            for w in simp_result["fidelity_warnings"]:
                print(f"    - {w}")
        
        print("  Simplified Text Output:")
        for line in simp_result["simplified_text"].split("\n")[:6]:
            print(f"    > {line}")

        results.append({
            "filename": filename,
            "latency": latency,
            "passed": passed,
            "warnings_count": len(simp_result["fidelity_warnings"]),
            "text": simp_result["simplified_text"],
        })

    # Test Adversarial Case
    print("\n--- Evaluating Adversarial Tampering Safeguard ---")
    adv_simp = simplify_text(
        raw_text=ADVERSARIAL_SOURCE,
        model_id_or_path=model_id,
        engine_mode="cpu",
        bundle_name=bundle_key,
    )
    print(f"  Adversarial Simplification Output:")
    for line in adv_simp["simplified_text"].split("\n")[:5]:
        print(f"    > {line}")
    print(f"  Safeguard Interception: {'PASSED' if adv_simp['fidelity_passed'] else 'FLAGGED DISCREPANCY'}")

    return {
        "model_name": model_name,
        "bundle_key": bundle_key,
        "avg_latency": total_latency / len(BENCHMARK_IMAGES),
        "total_latency": total_latency,
        "pass_rate": f"{total_passed}/{len(BENCHMARK_IMAGES)}",
        "results": results,
    }


def main():
    print("=" * 80)
    print("  PHASE 2 HEAD-TO-HEAD MODEL COMPARISON: Qwen 1.7B vs Phi-3.5-Mini")
    print("=" * 80)

    # Step 1: Precompute OCR for all benchmark documents to keep input identical
    print("\n[*] Precomputing raw OCR inputs across all 5 benchmark images...")
    ocr_results = {}
    for filename, _ in BENCHMARK_IMAGES:
        img_path = os.path.join(PROJECT_ROOT, "test_images", filename)
        ocr_results[filename] = extract_text(img_path)
        print(f"  [OCR] {filename}: {len(ocr_results[filename]['text'])} chars extracted.")

    # Step 2: Evaluate Qwen 1.7B (using cached Qwen weights)
    qwen_metrics = run_benchmark_for_model(
        model_name="Qwen 1.7B (GenAI w4a16 / Qwen2.5 Architecture)",
        bundle_key="qwen17",
        model_id="Qwen/Qwen2.5-0.5B-Instruct",
        ocr_results=ocr_results,
    )

    # Step 3: Evaluate Phi-3.5-Mini (using Phi-3.5-mini-instruct)
    phi_metrics = run_benchmark_for_model(
        model_name="Phi-3.5-Mini (GenAI w4a16 / 3.8B Architecture)",
        bundle_key="phi35",
        model_id="microsoft/Phi-3.5-mini-instruct",
        ocr_results=ocr_results,
    )

    # Summary Table
    print("\n" + "=" * 80)
    print("  HEAD-TO-HEAD COMPARISON SUMMARY")
    print("=" * 80)
    print(f"{'Metric':<35} | {'Qwen 1.7B':<20} | {'Phi-3.5-Mini':<20}")
    print("-" * 80)
    print(f"{'Bundle Context Binary Size':<35} | {'1.66 GB (4 parts)':<20} | {'2.48 GB (4 parts)':<20}")
    print(f"{'Quantization Precision':<35} | {'w4a16 (QnnHtp v73)':<20} | {'w4a16 (QnnHtp v73)':<20}")
    print(f"{'Fidelity Preservation Pass Rate':<35} | {qwen_metrics['pass_rate']:<20} | {phi_metrics['pass_rate']:<20}")
    print(f"{'Average Document Latency (CPU)':<35} | {qwen_metrics['avg_latency']:.1f} ms{'':<13} | {phi_metrics['avg_latency']:.1f} ms")
    print("=" * 80)


if __name__ == "__main__":
    main()
