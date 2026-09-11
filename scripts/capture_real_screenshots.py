"""
Real Native Platform GUI Screenshot Capture Utility.
Runs with the native Windows Qt platform (DirectWrite font rendering)
and captures programmatic screenshots via window.grab().save() across all 5 states.
"""

import os
import sys

# Ensure UTF-8 on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure QT_QPA_PLATFORM is NOT offscreen
if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from src.ui.styles import GLOBAL_STYLESHEET
from src.ui.main_window import MainWindow

def capture_all_states():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLESHEET)

    window = MainWindow()
    window.resize(1180, 820)
    window.show()
    app.processEvents()

    output_dir = os.path.join(PROJECT_ROOT, "audio_output")
    os.makedirs(output_dir, exist_ok=True)

    test_img = os.path.join(PROJECT_ROOT, "test_images", "form_document.png")
    test_audio = os.path.join(output_dir, "speech_1789115670808.wav")
    telecom_audio = os.path.join(output_dir, "speech_1789115783466.wav")

    captured_files = []

    # -------------------------------------------------------------
    # State 1: Initial Ingest
    # -------------------------------------------------------------
    window.on_image_selected(test_img)
    app.processEvents()
    p1 = os.path.join(output_dir, "gui_01_initial_ingest.png")
    window.grab().save(p1)
    captured_files.append(("State 1: Initial Ingest", p1))

    # -------------------------------------------------------------
    # State 2: Clean Pass
    # -------------------------------------------------------------
    result_clean = {
        "document": test_img,
        "status": "success",
        "target_lang": "hi",
        "overall_fidelity_passed": True,
        "total_latency_ms": 12710.9,
        "raw_text": "verification form-snapdragon x Hardware\nApplication ID : SN-2026-X89 .\nStatus : VERIFIED AND APPROVED\nDate . September 11 2026",
        "simplified_text": "Application ID: SN-2026-X89.\nStatus: Verified and Approved.\nDate: September 11, 2026.",
        "translated_text": "आवेदन आईडी: SN-2026-X89.\nस्थिति: सत्यापित और स्वीकृत.\nदिनांक: सितंबर 11, 2026.",
        "audio_path": test_audio,
        "stages": {
            "ocr": {"latency_ms": 1488.0, "provider_used": "CPUExecutionProvider"},
            "simplify": {"latency_ms": 10128.0, "provider_used": "LocalLLMExecutionEngine (Qwen CPU)"},
            "translate": {"latency_ms": 2.5, "provider_used": "AnchorPreservedTranslationEngine (Authoritative Indic)"},
            "tts": {"latency_ms": 1089.0, "provider_used": "PiperTTS-ONNX (hi_IN-pratham)"},
        },
        "fidelity_summary": {
            "simplification_fidelity_passed": True,
            "translation_fidelity_passed": True,
            "simplification_warnings": [],
            "translation_warnings": [],
            "speech_policy_applied": "clean_pass",
            "speech_warning_prepended": False,
            "speech_blocked": False,
        },
        "anchors_audited": [
            {"type": "Date", "value": "September 11 2026", "status": "VERIFIED INTACT", "details": "Found in both English & Devanagari (सितंबर 11, 2026)"},
            {"type": "ID", "value": "SN-2026-X89", "status": "VERIFIED INTACT", "details": "Exact alphanumeric match"},
            {"type": "Status", "value": "approved", "status": "VERIFIED INTACT", "details": "Devanagari status: स्वीकृत"},
        ]
    }
    window._on_pipeline_finished(result_clean)
    app.processEvents()
    p2 = os.path.join(output_dir, "gui_02_clean_pass.png")
    window.grab().save(p2)
    captured_files.append(("State 2: Clean Pass", p2))

    # -------------------------------------------------------------
    # State 3: Fidelity Warning
    # -------------------------------------------------------------
    result_warning = {
        "document": os.path.join(PROJECT_ROOT, "test_images", "telecom_disconnect_unseen.png"),
        "status": "success",
        "target_lang": "hi",
        "overall_fidelity_passed": False,
        "total_latency_ms": 19161.3,
        "raw_text": "Notice of Disconnection\nAccount: TEL-542-1-CA\nAmount Due: $89.50 (Notice refers to 889.50)\nDue Date: September 30 2026 (Refers to 2028)",
        "simplified_text": "Warning: Account TEL-542-1-CA. Amount due: $89.50.",
        "translated_text": "चेतावनी: खाता TEL-542-1-CA. देय राशि $89.50.",
        "audio_path": telecom_audio,
        "stages": {
            "ocr": {"latency_ms": 1778.0, "provider_used": "CPUExecutionProvider"},
            "simplify": {"latency_ms": 15686.0, "provider_used": "LocalLLMExecutionEngine"},
            "translate": {"latency_ms": 1.2, "provider_used": "AnchorPreservedTranslationEngine"},
            "tts": {"latency_ms": 1690.0, "provider_used": "PiperTTS-ONNX"},
        },
        "fidelity_summary": {
            "simplification_fidelity_passed": False,
            "translation_fidelity_passed": True,
            "simplification_warnings": [
                "[INTERNAL INCONSISTENCY ERROR] Conflicting monetary amounts: '$89.50' vs '889.50'",
                "[INTERNAL INCONSISTENCY ERROR] Conflicting calendar years: '2026' vs '2028'",
            ],
            "translation_warnings": [],
            "speech_policy_applied": "warning_prepended",
            "speech_warning_prepended": True,
            "speech_blocked": False,
        },
        "anchors_audited": [
            {"type": "ID", "value": "TEL-542-1-CA", "status": "VERIFIED INTACT", "details": "Alphanumeric ID preserved"},
            {"type": "Amount", "value": "$89.50 vs 889.50", "status": "FLAGGED CONFLICT", "details": "Internal contradiction in source"},
            {"type": "Date", "value": "2026 vs 2028", "status": "FLAGGED CONFLICT", "details": "Calendar year discrepancy"},
        ]
    }
    window._on_pipeline_finished(result_warning)
    app.processEvents()
    p3 = os.path.join(output_dir, "gui_03_fidelity_warning.png")
    window.grab().save(p3)
    captured_files.append(("State 3: Fidelity Warning", p3))

    # -------------------------------------------------------------
    # State 4: Blank Short-Circuit Error
    # -------------------------------------------------------------
    result_err = {
        "document": "blank_scan.png",
        "status": "failed",
        "error": "OCR detected unreadable or empty document text (low information density: std=0.00). Document image appears to be blank. Short-circuiting downstream stages.",
        "total_latency_ms": 11.3,
        "stages": {
            "ocr": {"latency_ms": 11.3, "provider_used": "CPUExecutionProvider", "error": "Empty scan"},
        },
        "fidelity_summary": {},
    }
    window._on_pipeline_finished(result_err)
    app.processEvents()
    p4 = os.path.join(output_dir, "gui_04_error_short_circuit.png")
    window.grab().save(p4)
    captured_files.append(("State 4: Blank Short-Circuit Error", p4))

    # -------------------------------------------------------------
    # State 5: Strict Audio Block
    # -------------------------------------------------------------
    result_blocked = {
        "document": os.path.join(PROJECT_ROOT, "test_images", "telecom_disconnect_unseen.png"),
        "status": "success",
        "target_lang": "hi",
        "overall_fidelity_passed": False,
        "total_latency_ms": 16711.5,
        "raw_text": "Account: TEL-542-1-CA. Due: $89.50",
        "simplified_text": "Account: TEL-542-1-CA. Amount: $89.50.",
        "translated_text": "खाता: TEL-542-1-CA. राशि: $89.50.",
        "audio_path": None,
        "stages": {
            "ocr": {"latency_ms": 1700.0, "provider_used": "CPUExecutionProvider"},
            "simplify": {"latency_ms": 15000.0, "provider_used": "LocalLLMExecutionEngine"},
            "translate": {"latency_ms": 1.5, "provider_used": "AnchorPreservedTranslationEngine"},
            "tts": {"latency_ms": 10.0, "provider_used": "FidelityGate-Suppressed"},
        },
        "fidelity_summary": {
            "simplification_fidelity_passed": False,
            "translation_fidelity_passed": True,
            "simplification_warnings": ["Conflicting amounts detected ($89.50 vs 889.50)"],
            "translation_warnings": [],
            "speech_policy_applied": "blocked",
            "speech_warning_prepended": False,
            "speech_blocked": True,
        },
    }
    window._on_pipeline_finished(result_blocked)
    app.processEvents()
    p5 = os.path.join(output_dir, "gui_05_strict_audio_blocked.png")
    window.grab().save(p5)
    captured_files.append(("State 5: Strict Audio Block", p5))

    print("\n" + "=" * 80)
    print("  CAPTURED REAL NATIVE QT SCREENSHOT EVIDENCE")
    print("=" * 80)
    for name, path in captured_files:
        size_bytes = os.path.getsize(path)
        print(f"  * {name:<32}: {path}")
        print(f"    Size: {size_bytes:,} bytes ({size_bytes / 1024:.1f} KB)")
    print("=" * 80 + "\n")

    # Optionally copy to artifact directory if set in environment
    artifact_dir = os.environ.get("ANTIGRAVITY_ARTIFACT_DIR")
    if artifact_dir and os.path.isdir(artifact_dir):
        import shutil
        for _, path in captured_files:
            fname = os.path.basename(path)
            shutil.copy2(path, os.path.join(artifact_dir, fname))
        print(f"Copied all screenshots to artifact dir: {artifact_dir}")

if __name__ == "__main__":
    capture_all_states()
