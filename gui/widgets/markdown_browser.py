from __future__ import annotations

from PySide6.QtWidgets import QTextBrowser


class MarkdownBrowser(QTextBrowser):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)


    def set_markdown_text(self, text: str):
        try:
            self.setMarkdown(text or "")
        except Exception:
            self.setPlainText(text or "")
