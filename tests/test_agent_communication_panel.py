import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.agent_communication_panel import AgentCommunicationPanel
from tests.gui_test_helpers import FakeGUIAPI


class AgentCommunicationPanelTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


    def test_communication_panel_renders_context(self):
        api = FakeGUIAPI()
        panel = AgentCommunicationPanel(api)
        panel.refresh(api.get_agent_communication())
        self.assertIn("events", panel.view.toPlainText())
        self.assertIn("Kommunikationsereignisse", panel.summary.text())


if __name__ == "__main__":
    unittest.main()
