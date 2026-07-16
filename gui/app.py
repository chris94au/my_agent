from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from api import AgentAPI
from .main_window import AgentMainWindow



def create_application(argv=None):
    os.environ.setdefault("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", "offscreen"))
    app = QApplication(argv or sys.argv)
    app.setApplicationName("AI Agent Workbench")
    app.setOrganizationName("Fleet")
    app.setOrganizationDomain("local")
    return app



def create_window(api: AgentAPI | None = None):
    return AgentMainWindow(api=api)



def launch(argv=None):
    app = create_application(argv)
    window = create_window()
    window.show()
    return app, window
