from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .base_panel import BasePanel
from .panel_registry import register_panel


@register_panel("tasks", "Tasks", area=Qt.BottomDockWidgetArea)
class TaskPanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._build_ui()
        self.api.tasks_updated.connect(self.refresh)
        self.refresh(self.api.get_tasks())


    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        controls = QHBoxLayout()
        self.title_edit = QLineEdit(self)
        self.title_edit.setPlaceholderText("Neue Aufgabe…")
        self.priority_spin = QSpinBox(self)
        self.priority_spin.setRange(1, 5)
        self.priority_spin.setValue(3)
        self.add_button = QPushButton("Aufgabe anlegen", self)
        self.pause_button = QPushButton("Pause", self)
        self.resume_button = QPushButton("Fortsetzen", self)
        self.cancel_button = QPushButton("Abbrechen", self)
        controls.addWidget(self.title_edit, 1)
        controls.addWidget(QLabel("Prio:", self))
        controls.addWidget(self.priority_spin)
        controls.addWidget(self.add_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.resume_button)
        controls.addWidget(self.cancel_button)
        layout.addLayout(controls)

        self.table = QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Titel", "Status", "Fortschritt", "Prio", "Nächster Schritt", "Geplant für", "ID"])
        layout.addWidget(self.table, 1)

        self.info_label = QLabel("Keine Tasks.", self)
        layout.addWidget(self.info_label)

        self.add_button.clicked.connect(self._add_task)
        self.pause_button.clicked.connect(self._pause_task)
        self.resume_button.clicked.connect(self._resume_task)
        self.cancel_button.clicked.connect(self._cancel_task)


    def refresh(self, snapshot=None):
        tasks = snapshot or self.api.get_tasks()
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            values = [
                task.get("title", ""),
                task.get("status", ""),
                f"{float(task.get('progress', 0.0)):.2f}",
                str(task.get("priority", "")),
                task.get("next_step", ""),
                task.get("scheduled_for", ""),
                str(task.get("id", "")),
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))
        self.info_label.setText(f"{len(tasks)} Tasks sichtbar")


    def _current_task_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 6)
        return int(item.text()) if item and item.text().isdigit() else None


    def _add_task(self):
        title = self.title_edit.text().strip()
        if not title:
            return
        self.api.add_task(title, priority=self.priority_spin.value())
        self.title_edit.clear()
        self.refresh()


    def _pause_task(self):
        task_id = self._current_task_id()
        if task_id is not None:
            self.api.pause_task(task_id)
            self.refresh()


    def _resume_task(self):
        task_id = self._current_task_id()
        if task_id is not None:
            self.api.resume_task(task_id)
            self.refresh()


    def _cancel_task(self):
        task_id = self._current_task_id()
        if task_id is not None:
            self.api.cancel_task(task_id)
            self.refresh()
