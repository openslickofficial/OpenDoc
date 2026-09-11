import os
import sys
import time
import logging

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ocr_module import extract_text
from src.simplify_module import simplify_text
from src.translate_module import translate_text
from src.fidelity_checker import verify_fidelity

def main():
    print("=" * 80)
    print("  ISOLATION TEST: legal_notice_deadline.png TRANSLATION ROUTING & FIDELITY")
    print("=" * 80)

    img_path = os.path.join(PROJECT_ROOT, "test_images", "legal_notice_deadline.png")
    if not os.path.exists(img_path):
        print(f"Error: image not found at {img_path}")
        return

    # Stage 1: OCR
    t0 = time.perf_counter()
    ocr_res = extract_text(img_path)
    ocr_lat = (time.perf_counter() - t0) * 1000.0
    raw_ocr = ocr_res["text"]
    print(f"\n[1] OCR Extracted in {ocr_lat:.1f} ms:")
    print("-" * 50)
    print(raw_ocr)

    # Stage 2: Simplification
    t1 = time.perf_counter()
    simp_res = simplify_text(raw_ocr, engine_mode="cpu")
    simp_lat = (time.perf_counter() - t1) * 1000.0
    simplified = simp_res["simplified_text"]
    print(f"\n[2] Simplified in {simp_lat:.1f} ms (Fidelity: {simp_res['fidelity_passed']}):")
    print("-" * 50)
    print(simplified)

    # Stage 3: Translation
    t2 = time.perf_counter()
    trans_res = translate_text(simplified, target_lang="hi", engine_mode="cpu")
    trans_lat = (time.perf_counter() - t2) * 1000.0
    translated = trans_res["translated_text"]
    provider = trans_res["provider_used"]
    fidelity = trans_res["fidelity_passed"]
    warnings = trans_res["fidelity_warnings"]

    print(f"\n[3] Translated in {trans_lat:.2f} ms:")
    print(f"    Engine Selected: {provider}")
    print(f"    Cross-Lang Fidelity: {fidelity} ({len(warnings)} warnings)")
    print("-" * 50)
    print(translated)
    print("-" * 50)

    if warnings:
        print("Fidelity Warnings:")
        for w in warnings:
            print(f"  * {w}")

    print("\n" + "=" * 80)
    print(f"SUMMARY: Provider = {provider} | Latency = {trans_lat:.2f} ms | Fidelity = {fidelity}")
    print("=" * 80)

if __name__ == "__main__":
    main()
