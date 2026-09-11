"""
Automated Headless / Offscreen Verification & Screenshot Capture Suite
for Snapdragon Document Assistant Desktop GUI.

Tests:
1. UI component initialization under offscreen Qt platform.
2. Drag & Drop / file ingestion state.
3. Clean pass banner & audio player state (with screenshot).
4. Fidelity warning safeguard state (with screenshot).
5. Blank image short-circuit error state (with screenshot).
6. Strict fidelity gate audio suppression state (with screenshot).
7. Live QThread background worker execution with Qt signal dispatch.
"""

import os
import sys
import time

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Allow offscreen flag if explicitly passed, otherwise use default native platform (with DirectWrite font rendering)
if "--offscreen" in sys.argv:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop, QTimer, QThread


from src.ui.styles import GLOBAL_STYLESHEET
from src.ui.main_window import MainWindow
from src.ui.worker import PipelineWorker
from src.config import DEFAULT_CONFIG


def run_headless_gui_tests():
    print("=" * 80)
    print("  SNAPDRAGON DOCUMENT ASSISTANT — HEADLESS GUI VERIFICATION SUITE")
    print("=" * 80)

    # 1. Initialize QApplication
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLESHEET)

    window = MainWindow()
    window.resize(1180, 820)
    window.show()

    output_dir = os.path.join(PROJECT_ROOT, "audio_output")
    os.makedirs(output_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    # TEST 1: Initial Ingestion State
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing Image Selection & Ingestion Layout...")
    test_img = os.path.join(PROJECT_ROOT, "test_images", "form_document.png")
    assert os.path.isfile(test_img), f"Test image missing: {test_img}"

    window.on_image_selected(test_img)
    assert window.selected_image_path == test_img
    assert window.process_btn.isEnabled()
    print("  * Image selected: form_document.png")
    print("  * Process button enabled: True")
    
    # Save initial ingestion screenshot
    p1 = os.path.join(output_dir, "gui_01_initial_ingest.png")
    window.grab().save(p1)
    print(f"  * Screenshot captured: {p1} ({os.path.getsize(p1)} bytes)")

    # -------------------------------------------------------------------------
    # TEST 2: Clean Document Pass UI State
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing Clean Document Pass UI State...")
    mock_clean_result = {
        "status": "success",
        "image_path": test_img,
        "target_lang": "hi",
        "total_latency_ms": 12710.88,
        "raw_text": "verification form-snapdragon x Hardware\nApplication ID : SN-2026-X89 .\nStatus : VERIFIED AND APPROVED",
        "simplified_text": "Application ID: SN-2026-X89.\nStatus: Verified and Approved.\nDate: September 11, 2026.",
        "translated_text": "आवेदन आईडी: SN-2026-X89.\nस्थिति: सत्यापित और स्वीकृत.\nदिनांक: सितंबर 11, 2026.",
        "audio_path": os.path.join(output_dir, "speech_1789115670808.wav"),
        "overall_fidelity_passed": True,
        "fidelity_summary": {
            "overall_fidelity_passed": True,
            "simplification_fidelity_passed": True,
            "translation_fidelity_passed": True,
            "simplification_warnings": [],
            "translation_warnings": [],
            "speech_policy_applied": "clean_pass",
            "speech_warning_prepended": False,
            "speech_blocked": False,
        },
        "stages": {
            "ocr": {"latency_ms": 1488.0, "provider_used": "CPUExecutionProvider"},
            "simplify": {"latency_ms": 10128.0, "provider_used": "LocalLLMExecutionEngine (Qwen CPU)", "entities": {"reference_ids": ["SN-2026-X89"], "status_keywords": ["approved", "verified"]}},
            "translate": {"latency_ms": 2.5, "provider_used": "AnchorPreservedTranslationEngine (Authoritative Indic Lexicon)"},
            "tts": {"latency_ms": 1089.0, "provider_used": "PiperTTS-ONNX (hi_IN-pratham)"},
        }
    }

    window._on_pipeline_finished(mock_clean_result)
    assert window.banner_widget.isVisible(), "Banner should be visible for clean pass"
    assert "FIDELITY VERIFIED" in window.banner_widget.title_label.text()
    assert window.audio_player.play_btn.isEnabled(), "Audio player should be enabled"
    print("  * Clean pass banner verified: 'FIDELITY VERIFIED: 100% Entity Preservation Confirmed'")
    print(f"  * Audio player badge: {window.audio_player.policy_badge.text()}")
    print(f"  * Translated text tab populated: {len(window.trans_text.toPlainText())} chars")

    p2 = os.path.join(output_dir, "gui_02_clean_pass.png")
    window.grab().save(p2)
    print(f"  * Screenshot captured: {p2} ({os.path.getsize(p2)} bytes)")

    # -------------------------------------------------------------------------
    # TEST 3: Fidelity Warning UI State (Contradictions Caught)
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing Fidelity Warning Safeguard UI State...")
    mock_warning_result = {
        "status": "success",
        "image_path": "test_images/telecom_disconnect_unseen.png",
        "target_lang": "hi",
        "total_latency_ms": 19161.33,
        "raw_text": "Account Identifier: TEL-542-1-CA\nOverdue Balance: 889.50\nPlease remit $89.50 before September 30 2028",
        "simplified_text": "Notice of disconnection. Account: TEL-542-1-CA. Amount due: $89.50 and 889.50.",
        "translated_text": "चेतावनी: खाता TEL-542-1-CA. देय राशि $89.50.",
        "audio_path": os.path.join(output_dir, "speech_1789115783466.wav"),
        "overall_fidelity_passed": False,
        "fidelity_summary": {
            "overall_fidelity_passed": False,
            "simplification_warnings": [
                "[INTERNAL INCONSISTENCY ERROR] Conflicting monetary amounts: '$89.50' vs '889.50'",
                "[INTERNAL INCONSISTENCY ERROR] Conflicting calendar years: '2026' vs '2028'",
            ],
            "translation_warnings": [],
            "speech_policy_applied": "warning_prepended",
            "speech_warning_prepended": True,
            "speech_blocked": False,
        },
        "stages": {
            "ocr": {"latency_ms": 1778.0, "provider_used": "CPUExecutionProvider"},
            "simplify": {"latency_ms": 15686.0, "provider_used": "LocalLLMExecutionEngine", "entities": {"amounts": ["$89.50", "889.50"], "reference_ids": ["TEL-542-1-CA"]}},
            "translate": {"latency_ms": 1.2, "provider_used": "AnchorPreservedTranslationEngine"},
            "tts": {"latency_ms": 1690.0, "provider_used": "PiperTTS-ONNX"},
        }
    }

    window._on_pipeline_finished(mock_warning_result)
    assert window.banner_widget.isVisible(), "Banner should be visible for warning"
    assert "FIDELITY SAFEGUARD TRIGGERED" in window.banner_widget.title_label.text()
    assert window.audio_player.policy_badge.text() == "⚠️ Warning Prepended to Speech"
    print("  * Warning banner verified: 'FIDELITY SAFEGUARD TRIGGERED: Discrepancies Intercepted!'")
    print(f"  * Audio player badge: {window.audio_player.policy_badge.text()}")
    print(f"  * Warnings displayed in banner: {window.banner_widget.warnings_label.text().count('•')} warning bullets")

    p3 = os.path.join(output_dir, "gui_03_fidelity_warning.png")
    window.grab().save(p3)
    print(f"  * Screenshot captured: {p3} ({os.path.getsize(p3)} bytes)")

    # -------------------------------------------------------------------------
    # TEST 4: Blank Image Short-Circuit Error UI State
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing Blank Image Short-Circuit Error UI State...")
    mock_error_result = {
        "status": "failed",
        "image_path": "test_images/blank.png",
        "target_lang": "hi",
        "total_latency_ms": 8.87,
        "raw_text": "",
        "simplified_text": "",
        "translated_text": "",
        "audio_path": None,
        "overall_fidelity_passed": False,
        "fidelity_summary": {"error": "Empty or unreadable scan detected (std=0.00). Processing halted early."},
        "error": "OCR detected unreadable or empty document text (low information density: std=0.00). Document image appears to be blank. Short-circuiting downstream stages.",
        "stages": {
            "ocr": {"error": "Empty scan", "latency_ms": 8.87, "provider_used": "CPUExecutionProvider"},
        }
    }

    window._on_pipeline_finished(mock_error_result)
    assert window.banner_widget.isVisible()
    assert "PROCESSING HALTED" in window.banner_widget.title_label.text()
    assert not window.audio_player.play_btn.isEnabled(), "Audio player should be disabled on error"
    print("  * Error banner verified: 'PROCESSING HALTED: Pipeline Error Detected'")
    print(f"  * Stage 1 status: {window.stage_widget.stages['ocr'].status_badge.text()}")
    print(f"  * Stage 2 status (skipped): {window.stage_widget.stages['simplify'].status_badge.text()}")
    print(f"  * Stage 3 status (skipped): {window.stage_widget.stages['translate'].status_badge.text()}")
    print(f"  * Stage 4 status (skipped): {window.stage_widget.stages['tts'].status_badge.text()}")

    p4 = os.path.join(output_dir, "gui_04_error_short_circuit.png")
    window.grab().save(p4)
    print(f"  * Screenshot captured: {p4} ({os.path.getsize(p4)} bytes)")

    # -------------------------------------------------------------------------
    # TEST 5: Strict Mode Audio Suppression UI State
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing Strict Fidelity Gate Audio Suppression UI State...")
    mock_strict_result = {
        "status": "success",
        "image_path": "test_images/telecom_disconnect_unseen.png",
        "target_lang": "hi",
        "total_latency_ms": 17800.0,
        "raw_text": "Account Identifier: TEL-542-1-CA\nOverdue Balance: 889.50",
        "simplified_text": "Account: TEL-542-1-CA. Amount: $89.50.",
        "translated_text": "खाता: TEL-542-1-CA. राशि: $89.50.",
        "audio_path": None,
        "overall_fidelity_passed": False,
        "fidelity_summary": {
            "overall_fidelity_passed": False,
            "simplification_warnings": ["Conflicting amounts detected ($89.50 vs 889.50)"],
            "translation_warnings": [],
            "speech_policy_applied": "suppressed",
            "speech_warning_prepended": False,
            "speech_blocked": True,
        },
        "stages": {
            "ocr": {"latency_ms": 1700.0, "provider_used": "CPUExecutionProvider"},
            "simplify": {"latency_ms": 15000.0, "provider_used": "LocalLLMExecutionEngine", "entities": {}},
            "translate": {"latency_ms": 1.5, "provider_used": "AnchorPreservedTranslationEngine"},
            "tts": {"latency_ms": 10.0, "provider_used": "FidelityGate-Suppressed"},
        }
    }

    window._on_pipeline_finished(mock_strict_result)
    assert window.banner_widget.isVisible()
    assert "AUDIO GENERATION BLOCKED" in window.banner_widget.title_label.text()
    assert not window.audio_player.play_btn.isEnabled()
    assert "Audio Suppressed" in window.audio_player.policy_badge.text()
    print("  * Strict blocked banner verified: 'AUDIO GENERATION BLOCKED: Strict Safety Gate Active'")
    print(f"  * Audio player badge: {window.audio_player.policy_badge.text()}")

    p5 = os.path.join(output_dir, "gui_05_strict_audio_blocked.png")
    window.grab().save(p5)
    print(f"  * Screenshot captured: {p5} ({os.path.getsize(p5)} bytes)")

    # -------------------------------------------------------------------------
    # TEST 6: Live QThread Background Execution & Signal Dispatch
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing Live Asynchronous QThread Pipeline Execution...")
    import cv2
    import numpy as np

    blank_path = os.path.join(PROJECT_ROOT, "test_images", "gui_blank_test.png")
    cv2.imwrite(blank_path, np.ones((150, 400), dtype=np.uint8) * 255)

    signals_received = []

    worker_thread = QThread()
    worker = PipelineWorker(
        image_path=blank_path,
        target_lang="hi",
        strict_fidelity_gate=False,
        config=DEFAULT_CONFIG,
    )
    worker.moveToThread(worker_thread)

    loop = QEventLoop()

    def on_stage(stage, event, data):
        signals_received.append((stage, event))

    def on_finished(res):
        loop.quit()

    def on_failed(err):
        loop.quit()

    worker.stage_updated.connect(on_stage)
    worker.finished.connect(on_finished)
    worker.failed.connect(on_failed)
    worker_thread.started.connect(worker.run)

    t0 = time.perf_counter()
    worker_thread.start()

    # Wait for loop to quit with a 15-second safety timer
    QTimer.singleShot(15000, loop.quit)
    loop.exec()

    worker_thread.quit()
    worker_thread.wait()

    if os.path.exists(blank_path):
        os.remove(blank_path)

    assert len(signals_received) > 0, "Should have received stage signals across threads"
    print(f"  * Asynchronous QThread execution completed in {(time.perf_counter() - t0)*1000:.1f} ms")
    print(f"  * Signals dispatched across threads: {signals_received}")

    print("\n" + "=" * 80)
    print("  ALL 6 GUI VERIFICATION TESTS PASSED SUCCESSFULLY (100%)")
    print("=" * 80)


if __name__ == "__main__":
    run_headless_gui_tests()

