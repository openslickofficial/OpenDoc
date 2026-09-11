import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ocr_module import extract_text
from src.simplify_module import simplify_text
from src.translate_module import translate_text, apply_anchor_preservation
from src.fidelity_checker import extract_all_entities, verify_fidelity

img_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_images", "telecom_disconnect_unseen.png")

print("=" * 80)
print("STAGE-BY-STAGE TRACING OF TELECOM DISCONNECTION NOTICE")
print("=" * 80)

# Expected Ground Truth
ground_truth = """PACIFIC BROADBAND AND TELECOM NETWORK
Service Disconnection Notice and Urgent Remittance Demand
Subscriber Name: Carlos Mendez
Account Identifier: TEL-55421-CA
Overdue Balance: $ 89.50
Final Disconnection Date: September 30 2026
Service Plan: Fiber Gigabit Internet
Line Status: SUSPENDED
Please remit $ 89.50 before September 30 2026 to restore network access."""

print("\n--- [STAGE 0: GROUND TRUTH IN IMAGE] ---")
print(ground_truth)
gt_ent = extract_all_entities(ground_truth)
print("Ground Truth Entities:", gt_ent)

# Stage 1: OCR
print("\n--- [STAGE 1: OCR EXTRACTION] ---")
ocr_res = extract_text(img_path)
ocr_text = ocr_res["text"]
print("OCR Raw Text:")
for idx, l in enumerate(ocr_text.split("\n")):
    print(f"  L{idx}: {repr(l)}")
ocr_ent = extract_all_entities(ocr_text)
print("OCR Entities:", ocr_ent)

# Stage 2: Simplification
print("\n--- [STAGE 2: SIMPLIFICATION] ---")
simp_res = simplify_text(ocr_text, engine_mode="cpu")
simp_text = simp_res["simplified_text"]
print("Simplified Text:")
for idx, l in enumerate(simp_text.split("\n")):
    print(f"  L{idx}: {repr(l)}")
simp_ent = extract_all_entities(simp_text)
print("Simplified Entities:", simp_ent)

# Stage 3: Translation
print("\n--- [STAGE 3: TRANSLATION] ---")
trans_res = translate_text(simp_text, target_lang="hi", engine_mode="cpu")
trans_text = trans_res["translated_text"]
print("Translated Text:")
for idx, l in enumerate(trans_text.split("\n")):
    print(f"  L{idx}: {repr(l)}")
trans_ent = extract_all_entities(trans_text)
print("Translated Entities:", trans_ent)

print("\n" + "=" * 80)
