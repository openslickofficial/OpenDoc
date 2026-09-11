"""
Desktop Application Lifecycle Manager for Snapdragon Document Assistant.
Instantiates the QApplication, applies global accessible styles,
and launches the MainWindow with optional automated CLI driving.
"""

import os
import sys
import json
import argparse
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

from src.ui.styles import GLOBAL_STYLESHEET
from src.ui.main_window import MainWindow


def run_app():
    """Initializes and runs the PySide6 desktop GUI application."""
    parser = argparse.ArgumentParser(description="Snapdragon Document Assistant")
    parser.add_argument("--image", type=str, default=None, help="Path to document scan to load")
    parser.add_argument("--auto-process", action="store_true", help="Automatically trigger processing on launch")
    parser.add_argument("--strict", action="store_true", help="Enable strict safety gate")
    parser.add_argument("--save-screenshot", type=str, default=None, help="Save GUI screenshot to file on finish")
    parser.add_argument("--dump-json", type=str, default=None, help="Dump pipeline result JSON to file on finish")
    parser.add_argument("--exit-on-finish", action="store_true", help="Exit application when pipeline completes")

    args, unknown = parser.parse_known_args()

    # Ensure application exists
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    app.setApplicationName("Snapdragon Document Assistant")
    app.setOrganizationName("Qualcomm AI Hub Hackathon")
    app.setStyleSheet(GLOBAL_STYLESHEET)

    window = MainWindow()
    window.show()

    if args.image:
        abs_img = os.path.abspath(args.image)
        window.on_image_selected(abs_img)

        if args.strict:
            window.strict_gate_check.setChecked(True)

        if args.auto_process:
            def on_finish(result=None):
                QApplication.processEvents()
                if args.save_screenshot:
                    os.makedirs(os.path.dirname(os.path.abspath(args.save_screenshot)), exist_ok=True)
                    window.grab().save(args.save_screenshot)
                    print(f"[UI-AUTO] Screenshot saved to: {args.save_screenshot}")
                if args.dump_json and window.last_pipeline_result:
                    os.makedirs(os.path.dirname(os.path.abspath(args.dump_json)), exist_ok=True)
                    with open(args.dump_json, "w", encoding="utf-8") as f:
                        json.dump(window.last_pipeline_result, f, indent=2, ensure_ascii=False)
                    print(f"[UI-AUTO] Result dumped to: {args.dump_json}")
                if args.exit_on_finish:
                    QTimer.singleShot(600, app.quit)

            window.pipeline_completed.connect(on_finish)
            window.pipeline_error.connect(lambda err: on_finish(None))
            QTimer.singleShot(250, window.start_pipeline)

    return app.exec()


if __name__ == "__main__":
    sys.exit(run_app())

