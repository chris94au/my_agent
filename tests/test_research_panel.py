import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.research_panel import ResearchPanel
from tests.gui_test_helpers import FakeGUIAPI


class ResearchPanelTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


    def test_research_panel_displays_sources_and_citations(self):
        api = FakeGUIAPI()
        panel = ResearchPanel(api)
        panel.refresh(api.get_research_snapshot())
        self.assertEqual(panel.sources_table.rowCount(), 1)
        self.assertEqual(panel.citations_table.rowCount(), 1)
        self.assertIn("Research Summary", panel.context_view.toPlainText())


if __name__ == "__main__":
    unittest.main()
