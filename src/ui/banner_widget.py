"""
High-Visibility Fidelity & Error Status Banner Widget.
Displays prominent, color-coded alerts for Clean Pass, Fidelity Warnings,
Fatal Pipeline Errors, Partial TTS Degradation, and Strict Audio Suppression.
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)
from PySide6.QtCore import Qt

from src.ui.styles import (
    STATE_SUCCESS_BG, STATE_SUCCESS_BORDER, STATE_SUCCESS_TEXT,
    STATE_WARNING_BG, STATE_WARNING_BORDER, STATE_WARNING_TEXT,
    STATE_ERROR_BG, STATE_ERROR_BORDER, STATE_ERROR_TEXT,
    STATE_INFO_BG, STATE_INFO_BORDER, STATE_INFO_TEXT,
    TEXT_PRIMARY, TEXT_SECONDARY
)


class BannerWidget(QFrame):
    """
    Prominent banner rendered at the top of document results.
    Never relies on small print or hidden tooltips.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("bannerWidget")
        self.setVisible(False)
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 12, 16, 12)
        self.layout.setSpacing(6)

        # Header row: Icon + Title
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(10)

        self.icon_label = QLabel()
        self.icon_label.setStyleSheet("font-size: 22px;")
        self.header_layout.addWidget(self.icon_label)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.header_layout.addWidget(self.title_label, 1)

        self.layout.addLayout(self.header_layout)

        # Description / Details label
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("font-size: 13px; line-height: 1.4;")
        self.layout.addWidget(self.desc_label)

        # Discrepancy warnings label (hidden if clean)
        self.warnings_label = QLabel()
        self.warnings_label.setWordWrap(True)
        self.warnings_label.setStyleSheet("font-size: 12px; font-family: monospace; padding-top: 4px;")
        self.warnings_label.setVisible(False)
        self.layout.addWidget(self.warnings_label)

    def show_clean_pass(self, total_latency_ms: float):
        """Clean document pass with 100% entity verification."""
        self.setStyleSheet(f"""
            QFrame#bannerWidget {{
                background-color: {STATE_SUCCESS_BG};
                border: 2px solid {STATE_SUCCESS_BORDER};
                border-radius: 8px;
            }}
        """)
        self.icon_label.setText("🛡️")
        self.title_label.setText("FIDELITY VERIFIED: 100% Entity Preservation Confirmed")
        self.title_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {STATE_SUCCESS_TEXT};")
        self.desc_label.setText(
            f"All critical factual anchors (dates, currency amounts, reference IDs, and legal status keywords) "
            f"were independently verified intact across simplification and translation. Safe for audio synthesis. "
            f"[Pipeline Total: {total_latency_ms:.1f} ms]"
        )
        self.desc_label.setStyleSheet(f"font-size: 13px; color: {TEXT_PRIMARY};")
        self.warnings_label.setVisible(False)
        self.setVisible(True)

    def show_fidelity_warning(self, warnings: List[str], warning_prepended: bool = True):
        """Fidelity check failed: discrepancies or contradictions caught."""
        self.setStyleSheet(f"""
            QFrame#bannerWidget {{
                background-color: {STATE_WARNING_BG};
                border: 2px solid {STATE_WARNING_BORDER};
                border-radius: 8px;
            }}
        """)
        self.icon_label.setText("⚠️")
        self.title_label.setText("FIDELITY SAFEGUARD TRIGGERED: Discrepancies Intercepted!")
        self.title_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {STATE_WARNING_TEXT};")
        
        policy_note = (
            "An authoritative spoken Hindi warning has been prepended to the speech output."
            if warning_prepended else "Audio generation has been suppressed per safety policy."
        )
        self.desc_label.setText(
            f"The cross-language fidelity safeguard intercepted {len(warnings)} discrepancy/contradiction(s) "
            f"between source text and output. {policy_note} Please inspect the original document carefully."
        )
        self.desc_label.setStyleSheet(f"font-size: 13px; color: {TEXT_PRIMARY};")

        # Format warnings
        warning_bullets = "\n".join([f"• {w}" for w in warnings[:5]])
        if len(warnings) > 5:
            warning_bullets += f"\n... and {len(warnings) - 5} additional warning(s)"
        self.warnings_label.setText(warning_bullets)
        self.warnings_label.setStyleSheet(f"font-size: 12px; color: {STATE_WARNING_TEXT}; font-weight: 500;")
        self.warnings_label.setVisible(True)
        self.setVisible(True)

    def show_strict_blocked(self, warnings: List[str]):
        """Strict fidelity gate completely blocked audio synthesis."""
        self.setStyleSheet(f"""
            QFrame#bannerWidget {{
                background-color: {STATE_ERROR_BG};
                border: 2px solid {STATE_ERROR_BORDER};
                border-radius: 8px;
            }}
        """)
        self.icon_label.setText("🚫")
        self.title_label.setText("AUDIO GENERATION BLOCKED: Strict Safety Gate Active")
        self.title_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {STATE_ERROR_TEXT};")
        self.desc_label.setText(
            "Document failed critical factual verification. In strict mode, speech synthesis is completely suppressed "
            "to prevent unverified or corrupted demands from being spoken aloud. Simplified text is retained below."
        )
        self.desc_label.setStyleSheet(f"font-size: 13px; color: {TEXT_PRIMARY};")
        
        warning_bullets = "\n".join([f"• {w}" for w in warnings[:5]])
        self.warnings_label.setText(warning_bullets)
        self.warnings_label.setStyleSheet(f"font-size: 12px; color: {STATE_ERROR_TEXT};")
        self.warnings_label.setVisible(True)
        self.setVisible(True)

    def show_partial_success(self, error_msg: str):
        """Text pipeline succeeded, but TTS audio synthesis encountered an error."""
        self.setStyleSheet(f"""
            QFrame#bannerWidget {{
                background-color: {STATE_INFO_BG};
                border: 2px solid {STATE_INFO_BORDER};
                border-radius: 8px;
            }}
        """)
        self.icon_label.setText("ℹ️")
        self.title_label.setText("PARTIAL SUCCESS: Text Available (Audio Synthesis Degraded)")
        self.title_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {STATE_INFO_TEXT};")
        self.desc_label.setText(
            f"Document OCR, plain-language simplification, and Hindi translation completed successfully. "
            f"Audio synthesis encountered an error ({error_msg}). All text deliverables are preserved below."
        )
        self.desc_label.setStyleSheet(f"font-size: 13px; color: {TEXT_PRIMARY};")
        self.warnings_label.setVisible(False)
        self.setVisible(True)

    def show_error(self, error_msg: str):
        """Fatal pipeline failure (e.g. blank scan or model crash)."""
        self.setStyleSheet(f"""
            QFrame#bannerWidget {{
                background-color: {STATE_ERROR_BG};
                border: 2px solid {STATE_ERROR_BORDER};
                border-radius: 8px;
            }}
        """)
        self.icon_label.setText("❌")
        self.title_label.setText("PROCESSING HALTED: Pipeline Error Detected")
        self.title_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {STATE_ERROR_TEXT};")
        self.desc_label.setText(error_msg)
        self.desc_label.setStyleSheet(f"font-size: 13px; color: {TEXT_PRIMARY};")
        self.warnings_label.setVisible(False)
        self.setVisible(True)

    def reset(self):
        """Hide and clear the banner."""
        self.setVisible(False)
        self.warnings_label.setVisible(False)
