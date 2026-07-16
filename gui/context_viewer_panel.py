from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout

from .base_panel import BasePanel
from .panel_registry import register_panel


@register_panel("context_viewer", "Context Viewer", area=Qt.RightDockWidgetArea)
class ContextViewerPanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._build_ui()
        signal = getattr(self.api, "context_updated", None)
        if signal is not None:
            signal.connect(self.refresh)
        self.refresh(self.api.get_context_snapshot())


    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.summary = QLabel("Kein Context Snapshot.", self)
        layout.addWidget(self.summary)
        self.view = QPlainTextEdit(self)
        self.view.setReadOnly(True)
        layout.addWidget(self.view, 1)


    def refresh(self, snapshot=None):
        snapshot = snapshot or self.api.get_context_snapshot()
        self.view.setPlainText(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str))
        shared = snapshot.get("shared", {}) if isinstance(snapshot, dict) else {}
        self.summary.setText(f"Shared Keys: {len(shared)} | Agent Reports: {len(snapshot.get('agent_reports', {})) if isinstance(snapshot, dict) else 0}")
        return snapshot
