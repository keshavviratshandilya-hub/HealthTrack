"""Automated tests for Module 7: CSV & PDF Export and Final End-to-End Persistence."""

from pathlib import Path
import tempfile
import unittest

import pandas as pd

from database.db_manager import DatabaseManager
from services.auth_service import AuthService
from services.export_service import ExportService
from services.health_service import HealthService
from ui.app import HealthTrackApp


class TestExportService(unittest.TestCase):
    """Test CSV and PDF generation, empty/error handling, and user isolation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db = DatabaseManager(self.root / "export_test.db")
        self.auth = AuthService(self.db)
        self.health = HealthService(self.db)
        self.exporter = ExportService(self.health)

        self.user_a = self.auth.register_user(
            username="maya_a",
            email="maya@test.edu",
            password="Password1",
            confirm_password="Password1",
            full_name="Maya Patel",
            age="24",
            gender="Female",
            height_cm="165",
            target_weight_kg="58",
        ).user
        self.user_b = self.auth.register_user(
            username="leo_b",
            email="leo@test.edu",
            password="Password1",
            confirm_password="Password1",
            full_name="Leo Empty",
        ).user

        self.health.add_weight_log(self.user_a["id"], "61.0", "2026-11-10", "Start")
        self.health.add_weight_log(self.user_a["id"], "60.2", "2026-11-20", "Progress")
        self.health.add_blood_pressure_log(self.user_a["id"], "118", "76", "2026-11-15")
        self.health.add_heart_rate_log(self.user_a["id"], "69", "2026-11-18")
        self.health.add_activity_log(self.user_a["id"], "9100", "45", "7.8", "410", "2026-11-19")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_csv_export_filtered_empty_and_isolation(self):
        csv_all = self.root / "all_records.csv"
        res_all = self.exporter.export_to_csv(self.user_a, csv_all)
        self.assertTrue(res_all.success)
        self.assertTrue(csv_all.exists())
        df = pd.read_csv(csv_all)
        self.assertEqual(len(df), 5)
        self.assertEqual(list(df.columns), ["Date", "Metric", "Details", "Notes"])

        # Filtered CSV export
        csv_weight = self.root / "weight_only.csv"
        res_w = self.exporter.export_to_csv(self.user_a, csv_weight, metric_filter="weight")
        self.assertTrue(res_w.success)
        df_w = pd.read_csv(csv_weight)
        self.assertEqual(len(df_w), 2)

        # User B has no data -> empty CSV blocked gracefully with clear message
        csv_b = self.root / "user_b.csv"
        res_b = self.exporter.export_to_csv(self.user_b, csv_b)
        self.assertFalse(res_b.success)
        self.assertFalse(csv_b.exists())
        self.assertIn("no health records", res_b.message.lower())

        # Invalid date filter error
        res_bad = self.exporter.export_to_csv(
            self.user_a, self.root / "bad.csv", start_date="2026-11-25", end_date="2026-11-01"
        )
        self.assertFalse(res_bad.success)

    def test_pdf_export_with_charts_empty_data_and_error_handling(self):
        pdf_full = self.root / "maya_report.pdf"
        res = self.exporter.export_to_pdf(self.user_a, pdf_full)
        self.assertTrue(res.success)
        self.assertTrue(pdf_full.exists())
        content = pdf_full.read_bytes()
        self.assertTrue(content.startswith(b"%PDF-"))
        self.assertGreater(len(content), 15_000)

        # User B has empty data -> still produces a valid PDF cleanly without errors
        pdf_empty = self.root / "leo_report.pdf"
        res_empty = self.exporter.export_to_pdf(self.user_b, pdf_empty)
        self.assertTrue(res_empty.success)
        self.assertTrue(pdf_empty.read_bytes().startswith(b"%PDF-"))

        # Invalid date range fails cleanly
        res_bad = self.exporter.export_to_pdf(
            self.user_a, self.root / "bad.pdf", start_date="not-a-date"
        )
        self.assertFalse(res_bad.success)


class TestEndToEndRestartAndUIExports(unittest.TestCase):
    """Test UI export buttons and full data persistence across app restarts."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / "e2e_app.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ui_exports_and_restart_persistence(self):
        # Session 1: register, log in, log metrics, export CSV & PDF, then close app
        app1 = HealthTrackApp(db_path=self.db_path)
        app1.withdraw()
        app1.update_idletasks()

        try:
            app1.auth_view.show_register()
            reg = app1.auth_view.register_frame
            reg.full_name_entry.insert(0, "Chris Final")
            reg.username_entry.insert(0, "chris_f")
            reg.email_entry.insert(0, "chris@csm216.edu")
            reg.password_entry.insert(0, "Final123")
            reg.confirm_password_entry.insert(0, "Final123")
            reg.height_entry.insert(0, "178")
            reg.submit_registration()

            login = app1.auth_view.login_frame
            login.password_entry.insert(0, "Final123")
            login.submit_login()
            app1.update_idletasks()

            # Add weight and activity through tracking views
            app1.navigate_to("weight")
            w_view = app1.current_page_view
            w_view.entries["weight_kg"].insert(0, "76.0")
            w_view.submit_record()

            app1.navigate_to("activity")
            act_view = app1.current_page_view
            act_view.entries["steps"].insert(0, "8400")
            act_view.entries["active_minutes"].insert(0, "40")
            act_view.entries["sleep_hours"].insert(0, "7.5")
            act_view.entries["calories_burned"].insert(0, "390")
            act_view.submit_record()

            # Export CSV & PDF from HistoryView
            app1.navigate_to("history")
            hist = app1.current_page_view
            csv_out = self.root / "ui_history.csv"
            pdf_out = self.root / "ui_history.pdf"

            hist.ask_save_path = lambda _ext, _name: str(csv_out)
            hist.export_csv()
            self.assertTrue(csv_out.exists())
            self.assertIn("exported 2 record", hist.status_banner.get_text().lower())

            hist.ask_save_path = lambda _ext, _name: str(pdf_out)
            hist.export_pdf()
            self.assertTrue(pdf_out.exists())
            self.assertIn("pdf report saved", hist.status_banner.get_text().lower())

            # Cancelled save dialog does nothing without error
            hist.ask_save_path = lambda _ext, _name: ""
            hist.export_csv()

            # Export PDF from ReportsView
            app1.navigate_to("reports")
            rep = app1.current_page_view
            rep_pdf_out = self.root / "ui_reports.pdf"
            rep.ask_save_path = lambda _ext, _name: str(rep_pdf_out)
            rep.export_pdf()
            self.assertTrue(rep_pdf_out.exists())
        finally:
            app1.destroy()

        # Session 2: Simulate full application restart with a fresh HealthTrackApp instance
        app2 = HealthTrackApp(db_path=self.db_path)
        app2.withdraw()
        app2.update_idletasks()
        try:
            login2 = app2.auth_view.login_frame
            login2.identifier_entry.insert(0, "chris_f")
            login2.password_entry.insert(0, "Final123")
            login2.submit_login()
            app2.update_idletasks()

            dash2 = app2.current_page_view
            self.assertEqual(dash2.kpi_cards["weight"].value_label.cget("text"), "76.0 kg")
            self.assertEqual(dash2.kpi_cards["bmi"].value_label.cget("text"), "24.0")
            self.assertEqual(dash2.kpi_cards["activity"].value_label.cget("text"), "8,400 steps")

            app2.navigate_to("history")
            self.assertIn("Showing 2 record(s)", app2.current_page_view.summary_label.cget("text"))
        finally:
            app2.destroy()


if __name__ == "__main__":
    unittest.main()
