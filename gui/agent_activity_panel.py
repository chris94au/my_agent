from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout

from .base_panel import BasePanel
from .panel_registry import register_panel


@register_panel("agent_activity", "Agent Activity", area=Qt.LeftDockWidgetArea)
class AgentActivityPanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._build_ui()
        signal = getattr(self.api, "agent_activity_updated", None)
        if signal is not None:
            signal.connect(self.refresh)
        self.refresh(self.api.get_agent_activity())


    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.summary = QLabel("Keine Aktivität.", self)
        layout.addWidget(self.summary)
        self.list_widget = QListWidget(self)
        layout.addWidget(self.list_widget, 1)


    def refresh(self, snapshot=None):
        activities = snapshot if snapshot is not None else self.api.get_agent_activity()
        self.list_widget.clear()
        for item in activities:
            source = item.get("source", "")
            payload = item.get("payload", {})
            timestamp = item.get("timestamp", "")
            self.list_widget.addItem(QListWidgetItem(f"[{timestamp}] {source}: {payload}"))
        self.summary.setText(f"{len(activities)} Aktivitätsereignisse")
        return activities
