from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout

from .base_panel import BasePanel
from .panel_registry import register_panel


@register_panel("agent_communication", "Agent Communication", area=Qt.RightDockWidgetArea)
class AgentCommunicationPanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._build_ui()
        signal = getattr(self.api, "agent_communication_updated", None)
        if signal is not None:
            signal.connect(self.refresh)
        self.refresh(self.api.get_agent_communication())


    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.summary = QLabel("Keine Kommunikation.", self)
        layout.addWidget(self.summary)
        self.view = QPlainTextEdit(self)
        self.view.setReadOnly(True)
        layout.addWidget(self.view, 1)


    def refresh(self, snapshot=None):
        snapshot = snapshot or self.api.get_agent_communication()
        self.view.setPlainText(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str))
        events = snapshot.get("events", []) if isinstance(snapshot, dict) else []
        self.summary.setText(f"{len(events)} Kommunikationsereignisse")
        return snapshot
