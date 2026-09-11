"""
End-to-End 4-Stage Document Assistant Pipeline Benchmark.
Runs:
  Stage 1: TrOCR (OCR)
  Stage 2: Qwen3-1.7B (Simplification) + Fidelity Verification
  Stage 3: Anchor-Preserved Translation Engine (Hindi Translation)
  Stage 4: EdgeTTS Neural Speech Synthesis + Pronunciation Normalization

Benchmarked on 2 complete documents:
1. test_images/medical_bill_receipt.png
2. test_images/legal_notice_deadline.png
"""

import os
import sys
import time
import json
import logging

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ocr_module import extract_text
from src.simplify_module import simplify_text
from src.translate_module import translate_text
from src.tts_module import synthesize_speech

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [E2EPipeline] %(message)s"
)
logger = logging.getLogger("E2EPipeline")


def run_pipeline_on_document(image_path: str, target_lang: str = "hi") -> dict:
    """Executes the full 4-stage pipeline on a document image."""
    base_name = os.path.basename(image_path)
    logger.info("=" * 60)
    logger.info("STARTING END-TO-END PIPELINE: %s", base_name)
    logger.info("=" * 60)

    t_start = time.perf_counter()

    # Stage 1: OCR
    logger.info("[Stage 1/4] OCR: Recognizing text lines...")
    ocr_out = extract_text(image_path)
    logger.info("  -> OCR Complete: %.2f ms (Provider: %s)", ocr_out["latency_ms"], ocr_out["provider_used"])

    # Stage 2: Simplification
    logger.info("[Stage 2/4] Simplification: Rewriting into plain language...")
    simp_out = simplify_text(ocr_out["text"])
    logger.info(
        "  -> Simplification Complete: %.2f ms (Provider: %s, Fidelity: %s)",
        simp_out["latency_ms"],
        simp_out["provider_used"],
        simp_out["fidelity_passed"]
    )

    # Stage 3: Translation
    logger.info("[Stage 3/4] Translation: Converting to Hindi...")
    trans_out = translate_text(simp_out["simplified_text"], target_lang=target_lang)
    logger.info(
        "  -> Translation Complete: %.2f ms (Provider: %s)",
        trans_out["latency_ms"],
        trans_out["provider_used"]
    )

    # Stage 4: Text-to-Speech (On-Device Piper ONNX Engine by Default)
    logger.info("[Stage 4/4] Text-to-Speech: Generating spoken audio on-device (Piper ONNX)...")
    tts_out = synthesize_speech(
        trans_out["translated_text"],
        lang=target_lang,
        fidelity_passed=simp_out["fidelity_passed"],
        use_online_enhancement=False
    )
    logger.info(
        "  -> TTS Complete: %.2f ms (Provider: %s, Audio Duration: %.2f s)",
        tts_out["latency_ms"],
        tts_out["provider_used"],
        tts_out["duration_ms"] / 1000.0
    )

    t_total = (time.perf_counter() - t_start) * 1000.0

    return {
        "document": base_name,
        "total_latency_ms": round(t_total, 2),
        "stage_latencies": {
            "ocr_ms": ocr_out["latency_ms"],
            "simplify_ms": simp_out["latency_ms"],
            "translate_ms": trans_out["latency_ms"],
            "tts_ms": tts_out["latency_ms"],
        },
        "stage_providers": {
            "ocr": ocr_out["provider_used"],
            "simplify": simp_out["provider_used"],
            "translate": trans_out["provider_used"],
            "tts": tts_out["provider_used"],
        },
        "outputs": {
            "ocr_text": ocr_out["text"],
            "simplified_text": simp_out["simplified_text"],
            "translated_text": trans_out["translated_text"],
            "normalized_speech_text": tts_out["normalized_text"],
            "audio_path": tts_out["audio_path"],
            "audio_duration_seconds": round(tts_out["duration_ms"] / 1000.0, 2),
            "audio_bytes": os.path.getsize(tts_out["audio_path"]),
        },
        "fidelity": {
            "simplification_fidelity_passed": simp_out["fidelity_passed"],
            "speech_normalization_passed": tts_out["pronunciation_audit"]["normalization_passed"],
            "speech_warning_prepended": tts_out["fidelity_gate"]["warning_prepended"],
        }
    }


def main():
    test_docs = [
        "test_images/medical_bill_receipt.png",
        "test_images/legal_notice_deadline.png",
    ]

    results = []
    for doc in test_docs:
        res = run_pipeline_on_document(doc, target_lang="hi")
        results.append(res)

    print("\n" + "=" * 80)
    print("END-TO-END PIPELINE BENCHMARK SUMMARY (4 STAGES)")
    print("=" * 80)
    for r in results:
        print(f"\nDOCUMENT: {r['document']}")
        print(f"  Total Pipeline Latency: {r['total_latency_ms']} ms ({r['total_latency_ms']/1000.0:.2f} s)")
        print(f"  Stage Breakdown:")
        print(f"    1. OCR:           {r['stage_latencies']['ocr_ms']:>8.2f} ms | Provider: {r['stage_providers']['ocr']}")
        print(f"    2. Simplify:      {r['stage_latencies']['simplify_ms']:>8.2f} ms | Provider: {r['stage_providers']['simplify']}")
        print(f"    3. Translate:     {r['stage_latencies']['translate_ms']:>8.2f} ms | Provider: {r['stage_providers']['translate']}")
        print(f"    4. TTS:           {r['stage_latencies']['tts_ms']:>8.2f} ms | Provider: {r['stage_providers']['tts']}")
        print(f"  Audio Output: {r['outputs']['audio_path']} ({r['outputs']['audio_duration_seconds']} s, {r['outputs']['audio_bytes']} bytes)")
        print(f"  Fidelity: Simplification={r['fidelity']['simplification_fidelity_passed']}, Normalization={r['fidelity']['speech_normalization_passed']}, Speech Warning Prepended={r['fidelity']['speech_warning_prepended']}")
        print(f"  Spoken Hindi Transcript (Sample):")
        print(f"    \"{r['outputs']['normalized_speech_text'][:120]}...\"")
    print("=" * 80)


if __name__ == "__main__":
    main()
