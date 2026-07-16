import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.agent_activity_panel import AgentActivityPanel
from tests.gui_test_helpers import FakeGUIAPI


class AgentActivityPanelTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


    def test_activity_panel_lists_events(self):
        api = FakeGUIAPI()
        panel = AgentActivityPanel(api)
        panel.refresh(api.get_agent_activity())
        self.assertGreater(panel.list_widget.count(), 0)
        self.assertIn("Aktivitätsereignisse", panel.summary.text())


if __name__ == "__main__":
    unittest.main()
