import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.planner_panel import PlannerPanel
from tests.gui_test_helpers import FakeGUIAPI


class PlannerPanelTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


    def test_planner_panel_renders_snapshot(self):
        api = FakeGUIAPI()
        panel = PlannerPanel(api)
        panel.refresh(api.get_planner_snapshot())
        self.assertIn("Projekt analysieren", panel.goal_label.text())
        self.assertGreater(panel.steps_list.count(), 0)
        self.assertIn("Schritt 3", panel.current_step_label.text())


if __name__ == "__main__":
    unittest.main()
