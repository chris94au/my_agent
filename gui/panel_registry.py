from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt


@dataclass
class PanelDefinition:
    name: str
    title: str
    factory: Callable
    area: Qt.DockWidgetArea = Qt.RightDockWidgetArea
    visible: bool = True
    central: bool = False


PANEL_REGISTRY: dict[str, PanelDefinition] = {}


def register_panel(name: str, title: str, area: Qt.DockWidgetArea = Qt.RightDockWidgetArea, visible: bool = True, central: bool = False):
    def decorator(cls):
        PANEL_REGISTRY[name] = PanelDefinition(
            name=name,
            title=title,
            factory=cls,
            area=area,
            visible=visible,
            central=central,
        )
        return cls

    return decorator



def get_panel_definitions():
    return list(PANEL_REGISTRY.values())



def load_panel_modules(package_name: str = "gui"):
    package = importlib.import_module(package_name)
    if not hasattr(package, "__path__"):
        return

    excluded = {
        "__init__",
        "main_window",
        "panel_registry",
        "base_panel",
        "widgets",
        "__main__",
        "app",
    }
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name in excluded:
            continue
        importlib.import_module(f"{package_name}.{module_info.name}")
