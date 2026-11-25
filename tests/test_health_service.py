"""Automated tests for Module 3: Core Health Logic, BMI Engine, and Pandas Summaries."""

from pathlib import Path
import tempfile
import unittest

from database.db_manager import DatabaseManager
from services.auth_service import AuthService
from services.health_service import (
    HealthService,
    calculate_bmi,
    classify_blood_pressure,
    classify_bmi,
)


class TestBMIEngine(unittest.TestCase):
    """Test BMI calculation formula, edge cases, and category classification."""

    def test_bmi_calculation_and_edge_cases(self):
        self.assertEqual(calculate_bmi(70.0, 175.0), 22.9)
        self.assertEqual(calculate_bmi(50.0, 170.0), 17.3)
        self.assertIsNone(calculate_bmi(None, 175.0))
        self.assertIsNone(calculate_bmi(70.0, None))
        self.assertIsNone(calculate_bmi(70.0, 0))
        self.assertIsNone(calculate_bmi(-70.0, 175.0))

    def test_bmi_classifications_at_boundaries(self):
        self.assertEqual(classify_bmi(None), "Unknown")
        self.assertEqual(classify_bmi(18.4), "Underweight")
        self.assertEqual(classify_bmi(18.5), "Normal")
        self.assertEqual(classify_bmi(24.9), "Normal")
        self.assertEqual(classify_bmi(25.0), "Overweight")
        self.assertEqual(classify_bmi(29.9), "Overweight")
        self.assertEqual(classify_bmi(30.0), "Obese")

    def test_blood_pressure_classification(self):
        self.assertEqual(classify_blood_pressure(118, 76), "Normal")
        self.assertEqual(classify_blood_pressure(125, 78), "Elevated")
        self.assertEqual(classify_blood_pressure(134, 82), "High (Stage 1)")
        self.assertEqual(classify_blood_pressure(145, 92), "High (Stage 2)")


class TestHealthServiceCRUDAndAnalytics(unittest.TestCase):
    """Test add, view, date filter, delete, Pandas summaries, and user isolation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_health.db"
        self.db = DatabaseManager(self.db_path)
        self.auth = AuthService(self.db)
        self.health = HealthService(self.db)

        self.user_a = self.auth.register_user(
            username="alice_h",
            email="alice@health.com",
            password="Password1",
            confirm_password="Password1",
            full_name="Alice Health",
            age="24",
            gender="Female",
            height_cm="170",
        ).user

        self.user_b = self.auth.register_user(
            username="bob_h",
            email="bob@health.com",
            password="Password1",
            confirm_password="Password1",
            full_name="Bob Health",
        ).user

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_and_view_all_four_metrics(self):
        w_res = self.health.add_weight_log(self.user_a["id"], "68.0", "2026-11-20", "Morning")
        self.assertTrue(w_res.success)
        # 68 / (1.7^2) = 23.5
        self.assertEqual(w_res.data["bmi"], 23.5)

        bp_res = self.health.add_blood_pressure_log(self.user_a["id"], "120", "80", "2026-11-20")
        self.assertTrue(bp_res.success)

        hr_res = self.health.add_heart_rate_log(self.user_a["id"], "72", "2026-11-20")
        self.assertTrue(hr_res.success)

        act_res = self.health.add_activity_log(
            self.user_a["id"], "8000", "45", "7.5", "380", "2026-11-20"
        )
        self.assertTrue(act_res.success)

        # User B has no height set, so BMI is None
        wb_res = self.health.add_weight_log(self.user_b["id"], "80.0", "2026-11-20")
        self.assertTrue(wb_res.success)
        self.assertIsNone(wb_res.data["bmi"])

        # Validation failures
        self.assertFalse(self.health.add_weight_log(self.user_a["id"], "abc").success)
        self.assertFalse(self.health.add_blood_pressure_log(self.user_a["id"], "70", "110").success)
        self.assertFalse(self.health.add_heart_rate_log(self.user_a["id"], "10").success)
        self.assertFalse(self.health.add_activity_log(self.user_a["id"], "0", "0", "0", "0").success)

    def test_date_filtering_and_delete(self):
        self.health.add_heart_rate_log(self.user_a["id"], "68", "2026-11-10")
        rec_mid = self.health.add_heart_rate_log(self.user_a["id"], "74", "2026-11-15").data
        self.health.add_heart_rate_log(self.user_a["id"], "70", "2026-11-20")

        filtered = self.health.get_records(
            self.user_a["id"], "heart_rate", start_date="2026-11-12", end_date="2026-11-18"
        )
        self.assertTrue(filtered.success)
        self.assertEqual(len(filtered.data), 1)
        self.assertEqual(filtered.data[0]["bpm"], 74)

        # Invalid date range
        bad_range = self.health.get_records(
            self.user_a["id"], "heart_rate", start_date="2026-11-20", end_date="2026-11-10"
        )
        self.assertFalse(bad_range.success)

        # Delete record
        del_ok = self.health.delete_record(self.user_a["id"], "heart_rate", rec_mid["id"])
        self.assertTrue(del_ok.success)
        remaining = self.health.get_records(self.user_a["id"], "heart_rate").data
        self.assertEqual(len(remaining), 2)

    def test_pandas_summaries_and_unified_history(self):
        self.health.add_weight_log(self.user_a["id"], "70.0", "2026-11-01")
        self.health.add_weight_log(self.user_a["id"], "68.0", "2026-11-15")
        self.health.add_activity_log(self.user_a["id"], "6000", "30", "7.0", "300", "2026-11-01")
        self.health.add_activity_log(self.user_a["id"], "10000", "60", "8.0", "500", "2026-11-15")

        w_summary = self.health.get_metric_summary(self.user_a["id"], "weight")
        self.assertTrue(w_summary.success)
        self.assertEqual(w_summary.data["count"], 2)
        self.assertEqual(w_summary.data["latest_weight"], 68.0)
        self.assertEqual(w_summary.data["avg_weight"], 69.0)
        self.assertEqual(w_summary.data["weight_change"], -2.0)
        self.assertEqual(w_summary.data["bmi_category"], "Normal")

        act_summary = self.health.get_metric_summary(self.user_a["id"], "activity")
        self.assertEqual(act_summary.data["total_steps"], 16000)
        self.assertEqual(act_summary.data["avg_sleep_hours"], 7.5)

        history = self.health.get_unified_history_df(self.user_a["id"], metric_filter="all")
        self.assertTrue(history.success)
        self.assertEqual(len(history.data), 4)

        overview = self.health.get_dashboard_overview(self.user_a["id"])
        self.assertTrue(overview.success)
        self.assertEqual(overview.data["weight"]["latest_weight"], 68.0)
        self.assertEqual(overview.data["blood_pressure"]["count"], 0)

    def test_user_data_isolation(self):
        rec_a = self.health.add_weight_log(self.user_a["id"], "65.0", "2026-11-20").data

        # User B cannot see or delete User A's records or summary
        b_records = self.health.get_records(self.user_b["id"], "weight").data
        self.assertEqual(b_records, [])

        b_summary = self.health.get_metric_summary(self.user_b["id"], "weight").data
        self.assertEqual(b_summary["count"], 0)

        del_attempt = self.health.delete_record(self.user_b["id"], "weight", rec_a["id"])
        self.assertFalse(del_attempt.success)

        # User A's record remains intact
        a_records = self.health.get_records(self.user_a["id"], "weight").data
        self.assertEqual(len(a_records), 1)


if __name__ == "__main__":
    unittest.main()
