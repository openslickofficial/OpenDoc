"""
Accessible Audio Player Control Widget for Generated Hindi Speech.
Utilizes PySide6.QtMultimedia (QMediaPlayer + QAudioOutput) with asynchronous
fallback to Windows built-in winsound for maximum hardware/driver compatibility.
"""

import os
import sys
from typing import Optional
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QWidget
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from src.ui.styles import (
    BG_CARD, BG_INPUT, BORDER_DEFAULT, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, ACCENT_PRIMARY, ACCENT_CYAN, STATE_WARNING_TEXT,
    STATE_SUCCESS_TEXT, STATE_ERROR_TEXT
)


def format_time_ms(ms: int) -> str:
    """Format milliseconds into MM:SS format."""
    total_seconds = max(0, int(ms / 1000))
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


class AudioPlayerWidget(QFrame):
    """
    Dedicated audio playback bar for document speech synthesis.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("audioPlayerCard")
        self.audio_path: Optional[str] = None
        self.is_winsound_fallback = False
        self._setup_player()
        self._setup_ui()
        self.set_disabled_state("No audio generated yet.")

    def _setup_player(self):
        """Initialize QMediaPlayer and QAudioOutput."""
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)

        # Connect signals
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(8)

        # Top row: Title + Speech Policy Badge
        self.top_row = QHBoxLayout()
        self.title_label = QLabel("ACCESSIBILITY AUDIO PLAYER")
        self.title_label.setStyleSheet(
            f"font-size: 11px; font-weight: bold; letter-spacing: 1px; color: {TEXT_MUTED};"
        )
        self.top_row.addWidget(self.title_label, 1)

        self.policy_badge = QLabel("Audio Inactive")
        self.policy_badge.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {TEXT_MUTED};")
        self.top_row.addWidget(self.policy_badge)

        self.layout.addLayout(self.top_row)

        # Middle row: Controls + Scrubber + Time Label
        self.controls_row = QHBoxLayout()
        self.controls_row.setSpacing(10)

        # Play / Pause Button
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setObjectName("secondaryButton")
        self.play_btn.setFixedWidth(90)
        self.play_btn.clicked.connect(self.toggle_playback)
        self.controls_row.addWidget(self.play_btn)

        # Stop Button
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("secondaryButton")
        self.stop_btn.setFixedWidth(80)
        self.stop_btn.clicked.connect(self.stop_playback)
        self.controls_row.addWidget(self.stop_btn)

        # Seek Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        self.controls_row.addWidget(self.slider, 1)

        # Time Label
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet(f"font-size: 12px; font-family: monospace; color: {TEXT_SECONDARY};")
        self.controls_row.addWidget(self.time_label)

        self.layout.addLayout(self.controls_row)

        # Bottom row: File Path / Status Label
        self.status_label = QLabel("Awaiting document processing...")
        self.status_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        self.layout.addWidget(self.status_label)

        self.setStyleSheet(f"""
            QFrame#audioPlayerCard {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: 10px;
            }}
        """)

    def load_audio(
        self,
        audio_path: Optional[str],
        policy_applied: str = "clean_pass",
        warning_prepended: bool = False,
        blocked: bool = False,
    ):
        """Loads an audio file and configures player state."""
        self.audio_path = audio_path

        if blocked or not audio_path or not os.path.isfile(audio_path):
            if blocked:
                self.set_disabled_state("Audio generation suppressed by strict fidelity gate.")
                self.policy_badge.setText("🚫 Audio Suppressed (Strict Mode)")
                self.policy_badge.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {STATE_ERROR_TEXT};")
            else:
                self.set_disabled_state("No audio file available for this document.")
                self.policy_badge.setText("⚠️ Audio Unavailable")
                self.policy_badge.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {TEXT_MUTED};")
            return

        # Enable controls
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.slider.setEnabled(True)
        self.play_btn.setText("▶ Play")

        # Set media source
        try:
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(audio_path)))
            self.is_winsound_fallback = False
        except Exception as e:
            self.is_winsound_fallback = True
            self.status_label.setText(f"Using system audio fallback: {os.path.basename(audio_path)}")

        filename = os.path.basename(audio_path)
        file_size_kb = os.path.getsize(audio_path) / 1024.0
        self.status_label.setText(f"File: {filename} ({file_size_kb:.1f} KB, 16kHz mono WAV)")
        self.status_label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")

        # Update policy badge
        if warning_prepended:
            self.policy_badge.setText("⚠️ Warning Prepended to Speech")
            self.policy_badge.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {STATE_WARNING_TEXT};")
        else:
            self.policy_badge.setText("🛡️ Clean Spoken Synthesis")
            self.policy_badge.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {STATE_SUCCESS_TEXT};")

    def toggle_playback(self):
        """Toggle between playing and pausing."""
        if not self.audio_path or not os.path.isfile(self.audio_path):
            return

        if self.is_winsound_fallback or sys.platform == "win32" and not self.player.isAvailable():
            self._play_winsound()
            return

        state = self.player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_btn.setText("▶ Play")
        else:
            self.player.play()
            self.play_btn.setText("⏸ Pause")

    def stop_playback(self):
        """Stop playback and reset scrubber."""
        if self.is_winsound_fallback:
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        else:
            self.player.stop()

        self.play_btn.setText("▶ Play")
        self.slider.setValue(0)
        self._update_time_display(0, self.player.duration())

    def _play_winsound(self):
        """Fallback playback using Windows winsound."""
        try:
            import winsound
            winsound.PlaySound(self.audio_path, winsound.SND_ASYNC | winsound.SND_FILENAME)
            self.play_btn.setText("▶ Playing...")
            self.status_label.setText("Playing via Windows SAPI/Sound driver...")
        except Exception as e:
            self.status_label.setText(f"Audio playback error: {e}")

    def _on_position_changed(self, position: int):
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        self._update_time_display(position, self.player.duration())

    def _on_duration_changed(self, duration: int):
        self.slider.setRange(0, duration)
        self._update_time_display(self.player.position(), duration)

    def _on_slider_moved(self, position: int):
        self.player.setPosition(position)

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸ Pause")
        else:
            self.play_btn.setText("▶ Play")

    def _update_time_display(self, pos_ms: int, dur_ms: int):
        pos_str = format_time_ms(pos_ms)
        dur_str = format_time_ms(dur_ms)
        self.time_label.setText(f"{pos_str} / {dur_str}")

    def set_disabled_state(self, message: str):
        """Disable player controls with message."""
        self.stop_playback()
        self.audio_path = None
        self.play_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.slider.setEnabled(False)
        self.slider.setValue(0)
        self.time_label.setText("00:00 / 00:00")
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        self.policy_badge.setText("Audio Inactive")
        self.policy_badge.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
