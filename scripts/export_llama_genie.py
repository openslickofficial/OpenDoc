#!/usr/bin/env python3
"""
Qualcomm AI Hub Genie Model Exporter: Llama-3.2-3B-Instruct.
Exports Llama-3.2-3B quantized context binaries targeting Snapdragon X Elite Hexagon HTP.
Includes Windows-compatible fcntl emulation for execution on Windows dev hosts.
"""

import os
import sys
import types
import argparse

# Windows fcntl emulation: qai_hub_models imports fcntl on line 5 of common.py
if "fcntl" not in sys.modules:
    mock_fcntl = types.ModuleType("fcntl")
    mock_fcntl.LOCK_EX = 0
    mock_fcntl.LOCK_UN = 0
    mock_fcntl.flock = lambda fd, op: None
    sys.modules["fcntl"] = mock_fcntl


def main():
    parser = argparse.ArgumentParser(
        description="Export Llama-3.2-3B-Instruct to Genie context binaries for Snapdragon X Elite"
    )
    parser.add_argument(
        "--device",
        default="Snapdragon X Elite CRD",
        help="Target Qualcomm hardware device (default: 'Snapdragon X Elite CRD')",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "genie_bundle"),
        help="Output directory for Genie bundle assets",
    )
    parser.add_argument(
        "--skip-profiling",
        action="store_true",
        default=False,
        help="Skip on-device profiling on AI Hub device farm",
    )
    args, unknown = parser.parse_known_args()

    print("=" * 70)
    print("QUALCOMM AI HUB GENIE EXPORT: Llama-3.2-3B-Instruct")
    print(f"Target Hardware Device : {args.device}")
    print(f"Target Runtime         : Genie (GenAI Inference Extensions)")
    print(f"Output Directory       : {args.output_dir}")
    print("=" * 70)

    try:
        from qai_hub_models.models.llama_v3_2_3b_instruct import export
        print("[*] Submitting Genie export job to Qualcomm AI Hub...")
        cmd_args = ["export.py", "--device", args.device, "--runtime", "genie", "--output-dir", args.output_dir]
        if args.skip_profiling:
            cmd_args.append("--skip-profiling")
        sys.argv = cmd_args
        export.main()
        print("[+] Genie export completed successfully!")
    except Exception as e:
        print(f"[-] Export notice/error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

