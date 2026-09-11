#!/usr/bin/env python3
"""
Qualcomm AI Hub Cloud Device Farm Job Submission for TrOCR.
Submits a compile, profile, and inference verification job targeting
real Qualcomm Snapdragon X Elite CRD hardware.
"""

import os
import sys
import argparse
import logging
from transformers import TrOCRProcessor, XLMRobertaTokenizer, AutoImageProcessor
import qai_hub as hub
from qai_hub_models.models.trocr.export import export_model
from qai_hub_models.models.common import TargetRuntime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ai_hub_submitter")

# Apply tokenizer monkeypatch for HuggingFace Transformers 5.x compatibility
orig_from_pretrained = TrOCRProcessor.from_pretrained

def patched_from_pretrained(pretrained_model_name_or_path, *args, **kwargs):
    try:
        return orig_from_pretrained(pretrained_model_name_or_path, *args, **kwargs)
    except Exception:
        tok = XLMRobertaTokenizer.from_pretrained(pretrained_model_name_or_path)
        img = AutoImageProcessor.from_pretrained("microsoft/trocr-base-printed")
        return TrOCRProcessor(image_processor=img, tokenizer=tok)

TrOCRProcessor.from_pretrained = patched_from_pretrained


def main():
    parser = argparse.ArgumentParser(description="Submit TrOCR compile & profile job to Qualcomm AI Hub")
    parser.add_argument(
        "--device",
        type=str,
        default="Snapdragon X Elite CRD",
        help="Target Snapdragon device (default: 'Snapdragon X Elite CRD')",
    )
    parser.add_argument(
        "--runtime",
        type=str,
        default="onnx",
        choices=["onnx", "precompiled_qnn_onnx", "qnn_context_binary", "qnn_dlc"],
        help="Target runtime (default: onnx)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "trocr-qnn-compiled"),
        help="Target directory for downloaded compiled assets",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    logger.info("Initializing Qualcomm AI Hub device target: %s", args.device)
    device = hub.Device(args.device)

    target_runtime_map = {
        "onnx": TargetRuntime.ONNX,
        "precompiled_qnn_onnx": TargetRuntime.PRECOMPILED_QNN_ONNX,
        "qnn_context_binary": TargetRuntime.QNN_CONTEXT_BINARY,
        "qnn_dlc": TargetRuntime.QNN_DLC,
    }
    target_rt = target_runtime_map[args.runtime]

    logger.info("Submitting TrOCR compilation and profiling job to Qualcomm AI Hub...")
    logger.info("Target Runtime: %s", target_rt.value)
    logger.info("Target Device : %s", device.name)
    logger.info("Output Dir    : %s", args.output_dir)

    result = export_model(
        device=device,
        target_runtime=target_rt,
        output_dir=args.output_dir,
        skip_compiling=False,
        skip_profiling=False,
        skip_inferencing=False,
        skip_downloading=False,
        skip_summary=False,
    )

    print("\n" + "=" * 75)
    print("  QUALCOMM AI HUB CLOUD JOB EXECUTION COMPLETE")
    print("=" * 75)
    print(f"Target Device        : {device.name}")
    print(f"Target Runtime       : {target_rt.value}")
    print(f"Compiled Assets Dir  : {args.output_dir}")
    print("=" * 75 + "\n")

    return result


if __name__ == "__main__":
    main()
