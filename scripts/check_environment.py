#!/usr/bin/env python3
"""
Environment and Hardware Acceleration Checker for Snapdragon X Document Assistant.
Validates:
1. Python version & machine architecture (ARM64 Snapdragon vs AMD64 dev machine).
2. ONNX Runtime installation and Execution Provider support (QNN vs CPU).
3. Core library dependencies (OpenCV, NumPy, Pillow, QAI Hub, Transformers).
4. Overall readiness status and cloud profiling instructions if not on ARM64.
"""

import os
import platform
import sys
from importlib.metadata import version, PackageNotFoundError

# Configure stdout for UTF-8 on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ANSI color codes for terminal formatting
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner():
    print(f"\n{CYAN}{BOLD}{'=' * 75}{RESET}")
    print(f"{CYAN}{BOLD}   Snapdragon X Elite - NPU Environment Diagnostic & Readiness Tool{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 75}{RESET}\n")


def check_python_and_arch():
    py_ver = platform.python_version()
    major, minor, micro = sys.version_info[:3]
    machine = platform.machine()
    system = platform.system()
    arch, os_type = platform.architecture()

    print(f"{BOLD}[1] Operating System & Hardware Architecture Check{RESET}")
    print(f"  * Operating System   : {system} ({platform.release()})")
    print(f"  * Machine Arch       : {machine} ({arch})")
    print(f"  * Python Version     : {py_ver} ({sys.executable})")

    is_python_311 = (major == 3 and minor == 11)
    is_arm64 = machine.upper() in ("ARM64", "AARCH64")

    warnings = []

    if is_python_311:
        print(f"  * Python 3.11 Status : {GREEN}PASS (v{py_ver}){RESET}")
    else:
        print(f"  * Python 3.11 Status : {YELLOW}WARNING (Running v{py_ver}; Python 3.11 recommended for QNN EP){RESET}")
        warnings.append(f"Python {py_ver} is running instead of recommended Python 3.11")

    if is_arm64:
        print(f"  * Target Hardware    : {GREEN}PASS - Snapdragon ARM64 hardware detected.{RESET}")
        print(f"                         Qualcomm Hexagon NPU is available locally.")
    else:
        print(f"  * Target Hardware    : {YELLOW}NOTICE - Running on {machine} (Non-Snapdragon / Dev Machine){RESET}")
        print(f"    {YELLOW}-> Note: Physical Qualcomm Hexagon NPU inference requires Snapdragon X (ARM64).{RESET}")
        print(f"    {YELLOW}-> Local inference will fall back to CPUExecutionProvider.{RESET}")
        print(f"    {YELLOW}-> To validate NPU execution before testing on physical HP OmniBook hardware,{RESET}")
        print(f"    {YELLOW}   submit profiling/compile jobs to Qualcomm AI Hub's Cloud Device Farm.{RESET}")

    return {
        "is_arm64": is_arm64,
        "is_python_311": is_python_311,
        "machine": machine,
        "py_ver": py_ver,
        "warnings": warnings,
    }


def check_onnx_runtime():
    print(f"\n{BOLD}[2] ONNX Runtime & Execution Provider Inspection{RESET}")
    ort_installed = False
    providers = []
    has_qnn = False
    ort_version = "Not installed"

    try:
        import onnxruntime as ort
        ort_installed = True
        ort_version = ort.__version__
        providers = ort.get_available_providers()
        has_qnn = "QNNExecutionProvider" in providers
    except ImportError as e:
        print(f"  * ONNX Runtime       : {RED}FAIL (Not installed or import error: {e}){RESET}")
        return {
            "installed": False,
            "version": None,
            "providers": [],
            "has_qnn": False,
        }

    print(f"  * ONNX Runtime Ver   : {GREEN}PASS (v{ort_version}){RESET}")
    print(f"  * Available Providers: {providers}")

    if has_qnn:
        print(f"  * QNN Provider Check : {GREEN}PASS - QNNExecutionProvider is active and ready for NPU!{RESET}")
    else:
        print(f"  * QNN Provider Check : {YELLOW}NOT PRESENT (Expected on non-ARM64 dev hosts){RESET}")
        if "CPUExecutionProvider" in providers:
            print(f"  * Fallback Provider  : {GREEN}PASS - CPUExecutionProvider is available for local testing.{RESET}")
        else:
            print(f"  * Fallback Provider  : {RED}FAIL - No standard CPU execution provider detected.{RESET}")

    return {
        "installed": ort_installed,
        "version": ort_version,
        "providers": providers,
        "has_qnn": has_qnn,
    }


def check_dependencies():
    print(f"\n{BOLD}[3] Core Dependencies & Toolchain Inspection{RESET}")
    packages = [
        ("numpy", "NumPy (pinned >=1.26.4 for QNN)", lambda v: v >= "1.25.2"),
        ("cv2", "OpenCV (cv2)", None),
        ("PIL", "Pillow (PIL)", None),
        ("transformers", "Hugging Face Transformers", None),
        ("torch", "PyTorch", None),
        ("qai_hub", "Qualcomm AI Hub Client (qai-hub)", None),
        ("qai_hub_models", "Qualcomm AI Hub Models (qai-hub-models)", None),
    ]

    results = {}
    for mod_name, label, validator in packages:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", None)
            if ver is None:
                try:
                    ver = version(mod_name.replace("_", "-"))
                except PackageNotFoundError:
                    ver = "installed"

            valid = True if validator is None else validator(str(ver))
            if valid:
                print(f"  * {label:<38}: {GREEN}PASS (v{ver}){RESET}")
            else:
                print(f"  * {label:<38}: {YELLOW}WARNING (v{ver} - check QNN compatibility){RESET}")
            results[mod_name] = {"installed": True, "version": ver, "valid": valid}
        except ImportError:
            print(f"  * {label:<38}: {YELLOW}PENDING / NOT INSTALLED YET{RESET}")
            results[mod_name] = {"installed": False, "version": None, "valid": False}

    return results


def check_qai_hub_config():
    print(f"\n{BOLD}[4] Qualcomm AI Hub Cloud Access Configuration{RESET}")
    token = os.environ.get("QAI_HUB_API_TOKEN", "")
    config_file = os.path.expanduser("~/.qai_hub/config.yaml")
    has_file = os.path.isfile(config_file)

    if token:
        print(f"  * QAI Hub Token (Env): {GREEN}CONFIGURED ($QAI_HUB_API_TOKEN is set){RESET}")
    elif has_file:
        print(f"  * QAI Hub Config File: {GREEN}CONFIGURED (~/.qai_hub/config.yaml exists){RESET}")
    else:
        print(f"  * QAI Hub Cloud Token: {YELLOW}NOT CONFIGURED YET{RESET}")
        print(f"    {YELLOW}-> Run 'qai-hub configure --api_token <YOUR_TOKEN>' to enable cloud device profiling on Snapdragon X Elite.{RESET}")


def print_summary(arch_info, ort_info, deps_info):
    print(f"\n{CYAN}{BOLD}{'=' * 75}{RESET}")
    print(f"{CYAN}{BOLD}                     DIAGNOSTIC SUMMARY & READINESS{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 75}{RESET}")

    critical_missing = []
    if not ort_info["installed"]:
        critical_missing.append("onnxruntime")
    if not deps_info.get("cv2", {}).get("installed"):
        critical_missing.append("opencv-python")
    if not deps_info.get("numpy", {}).get("installed"):
        critical_missing.append("numpy")
    if not deps_info.get("PIL", {}).get("installed"):
        critical_missing.append("pillow")

    if critical_missing:
        print(f"\n{RED}{BOLD}OVERALL STATUS: FAIL{RESET}")
        print(f"Missing critical dependencies: {', '.join(critical_missing)}")
        print(f"Run: pip install -r requirements.txt\n")
        return 1

    if arch_info["is_arm64"] and ort_info["has_qnn"]:
        print(f"\n{GREEN}{BOLD}OVERALL STATUS: READY FOR ON-DEVICE NPU INFERENCE{RESET}")
        print("Hardware is ARM64 Snapdragon X with QNNExecutionProvider active.")
        print("Inference will directly accelerate on the Qualcomm Hexagon NPU.\n")
        return 0
    else:
        print(f"\n{YELLOW}{BOLD}OVERALL STATUS: READY FOR DEVELOPMENT & CPU FALLBACK{RESET}")
        print(f"Running on {arch_info['machine']} workstation.")
        print("* Local inference will execute via CPUExecutionProvider (working fallback).")
        print("* Remote NPU verification is available via Qualcomm AI Hub Cloud Device Farm.")
        print(f"* Deploying to target HP OmniBook ARM64 PC will seamlessly switch to QNNExecutionProvider.\n")
        return 0


def main():
    print_banner()
    arch_info = check_python_and_arch()
    ort_info = check_onnx_runtime()
    deps_info = check_dependencies()
    check_qai_hub_config()
    exit_code = print_summary(arch_info, ort_info, deps_info)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
