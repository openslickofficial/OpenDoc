"""
CLI Entry Point for Snapdragon Document Assistant Pipeline.
Processes an input document image end-to-end through:
1. OCR (TrOCR)
2. Plain-Language Simplification (Qwen3-1.7B)
3. Indian Language Translation (AnchorPreserved / Hindi)
4. Speech Synthesis (Piper ONNX)

Usage:
  python scripts/run_pipeline.py test_images/form_document.png
  python scripts/run_pipeline.py test_images/legal_notice_deadline.png --lang hi --strict
  python scripts/run_pipeline.py test_images/medical_bill_receipt.png --json
"""

import os
import sys
import json
import argparse

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import PipelineConfig
from src.pipeline import process_document

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def print_banner(text: str):
    print("\n" + "=" * 78)
    print(f"  {BOLD}{text}{RESET}")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(
        description="Snapdragon Document Assistant - End-to-End Multimodal Pipeline"
    )
    parser.add_argument("image_path", help="Path to input document image (PNG/JPG/TIFF)")
    parser.add_argument("--lang", default="hi", help="Target Indian language code (default: hi)")
    parser.add_argument("--strict", action="store_true", help="Enable strict fidelity suppression for speech")
    parser.add_argument("--mode", choices=["auto", "npu", "cpu"], default="auto", help="Execution mode")
    parser.add_argument("--bundle", choices=["qwen17", "phi35"], default="qwen17", help="Simplification bundle")
    parser.add_argument("--config", help="Optional path to custom JSON configuration file")
    parser.add_argument("--output-dir", help="Directory to store synthesized speech audio files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON to stdout")
    parser.add_argument("--save-json", help="Path to save output result JSON")

    args = parser.parse_args()

    # Load base config
    if args.config:
        config = PipelineConfig.from_json(args.config)
    else:
        config = PipelineConfig()

    # Apply CLI flag overrides
    config.target_lang = args.lang
    config.strict_fidelity_gate = args.strict
    config.engine_mode = args.mode
    config.bundle_name = args.bundle
    if args.output_dir:
        config.tts_output_dir = args.output_dir

    # Execute pipeline
    result = process_document(
        image_path=args.image_path,
        target_lang=config.target_lang,
        strict_fidelity_gate=config.strict_fidelity_gate,
        config=config,
    )

    # Save JSON if requested
    if args.save_json:
        os.makedirs(os.path.dirname(os.path.abspath(args.save_json)), exist_ok=True)
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    # Machine-readable stdout JSON mode for Phase 6 Desktop UI
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["status"] in ["success", "partial_success"] else 1)

    # Human-readable formatted terminal output
    print_banner("SNAPDRAGON DOCUMENT ASSISTANT: PIPELINE EXECUTION REPORT")
    print(f"Input Document : {BOLD}{args.image_path}{RESET}")
    print(f"Target Language: {BOLD}{result['target_lang'].upper()}{RESET}")
    status_color = GREEN if result["status"] == "success" else (YELLOW if result["status"] == "partial_success" else RED)
    print(f"Overall Status : {status_color}{BOLD}{result['status'].upper()}{RESET}")
    print(f"Total Latency  : {BOLD}{result['total_latency_ms']:.2f} ms ({result['total_latency_ms']/1000.0:.2f} s){RESET}")

    if result["status"] == "failed":
        print(f"\n{RED}[FAILURE ERROR]{RESET} {result['error']}")
        sys.exit(1)

    # Stage Latency Breakdown
    stages = result.get("stages", {})
    print(f"\n{BOLD}Stage Performance & Provider Breakdown:{RESET}")
    print(f"{'-'*78}")
    print(f"{'Stage':<18} | {'Latency (ms)':<14} | {'Provider Used':<40}")
    print(f"{'-'*78}")
    if "ocr" in stages:
        print(f"{'1. OCR':<18} | {stages['ocr'].get('latency_ms', 0):<14.2f} | {stages['ocr'].get('provider_used', 'N/A'):<40}")
    if "simplify" in stages:
        print(f"{'2. Simplify':<18} | {stages['simplify'].get('latency_ms', 0):<14.2f} | {stages['simplify'].get('provider_used', 'N/A'):<40}")
    if "translate" in stages:
        print(f"{'3. Translate':<18} | {stages['translate'].get('latency_ms', 0):<14.2f} | {stages['translate'].get('provider_used', 'N/A'):<40}")
    if "tts" in stages:
        print(f"{'4. Speech (TTS)':<18} | {stages['tts'].get('latency_ms', 0):<14.2f} | {stages['tts'].get('provider_used', 'N/A'):<40}")
    print(f"{'-'*78}")

    # Intermediate Outputs
    print(f"\n{CYAN}{BOLD}--- [1] Raw OCR Text (Cleaned) ---{RESET}")
    for l in result["raw_text"].splitlines():
        print(f"  | {l}")

    print(f"\n{CYAN}{BOLD}--- [2] Plain-Language Simplified English ---{RESET}")
    for l in result["simplified_text"].splitlines():
        print(f"  > {l}")

    print(f"\n{CYAN}{BOLD}--- [3] Hindi Translated Output ---{RESET}")
    for l in result["translated_text"].splitlines():
        print(f"  * {l}")

    # Fidelity Safeguard Audit
    fid = result.get("fidelity_summary", {})
    fid_pass = fid.get("overall_fidelity_passed", False)
    fid_color = GREEN if fid_pass else YELLOW
    print(f"\n{BOLD}Fidelity Safeguard & Speech Policy Audit:{RESET}")
    print(f"  • Overall Fidelity Status: {fid_color}{BOLD}{'PASSED' if fid_pass else 'FLAGGED DISCREPANCIES'}{RESET}")
    print(f"  • Simplification Fidelity: {'PASS' if fid.get('simplification_fidelity_passed') else 'FLAGGED'}")
    print(f"  • Translation Fidelity   : {'PASS' if fid.get('translation_fidelity_passed') else 'FLAGGED'}")
    print(f"  • Speech Policy Applied  : {BOLD}{fid.get('speech_policy_applied')}{RESET}")

    if fid.get("simplification_warnings"):
        print(f"  • Simplification Warnings ({len(fid['simplification_warnings'])}):")
        for w in fid["simplification_warnings"]:
            print(f"    - {YELLOW}{w}{RESET}")

    if fid.get("translation_warnings"):
        print(f"  • Translation Warnings ({len(fid['translation_warnings'])}):")
        for w in fid["translation_warnings"]:
            print(f"    - {YELLOW}{w}{RESET}")

    # Audio Output
    if result["audio_path"]:
        duration_s = stages.get("tts", {}).get("duration_ms", 0) / 1000.0
        print(f"\n{GREEN}{BOLD}[Audio Output Generated]{RESET}")
        print(f"  File Path: {BOLD}{result['audio_path']}{RESET} ({duration_s:.2f} seconds)")
    else:
        print(f"\n{YELLOW}[No Audio Generated]{RESET} ({result.get('error') or 'Suppressed by policy'})")

    print("\n" + "=" * 78 + "\n")


if __name__ == "__main__":
    main()
