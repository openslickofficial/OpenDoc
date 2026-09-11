"""
Plain-Language Simplification Module for Snapdragon X NPU Document Assistant.
Takes raw OCR output (including scanner noise and legal/bureaucratic terms)
and rewrites it into clear, simple English for users with limited literacy,
while strictly preserving all factual details (dates, names, amounts, reference IDs, status).

Supports:
- GenieExecutionEngine (Qualcomm Hexagon NPU on Snapdragon X Windows 11 ARM64)
- LocalLLMExecutionEngine (CPU fallback for development and testing)
- Automatic integration with Fidelity-Check Safeguard (fidelity_checker.py)
"""

import os
import sys
import time
import logging
import subprocess
from typing import Dict, Any, Optional, Tuple, List

from src.fidelity_checker import verify_fidelity

# Setup structured logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SimplifyModule] %(message)s",
)
logger = logging.getLogger("SimplifyModule")

from src.config import PROJECT_ROOT
QWEN17_GENIE_DIR = os.path.join(PROJECT_ROOT, "models", "genie_bundle_qwen17")
PHI35_GENIE_DIR = os.path.join(PROJECT_ROOT, "models", "genie_bundle_phi35")
QWEN17_GENIE_CONFIG = os.path.join(QWEN17_GENIE_DIR, "genie_config.json")
PHI35_GENIE_CONFIG = os.path.join(PHI35_GENIE_DIR, "genie_config.json")
DEFAULT_GENIE_CONFIG = QWEN17_GENIE_CONFIG

DEFAULT_LOCAL_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

# System prompt engineered for strict fidelity and Grade 5-6 readability
SYSTEM_PROMPT = """You are a helpful document simplification assistant.
Your job is to rewrite official, government, legal, medical, or technical text into plain, simple, easy-to-understand English for people with limited reading ability.

CRITICAL RULES:
1. REWRITE, DO NOT SUMMARIZE: Do not skip sections or leave out details.
2. NEVER ALTER OR DROP FACTUAL ANCHORS:
   - You MUST keep all exact dates (e.g. September 11, 2026).
   - You MUST keep all monetary amounts (e.g. $450.00, $250.00, ₹12,500).
   - You MUST keep all reference IDs, case numbers, and application codes (e.g. SN-2026-X89, GOV-2026-LAW-77).
   - You MUST keep all people and device names (e.g. Dr. Arthur Vance, HP OmniBook).
   - You MUST keep all status words exactly intact (e.g. APPROVED, REJECTED, PENDING, DUE). Never change an approval into a rejection or vice versa!
3. CLEAN UP OCR NOISE: If you see obvious OCR artifacts (like stray dots, broken punctuation, or scanning typos like 'T.O.OR' for 'TrOCR'), clean them up into plain language.
4. SIMPLIFY COMPLEX WORDS:
   - Instead of 'verification procedure initiated', say 'the check has started'.
   - Instead of 'reimbursement authorization granted', say 'the refund was approved'.
   - Instead of 'mandatory deadline for settlement', say 'the last date you can pay'.
5. Output ONLY the rewritten simple text. Do not add intro greetings, explanations, or disclaimers."""

FEW_SHOT_EXAMPLES = [
    {
        "input": "verification form-snapdragon x Hardware\nApplication ID : SN-2026-X89 .\nApplicant Name : Dr. Arthur Vance\nVerification Date . September 11 2026\nDevice Model : HP OmniBook Snapdragon X\nInference Provider : QNN ExecutionProvider .\nStatus : VERIFIED AND APPROVED",
        "output": "This is a verification form for Snapdragon X hardware.\nApplication ID: SN-2026-X89.\nApplicant Name: Dr. Arthur Vance.\nVerification Date: September 11, 2026.\nDevice Model: HP OmniBook Snapdragon X.\nSystem used: QNN ExecutionProvider.\nStatus: VERIFIED AND APPROVED."
    },
    {
        "input": "NOTICE OF PENDING FINE . Case ID: GOV-2026-LAW-77 .\nImmediate settlement required . Total monetary sum: $250.00 .\nMandatory payment deadline: November 15 2026 .\nFailure to remit payment will incur statutory penalties .\nCurrent Case Status: PENDING PAYMENT .",
        "output": "Notice about a fine waiting to be paid. Case ID: GOV-2026-LAW-77.\nYou must pay the amount soon. The total amount to pay is $250.00.\nThe last date to pay is November 15, 2026.\nIf you do not pay on time, you will receive extra fines.\nCurrent Status: PENDING PAYMENT."
    }
]


class BaseSimplificationEngine:
    """Abstract base class for document simplification engines."""

    def generate(self, raw_text: str) -> Tuple[str, str]:
        """Returns (simplified_text, provider_name)."""
        raise NotImplementedError


class GenieExecutionEngine(BaseSimplificationEngine):
    """
    Qualcomm Genie SDK (Generative AI Inference Extensions) Engine.
    Supports selecting between Qwen3-1.7B and Phi-3.5-Mini (w4a16 context binaries)
    executing on Qualcomm Hexagon NPU.
    """

    def __init__(self, bundle_name: str = "qwen17", config_path: Optional[str] = None):
        self.bundle_name = bundle_name.lower()
        if config_path:
            self.config_path = config_path
            self.bundle_dir = os.path.dirname(config_path)
        elif self.bundle_name in ("phi35", "phi_3_5", "phi-3.5", "phi"):
            self.bundle_name = "phi35"
            self.config_path = PHI35_GENIE_CONFIG
            self.bundle_dir = PHI35_GENIE_DIR
        else:
            self.bundle_name = "qwen17"
            self.config_path = QWEN17_GENIE_CONFIG
            self.bundle_dir = QWEN17_GENIE_DIR

    def is_available(self) -> bool:
        """Checks if genie-t2t-run binary is installed and bundle context binaries exist."""
        import shutil
        genie_bin = shutil.which("genie-t2t-run")
        if not genie_bin:
            # Check standard QAIRT Windows ARM64 installation path
            qairt_home = os.environ.get("QAIRT_HOME", r"C:\Program Files\Qualcomm\QAIRT")
            candidate_bin = os.path.join(qairt_home, "bin", "aarch64-windows-msvc", "genie-t2t-run.exe")
            if os.path.isfile(candidate_bin):
                genie_bin = candidate_bin

        if not genie_bin or not os.path.exists(self.config_path):
            return False

        # Verify context binaries exist in bundle directory
        if not os.path.exists(self.bundle_dir):
            return False
        bins = [f for f in os.listdir(self.bundle_dir) if f.endswith(".bin")]
        return len(bins) > 0

    def generate(self, raw_text: str) -> Tuple[str, str]:
        prompt = f"{SYSTEM_PROMPT}\n\nDocument Text to Simplify:\n{raw_text}\n\nSimplified Text:"
        genie_cmd = ["genie-t2t-run", "-c", self.config_path, "-p", prompt]
        logger.info("Executing on-device LLM via Genie (%s) on Qualcomm Hexagon NPU...", self.bundle_name)
        try:
            result = subprocess.run(
                genie_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
                cwd=self.bundle_dir,
            )
            simplified = result.stdout.strip()
            return simplified, f"GenieExecutionEngine ({self.bundle_name} on Qualcomm Hexagon NPU)"
        except Exception as e:
            logger.warning("Genie on-device execution unavailable: %s. Falling back to CPU engine.", e)
            raise


class LocalLLMExecutionEngine(BaseSimplificationEngine):
    """
    Local Lightweight LLM Fallback Engine using Hugging Face Transformers.
    Runs on CPU without requiring cloud tokens or gated model permissions.
    """

    def __init__(self, model_id: str = DEFAULT_LOCAL_MODEL):
        self.model_id = model_id
        self.tokenizer = None
        self.model = None
        self._load_model()

    def _load_model(self):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        # Priority 1: Check bundled local proxy model directory
        local_qwen = os.path.join(PROJECT_ROOT, "models", "qwen_local_proxy")
        target_model = local_qwen if os.path.isdir(local_qwen) else self.model_id

        logger.info("Initializing Local LLM Fallback Engine from: %s (local_files_only=True)...", target_model)
        self.tokenizer = AutoTokenizer.from_pretrained(target_model, local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            target_model,
            dtype=torch.float32,
            low_cpu_mem_usage=True,
            local_files_only=True,
        )
        self.model.eval()
        logger.info("Local LLM Fallback Engine loaded successfully offline.")


    def generate(self, raw_text: str) -> Tuple[str, str]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        # Add few-shot examples
        for ex in FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": f"Simplify this document text:\n{ex['input']}"})
            messages.append({"role": "assistant", "content": ex["output"]})
        
        # User input
        messages.append({"role": "user", "content": f"Simplify this document text:\n{raw_text}"})

        prompt_str = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.tokenizer([prompt_str], return_tensors="pt")

        import torch
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=256,
                do_sample=False,
                repetition_penalty=1.05,
            )

        gen_tokens = outputs[0][len(inputs.input_ids[0]):]
        simplified = self.tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()

        return simplified, f"LocalLLMExecutionEngine ({self.model_id} on CPU Fallback)"


# Engine cache for reuse across calls
_SIMPLIFY_ENGINES: Dict[str, BaseSimplificationEngine] = {}


def _get_engine(
    engine_mode: str = "auto",
    model_id: Optional[str] = None,
    bundle_name: str = "qwen17",
) -> BaseSimplificationEngine:
    global _SIMPLIFY_ENGINES
    cache_key = f"{engine_mode}_{bundle_name}_{model_id}"
    if cache_key in _SIMPLIFY_ENGINES:
        return _SIMPLIFY_ENGINES[cache_key]

    # Try Genie engine first if on Snapdragon target or requested
    if engine_mode in ("auto", "genie"):
        genie = GenieExecutionEngine(bundle_name=bundle_name)
        if genie.is_available() or engine_mode == "genie":
            try:
                _SIMPLIFY_ENGINES[cache_key] = genie
                return genie
            except Exception:
                logger.warning("Could not initialize Genie engine (%s), falling back to local LLM.", bundle_name)

    # Fallback to local HuggingFace causal LM
    selected_model = model_id or os.environ.get("SIMPLIFY_MODEL_ID", DEFAULT_LOCAL_MODEL)
    engine = LocalLLMExecutionEngine(model_id=selected_model)
    _SIMPLIFY_ENGINES[cache_key] = engine
    return engine


def simplify_text(
    raw_text: str,
    model_id_or_path: Optional[str] = None,
    engine_mode: str = "auto",
    bundle_name: str = "qwen17",
) -> Dict[str, Any]:
    """
    Main Phase 2 Pipeline Interface:
    Takes raw OCR text, rewrites it into plain, simple English,
    and runs the Fidelity-Check Safeguard to ensure no facts were lost.

    Parameters:
        raw_text: Raw string output from OCR module (may contain OCR artifacts, linebreaks).
        model_id_or_path: Optional custom model name or path.
        engine_mode: "auto" (prioritizes Genie on Snapdragon NPU, falls back to local CPU),
                     "genie" (force Genie execution),
                     "cpu" (force local CPU fallback).
        bundle_name: "qwen17" (Qwen3-1.7B w4a16) or "phi35" (Phi-3.5-Mini w4a16).

    Returns:
        {
            "raw_text": str,
            "simplified_text": str,
            "provider_used": str,
            "latency_ms": float,
            "fidelity_passed": bool,
            "fidelity_warnings": List[str],
            "entities_detected": dict
        }
    """
    if not raw_text or not raw_text.strip():
        return {
            "raw_text": raw_text,
            "simplified_text": "",
            "provider_used": "None",
            "latency_ms": 0.0,
            "fidelity_passed": True,
            "fidelity_warnings": [],
            "entities_detected": {},
        }

    logger.info("Simplifying document text (%d characters) via bundle=%s...", len(raw_text), bundle_name)
    start_time = time.perf_counter()

    # Step 1: Execute Generation via Active Engine
    engine = _get_engine(engine_mode=engine_mode, model_id=model_id_or_path, bundle_name=bundle_name)
    simplified_text, provider_used = engine.generate(raw_text)

    # Step 2: Measure Inference Latency
    end_time = time.perf_counter()
    latency_ms = round((end_time - start_time) * 1000.0, 2)
    logger.info("Generation completed in %.2f ms via %s", latency_ms, provider_used)

    # Step 3: Execute Fidelity-Check Safeguard
    logger.info("Executing Fidelity-Check Safeguard on generated output...")
    fidelity_result = verify_fidelity(original_text=raw_text, simplified_text=simplified_text)

    if not fidelity_result["fidelity_passed"]:
        logger.warning(
            "FIDELITY WARNING: %d discrepancy/discrepancies detected between original OCR and simplified text!",
            len(fidelity_result["fidelity_warnings"]),
        )
        for warn in fidelity_result["fidelity_warnings"]:
            logger.warning("  * %s", warn)
    else:
        logger.info("SUCCESS: All critical entities (dates, amounts, IDs, status keywords) verified preserved.")

    return {
        "raw_text": raw_text,
        "simplified_text": simplified_text,
        "provider_used": provider_used,
        "latency_ms": latency_ms,
        "fidelity_passed": fidelity_result["fidelity_passed"],
        "fidelity_warnings": fidelity_result["fidelity_warnings"],
        "entities_detected": fidelity_result["original_entities"],
        "missing_entities": fidelity_result["missing_entities"],
    }
