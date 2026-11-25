"""Automated tests for Module 6: Health History & Graphical Reports."""

from pathlib import Path
import tempfile
import unittest

import pandas as pd

from ui.app import HealthTrackApp
from ui.components.charts import (
    build_activity_figure,
    build_blood_pressure_figure,
    build_heart_rate_figure,
    build_weight_bmi_figure,
)


class TestChartBuilders(unittest.TestCase):
    """Verify all 4 Matplotlib figures handle empty, single, and multi-row DataFrames."""

    def test_empty_dataframes_render_cleanly(self):
        empty_df = pd.DataFrame()
        for builder in (
            build_weight_bmi_figure,
            build_blood_pressure_figure,
            build_heart_rate_figure,
            build_activity_figure,
        ):
            fig = builder(empty_df)
            self.assertEqual(len(fig.axes), 1)

    def test_single_and_multiple_records_render_cleanly(self):
        w_single = pd.DataFrame(
            {"recorded_date": pd.to_datetime(["2026-11-20"]), "weight_kg": [70.0], "bmi": [22.9]}
        )
        bp_multi = pd.DataFrame(
            {
                "recorded_date": pd.to_datetime(["2026-11-19", "2026-11-20"]),
                "systolic": [122, 118],
                "diastolic": [80, 76],
            }
        )
        hr_single = pd.DataFrame(
            {"recorded_date": pd.to_datetime(["2026-11-20"]), "bpm": [72]}
        )
        act_multi = pd.DataFrame(
            {
                "recorded_date": pd.to_datetime(["2026-11-19", "2026-11-20"]),
                "steps": [7500, 9200],
            }
        )

        fig_w = build_weight_bmi_figure(w_single)
        fig_bp = build_blood_pressure_figure(bp_multi)
        fig_hr = build_heart_rate_figure(hr_single)
        fig_act = build_activity_figure(act_multi)

        self.assertGreaterEqual(len(fig_w.axes[0].lines), 1)
        self.assertEqual(len(fig_bp.axes[0].lines), 2)
        self.assertEqual(len(fig_hr.axes[0].lines), 1)
        self.assertEqual(len(fig_act.axes[0].patches), 2)


class TestModule6HistoryAndReportsViews(unittest.TestCase):
    """End-to-end GUI tests for Health History filters/deletion and Reports rendering."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_mod6.db"
        self.app = HealthTrackApp(db_path=self.db_path)
        self.app.withdraw()
        self.app.update_idletasks()

        self.user_a = self.app.auth_service.register_user(
            username="nina_a",
            email="nina@test.edu",
            password="Password1",
            confirm_password="Password1",
            full_name="Nina User",
            height_cm="168",
        ).user
        self.user_b = self.app.auth_service.register_user(
            username="omar_b",
            email="omar@test.edu",
            password="Password1",
            confirm_password="Password1",
            full_name="Omar User",
        ).user

        # Seed User A with records across multiple dates and all 4 metrics
        hs = self.app.health_service
        self.w1 = hs.add_weight_log(self.user_a["id"], "64.0", "2026-11-10", "Week 1").data
        hs.add_weight_log(self.user_a["id"], "63.2", "2026-11-20", "Week 2")
        hs.add_blood_pressure_log(self.user_a["id"], "120", "78", "2026-11-12")
        hs.add_heart_rate_log(self.user_a["id"], "70", "2026-11-15")
        hs.add_activity_log(self.user_a["id"], "8500", "40", "7.5", "350", "2026-11-18")

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        self.temp_dir.cleanup()

    def test_history_filtering_confirmed_deletion_and_isolation(self):
        self.app.on_login_success(self.user_a)
        self.app.navigate_to("history")
        self.app.update_idletasks()

        hist = self.app.current_page_view
        self.assertIn("Showing 5 record(s)", hist.summary_label.cget("text"))

        # Filter by metric type
        hist.metric_menu.set("Weight & BMI")
        hist.apply_filters()
        self.assertIn("Showing 2 record(s)", hist.summary_label.cget("text"))

        # Filter by date range + invalid date range handling
        hist.metric_menu.set("All Metrics")
        hist.start_date_entry.insert(0, "2026-11-20")
        hist.end_date_entry.insert(0, "2026-11-10")
        hist.apply_filters()
        self.assertIn("cannot be later", hist.status_banner.get_text().lower())

        hist.start_date_entry.delete(0, "end")
        hist.end_date_entry.delete(0, "end")
        hist.start_date_entry.insert(0, "2026-11-12")
        hist.end_date_entry.insert(0, "2026-11-18")
        hist.apply_filters()
        self.assertIn("Showing 3 record(s)", hist.summary_label.cget("text"))

        hist.reset_filters()
        self.assertIn("Showing 5 record(s)", hist.summary_label.cget("text"))

        # Cancel deletion -> record remains
        hist.confirm_delete = lambda _lbl, _dt: False
        hist.handle_delete(("weight", self.w1["id"]))
        self.assertIn("Showing 5 record(s)", hist.summary_label.cget("text"))

        # Confirm deletion -> record is deleted from SQLite
        hist.confirm_delete = lambda _lbl, _dt: True
        hist.handle_delete(("weight", self.w1["id"]))
        self.assertIn("Showing 4 record(s)", hist.summary_label.cget("text"))
        self.assertIn("deleted", hist.status_banner.get_text().lower())

        # Switch to User B -> sees 0 records
        self.app.logout()
        self.app.on_login_success(self.user_b)
        self.app.navigate_to("history")
        self.app.update_idletasks()
        hist_b = self.app.current_page_view
        self.assertIn("Showing 0 record(s)", hist_b.summary_label.cget("text"))

    def test_reports_view_empty_single_multi_and_date_filter(self):
        # User B has empty data -> Reports renders all 4 charts without error
        self.app.on_login_success(self.user_b)
        self.app.navigate_to("reports")
        self.app.update_idletasks()
        rep_b = self.app.current_page_view
        self.assertEqual(len(rep_b.canvases), 4)

        # User A has multi-metric data -> Reports renders all 4 charts and filters by date
        self.app.logout()
        self.app.on_login_success(self.user_a)
        self.app.navigate_to("reports")
        self.app.update_idletasks()
        rep_a = self.app.current_page_view
        self.assertEqual(len(rep_a.canvases), 4)

        rep_a.start_date_entry.insert(0, "2026-11-15")
        rep_a.end_date_entry.insert(0, "2026-11-25")
        rep_a.refresh_reports()
        self.assertEqual(len(rep_a.canvases), 4)
        self.assertEqual(rep_a.status_banner.get_text(), "")


if __name__ == "__main__":
    unittest.main()
