"""
Visual 4-Stage Pipeline Progress & Execution Badge Widget.
Shows real-time status of each stage (OCR, Simplify, Translate, TTS)
along with hardware execution provider and latency metrics upon completion.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QProgressBar
)
from PySide6.QtCore import Qt

from src.ui.styles import (
    BG_CARD, BG_INPUT, BORDER_DEFAULT, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, ACCENT_CYAN, STATE_SUCCESS_TEXT, STATE_WARNING_TEXT,
    STATE_ERROR_TEXT
)


class SingleStageRow(QFrame):
    """Single row representing one pipeline stage."""

    def __init__(self, stage_id: str, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.stage_id = stage_id
        self.title = title
        self.setObjectName("stageRow")
        self._setup_ui()
        self.set_pending()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(4)

        # Top row: Title + Status Indicator
        self.top_row = QHBoxLayout()
        self.top_row.setSpacing(8)

        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};")
        self.top_row.addWidget(self.title_label, 1)

        self.status_badge = QLabel("Pending")
        self.status_badge.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT_MUTED};")
        self.top_row.addWidget(self.status_badge)

        self.layout.addLayout(self.top_row)

        # Subtitle: Provider & Latency details
        self.details_label = QLabel("Awaiting document processing...")
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        self.layout.addWidget(self.details_label)

        self.setStyleSheet(f"""
            QFrame#stageRow {{
                background-color: {BG_INPUT};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: 6px;
            }}
        """)

    def set_pending(self):
        self.status_badge.setText("⚪ Pending")
        self.status_badge.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT_MUTED};")
        self.details_label.setText("Waiting for preceding stages...")
        self.details_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        self.setStyleSheet(f"""
            QFrame#stageRow {{
                background-color: {BG_INPUT};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: 6px;
            }}
        """)

    def set_running(self, info: str = "Processing on device..."):
        self.status_badge.setText("🔄 Running...")
        self.status_badge.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {ACCENT_CYAN};")
        self.details_label.setText(info)
        self.details_label.setStyleSheet(f"font-size: 11px; color: {ACCENT_CYAN};")
        self.setStyleSheet(f"""
            QFrame#stageRow {{
                background-color: #0c1a2e;
                border: 1px solid {ACCENT_CYAN};
                border-radius: 6px;
            }}
        """)

    def set_completed(self, latency_ms: float, provider: str, note: str = ""):
        self.status_badge.setText("✅ Complete")
        self.status_badge.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {STATE_SUCCESS_TEXT};")
        details = f"{latency_ms:.1f} ms via {provider}"
        if note:
            details += f" ({note})"
        self.details_label.setText(details)
        self.details_label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        self.setStyleSheet(f"""
            QFrame#stageRow {{
                background-color: {BG_INPUT};
                border: 1px solid #1e452a;
                border-radius: 6px;
            }}
        """)

    def set_warning(self, latency_ms: float, provider: str, warning_msg: str):
        self.status_badge.setText("⚠️ Warning")
        self.status_badge.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {STATE_WARNING_TEXT};")
        self.details_label.setText(f"{latency_ms:.1f} ms via {provider} — {warning_msg}")
        self.details_label.setStyleSheet(f"font-size: 11px; color: {STATE_WARNING_TEXT};")
        self.setStyleSheet(f"""
            QFrame#stageRow {{
                background-color: #261b0a;
                border: 1px solid {STATE_WARNING_TEXT};
                border-radius: 6px;
            }}
        """)

    def set_failed(self, error_msg: str):
        self.status_badge.setText("❌ Failed")
        self.status_badge.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {STATE_ERROR_TEXT};")
        self.details_label.setText(error_msg)
        self.details_label.setStyleSheet(f"font-size: 11px; color: {STATE_ERROR_TEXT};")
        self.setStyleSheet(f"""
            QFrame#stageRow {{
                background-color: #2a0e16;
                border: 1px solid {STATE_ERROR_TEXT};
                border-radius: 6px;
            }}
        """)

    def set_skipped(self, reason: str = "Short-circuited due to earlier failure"):
        self.status_badge.setText("⏸️ Skipped")
        self.status_badge.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {TEXT_MUTED};")
        self.details_label.setText(reason)
        self.details_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        self.setStyleSheet(f"""
            QFrame#stageRow {{
                background-color: {BG_INPUT};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: 6px;
            }}
        """)


class StageWidget(QFrame):
    """
    Panel containing all 4 stage rows and overall progress state.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("stageCard")
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(10)

        # Header
        self.header_label = QLabel("PIPELINE EXECUTION STAGES")
        self.header_label.setStyleSheet(
            f"font-size: 11px; font-weight: bold; letter-spacing: 1px; color: {TEXT_MUTED};"
        )
        self.layout.addWidget(self.header_label)

        # 4 Stage Rows
        self.stages = {
            "ocr": SingleStageRow("ocr", "1. Document OCR (TrOCR)"),
            "simplify": SingleStageRow("simplify", "2. Plain-Language (Genie / CPU)"),
            "translate": SingleStageRow("translate", "3. Indic Translation (Anchor/LLM)"),
            "tts": SingleStageRow("tts", "4. Speech Synthesis (Piper ONNX)"),
        }

        for row in self.stages.values():
            self.layout.addWidget(row)

        self.setStyleSheet(f"""
            QFrame#stageCard {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: 10px;
            }}
        """)

    def reset(self):
        """Reset all stages to pending state."""
        for row in self.stages.values():
            row.set_pending()

    def set_stage_running(self, stage_id: str, info: str = "Processing..."):
        if stage_id in self.stages:
            self.stages[stage_id].set_running(info)

    def set_stage_completed(self, stage_id: str, latency_ms: float, provider: str, note: str = ""):
        if stage_id in self.stages:
            self.stages[stage_id].set_completed(latency_ms, provider, note)

    def set_stage_warning(self, stage_id: str, latency_ms: float, provider: str, warning_msg: str):
        if stage_id in self.stages:
            self.stages[stage_id].set_warning(latency_ms, provider, warning_msg)

    def set_stage_failed(self, stage_id: str, error_msg: str):
        if stage_id in self.stages:
            self.stages[stage_id].set_failed(error_msg)

    def set_stage_skipped(self, stage_id: str, reason: str = "Skipped"):
        if stage_id in self.stages:
            self.stages[stage_id].set_skipped(reason)
