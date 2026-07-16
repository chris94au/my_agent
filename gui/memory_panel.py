from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
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


@register_panel("memory", "Memory", area=Qt.RightDockWidgetArea)
class MemoryPanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._build_ui()
        self.api.memory_updated.connect(self.refresh)
        self.refresh(self.api.get_memory_snapshot())


    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        controls = QHBoxLayout()
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Memory durchsuchen…")
        self.kind_filter = QComboBox(self)
        self.kind_filter.addItems(["Alle", "Fakten", "Zusammenfassungen"])
        self.refresh_button = QPushButton("Aktualisieren", self)
        self.semantic_button = QPushButton("Semantische Suche testen", self)
        controls.addWidget(self.search_edit, 1)
        controls.addWidget(self.kind_filter)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.semantic_button)
        layout.addLayout(controls)

        self.table = QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Typ", "Kategorie", "Key", "Value", "Importance", "Confidence", "Recency", "Embedding"])
        layout.addWidget(self.table, 1)

        edit_bar = QHBoxLayout()
        self.importance_spin = QSpinBox(self)
        self.importance_spin.setRange(1, 10)
        self.confidence_spin = QSpinBox(self)
        self.confidence_spin.setRange(0, 100)
        self.confidence_spin.setSuffix(" %")
        self.update_button = QPushButton("Ändern", self)
        self.delete_button = QPushButton("Löschen", self)
        self.history_button = QPushButton("Historie", self)
        edit_bar.addWidget(QLabel("Importance:", self))
        edit_bar.addWidget(self.importance_spin)
        edit_bar.addWidget(QLabel("Confidence:", self))
        edit_bar.addWidget(self.confidence_spin)
        edit_bar.addWidget(self.update_button)
        edit_bar.addWidget(self.delete_button)
        edit_bar.addWidget(self.history_button)
        edit_bar.addStretch(1)
        layout.addLayout(edit_bar)

        self.history_box = QLineEdit(self)
        self.history_box.setPlaceholderText("Memory-Historie / semantische Treffer")
        layout.addWidget(self.history_box)

        self.refresh_button.clicked.connect(lambda: self.refresh())
        self.semantic_button.clicked.connect(self._semantic_search)
        self.update_button.clicked.connect(self._update_selected)
        self.delete_button.clicked.connect(self._delete_selected)
        self.history_button.clicked.connect(self._show_history)
        self.search_edit.returnPressed.connect(lambda: self.refresh())
        self.table.itemSelectionChanged.connect(self._selection_changed)


    def _current_items(self):
        items = []
        search_term = self.search_edit.text().strip().casefold()
        kind = self.kind_filter.currentText()
        snapshot = self.api.get_memory_snapshot(search_term or None)
        facts = snapshot.get("facts", [])
        summaries = snapshot.get("summaries", [])
        if kind in {"Alle", "Fakten"}:
            for entry in facts:
                items.append(("fact", entry))
        if kind in {"Alle", "Zusammenfassungen"}:
            for entry in summaries:
                items.append(("summary", entry))
        if search_term:
            items = [
                item for item in items
                if search_term in json_dump(item[1]).casefold()
            ]
        return items


    def _selection_changed(self):
        row = self.table.currentRow()
        if row < 0:
            return
        importance_item = self.table.item(row, 4)
        confidence_item = self.table.item(row, 5)
        if importance_item:
            try:
                self.importance_spin.setValue(int(float(importance_item.text())))
            except Exception:
                pass
        if confidence_item:
            try:
                self.confidence_spin.setValue(int(float(confidence_item.text()) * 100))
            except Exception:
                pass


    def refresh(self, snapshot=None):
        items = self._current_items()
        self.table.setRowCount(len(items))
        for row, (kind, item) in enumerate(items):
            embedding_present = bool(item.get("embedding"))
            recency = item.get("last_used_at") or item.get("last_seen_at") or item.get("timestamp") or ""
            values = [
                kind,
                item.get("category") or item.get("topic") or "",
                item.get("key") or item.get("topic") or "",
                item.get("value") or item.get("summary") or "",
                str(item.get("importance", "")),
                f"{float(item.get('confidence', 0.0)):.2f}",
                recency,
                "✓" if embedding_present else "",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

        self.history_box.setText(f"{len(items)} Einträge geladen")


    def _selected_record(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        kind = self.table.item(row, 0).text()
        key = self.table.item(row, 2).text()
        value = self.table.item(row, 3).text()
        return kind, key, value, row


    def _update_selected(self):
        selected = self._selected_record()
        if not selected:
            return
        kind, key, value, row = selected
        importance = self.importance_spin.value()
        confidence = self.confidence_spin.value() / 100.0
        record_id = self._resolve_record_id(row)
        if record_id is None:
            return
        self.api.update_memory_record(kind, record_id, importance=importance, confidence=confidence)
        self.refresh()


    def _delete_selected(self):
        selected = self._selected_record()
        if not selected:
            return
        kind, key, value, row = selected
        record_id = self._resolve_record_id(row)
        if record_id is None:
            return
        self.api.delete_memory_record(kind, record_id)
        self.refresh()


    def _show_history(self):
        selected = self._selected_record()
        if not selected:
            self.history_box.setText(self.api.get_memory_snapshot().get("relevant", ""))
            return
        kind, key, value, row = selected
        record_id = self._resolve_record_id(row)
        history = self.api.get_memory_history(kind, record_id)
        self.history_box.setText("\n".join(history) if history else "Keine Historie gefunden")


    def _semantic_search(self):
        query = self.search_edit.text().strip()
        results = self.api.search_memory(query)
        self.history_box.setText("\n".join([json_dump(item) for item in results]) if results else "Keine Treffer")


    def _resolve_record_id(self, row):
        search_term = self.search_edit.text().strip().casefold()
        items = self._current_items()
        if row >= len(items):
            return None
        kind, item = items[row]
        return item.get("id")


def json_dump(value):
    try:
        import json

        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)
