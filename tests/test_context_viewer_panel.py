import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.context_viewer_panel import ContextViewerPanel
from tests.gui_test_helpers import FakeGUIAPI


class ContextViewerPanelTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


    def test_context_viewer_renders_snapshot(self):
        api = FakeGUIAPI()
        panel = ContextViewerPanel(api)
        panel.refresh(api.get_context_snapshot())
        self.assertIn("shared", panel.view.toPlainText())
        self.assertIn("Shared Keys", panel.summary.text())


if __name__ == "__main__":
    unittest.main()
