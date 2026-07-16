from __future__ import annotations

from PySide6.QtWidgets import QWidget


class BasePanel(QWidget):

    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api


    def refresh(self, snapshot=None):
        return snapshot
