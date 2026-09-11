import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ocr_module import extract_text
from src.simplify_module import simplify_text
from src.translate_module import translate_text

image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_images", "telecom_disconnect_unseen.png")

print("=" * 80)
print("  RUNNING UNTOUCHED GENERALIZATION TEST: TELECOM DISCONNECTION NOTICE")
print("  (Zero modifications to OFFICIAL_LABEL_MAP_HI or ADMIN_TERM_MAP_HI)")
print("=" * 80)

# Step 1: OCR
t0 = time.perf_counter()
ocr_res = extract_text(image_path)
ocr_lat = (time.perf_counter() - t0) * 1000.0
print(f"\n[1] OCR Output ({ocr_lat:.1f} ms, Provider: {ocr_res['provider_used']}):")
for line in ocr_res["text"].split("\n"):
    print(f"    | {line}")

# Step 2: Simplification
t1 = time.perf_counter()
simp_res = simplify_text(ocr_res["text"], engine_mode="cpu")
simp_lat = simp_res["latency_ms"]
print(f"\n[2] Simplification Output ({simp_lat:.1f} ms, Provider: {simp_res['provider_used']}):")
for line in simp_res["simplified_text"].split("\n"):
    print(f"    | {line}")

# Step 3: Translation
t2 = time.perf_counter()
trans_res = translate_text(simp_res["simplified_text"], target_lang="hi", engine_mode="cpu")
trans_lat = trans_res["latency_ms"]
print(f"\n[3] Translation Output ({trans_lat:.1f} ms, Provider: {trans_res['provider_used']}):")
for line in trans_res["translated_text"].split("\n"):
    print(f"    > {line}")

print(f"\n[4] Fidelity Safeguard Result:")
print(f"    Fidelity Passed : {trans_res['fidelity_passed']}")
print(f"    Warnings ({len(trans_res['fidelity_warnings'])}):")
for w in trans_res["fidelity_warnings"]:
    print(f"      - {w}")

print("=" * 80)
