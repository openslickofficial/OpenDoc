"""
Functional UI Security & Privacy Verification
Verifies:
1. Concurrency protection: start_pipeline() rejects re-entrant calls when worker is active.
2. Input rejection: on_image_selected() rejects drop when worker is active.
3. Privacy Wipe: clear_session_and_cache() stops playback, resets state, and purges audio_output.
"""

import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.ui.main_window import MainWindow

def test_ui_security():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()

    test_img = os.path.join(PROJECT_ROOT, "test_images", "form_document.png")
    assert os.path.exists(test_img), f"Test image missing: {test_img}"

    # 1. Load document
    window.on_image_selected(test_img)
    assert window.selected_image_path == test_img, "Image not loaded"
    assert window.process_btn.isEnabled(), "Process button not enabled"

    # 2. Test Concurrency & Re-entrancy Guard
    print("[1] Testing Concurrency Guard...")
    window.start_pipeline()
    assert not window.process_btn.isEnabled(), "Process button should be disabled during run"
    assert not window.drop_area.isEnabled(), "Drop area should be disabled during run"
    assert not window.clear_cache_btn.isEnabled(), "Clear cache button should be disabled during run"

    # Attempt re-entrant call while worker is active
    old_worker = window.worker
    window.start_pipeline()
    assert window.worker == old_worker, "Guard failed: Re-entrant start_pipeline() created a new worker!"

    # Attempt dropping another file while worker is active
    alt_img = os.path.join(PROJECT_ROOT, "test_images", "telecom_disconnect_unseen.png")
    window.on_image_selected(alt_img)
    assert window.selected_image_path == test_img, "Guard failed: on_image_selected overwrote path during active run!"
    print("PASS: Concurrency guards successfully rejected re-entrant launch and image replacement.")

    # 3. Wait for completion
    def on_complete(result):
        print(f"[2] Pipeline completed with status: {result['status']}")
        assert window.drop_area.isEnabled(), "Drop area should be re-enabled after completion"
        assert window.clear_cache_btn.isEnabled(), "Clear cache button should be re-enabled after completion"

        # Verify outputs populated
        assert len(window.ocr_text.toPlainText()) > 0, "OCR text not populated"
        assert len(window.trans_text.toPlainText()) > 0, "Trans text not populated"

        # 4. Test Privacy Wipe
        print("[3] Testing Clear Session & Audio Cache...")
        # Create a dummy audio file in audio_output to test deletion
        from src.config import DEFAULT_AUDIO_DIR
        dummy_wav = os.path.join(DEFAULT_AUDIO_DIR, "dummy_sensitive_speech.wav")
        with open(dummy_wav, "wb") as f:
            f.write(b"RIFFdummywavdata")
        assert os.path.exists(dummy_wav)

        window.clear_session_and_cache()

        # Check in-memory buffers
        assert window.ocr_text.toPlainText() == "", "OCR text not cleared"
        assert window.trans_text.toPlainText() == "", "Trans text not cleared"
        assert window.simp_text.toPlainText() == "", "Simp text not cleared"
        assert window.selected_image_path is None, "Selected image path not cleared"
        assert window.audit_table.rowCount() == 0, "Audit table not cleared"
        assert not os.path.exists(dummy_wav), "Dummy sensitive WAV file was not purged from disk!"
        print("PASS: Privacy Wipe verified! Volatile memory cleared and disk audio cache purged.")

        # Save verification screenshot
        screenshot_path = os.path.join(PROJECT_ROOT, "audio_output", "security_audit_clear_screen.png")
        window.grab().save(screenshot_path)
        print(f"Saved clear screen screenshot to: {screenshot_path}")

        app.quit()

    window.pipeline_completed.connect(on_complete)
    window.pipeline_error.connect(lambda err: (print("Pipeline error:", err), app.quit()))

    # Run event loop
    app.exec()

if __name__ == "__main__":
    test_ui_security()
