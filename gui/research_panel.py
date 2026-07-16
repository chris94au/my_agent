from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .base_panel import BasePanel
from .panel_registry import register_panel
from .widgets import MarkdownBrowser


@register_panel("research", "Research", area=Qt.BottomDockWidgetArea)
class ResearchPanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._build_ui()
        self.api.research_updated.connect(self.refresh)
        self.refresh(self.api.get_research_snapshot())


    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        controls = QHBoxLayout()
        self.query_edit = QLineEdit(self)
        self.query_edit.setPlaceholderText("Research-Anfrage…")
        self.refresh_button = QPushButton("Aktualisieren", self)
        controls.addWidget(self.query_edit, 1)
        controls.addWidget(self.refresh_button)
        layout.addLayout(controls)

        self.summary_label = QLabel("Keine Research-Daten.", self)
        layout.addWidget(self.summary_label)

        self.sources_table = QTableWidget(self)
        self.sources_table.setColumnCount(5)
        self.sources_table.setHorizontalHeaderLabels(["Quelle", "Score", "Reliability", "Relevance", "URL"])
        layout.addWidget(self.sources_table, 1)

        self.citations_table = QTableWidget(self)
        self.citations_table.setColumnCount(4)
        self.citations_table.setHorizontalHeaderLabels(["Claim", "Source", "Confidence", "Timestamp"])
        layout.addWidget(self.citations_table, 1)

        self.context_view = MarkdownBrowser(self)
        layout.addWidget(self.context_view, 1)

        self.refresh_button.clicked.connect(lambda: self.refresh())


    def refresh(self, snapshot=None):
        snapshot = snapshot or self.api.get_research_snapshot()
        query = snapshot.get("query") or self.query_edit.text().strip() or "—"
        self.query_edit.setText(query if query != "—" else "")
        self.summary_label.setText(
            f"Query: {query} | Confidence: {float(snapshot.get('confidence', 0.0)):.2f} | Sources: {len(snapshot.get('sources_used', []))}"
        )
        self.context_view.set_markdown_text(snapshot.get("research_context") or snapshot.get("summary") or "Keine Research-Details.")

        sources = snapshot.get("sources_used", [])
        self.sources_table.setRowCount(len(sources))
        for row, source in enumerate(sources):
            self.sources_table.setItem(row, 0, QTableWidgetItem(str(source).split("//")[-1]))
            self.sources_table.setItem(row, 1, QTableWidgetItem(""))
            self.sources_table.setItem(row, 2, QTableWidgetItem(""))
            self.sources_table.setItem(row, 3, QTableWidgetItem(""))
            self.sources_table.setItem(row, 4, QTableWidgetItem(str(source)))

        citations = snapshot.get("citations", [])
        self.citations_table.setRowCount(len(citations))
        for row, citation in enumerate(citations):
            self.citations_table.setItem(row, 0, QTableWidgetItem(str(citation.get("claim", ""))))
            self.citations_table.setItem(row, 1, QTableWidgetItem(str(citation.get("source", ""))))
            self.citations_table.setItem(row, 2, QTableWidgetItem(f"{float(citation.get('confidence', 0.0)):.2f}"))
            self.citations_table.setItem(row, 3, QTableWidgetItem(str(citation.get("timestamp", ""))))
