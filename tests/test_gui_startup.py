import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.main_window import AgentMainWindow
from tests.gui_test_helpers import FakeGUIAPI


class GuiStartupTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


    def test_main_window_loads_panels(self):
        window = AgentMainWindow(api=FakeGUIAPI())
        self.assertIsNotNone(window.centralWidget())
        self.assertIn("chat", window.panels)
        self.assertIn("planner", window.panels)
        self.assertIn("memory", window.panels)
        self.assertIn("research", window.panels)
        self.assertIn("tools", window.panels)


if __name__ == "__main__":
    unittest.main()
