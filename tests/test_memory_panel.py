import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.memory_panel import MemoryPanel
from tests.gui_test_helpers import FakeGUIAPI


class MemoryPanelTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


    def test_memory_panel_lists_and_semantic_searches(self):
        api = FakeGUIAPI()
        panel = MemoryPanel(api)
        panel.refresh(api.get_memory_snapshot())
        self.assertEqual(panel.table.rowCount(), 2)
        panel.search_edit.setText("Pasta")
        panel.refresh()
        self.assertGreaterEqual(panel.table.rowCount(), 1)
        panel._semantic_search()
        self.assertIn("Pasta", panel.history_box.text())


if __name__ == "__main__":
    unittest.main()
