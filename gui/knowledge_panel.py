from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
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


@register_panel("knowledge", "Knowledge", area=Qt.RightDockWidgetArea)
class KnowledgePanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._build_ui()
        self.api.knowledge_updated.connect(self.refresh)
        self.refresh(self.api.get_knowledge_snapshot())


    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        controls = QHBoxLayout()
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Knowledge Base durchsuchen…")
        self.import_button = QPushButton("Importieren", self)
        self.reindex_button = QPushButton("Neuindexieren", self)
        self.delete_button = QPushButton("Löschen", self)
        controls.addWidget(self.search_edit, 1)
        controls.addWidget(self.import_button)
        controls.addWidget(self.reindex_button)
        controls.addWidget(self.delete_button)
        layout.addLayout(controls)

        self.documents_table = QTableWidget(self)
        self.documents_table.setColumnCount(5)
        self.documents_table.setHorizontalHeaderLabels(["Titel", "Quelle", "Chunks", "Importstatus", "Embedding"])
        layout.addWidget(self.documents_table, 1)

        self.results_table = QTableWidget(self)
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Chunk", "Quelle", "Score", "Text"])
        layout.addWidget(self.results_table, 1)

        self.status_label = QLabel("Keine Dokumente geladen.", self)
        layout.addWidget(self.status_label)

        self.search_edit.returnPressed.connect(lambda: self.refresh())
        self.import_button.clicked.connect(self._import_document)
        self.reindex_button.clicked.connect(self._reindex)
        self.delete_button.clicked.connect(self._delete_selected)


    def refresh(self, snapshot=None):
        snapshot = snapshot or self.api.get_knowledge_snapshot()
        documents = snapshot.get("documents", [])
        results = snapshot.get("retrieval_results", [])
        self.documents_table.setRowCount(len(documents))
        for row, doc in enumerate(documents):
            values = [
                doc.get("title", ""),
                doc.get("source", ""),
                str(doc.get("chunk_count", 0)),
                doc.get("import_status", ""),
                "✓" if doc.get("embedding") else "",
            ]
            for col, value in enumerate(values):
                self.documents_table.setItem(row, col, QTableWidgetItem(str(value)))

        self.results_table.setRowCount(len(results))
        for row, item in enumerate(results):
            values = [
                str(item.get("chunk_index", "")),
                item.get("document_id", ""),
                f"{float(item.get('score', 0.0)):.2f}",
                item.get("content", ""),
            ]
            for col, value in enumerate(values):
                self.results_table.setItem(row, col, QTableWidgetItem(str(value)))

        self.status_label.setText(f"{len(documents)} Dokumente, {len(results)} Retrieval-Treffer")


    def _import_document(self):
        path, _ = QFileDialog.getOpenFileName(self, "Dokument importieren", "", "Text Files (*.txt *.md *.rst);;All Files (*)")
        if not path:
            return
        file_path = path
        with open(file_path, "r", encoding="utf-8") as handle:
            content = handle.read()
        title = file_path.split("/")[-1]
        self.api.import_knowledge_document(title=title, source=file_path, content=content)
        self.refresh()


    def _reindex(self):
        self.api.reindex_knowledge_base()
        self.refresh()


    def _delete_selected(self):
        row = self.documents_table.currentRow()
        if row < 0:
            return
        doc_id_item = self.documents_table.item(row, 0)
        docs = self.api.get_knowledge_snapshot().get("documents", [])
        if row >= len(docs):
            return
        self.api.delete_knowledge_document(int(docs[row]["id"]))
        self.refresh()
