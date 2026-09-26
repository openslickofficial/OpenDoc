"""
Main Desktop Application Window for Snapdragon Document Assistant.
Built with PySide6, featuring accessible typography, drag-and-drop document ingestion,
asynchronous multi-threaded execution, live 4-stage pipeline tracking,
multi-tab document inspection, and integrated audio playback.
"""

import os
import sys
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QCheckBox, QTabWidget, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSplitter, QApplication
)
from PySide6.QtCore import Qt, QThread, Slot, Signal
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QIcon, QFont, QClipboard

from src.config import PipelineConfig, DEFAULT_CONFIG
from src.ui.styles import (
    GLOBAL_STYLESHEET, BG_MAIN, BG_CARD, BG_INPUT, BORDER_DEFAULT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, ACCENT_PRIMARY,
    ACCENT_CYAN, STATE_SUCCESS_TEXT, STATE_WARNING_TEXT, STATE_ERROR_TEXT
)
from src.ui.banner_widget import BannerWidget
from src.ui.stage_widget import StageWidget
from src.ui.audio_player import AudioPlayerWidget
from src.ui.worker import PipelineWorker


class DropArea(QFrame):
    """
    Drag & Drop file ingestion zone with fallback browse button.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.on_file_selected = None
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 20, 16, 20)
        self.layout.setSpacing(10)
        self.layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel("📄")
        self.icon_label.setStyleSheet("font-size: 32px;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.icon_label)

        self.prompt_label = QLabel("Drag & Drop Document Scan\n— or click browse below —")
        self.prompt_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {TEXT_SECONDARY};")
        self.prompt_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.prompt_label)

        self.browse_btn = QPushButton("📁 Browse Files...")
        self.browse_btn.setObjectName("secondaryButton")
        self.browse_btn.setFixedWidth(140)
        self.browse_btn.clicked.connect(self._open_file_dialog)
        self.layout.addWidget(self.browse_btn, 0, Qt.AlignCenter)

    def _open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Document Image",
            os.path.join(os.getcwd(), "test_images"),
            "Document Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp);;All Files (*)"
        )
        if file_path and self.on_file_selected:
            self.on_file_selected(file_path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if not self.isEnabled():
            event.ignore()
            return
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(f"""
                QFrame#dropArea {{
                    background-color: #1e2538;
                    border: 2px dashed {ACCENT_CYAN};
                    border-radius: 12px;
                }}
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        if not self.isEnabled():
            event.ignore()
            return
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if os.path.isfile(file_path) and self.on_file_selected:
                self.on_file_selected(file_path)


class MainWindow(QMainWindow):
    """
    Main application window for Snapdragon Document Assistant.
    """

    pipeline_completed = Signal(dict)
    pipeline_error = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Snapdragon® Document Assistant — On-Device NPU Intelligence")
        self.resize(1180, 820)
        self.setMinimumSize(960, 680)

        self.selected_image_path: Optional[str] = None
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[PipelineWorker] = None
        self.last_pipeline_result: Optional[Dict[str, Any]] = None
        self.is_processing: bool = False

        self._setup_ui()

    def _setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(12)

        # ---------------------------------------------------------------------
        # 1. Top Bar: Title + Config Controls
        # ---------------------------------------------------------------------
        top_bar = QHBoxLayout()
        top_bar.setSpacing(14)

        # App Title & Branding
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        app_title = QLabel("SNAPDRAGON® DOCUMENT ASSISTANT")
        app_title.setStyleSheet(f"font-size: 16px; font-weight: bold; letter-spacing: 1px; color: {TEXT_PRIMARY};")
        title_box.addWidget(app_title)

        app_subtitle = QLabel("Accessible On-Device Document OCR, Simplification, Translation & Speech")
        app_subtitle.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED};")
        title_box.addWidget(app_subtitle)
        top_bar.addLayout(title_box, 1)

        # Target Language Selector
        lang_box = QVBoxLayout()
        lang_box.setSpacing(2)
        lang_label = QLabel("Target Language")
        lang_label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {TEXT_MUTED};")
        lang_box.addWidget(lang_label)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Hindi (hi) [Primary / Supported]", "hi")
        self.lang_combo.addItem("Tamil (ta) [Limited / Lexicon Only]", "ta")
        self.lang_combo.addItem("Bengali (bn) [Limited / Lexicon Only]", "bn")
        self.lang_combo.setFixedWidth(240)
        lang_box.addWidget(self.lang_combo)
        top_bar.addLayout(lang_box)

        # Strict Fidelity Gate Checkbox
        gate_box = QVBoxLayout()
        gate_box.setSpacing(2)
        gate_label = QLabel("Safety Policy")
        gate_label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {TEXT_MUTED};")
        gate_box.addWidget(gate_label)

        self.strict_gate_check = QCheckBox("Strict Safety Gate (Block audio on mismatch)")
        self.strict_gate_check.setToolTip(
            "When checked: Blocks audio generation entirely if fidelity check fails.\n"
            "When unchecked (default): Prepends an authoritative spoken Hindi warning."
        )
        self.strict_gate_check.setChecked(False)
        gate_box.addWidget(self.strict_gate_check)
        top_bar.addLayout(gate_box)

        # Privacy & Cache Clearance Action
        privacy_box = QVBoxLayout()
        privacy_box.setSpacing(2)
        privacy_label = QLabel("Privacy & Data Retention")
        privacy_label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {TEXT_MUTED};")
        privacy_box.addWidget(privacy_label)

        self.clear_cache_btn = QPushButton("🧹 Clear Session & Cache")
        self.clear_cache_btn.setObjectName("secondaryButton")
        self.clear_cache_btn.setToolTip("Immediately purge all document text from memory and delete generated audio files from disk.")
        self.clear_cache_btn.clicked.connect(self.clear_session_and_cache)
        privacy_box.addWidget(self.clear_cache_btn)
        top_bar.addLayout(privacy_box)

        main_layout.addLayout(top_bar)

        # ---------------------------------------------------------------------
        # 2. Main Content Splitter (Left: Controls & Stages | Right: Results)
        # ---------------------------------------------------------------------
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setHandleWidth(8)

        # ---------------------------
        # Left Panel: Ingestion & Stages
        # ---------------------------
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(12)

        # Drop Area
        self.drop_area = DropArea(self)
        self.drop_area.on_file_selected = self.on_image_selected
        left_layout.addWidget(self.drop_area)

        # Thumbnail Preview Card
        self.preview_card = QFrame()
        self.preview_card.setObjectName("cardFrame")
        preview_layout = QVBoxLayout(self.preview_card)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(6)

        self.preview_label = QLabel("No document loaded")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        self.preview_label.setFixedHeight(120)
        preview_layout.addWidget(self.preview_label)

        self.file_info_label = QLabel("Please select a document image above")
        self.file_info_label.setAlignment(Qt.AlignCenter)
        self.file_info_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        self.file_info_label.setWordWrap(True)
        preview_layout.addWidget(self.file_info_label)

        left_layout.addWidget(self.preview_card)

        # Process Button
        self.process_btn = QPushButton("⚡ Process Document")
        self.process_btn.setObjectName("primaryButton")
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self.start_pipeline)
        left_layout.addWidget(self.process_btn)

        # Stage Progress Widget
        self.stage_widget = StageWidget(self)
        left_layout.addWidget(self.stage_widget)
        left_layout.addStretch(1)

        left_panel.setFixedWidth(380)
        content_splitter.addWidget(left_panel)

        # ---------------------------
        # Right Panel: Results & Player
        # ---------------------------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(10)

        # Banner Widget (Clean Pass, Warning, Partial, Error)
        self.banner_widget = BannerWidget(self)
        right_layout.addWidget(self.banner_widget)

        # Document Output Tab Widget
        self.tabs = QTabWidget()

        # Tab 1: Translated Indic Text
        self.tab_trans = QWidget()
        tab_trans_layout = QVBoxLayout(self.tab_trans)
        tab_trans_layout.setContentsMargins(12, 12, 12, 12)
        tab_trans_layout.setSpacing(8)

        trans_hdr = QHBoxLayout()
        trans_title = QLabel("TRANSLATED ACCESSIBILITY TEXT (HINDI)")
        trans_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {TEXT_MUTED};")
        trans_hdr.addWidget(trans_title, 1)

        copy_trans_btn = QPushButton("📋 Copy Text")
        copy_trans_btn.setObjectName("secondaryButton")
        copy_trans_btn.clicked.connect(lambda: self._copy_to_clipboard(self.trans_text.toPlainText()))
        trans_hdr.addWidget(copy_trans_btn)
        tab_trans_layout.addLayout(trans_hdr)

        self.trans_text = QTextEdit()
        self.trans_text.setReadOnly(True)
        self.trans_text.setPlaceholderText("Translated Indian language text will appear here...")
        # High legibility Devanagari font rendering
        font_trans = QFont("Nirmala UI", 12)
        font_trans.setStyleHint(QFont.SansSerif)
        self.trans_text.setFont(font_trans)
        tab_trans_layout.addWidget(self.trans_text)
        self.tabs.addTab(self.tab_trans, "🇮🇳 Translated Text")

        # Tab 2: Simplified Plain English
        self.tab_simp = QWidget()
        tab_simp_layout = QVBoxLayout(self.tab_simp)
        tab_simp_layout.setContentsMargins(12, 12, 12, 12)
        tab_simp_layout.setSpacing(8)

        simp_hdr = QHBoxLayout()
        simp_title = QLabel("SIMPLIFIED PLAIN-LANGUAGE TEXT (6TH–8TH GRADE)")
        simp_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {TEXT_MUTED};")
        simp_hdr.addWidget(simp_title, 1)

        copy_simp_btn = QPushButton("📋 Copy Text")
        copy_simp_btn.setObjectName("secondaryButton")
        copy_simp_btn.clicked.connect(lambda: self._copy_to_clipboard(self.simp_text.toPlainText()))
        simp_hdr.addWidget(copy_simp_btn)
        tab_simp_layout.addLayout(simp_hdr)

        self.simp_text = QTextEdit()
        self.simp_text.setReadOnly(True)
        self.simp_text.setPlaceholderText("Plain-language simplified English will appear here...")
        self.simp_text.setFont(QFont("Segoe UI", 11))
        tab_simp_layout.addWidget(self.simp_text)
        self.tabs.addTab(self.tab_simp, "📝 Simplified English")

        # Tab 3: Raw OCR Text
        self.tab_ocr = QWidget()
        tab_ocr_layout = QVBoxLayout(self.tab_ocr)
        tab_ocr_layout.setContentsMargins(12, 12, 12, 12)
        tab_ocr_layout.setSpacing(8)

        ocr_hdr = QHBoxLayout()
        ocr_title = QLabel("RAW EXTRACTED OCR TRANSCRIPTION (TrOCR)")
        ocr_title.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {TEXT_MUTED};")
        ocr_hdr.addWidget(ocr_title, 1)

        copy_ocr_btn = QPushButton("📋 Copy Text")
        copy_ocr_btn.setObjectName("secondaryButton")
        copy_ocr_btn.clicked.connect(lambda: self._copy_to_clipboard(self.ocr_text.toPlainText()))
        ocr_hdr.addWidget(copy_ocr_btn)
        tab_ocr_layout.addLayout(ocr_hdr)

        self.ocr_text = QTextEdit()
        self.ocr_text.setReadOnly(True)
        self.ocr_text.setPlaceholderText("Verbatim text recognized from the document scan will appear here...")
        self.ocr_text.setFont(QFont("Consolas", 11))
        tab_ocr_layout.addWidget(self.ocr_text)
        self.tabs.addTab(self.tab_ocr, "🔍 Raw OCR Text")

        # Tab 4: Fidelity & Diagnostic Audit Table
        self.tab_audit = QWidget()
        tab_audit_layout = QVBoxLayout(self.tab_audit)
        tab_audit_layout.setContentsMargins(12, 12, 12, 12)
        tab_audit_layout.setSpacing(8)

        audit_hdr = QLabel("DETERMINISTIC ENTITY PRESERVATION & FIDELITY AUDIT")
        audit_hdr.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {TEXT_MUTED};")
        tab_audit_layout.addWidget(audit_hdr)

        self.audit_table = QTableWidget(0, 4)
        self.audit_table.setHorizontalHeaderLabels(["Entity Category", "Original Source Anchor", "Preserved Output Entity", "Status"])
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tab_audit_layout.addWidget(self.audit_table)
        self.tabs.addTab(self.tab_audit, "🛡️ Fidelity Audit")

        right_layout.addWidget(self.tabs, 1)

        # Audio Player Bar
        self.audio_player = AudioPlayerWidget(self)
        right_layout.addWidget(self.audio_player)

        content_splitter.addWidget(right_panel)
        content_splitter.setSizes([380, 800])
        main_layout.addWidget(content_splitter, 1)

    def on_image_selected(self, image_path: str):
        """Called when a document image is loaded via drop or browse."""
        # Concurrency guard: Do not accept new documents while pipeline is running
        if self.is_processing or (self.worker_thread and self.worker_thread.isRunning()):
            return

        if not os.path.isfile(image_path):
            return

        self.selected_image_path = image_path
        filename = os.path.basename(image_path)
        file_size_kb = os.path.getsize(image_path) / 1024.0

        # Update thumbnail preview
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(320, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
            self.file_info_label.setText(f"{filename} ({pixmap.width()}×{pixmap.height()} px, {file_size_kb:.1f} KB)")
        else:
            self.preview_label.setText("Image preview unavailable")
            self.file_info_label.setText(f"{filename} ({file_size_kb:.1f} KB)")

        self.file_info_label.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {TEXT_PRIMARY};")
        self.process_btn.setEnabled(True)
        self.process_btn.setText(f"⚡ Process '{filename}'")

        # Reset outputs
        self.banner_widget.reset()
        self.stage_widget.reset()
        self.trans_text.clear()
        self.simp_text.clear()
        self.ocr_text.clear()
        self.audit_table.setRowCount(0)
        self.audio_player.set_disabled_state("Ready to process.")

    def start_pipeline(self):
        """Launches the background worker thread to process the document."""
        # Concurrency & Re-entrancy guard
        if self.is_processing or (self.worker_thread and self.worker_thread.isRunning()):
            return

        if not self.selected_image_path or not os.path.isfile(self.selected_image_path):
            return

        # Prepare UI for execution
        self.is_processing = True
        self.process_btn.setEnabled(False)
        self.process_btn.setText("⏳ Processing Document on Device...")
        self.drop_area.setEnabled(False)
        self.clear_cache_btn.setEnabled(False)
        self.banner_widget.reset()
        self.stage_widget.reset()
        self.audio_player.set_disabled_state("Processing document...")

        # Setup configuration
        selected_lang = self.lang_combo.currentData() or "hi"
        strict_gate = self.strict_gate_check.isChecked()

        # Build Worker & Thread
        self.worker_thread = QThread()
        self.worker = PipelineWorker(
            image_path=self.selected_image_path,
            target_lang=selected_lang,
            strict_fidelity_gate=strict_gate,
            config=DEFAULT_CONFIG,
        )
        self.worker.moveToThread(self.worker_thread)

        # Connect signals
        self.worker_thread.started.connect(self.worker.run)
        self.worker.stage_updated.connect(self._on_stage_updated)
        self.worker.finished.connect(self._on_pipeline_finished)
        self.worker.failed.connect(self._on_pipeline_failed)

        # Clean up worker thread when done
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    @Slot(str, str, dict)
    def _on_stage_updated(self, stage_name: str, event_type: str, data: Dict[str, Any]):
        """Slot receiving live progress from the pipeline worker."""
        if event_type == "running":
            self.stage_widget.set_stage_running(stage_name)
        elif event_type == "completed":
            latency = data.get("latency_ms", 0.0)
            provider = data.get("provider_used", "Unknown Provider")
            fidelity = data.get("fidelity_passed", True)
            if fidelity is False:
                self.stage_widget.set_stage_warning(stage_name, latency, provider, "Fidelity Warnings")
            else:
                self.stage_widget.set_stage_completed(stage_name, latency, provider)
        elif event_type == "degraded":
            latency = data.get("latency_ms", 0.0)
            provider = data.get("provider_used", "Degraded")
            self.stage_widget.set_stage_warning(stage_name, latency, provider, "Audio synthesis failed")
        elif event_type == "failed":
            err = data.get("error", "Error")
            self.stage_widget.set_stage_failed(stage_name, err)

    @Slot(dict)
    def _on_pipeline_finished(self, result: Dict[str, Any]):
        """Slot receiving the completed pipeline structured dictionary."""
        self.last_pipeline_result = result
        self.process_btn.setEnabled(True)
        self.process_btn.setText(f"⚡ Re-process '{os.path.basename(self.selected_image_path)}'")

        status = result.get("status", "failed")
        overall_fidelity = result.get("overall_fidelity_passed", False)
        tot_latency = result.get("total_latency_ms", 0.0)

        # Populate text fields
        self.ocr_text.setPlainText(result.get("raw_text", ""))
        self.simp_text.setPlainText(result.get("simplified_text", ""))
        self.trans_text.setPlainText(result.get("translated_text", ""))

        # Populate Audit Table
        self._populate_audit_table(result)

        # Configure Audio Player
        speech_policy = result.get("fidelity_summary", {}).get("speech_policy_applied", "clean_pass")
        warning_prepended = result.get("fidelity_summary", {}).get("speech_warning_prepended", False)
        speech_blocked = result.get("fidelity_summary", {}).get("speech_blocked", False)
        audio_path = result.get("audio_path")

        self.audio_player.load_audio(
            audio_path=audio_path,
            policy_applied=speech_policy,
            warning_prepended=warning_prepended,
            blocked=speech_blocked,
        )

        # Update stage status widgets from stages_dict if present
        stages_dict = result.get("stages", {})
        if stages_dict:
            for stg in ["ocr", "simplify", "translate", "tts"]:
                if stg in stages_dict:
                    stg_data = stages_dict[stg]
                    lat = stg_data.get("latency_ms", 0.0)
                    prov = stg_data.get("provider_used", "Active Provider")
                    if "error" in stg_data:
                        self.stage_widget.set_stage_failed(stg, str(stg_data["error"]))
                    elif stg == "simplify" and not result.get("fidelity_summary", {}).get("simplification_fidelity_passed", True):
                        self.stage_widget.set_stage_warning(stg, lat, prov, "Fidelity Warnings")
                    elif stg == "translate" and not result.get("fidelity_summary", {}).get("translation_fidelity_passed", True):
                        self.stage_widget.set_stage_warning(stg, lat, prov, "Fidelity Warnings")
                    else:
                        self.stage_widget.set_stage_completed(stg, lat, prov)

        # Update Banner based on Status & Fidelity
        if status == "failed":
            err_msg = result.get("error", "Unknown processing failure")
            self.banner_widget.show_error(err_msg)
            # Mark failed stage and subsequent skipped stages
            for stg in ["ocr", "simplify", "translate", "tts"]:
                if stg in stages_dict and "error" in stages_dict[stg]:
                    self.stage_widget.set_stage_failed(stg, str(stages_dict[stg]["error"]))
                elif stg not in stages_dict:
                    self.stage_widget.set_stage_skipped(stg, "Skipped due to pipeline failure")

        elif speech_blocked:
            warnings = (
                result.get("fidelity_summary", {}).get("simplification_warnings", []) +
                result.get("fidelity_summary", {}).get("translation_warnings", [])
            )
            self.banner_widget.show_strict_blocked(warnings)
        elif status == "partial_success":
            tts_err = result.get("stages", {}).get("tts", {}).get("error", "Audio synthesis unavailable")
            self.banner_widget.show_partial_success(tts_err)
        elif not overall_fidelity:
            warnings = (
                result.get("fidelity_summary", {}).get("simplification_warnings", []) +
                result.get("fidelity_summary", {}).get("translation_warnings", [])
            )
            self.banner_widget.show_fidelity_warning(warnings, warning_prepended=warning_prepended)
        else:
            self.banner_widget.show_clean_pass(tot_latency)

        self.is_processing = False
        self.drop_area.setEnabled(True)
        self.clear_cache_btn.setEnabled(True)
        self.pipeline_completed.emit(result)

    @Slot(str)
    def _on_pipeline_failed(self, error_msg: str):
        """Slot receiving fatal worker exceptions."""
        self.is_processing = False
        self.process_btn.setEnabled(True)
        self.process_btn.setText("⚡ Process Document")
        self.drop_area.setEnabled(True)
        self.clear_cache_btn.setEnabled(True)
        self.banner_widget.show_error(f"Fatal background worker error: {error_msg}")
        self.stage_widget.set_stage_failed("ocr", error_msg)
        self.pipeline_error.emit(error_msg)

    def _populate_audit_table(self, result: Dict[str, Any]):
        """Populates the Fidelity Audit tab with entity comparisons."""
        self.audit_table.setRowCount(0)

        # Get entity reports from simplification and translation
        simp_stage = result.get("stages", {}).get("simplify", {})
        trans_stage = result.get("stages", {}).get("translate", {})
        entities = simp_stage.get("entities", {})

        row_idx = 0
        categories = [
            ("Dates", entities.get("dates", [])),
            ("Monetary Amounts", entities.get("amounts", [])),
            ("Reference IDs", entities.get("reference_ids", [])),
            ("Status Keywords", entities.get("status_keywords", [])),
        ]

        warnings = (
            result.get("fidelity_summary", {}).get("simplification_warnings", []) +
            result.get("fidelity_summary", {}).get("translation_warnings", [])
        )

        for cat_name, items in categories:
            for item in items:
                self.audit_table.insertRow(row_idx)
                self.audit_table.setItem(row_idx, 0, QTableWidgetItem(cat_name))
                self.audit_table.setItem(row_idx, 1, QTableWidgetItem(str(item)))
                self.audit_table.setItem(row_idx, 2, QTableWidgetItem(str(item)))

                # Check if item triggered a warning
                item_warning = any(str(item) in w for w in warnings)
                if item_warning:
                    status_item = QTableWidgetItem("⚠️ Flagged Warning")
                    status_item.setForeground(Qt.yellow)
                else:
                    status_item = QTableWidgetItem("✅ Verified Intact")
                    status_item.setForeground(Qt.green)

                self.audit_table.setItem(row_idx, 3, status_item)
                row_idx += 1

        # If warnings exist that aren't tied to single entities
        for w in warnings:
            self.audit_table.insertRow(row_idx)
            self.audit_table.setItem(row_idx, 0, QTableWidgetItem("Cross-Stage Discrepancy"))
            self.audit_table.setItem(row_idx, 1, QTableWidgetItem("Discrepancy / Contradiction"))
            self.audit_table.setItem(row_idx, 2, QTableWidgetItem(w[:60]))
            status_item = QTableWidgetItem("⚠️ Intercepted")
            status_item.setForeground(Qt.yellow)
            self.audit_table.setItem(row_idx, 3, status_item)
            row_idx += 1

    def _copy_to_clipboard(self, text: str):
        """Copies text to the system clipboard with feedback."""
        if text.strip():
            clipboard = QApplication.clipboard()
            clipboard.setText(text)

    def clear_session_and_cache(self):
        """
        Wipes active document session data from RAM and deletes derived audio
        artifacts from audio_output/ on disk to protect sensitive user privacy.
        """
        if self.is_processing:
            return

        # 1. Stop audio playback and reset player
        self.audio_player.stop_playback()
        self.audio_player.set_disabled_state("Session wiped. Cache cleared.")

        # 2. Clear volatile memory text buffers and UI tables
        self.ocr_text.clear()
        self.simp_text.clear()
        self.trans_text.clear()
        self.audit_table.setRowCount(0)
        self.banner_widget.reset()
        self.stage_widget.reset()

        # 3. Reset document ingestion states
        self.selected_image_path = None
        self.last_pipeline_result = None
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText("No document loaded")
        self.process_btn.setEnabled(False)
        self.process_btn.setText("⚡ Process Document")

        # 4. Purge generated audio files from audio_output directory
        from src.config import DEFAULT_AUDIO_DIR
        deleted_count = 0
        if os.path.exists(DEFAULT_AUDIO_DIR):
            for fname in os.listdir(DEFAULT_AUDIO_DIR):
                if fname.lower().endswith((".wav", ".mp3")):
                    fpath = os.path.join(DEFAULT_AUDIO_DIR, fname)
                    try:
                        os.remove(fpath)
                        deleted_count += 1
                    except Exception:
                        pass

        self.file_info_label.setText(
            f"Privacy Wipe Complete: Memory cleared, {deleted_count} audio file(s) removed."
        )
        self.file_info_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
