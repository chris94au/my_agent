from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .base_panel import BasePanel
from .panel_registry import register_panel


@register_panel("settings", "Settings", area=Qt.RightDockWidgetArea)
class SettingsPanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._build_ui()
        self.refresh(self.api.get_settings())
        self.save_button.clicked.connect(self._save)
        self.refresh_button.clicked.connect(self.refresh)


    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        box = QGroupBox("Einstellungen", self)
        form = QFormLayout(box)
        self.llm_model = QLineEdit(box)
        self.embedding_model = QLineEdit(box)
        self.temperature = QDoubleSpinBox(box)
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.context_size = QSpinBox(box)
        self.context_size.setRange(1024, 65536)
        self.memory_enabled = QCheckBox(box)
        self.research_enabled = QCheckBox(box)
        self.knowledge_enabled = QCheckBox(box)
        self.scheduler_enabled = QCheckBox(box)
        self.theme = QLineEdit(box)
        self.logging_enabled = QCheckBox(box)
        self.auto_save_interval = QSpinBox(box)
        self.auto_save_interval.setRange(1, 120)

        form.addRow("LLM", self.llm_model)
        form.addRow("Embedding", self.embedding_model)
        form.addRow("Temperature", self.temperature)
        form.addRow("Context Size", self.context_size)
        form.addRow("Memory", self.memory_enabled)
        form.addRow("Research", self.research_enabled)
        form.addRow("Knowledge Base", self.knowledge_enabled)
        form.addRow("Scheduler", self.scheduler_enabled)
        form.addRow("Theme", self.theme)
        form.addRow("Logging", self.logging_enabled)
        form.addRow("Auto Save (min)", self.auto_save_interval)
        layout.addWidget(box)

        buttons = QHBoxLayout()
        self.refresh_button = QPushButton("Neu laden", self)
        self.save_button = QPushButton("Speichern", self)
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.save_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.status_label = QLabel("Einstellungen geladen.", self)
        layout.addWidget(self.status_label)


    def refresh(self, snapshot=None):
        snapshot = snapshot or self.api.get_settings()
        self.llm_model.setText(snapshot.get("llm_model", ""))
        self.embedding_model.setText(snapshot.get("embedding_model", ""))
        self.temperature.setValue(float(snapshot.get("temperature", 0.7)))
        self.context_size.setValue(int(snapshot.get("context_size", 8192)))
        self.memory_enabled.setChecked(bool(snapshot.get("memory_enabled", True)))
        self.research_enabled.setChecked(bool(snapshot.get("research_enabled", True)))
        self.knowledge_enabled.setChecked(bool(snapshot.get("knowledge_base_enabled", True)))
        self.scheduler_enabled.setChecked(bool(snapshot.get("scheduler_enabled", True)))
        self.theme.setText(snapshot.get("theme", "System"))
        self.logging_enabled.setChecked(bool(snapshot.get("logging_enabled", True)))
        self.auto_save_interval.setValue(int(snapshot.get("auto_save_interval", 10)))
        self.status_label.setText("Einstellungen geladen.")


    def _save(self):
        self.api.update_settings(
            llm_model=self.llm_model.text().strip(),
            embedding_model=self.embedding_model.text().strip(),
            temperature=self.temperature.value(),
            context_size=self.context_size.value(),
            memory_enabled=self.memory_enabled.isChecked(),
            research_enabled=self.research_enabled.isChecked(),
            knowledge_base_enabled=self.knowledge_enabled.isChecked(),
            scheduler_enabled=self.scheduler_enabled.isChecked(),
            theme=self.theme.text().strip() or "System",
            logging_enabled=self.logging_enabled.isChecked(),
            auto_save_interval=self.auto_save_interval.value(),
        )
        self.status_label.setText("Gespeichert.")
