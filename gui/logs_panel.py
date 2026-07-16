from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
)

from .base_panel import BasePanel
from .panel_registry import register_panel


@register_panel("logs", "Logs", area=Qt.BottomDockWidgetArea)
class LogsPanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._build_ui()
        self.api.logs_updated.connect(self.refresh)
        self.refresh(self.api.get_logs())


    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        controls = QHBoxLayout()
        self.logger_filter = QComboBox(self)
        self.logger_filter.setEditable(True)
        self.level_filter = QComboBox(self)
        self.level_filter.addItems(["Alle", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.export_button = QPushButton("Export", self)
        self.refresh_button = QPushButton("Aktualisieren", self)
        controls.addWidget(QLabel("Logger:", self))
        controls.addWidget(self.logger_filter, 1)
        controls.addWidget(self.level_filter)
        controls.addWidget(self.export_button)
        controls.addWidget(self.refresh_button)
        layout.addLayout(controls)

        self.log_view = QPlainTextEdit(self)
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, 1)

        self.info_label = QLabel("Keine Logs.", self)
        layout.addWidget(self.info_label)

        self.refresh_button.clicked.connect(lambda: self.refresh())
        self.export_button.clicked.connect(self._export_logs)
        self.logger_filter.lineEdit().returnPressed.connect(lambda: self.refresh())
        self.level_filter.currentIndexChanged.connect(lambda *_: self.refresh())


    def refresh(self, snapshot=None):
        logger_name = self.logger_filter.currentText().strip() or None
        level = self.level_filter.currentText()
        if level == "Alle":
            level = None
        logs = snapshot if snapshot is not None else self.api.get_logs(logger_name=logger_name, level=level)
        text = "\n".join(
            f"[{entry.get('timestamp')}] {entry.get('level')} {entry.get('logger_name')}: {entry.get('message')}"
            for entry in logs
        )
        self.log_view.setPlainText(text)
        self.info_label.setText(f"{len(logs)} Log-Einträge")


    def _export_logs(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(self, "Logs exportieren", "agent_logs.json", "JSON Files (*.json)")
        if not path:
            return
        self.api.export_logs(path)
