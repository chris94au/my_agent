from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout

from .base_panel import BasePanel
from .panel_registry import register_panel


@register_panel("agent_dashboard", "Agent Dashboard", area=Qt.LeftDockWidgetArea)
class AgentDashboardPanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._build_ui()
        signal = getattr(self.api, "agent_dashboard_updated", None)
        if signal is not None:
            signal.connect(self.refresh)
        self.refresh(self.api.get_agent_dashboard())


    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.summary = QLabel("Keine Agenten geladen.", self)
        layout.addWidget(self.summary)
        self.table = QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Name", "Rolle", "Version", "Priorität", "Capabilities", "Allowed Tools", "Denied Tools"])
        layout.addWidget(self.table, 1)


    def refresh(self, snapshot=None):
        snapshot = snapshot or self.api.get_agent_dashboard()
        agents = snapshot.get("agents", []) or []
        self.table.setRowCount(len(agents))
        for row, agent in enumerate(agents):
            values = [
                agent.get("name", ""),
                agent.get("role", ""),
                agent.get("version", ""),
                str(agent.get("priority", "")),
                ", ".join(agent.get("capabilities", []) or []),
                ", ".join(agent.get("allowed_tools", []) or []),
                ", ".join(agent.get("denied_tools", []) or []),
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))
        route = snapshot.get("route") or {}
        self.summary.setText(f"{len(agents)} Agenten aktiv | Route: {', '.join(route.get('agents', []) or [])}")
        return snapshot
