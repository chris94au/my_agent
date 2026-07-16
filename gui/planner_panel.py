from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QVBoxLayout,
)

from .base_panel import BasePanel
from .panel_registry import register_panel


@register_panel("planner", "Planner", area=Qt.RightDockWidgetArea)
class PlannerPanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._build_ui()
        self.api.planner_updated.connect(self.refresh)
        self.refresh(self.api.get_planner_snapshot())


    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        header = QGroupBox("Aktueller Plan", self)
        form = QFormLayout(header)
        self.goal_label = QLabel("—", header)
        self.status_label = QLabel("idle", header)
        self.current_step_label = QLabel("—", header)
        form.addRow("Ziel", self.goal_label)
        form.addRow("Status", self.status_label)
        form.addRow("Aktueller Schritt", self.current_step_label)
        layout.addWidget(header)

        self.steps_list = QListWidget(self)
        layout.addWidget(self.steps_list, 1)

        self.errors_box = QPlainTextEdit(self)
        self.errors_box.setReadOnly(True)
        self.errors_box.setPlaceholderText("Fehler und Reflection erscheinen hier…")
        layout.addWidget(self.errors_box, 1)


    def refresh(self, snapshot=None):
        snapshot = snapshot or self.api.get_planner_snapshot()
        self.goal_label.setText(snapshot.get("goal") or "—")
        self.status_label.setText(snapshot.get("status") or "idle")
        current = snapshot.get("current_step") or {}
        self.current_step_label.setText(current.get("description") or current.get("action") or "—")

        self.steps_list.clear()
        for step in snapshot.get("steps", []):
            status = step.get("status", "pending")
            icon = "✓" if status == "ok" else "⏳" if status == "pending" else "⚠"
            text = f"{icon} Schritt {step.get('index')}: {step.get('description') or step.get('action')}"
            item = QListWidgetItem(text)
            self.steps_list.addItem(item)

        reflection = snapshot.get("reflection") or {}
        errors = snapshot.get("errors") or []
        lines = []
        if reflection:
            lines.append(f"Reflection: {reflection.get('summary', '')}")
            for risk in reflection.get("risks", []) or []:
                lines.append(f"Risk: {risk}")
            for improvement in reflection.get("improvements", []) or []:
                lines.append(f"Improvement: {improvement}")
        if errors:
            lines.append("Fehler:")
            lines.extend([f"- {error}" for error in errors])
        self.errors_box.setPlainText("\n".join(lines))
