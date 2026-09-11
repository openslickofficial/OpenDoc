"""
Configuration Layer for Snapdragon Document Assistant Pipeline.
Provides a unified PipelineConfig dataclass consolidating target language,
execution modes (NPU vs CPU fallback), model paths, directory locations,
and fidelity gating behavior across all four pipeline stages.
"""

import os
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any

# Enforce 100% offline operation across all processes and dependencies
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)

DEFAULT_MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
DEFAULT_AUDIO_DIR = os.path.join(PROJECT_ROOT, "audio_output")
DEFAULT_PIPER_MODEL = os.path.join(DEFAULT_MODELS_DIR, "piper_hi", "hi_IN-pratham-medium.onnx")
DEFAULT_GENIE_CONFIG = os.path.join(DEFAULT_MODELS_DIR, "genie_bundle_qwen17", "genie_config.json")
DEFAULT_TROCR_PROCESSOR_DIR = os.path.join(DEFAULT_MODELS_DIR, "trocr_processor")
DEFAULT_QWEN_PROXY_DIR = os.path.join(DEFAULT_MODELS_DIR, "qwen_local_proxy")


@dataclass
class PipelineConfig:
    """
    Central configuration object for the end-to-end document assistant pipeline.
    """
    # Core target settings
    target_lang: str = "hi"
    engine_mode: str = "auto"       # "auto" (prefers Snapdragon NPU), "npu", or "cpu"
    bundle_name: str = "qwen17"     # "qwen17" (Qwen3-1.7B w4a16) or "phi35" (Phi-3.5-Mini w4a16)
    
    # Safety and fidelity policies
    strict_fidelity_gate: bool = False  # False: prepends warning to speech; True: halts audio generation
    min_ocr_chars: int = 5              # Minimum characters required from OCR before short-circuiting

    # TTS options
    use_online_tts_enhancement: bool = False  # False: 100% on-device Piper; True: EdgeTTS cloud mode
    
    # Paths
    models_dir: str = DEFAULT_MODELS_DIR
    ocr_models_dir: Optional[str] = None
    tts_output_dir: str = DEFAULT_AUDIO_DIR
    piper_model_path: str = DEFAULT_PIPER_MODEL
    genie_config_path: str = DEFAULT_GENIE_CONFIG

    def __post_init__(self):
        if self.ocr_models_dir is None:
            self.ocr_models_dir = self.models_dir
        os.makedirs(self.tts_output_dir, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the config to a plain dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineConfig":
        """Creates a PipelineConfig instance from a dictionary, ignoring extra keys."""
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    @classmethod
    def from_json(cls, json_path: str) -> "PipelineConfig":
        """Loads configuration from a JSON file."""
        if not os.path.isfile(json_path):
            raise FileNotFoundError(f"Configuration file not found: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_json(self, json_path: str) -> None:
        """Saves current configuration to a JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


# Default global singleton
DEFAULT_CONFIG = PipelineConfig()
