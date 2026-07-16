from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QToolBar,
    QVBoxLayout,
)

from .base_panel import BasePanel
from .panel_registry import register_panel
from .widgets import MarkdownBrowser


@register_panel("chat", "Chat", area=Qt.LeftDockWidgetArea, central=True)
class ChatPanel(BasePanel):

    def __init__(self, api, parent=None):
        super().__init__(api, parent)
        self._stream_buffer = ""
        self._build_ui()
        self._wire_api()
        self.refresh()


    def _build_ui(self):
        root = QVBoxLayout(self)
        self.setLayout(root)

        toolbar = QToolBar(self)
        toolbar.setMovable(False)
        self.new_action = QAction("Neue Unterhaltung", self)
        self.clear_action = QAction("Gespräch löschen", self)
        self.regenerate_action = QAction("Antwort neu erzeugen", self)
        self.copy_action = QAction("Letzte Antwort kopieren", self)
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.clear_action)
        toolbar.addAction(self.regenerate_action)
        toolbar.addAction(self.copy_action)
        root.addWidget(toolbar)

        splitter = QSplitter(Qt.Vertical, self)
        root.addWidget(splitter, 1)

        self.chat_view = MarkdownBrowser(self)
        self.chat_view.setPlaceholderText("Chatverlauf erscheint hier…")
        splitter.addWidget(self.chat_view)

        editor_container = BasePanel(self.api, self)
        editor_layout = QVBoxLayout(editor_container)
        editor_container.setLayout(editor_layout)

        self.status_label = QLabel("Bereit", editor_container)
        self.status_label.setStyleSheet("font-weight: 600;")
        editor_layout.addWidget(self.status_label)

        self.input_edit = QPlainTextEdit(editor_container)
        self.input_edit.setPlaceholderText("Nachricht eingeben…")
        self.input_edit.setTabChangesFocus(True)
        self.input_edit.setMinimumHeight(90)
        font = QFont("Monospace")
        font.setStyleHint(QFont.Monospace)
        self.input_edit.setFont(font)
        editor_layout.addWidget(self.input_edit, 1)

        controls = QHBoxLayout()
        self.send_button = QPushButton("Senden", editor_container)
        self.stop_button = QPushButton("Stream beenden", editor_container)
        self.stop_button.setEnabled(False)
        controls.addWidget(self.send_button)
        controls.addWidget(self.stop_button)
        controls.addStretch(1)
        editor_layout.addLayout(controls)

        self.planner_hint = QLabel("Planner: kein aktiver Schritt", editor_container)
        self.planner_hint.setWordWrap(True)
        editor_layout.addWidget(self.planner_hint)

        splitter.addWidget(editor_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.new_action.triggered.connect(self._new_conversation)
        self.clear_action.triggered.connect(self._clear_conversation)
        self.regenerate_action.triggered.connect(self._regenerate)
        self.copy_action.triggered.connect(self._copy_last_response)
        self.send_button.clicked.connect(self._send_message)
        self.stop_button.clicked.connect(self._finish_stream)
        self.input_edit.installEventFilter(self)


    def _wire_api(self):
        self.api.chat_message_added.connect(self._on_chat_message)
        self.api.stream_chunk.connect(self._on_stream_chunk)
        self.api.planner_updated.connect(self._on_planner_updated)
        self.api.state_changed.connect(self.refresh)


    def eventFilter(self, obj, event):
        if obj is self.input_edit and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() == Qt.ControlModifier:
                self._send_message()
                return True
        return super().eventFilter(obj, event)


    def _conversation_markdown(self):
        lines = ["# Gespräch"]
        history = self.api.get_chat_history()
        if not history:
            lines.append("Noch keine Nachrichten.")
            return "\n\n".join(lines)

        for entry in history:
            role = entry.get("role", "")
            content = entry.get("content", "")
            label = "Benutzer" if role == "user" else "Agent"
            lines.append(f"## {label}")
            lines.append(content or "")

        return "\n\n".join(lines)


    def _render(self):
        content = self._conversation_markdown()
        if self._stream_buffer:
            content += f"\n\n## Agent (Streaming)\n{self._stream_buffer}"
        self.chat_view.set_markdown_text(content)


    def _send_message(self):
        message = self.input_edit.toPlainText().strip()
        if not message:
            return
        self.input_edit.clear()
        self._stream_buffer = ""
        self.status_label.setText("Nachricht wird verarbeitet…")
        self.stop_button.setEnabled(True)
        self.api.send_message(message, stream=True)
        self._render()


    def _finish_stream(self):
        self.status_label.setText("Warte auf Abschluss…")
        self.stop_button.setEnabled(False)


    def _on_chat_message(self, message: dict):
        if message.get("role") == "assistant":
            self._stream_buffer = ""
            self.stop_button.setEnabled(False)
        self._render()


    def _on_stream_chunk(self, chunk: str):
        self._stream_buffer += chunk
        self._render()


    def _on_planner_updated(self, snapshot: dict):
        goal = snapshot.get("goal") or "kein aktiver Plan"
        current = snapshot.get("current_step") or {}
        current_text = current.get("description") or current.get("action") or "—"
        self.planner_hint.setText(f"Planner: {goal} | Aktuell: {current_text}")


    def _new_conversation(self):
        self.api.new_conversation()
        self._stream_buffer = ""
        self.status_label.setText("Neue Unterhaltung")
        self._render()


    def _clear_conversation(self):
        self.api.clear_conversation()
        self._stream_buffer = ""
        self.status_label.setText("Gespräch gelöscht")
        self._render()


    def _regenerate(self):
        self._stream_buffer = ""
        self.status_label.setText("Antwort wird neu erzeugt…")
        self.api.regenerate_last(stream=True)


    def _copy_last_response(self):
        history = self.api.get_chat_history()
        assistant_messages = [item for item in history if item.get("role") == "assistant"]
        if not assistant_messages:
            return
        from PySide6.QtWidgets import QApplication

        clipboard = QApplication.instance().clipboard()
        clipboard.setText(assistant_messages[-1].get("content", ""))


    def refresh(self, snapshot=None):
        self._render()
        planner_snapshot = self.api.get_planner_snapshot()
        goal = planner_snapshot.get("goal") or "kein aktiver Plan"
        current = planner_snapshot.get("current_step") or {}
        current_text = current.get("description") or current.get("action") or "—"
        self.planner_hint.setText(f"Planner: {goal} | Aktuell: {current_text}")
        self.status_label.setText("Bereit" if not self._stream_buffer else "Streaming…")
