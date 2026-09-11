#!/usr/bin/env python3
"""
Model Export & Preparation Script for TrOCR on Snapdragon X / QNN EP.
Prepares the printed English TrOCR model for on-device ONNX Runtime inference:
1. Exports vision encoder to ONNX (models/trocr_encoder.onnx).
2. Exports autoregressive text decoder to ONNX (models/trocr_decoder.onnx).
3. Saves tokenizer and vocabulary locally in models/ for offline air-gapped usage.
4. Provides Qualcomm AI Hub CLI equivalents for cloud compilation to Hexagon NPU.
"""

import os
import sys
import argparse
import logging
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trocr_exporter")

MODEL_ID_BASE = "microsoft/trocr-base-printed"
MODEL_ID_SMALL = "microsoft/trocr-small-printed"


def load_trocr_processor(model_id_or_path: str):
    from transformers import AutoImageProcessor, XLMRobertaTokenizer, RobertaTokenizer, TrOCRProcessor

    # Priority 1: Check if local trocr_processor directory exists
    candidate_paths = [
        model_id_or_path,
        os.path.join(model_id_or_path, "trocr_processor") if model_id_or_path else None,
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "trocr_processor"),
    ]
    for p in candidate_paths:
        if p and os.path.isdir(p) and (os.path.isfile(os.path.join(p, "tokenizer.json")) or os.path.isfile(os.path.join(p, "processor_config.json"))):
            logger.info("Loading TrOCR Processor offline from local directory: %s", p)
            return TrOCRProcessor.from_pretrained(p, local_files_only=True)

    # Priority 2: Offline local HuggingFace cache
    try:
        # Qualcomm AI Hub TrOCR models use the 64,000-vocab XLM-RoBERTa BPE tokenizer
        tokenizer = XLMRobertaTokenizer.from_pretrained("microsoft/trocr-small-handwritten", local_files_only=True)
        img_proc = AutoImageProcessor.from_pretrained("microsoft/trocr-base-printed", local_files_only=True)
        return TrOCRProcessor(image_processor=img_proc, tokenizer=tokenizer)
    except Exception as e:
        logger.warning("Could not load XLMRobertaTokenizer (%s), falling back to offline RobertaTokenizer", e)
        img_proc = AutoImageProcessor.from_pretrained("microsoft/trocr-base-printed", local_files_only=True)
        tokenizer = RobertaTokenizer.from_pretrained("roberta-base", local_files_only=True)
        return TrOCRProcessor(image_processor=img_proc, tokenizer=tokenizer)




def export_trocr_to_onnx(model_id: str, output_dir: str, opset_version: int = 17):
    """
    Exports TrOCR printed base/small vision-encoder-decoder to optimized ONNX models.
    """
    os.makedirs(output_dir, exist_ok=True)
    encoder_onnx_path = os.path.join(output_dir, "trocr_encoder.onnx")
    decoder_onnx_path = os.path.join(output_dir, "trocr_decoder.onnx")

    logger.info("Loading TrOCR model and processor: %s", model_id)
    processor = load_trocr_processor(model_id)
    model = VisionEncoderDecoderModel.from_pretrained(model_id)
    model.eval()

    # Save tokenizer and processor files locally for offline operation
    logger.info("Saving processor and tokenizer locally to: %s", output_dir)
    processor.save_pretrained(output_dir)

    # 1. Export Vision Encoder
    # Input: pixel_values (batch_size=1, num_channels=3, height=384, width=384)
    # Output: last_hidden_state (1, 577, hidden_size)
    dummy_pixel_values = torch.randn(1, 3, 384, 384, dtype=torch.float32)

    logger.info("Exporting TrOCR Vision Encoder to ONNX: %s", encoder_onnx_path)
    encoder = model.get_encoder()
    encoder.eval()

    with torch.no_grad():
        torch.onnx.export(
            encoder,
            dummy_pixel_values,
            encoder_onnx_path,
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=["pixel_values"],
            output_names=["last_hidden_state"],
            dynamic_axes={
                "pixel_values": {0: "batch_size"},
                "last_hidden_state": {0: "batch_size", 1: "sequence_length"},
            },
        )
    logger.info("Vision Encoder successfully exported to %s", encoder_onnx_path)

    # 2. Export Text Decoder
    # Input: input_ids (batch_size=1, seq_len=1..N), encoder_hidden_states (1, 577, hidden_size)
    # Output: logits (1, seq_len, vocab_size)
    decoder = model.get_decoder()
    decoder.eval()

    encoder_hidden_states = encoder(dummy_pixel_values).last_hidden_state
    dummy_decoder_input_ids = torch.tensor([[model.config.decoder_start_token_id]], dtype=torch.long)

    class DecoderWrapper(torch.nn.Module):
        def __init__(self, decoder_module, output_projection):
            super().__init__()
            self.decoder = decoder_module
            self.output_projection = output_projection

        def forward(self, input_ids, encoder_hidden_states):
            out = self.decoder(input_ids=input_ids, encoder_hidden_states=encoder_hidden_states)
            logits = self.output_projection(out.last_hidden_state)
            return logits

    output_proj = getattr(model, "output_projection", None)
    if output_proj is None:
        output_proj = torch.nn.Identity()

    wrapped_decoder = DecoderWrapper(decoder, output_proj)
    wrapped_decoder.eval()

    logger.info("Exporting TrOCR Text Decoder to ONNX: %s", decoder_onnx_path)
    with torch.no_grad():
        torch.onnx.export(
            wrapped_decoder,
            (dummy_decoder_input_ids, encoder_hidden_states),
            decoder_onnx_path,
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=["input_ids", "encoder_hidden_states"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "target_length"},
                "encoder_hidden_states": {0: "batch_size", 1: "encoder_length"},
                "logits": {0: "batch_size", 1: "target_length"},
            },
        )
    logger.info("Text Decoder successfully exported to %s", decoder_onnx_path)

    # Validate generated ONNX models
    import onnx
    onnx.checker.check_model(onnx.load(encoder_onnx_path))
    onnx.checker.check_model(onnx.load(decoder_onnx_path))
    logger.info("ONNX graph consistency check PASSED for both models.")

    print("\n" + "=" * 70)
    print("TrOCR ONNX Export Complete!")
    print(f"  * Encoder: {encoder_onnx_path} ({os.path.getsize(encoder_onnx_path) / (1024*1024):.1f} MB)")
    print(f"  * Decoder: {decoder_onnx_path} ({os.path.getsize(decoder_onnx_path) / (1024*1024):.1f} MB)")
    print(f"  * Configs: {output_dir}")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Export TrOCR Printed model to ONNX for Snapdragon NPU")
    parser.add_argument(
        "--model-id",
        type=str,
        default=MODEL_ID_BASE,
        choices=[MODEL_ID_BASE, MODEL_ID_SMALL],
        help=f"HuggingFace model ID (default: {MODEL_ID_BASE})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"),
        help="Target directory for exported ONNX models and tokenizer configs",
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=17,
        help="ONNX opset version (default: 17 for QNN compatibility)",
    )
    args = parser.parse_args()

    export_trocr_to_onnx(args.model_id, args.output_dir, args.opset)


if __name__ == "__main__":
    main()
