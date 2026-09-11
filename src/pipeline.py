"""
Unified End-to-End Document Assistant Pipeline.
Chains all 4 individually verified stages:
1. OCR (TrOCR via QNN / Hexagon NPU or CPU fallback)
2. Plain-Language Simplification (Qwen3-1.7B via Genie or CPU proxy)
3. Indian Language Translation (AnchorPreservedTranslationEngine / Genie)
4. On-Device Speech Synthesis (Piper ONNX with Fidelity Gate & SAPI5 fallback)

Provides single entry-point function:
process_document(image_path: str, target_lang: str = "hi", strict_fidelity_gate: bool = False, config: Optional[PipelineConfig] = None) -> dict
"""

import os
import sys
import re
import time
import logging
from typing import Dict, Any, Optional, Tuple

from src.config import PipelineConfig, DEFAULT_CONFIG
from src.ocr_module import extract_text
from src.simplify_module import simplify_text
from src.translate_module import translate_text
from src.tts_module import synthesize_speech

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Pipeline] %(message)s",
)
logger = logging.getLogger("Pipeline")


def is_garbage_or_empty_ocr(text: str, min_chars: int = 5) -> Tuple[bool, str]:
    """
    Evaluates whether raw OCR output is empty, near-empty, or hallucinated garbage
    (e.g., when run on blank, severely blurred, or degraded scans).
    """
    cleaned = text.strip()
    if len(cleaned) < min_chars:
        return True, f"Insufficient readable text ({len(cleaned)} char(s) < minimum threshold {min_chars})"

    # Check for isolated single-character hallucination loops (e.g. 'a b c d e f g h o o')
    tokens = cleaned.split()
    single_char_tokens = [t for t in tokens if len(t) == 1 and t.isalpha()]
    if len(tokens) >= 4 and (len(single_char_tokens) / len(tokens)) >= 0.75:
        return True, "TrOCR hallucinated isolated single-character sequence (blank/unreadable image artifact)"

    # Check for text with zero alphanumeric content
    if not re.search(r"[A-Za-z0-9]", cleaned):
        return True, "OCR output contains no recognizable alphanumeric characters"

    return False, ""


def _notify_stage(callback, stage_name: str, event_type: str, data: Optional[Dict[str, Any]] = None):
    if callback and callable(callback):
        try:
            callback(stage_name, event_type, data or {})
        except Exception as e:
            logger.warning("Stage callback error for stage %s: %s", stage_name, e)


def process_document(
    image_path: str,
    target_lang: str = "hi",
    strict_fidelity_gate: bool = False,
    config: Optional[PipelineConfig] = None,
    stage_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Unified 4-Stage Document Processing Pipeline.

    Parameters:
        image_path: Path to the input document image (PNG, JPG, TIFF).
        target_lang: Target Indian language code (default: "hi" for Hindi).
        strict_fidelity_gate: If True, halts audio generation on unverified documents;
                              if False, prepends an authoritative spoken warning.
        config: Optional PipelineConfig object. If omitted, uses default settings.
        stage_callback: Optional callable(stage_name: str, event_type: str, data: dict)
                        invoked during execution for live GUI progress updates.

    Returns:
        Structured dictionary containing:
        - status: "success", "partial_success", or "failed"
        - image_path: str
        - target_lang: str
        - total_latency_ms: float
        - raw_text: str
        - simplified_text: str
        - translated_text: str
        - audio_path: Optional[str]
        - overall_fidelity_passed: bool
        - fidelity_summary: dict
        - stages: { "ocr": dict, "simplify": dict, "translate": dict, "tts": dict }
        - error: Optional[str]
    """
    if config is None:
        config = DEFAULT_CONFIG

    # Override config with explicit function parameters if specified
    if target_lang != config.target_lang:
        config.target_lang = target_lang
    if strict_fidelity_gate != config.strict_fidelity_gate:
        config.strict_fidelity_gate = strict_fidelity_gate

    start_wall_time = time.perf_counter()
    logger.info("=" * 70)
    logger.info("PROCESSING DOCUMENT: %s (target_lang=%s, strict_gate=%s)", 
                os.path.basename(image_path), config.target_lang, config.strict_fidelity_gate)
    logger.info("=" * 70)

    # -------------------------------------------------------------------------
    # 0. Initial Validation
    # -------------------------------------------------------------------------
    if not os.path.isfile(image_path):
        err_msg = f"Target document image not found at path: {image_path}"
        logger.error(err_msg)
        _notify_stage(stage_callback, "ocr", "failed", {"error": err_msg})
        return {
            "status": "failed",
            "image_path": image_path,
            "target_lang": config.target_lang,
            "total_latency_ms": 0.0,
            "stages": {},
            "raw_text": "",
            "simplified_text": "",
            "translated_text": "",
            "audio_path": None,
            "overall_fidelity_passed": False,
            "fidelity_summary": {"error": err_msg},
            "error": err_msg,
        }

    # -------------------------------------------------------------------------
    # 1. Stage 1: OCR Text Extraction
    # -------------------------------------------------------------------------
    logger.info("[STAGE 1/4] Running Document OCR...")
    _notify_stage(stage_callback, "ocr", "running", {"image_path": image_path})
    t_ocr_start = time.perf_counter()
    try:
        ocr_result = extract_text(image_path, models_dir=config.ocr_models_dir)
    except Exception as e:
        err_msg = f"OCR module failed to process image: {e}"
        logger.error(err_msg)
        _notify_stage(stage_callback, "ocr", "failed", {"error": err_msg})
        return {
            "status": "failed",
            "image_path": image_path,
            "target_lang": config.target_lang,
            "total_latency_ms": round((time.perf_counter() - start_wall_time) * 1000.0, 2),
            "stages": {"ocr": {"error": str(e)}},
            "raw_text": "",
            "simplified_text": "",
            "translated_text": "",
            "audio_path": None,
            "overall_fidelity_passed": False,
            "fidelity_summary": {"error": err_msg},
            "error": err_msg,
        }

    raw_text = ocr_result.get("text", "").strip()
    logger.info("[STAGE 1/4] OCR complete: %d chars, %.2f ms via %s", 
                len(raw_text), ocr_result["latency_ms"], ocr_result["provider_used"])

    # Short-circuit check: Near-empty or garbage output (blank or blurry image)
    is_bad_ocr, bad_reason = is_garbage_or_empty_ocr(raw_text, min_chars=config.min_ocr_chars)
    if is_bad_ocr:
        err_msg = (
            f"OCR detected unreadable or empty document text ({bad_reason}). "
            f"Document image appears to be blank, severely blurred, or unreadable. Short-circuiting downstream stages."
        )
        logger.warning("[STAGE 1 SHORT-CIRCUIT] %s", err_msg)
        _notify_stage(stage_callback, "ocr", "failed", {"error": err_msg, "ocr_result": ocr_result})
        total_latency = round((time.perf_counter() - start_wall_time) * 1000.0, 2)
        return {
            "status": "failed",
            "image_path": image_path,
            "target_lang": config.target_lang,
            "total_latency_ms": total_latency,
            "stages": {
                "ocr": ocr_result,
            },
            "raw_text": raw_text,
            "simplified_text": "",
            "translated_text": "",
            "audio_path": None,
            "overall_fidelity_passed": False,
            "fidelity_summary": {"error": err_msg},
            "error": err_msg,
        }

    _notify_stage(stage_callback, "ocr", "completed", ocr_result)

    # -------------------------------------------------------------------------
    # 2. Stage 2: Plain-Language Simplification
    # -------------------------------------------------------------------------
    logger.info("[STAGE 2/4] Running Plain-Language Simplification...")
    _notify_stage(stage_callback, "simplify", "running", {"raw_text": raw_text})
    t_simp_start = time.perf_counter()
    try:
        simplify_result = simplify_text(
            raw_text=raw_text,
            engine_mode=config.engine_mode,
            bundle_name=config.bundle_name,
        )
    except Exception as e:
        err_msg = f"Simplification stage failed: {e}"
        logger.error(err_msg)
        _notify_stage(stage_callback, "simplify", "failed", {"error": str(e)})
        total_latency = round((time.perf_counter() - start_wall_time) * 1000.0, 2)
        return {
            "status": "failed",
            "image_path": image_path,
            "target_lang": config.target_lang,
            "total_latency_ms": total_latency,
            "stages": {
                "ocr": ocr_result,
                "simplify": {"error": str(e), "latency_ms": round((time.perf_counter() - t_simp_start) * 1000.0, 2)},
            },
            "raw_text": raw_text,
            "simplified_text": "",
            "translated_text": "",
            "audio_path": None,
            "overall_fidelity_passed": False,
            "fidelity_summary": {"error": err_msg},
            "error": err_msg,
        }

    simplified_text = simplify_result.get("simplified_text", "").strip()
    logger.info("[STAGE 2/4] Simplification complete: %.2f ms via %s (Fidelity: %s)",
                simplify_result["latency_ms"], simplify_result["provider_used"], simplify_result["fidelity_passed"])
    _notify_stage(stage_callback, "simplify", "completed", simplify_result)

    # -------------------------------------------------------------------------
    # 3. Stage 3: Indian Language Translation
    # -------------------------------------------------------------------------
    logger.info("[STAGE 3/4] Running Translation into %s...", config.target_lang)
    _notify_stage(stage_callback, "translate", "running", {"simplified_text": simplified_text})
    t_trans_start = time.perf_counter()
    try:
        translate_result = translate_text(
            text=simplified_text,
            target_lang=config.target_lang,
            engine_mode=config.engine_mode,
        )
    except Exception as e:
        err_msg = f"Translation stage failed: {e}"
        logger.error(err_msg)
        _notify_stage(stage_callback, "translate", "failed", {"error": str(e)})
        total_latency = round((time.perf_counter() - start_wall_time) * 1000.0, 2)
        return {
            "status": "failed",
            "image_path": image_path,
            "target_lang": config.target_lang,
            "total_latency_ms": total_latency,
            "stages": {
                "ocr": ocr_result,
                "simplify": simplify_result,
                "translate": {"error": str(e), "latency_ms": round((time.perf_counter() - t_trans_start) * 1000.0, 2)},
            },
            "raw_text": raw_text,
            "simplified_text": simplified_text,
            "translated_text": "",
            "audio_path": None,
            "overall_fidelity_passed": False,
            "fidelity_summary": {"error": err_msg},
            "error": err_msg,
        }

    translated_text = translate_result.get("translated_text", "").strip()
    logger.info("[STAGE 3/4] Translation complete: %.2f ms via %s (Fidelity: %s)",
                translate_result["latency_ms"], translate_result["provider_used"], translate_result["fidelity_passed"])
    _notify_stage(stage_callback, "translate", "completed", translate_result)

    # Aggregate cross-stage fidelity decisions
    simp_fidelity_passed = simplify_result.get("fidelity_passed", True)
    trans_fidelity_passed = translate_result.get("fidelity_passed", True)
    overall_fidelity_passed = simp_fidelity_passed and trans_fidelity_passed

    # -------------------------------------------------------------------------
    # 4. Stage 4: On-Device Speech Synthesis (Graceful Degradation)
    # -------------------------------------------------------------------------
    logger.info("[STAGE 4/4] Running Speech Synthesis (overall_fidelity_passed=%s, strict=%s)...",
                overall_fidelity_passed, config.strict_fidelity_gate)
    _notify_stage(stage_callback, "tts", "running", {"translated_text": translated_text})
    t_tts_start = time.perf_counter()
    tts_error = None
    try:
        tts_result = synthesize_speech(
            text=translated_text,
            lang=config.target_lang,
            fidelity_passed=overall_fidelity_passed,
            strict_fidelity_gate=config.strict_fidelity_gate,
            use_online_enhancement=config.use_online_tts_enhancement,
            output_dir=config.tts_output_dir,
        )
    except Exception as e:
        tts_error = f"Speech synthesis failed: {e}"
        logger.error("[STAGE 4 TTS EXCEPTION] %s. Degrading gracefully to text outputs.", tts_error)
        tts_result = {
            "audio_path": None,
            "provider_used": "TTS-Failed-Degraded",
            "latency_ms": round((time.perf_counter() - t_tts_start) * 1000.0, 2),
            "duration_ms": 0.0,
            "normalized_text": translated_text,
            "error": tts_error,
            "fidelity_gate": {
                "fidelity_passed": overall_fidelity_passed,
                "warning_prepended": False,
                "blocked": False,
                "policy_applied": f"tts_error_fallback ({tts_error})"
            },
            "anchor_survival": {"anchors_survived": False, "dropped_anchors": [tts_error]},
            "pronunciation_audit": {"normalization_passed": False, "warnings": [tts_error]}
        }

    logger.info("[STAGE 4/4] Speech synthesis completed: %.2f ms via %s (Audio: %s)",
                tts_result["latency_ms"], tts_result["provider_used"], tts_result.get("audio_path"))
    _notify_stage(stage_callback, "tts", "completed" if tts_error is None else "degraded", tts_result)

    # -------------------------------------------------------------------------
    # 5. Pipeline Consolidation & Return
    # -------------------------------------------------------------------------
    total_wall_latency = round((time.perf_counter() - start_wall_time) * 1000.0, 2)
    pipeline_status = "success" if tts_error is None else "partial_success"

    fidelity_summary = {
        "overall_fidelity_passed": overall_fidelity_passed,
        "simplification_fidelity_passed": simp_fidelity_passed,
        "translation_fidelity_passed": trans_fidelity_passed,
        "simplification_warnings": simplify_result.get("fidelity_warnings", []),
        "translation_warnings": translate_result.get("fidelity_warnings", []),
        "speech_policy_applied": tts_result.get("fidelity_gate", {}).get("policy_applied", "clean_pass"),
        "speech_warning_prepended": tts_result.get("fidelity_gate", {}).get("warning_prepended", False),
        "speech_blocked": tts_result.get("fidelity_gate", {}).get("blocked", False),
        "anchor_survival": tts_result.get("anchor_survival", {}),
    }

    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETED: %s in %.2f ms [Status: %s]",
                os.path.basename(image_path), total_wall_latency, pipeline_status)
    logger.info("=" * 70)

    return {
        "status": pipeline_status,
        "image_path": image_path,
        "target_lang": config.target_lang,
        "total_latency_ms": total_wall_latency,
        "raw_text": raw_text,
        "simplified_text": simplified_text,
        "translated_text": translated_text,
        "audio_path": tts_result.get("audio_path"),
        "overall_fidelity_passed": overall_fidelity_passed,
        "fidelity_summary": fidelity_summary,
        "stages": {
            "ocr": ocr_result,
            "simplify": simplify_result,
            "translate": translate_result,
            "tts": tts_result,
        },
        "error": tts_error,
    }
