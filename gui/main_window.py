from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDockWidget, QMainWindow, QMenu, QMessageBox, QTabWidget

from api import AgentAPI

from .panel_registry import PANEL_REGISTRY, get_panel_definitions, load_panel_modules


class AgentMainWindow(QMainWindow):

    def __init__(self, api: AgentAPI | None = None, parent=None):
        super().__init__(parent)
        self.api = api or AgentAPI()
        self.setWindowTitle("AI Agent Workbench")
        self.resize(1500, 950)
        self.panels: dict[str, object] = {}
        self.docks: dict[str, QDockWidget] = {}
        self._build_ui()
        self.api.refresh_all()


    def _build_ui(self):
        load_panel_modules("gui")
        central_def = None
        for definition in get_panel_definitions():
            if definition.central:
                central_def = definition
                break

        if central_def is None:
            raise RuntimeError("No central panel registered")

        central_widget = central_def.factory(self.api, self)
        self.panels[central_def.name] = central_widget
        self.setCentralWidget(central_widget)

        for definition in get_panel_definitions():
            if definition.central:
                continue
            panel_widget = definition.factory(self.api, self)
            self.panels[definition.name] = panel_widget
            dock = QDockWidget(definition.title, self)
            dock.setObjectName(f"dock_{definition.name}")
            dock.setWidget(panel_widget)
            dock.setFeatures(
                QDockWidget.DockWidgetMovable
                | QDockWidget.DockWidgetFloatable
                | QDockWidget.DockWidgetClosable
            )
            self.addDockWidget(definition.area, dock)
            self.docks[definition.name] = dock

        self._build_menus()
        self.statusBar().showMessage("Agent Workbench bereit")


    def _build_menus(self):
        view_menu = self.menuBar().addMenu("Ansicht")
        for name, dock in self.docks.items():
            action = dock.toggleViewAction()
            view_menu.addAction(action)

        actions_menu = self.menuBar().addMenu("Aktionen")
        refresh_action = actions_menu.addAction("Alles aktualisieren")
        refresh_action.triggered.connect(self._refresh_all)
        new_chat_action = actions_menu.addAction("Neue Unterhaltung")
        new_chat_action.triggered.connect(self.api.new_conversation)
        export_logs_action = actions_menu.addAction("Logs exportieren")
        export_logs_action.triggered.connect(self._export_logs)

        help_menu = self.menuBar().addMenu("Hilfe")
        about_action = help_menu.addAction("Über")
        about_action.triggered.connect(self._show_about)


    def _refresh_all(self):
        self.api.refresh_all()
        for panel in self.panels.values():
            refresh = getattr(panel, "refresh", None)
            if callable(refresh):
                try:
                    refresh()
                except TypeError:
                    refresh(None)


    def _export_logs(self):
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(self, "Logs exportieren", "agent_logs.json", "JSON Files (*.json)")
        if not path:
            return
        self.api.export_logs(path)
        self.statusBar().showMessage(f"Logs exportiert nach {path}")


    def _show_about(self):
        QMessageBox.information(
            self,
            "Über",
            "AI Agent Workbench\n\nModulare Desktop-Oberfläche für Chat, Planner, Memory, Research, Tools, Tasks und Logs.",
        )


    def register_panel(self, name: str, widget, title: str, area: Qt.DockWidgetArea = Qt.RightDockWidgetArea):
        dock = QDockWidget(title, self)
        dock.setObjectName(f"dock_{name}")
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )
        self.addDockWidget(area, dock)
        self.panels[name] = widget
        self.docks[name] = dock
        return dock



def create_main_window(api: AgentAPI | None = None):
    return AgentMainWindow(api=api)
