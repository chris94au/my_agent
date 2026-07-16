from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .base_panel import BasePanel
from .panel_registry import register_panel


@register_panel("tools", "Tools", area=Qt.BottomDockWidgetArea)
class ToolPanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._build_ui()
        self.api.tool_events_updated.connect(self.refresh)
        self.refresh(self.api.get_tool_events())


    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        controls = QHBoxLayout()
        self.filter_combo = QComboBox(self)
        self.filter_combo.addItem("Alle", None)
        self.filter_combo.addItem("Erfolgreich", "ok")
        self.filter_combo.addItem("Fehlgeschlagen", "error")
        self.filter_combo.addItem("Laufend", "running")
        self.refresh_button = QPushButton("Aktualisieren", self)
        controls.addWidget(QLabel("Filter:", self))
        controls.addWidget(self.filter_combo)
        controls.addWidget(self.refresh_button)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.table = QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Zeit", "Tool", "Parameter", "Status", "Laufzeit (ms)", "Ergebnis", "Fehler"])
        layout.addWidget(self.table, 1)

        self.summary = QLabel("Keine Tool-Aufrufe geladen.", self)
        layout.addWidget(self.summary)

        self.refresh_button.clicked.connect(lambda: self.refresh())
        self.filter_combo.currentIndexChanged.connect(lambda *_: self.refresh())


    def refresh(self, snapshot=None):
        status = self.filter_combo.currentData()
        events = snapshot if snapshot is not None else self.api.get_tool_events(status=status)
        if status and snapshot is None:
            events = self.api.get_tool_events(status=status)
        if status is None and snapshot is None:
            events = self.api.get_tool_events()

        self.table.setRowCount(len(events))
        for row, event in enumerate(events):
            values = [
                event.get("timestamp", ""),
                event.get("tool", ""),
                event.get("input", ""),
                event.get("status", ""),
                f"{event.get('runtime_ms', ''):.2f}" if isinstance(event.get("runtime_ms"), (int, float)) else str(event.get("runtime_ms", "")),
                event.get("result", ""),
                event.get("error", ""),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col in (2, 5):
                    item.setToolTip(str(value))
                self.table.setItem(row, col, item)

        self.summary.setText(f"{len(events)} Tool-Aufrufe angezeigt.")
