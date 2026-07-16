import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.tool_panel import ToolPanel
from tests.gui_test_helpers import FakeGUIAPI


class ToolPanelTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


    def test_tool_panel_filters_events(self):
        api = FakeGUIAPI()
        panel = ToolPanel(api)
        panel.refresh(api.get_tool_events())
        self.assertEqual(panel.table.rowCount(), 2)
        panel.filter_combo.setCurrentIndex(1)
        panel.refresh()
        self.assertEqual(panel.table.rowCount(), 1)
        self.assertGreaterEqual(len(panel.summary.text()), 1)


if __name__ == "__main__":
    unittest.main()
