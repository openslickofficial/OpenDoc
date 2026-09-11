"""
Background Thread Worker for Non-Blocking Document Processing.
Runs process_document() on a separate QThread, preventing UI freezing
and delivering live stage updates via PySide6 Qt Signals.
"""

from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal, Slot

from src.config import PipelineConfig
from src.pipeline import process_document


class PipelineWorker(QObject):
    """
    Worker executing the unified 4-stage pipeline asynchronously.
    """

    # Signals
    stage_updated = Signal(str, str, dict)  # stage_name, event_type, data_dict
    finished = Signal(dict)                 # full pipeline structured result
    failed = Signal(str)                    # fatal failure message

    def __init__(
        self,
        image_path: str,
        target_lang: str = "hi",
        strict_fidelity_gate: bool = False,
        config: Optional[PipelineConfig] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.image_path = image_path
        self.target_lang = target_lang
        self.strict_fidelity_gate = strict_fidelity_gate
        self.config = config

    def _stage_callback(self, stage_name: str, event_type: str, data: Dict[str, Any]):
        """Thread-safe callback routed to PySide6 Qt Signal."""
        self.stage_updated.emit(stage_name, event_type, data)

    @Slot()
    def run(self):
        """Main execution slot invoked when thread starts."""
        try:
            result = process_document(
                image_path=self.image_path,
                target_lang=self.target_lang,
                strict_fidelity_gate=self.strict_fidelity_gate,
                config=self.config,
                stage_callback=self._stage_callback,
            )
            self.finished.emit(result)
        except Exception as e:
            self.failed.emit(str(e))
