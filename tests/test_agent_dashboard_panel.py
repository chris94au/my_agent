import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.agent_dashboard_panel import AgentDashboardPanel
from tests.gui_test_helpers import FakeGUIAPI


class AgentDashboardPanelTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


    def test_dashboard_shows_agents(self):
        api = FakeGUIAPI()
        panel = AgentDashboardPanel(api)
        panel.refresh(api.get_agent_dashboard())
        self.assertGreater(panel.table.rowCount(), 0)
        self.assertIn("Agenten aktiv", panel.summary.text())


if __name__ == "__main__":
    unittest.main()
