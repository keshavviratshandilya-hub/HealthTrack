"""End-to-end GUI and persistence tests for Module 5 views."""

from pathlib import Path
import tempfile
import unittest

from ui.app import HealthTrackApp


class TestModule5DashboardProfileAndTracking(unittest.TestCase):
    """Test Dashboard KPIs, Profile updates, all 4 tracking pages, and user isolation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_mod5.db"
        self.app = HealthTrackApp(db_path=self.db_path)
        self.app.withdraw()
        self.app.update_idletasks()

        # Register two distinct users through AuthService
        self.user_a = self.app.auth_service.register_user(
            username="sam_a",
            email="sama@test.edu",
            password="Password1",
            confirm_password="Password1",
            full_name="Sam User",
            age="21",
            gender="Male",
            height_cm="175",
        ).user
        self.user_b = self.app.auth_service.register_user(
            username="sam_b",
            email="samb@test.edu",
            password="Password1",
            confirm_password="Password1",
            full_name="Other User",
        ).user

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        self.temp_dir.cleanup()

    def test_profile_tracking_dashboard_and_isolation(self):
        # Log in as User A -> opens Dashboard
        self.app.on_login_success(self.user_a)
        self.app.update_idletasks()

        dash = self.app.current_page_view
        self.assertEqual(dash.kpi_cards["weight"].value_label.cget("text"), "No data")
        self.assertEqual(dash.kpi_cards["bmi"].value_label.cget("text"), "--")
        self.assertEqual(dash.kpi_cards["blood_pressure"].value_label.cget("text"), "No data")
        self.assertEqual(dash.kpi_cards["heart_rate"].value_label.cget("text"), "No data")
        self.assertEqual(dash.kpi_cards["activity"].value_label.cget("text"), "0 steps")

        # 1. Profile Management: edit profile & change password
        self.app.navigate_to("profile")
        self.app.update_idletasks()
        prof = self.app.current_page_view

        prof.full_name_entry.delete(0, "end")
        prof.full_name_entry.insert(0, "Sam Updated")
        prof.height_entry.delete(0, "end")
        prof.height_entry.insert(0, "180")
        prof.target_weight_entry.delete(0, "end")
        prof.target_weight_entry.insert(0, "74")
        prof.save_profile()

        self.assertIn("updated successfully", prof.profile_status.get_text().lower())
        self.assertEqual(self.app.current_user["height_cm"], 180.0)
        self.assertEqual(self.app.sidebar_name_label.cget("text"), "Sam Updated")

        # Invalid password change (wrong current password)
        prof.current_pass_entry.insert(0, "Wrong123")
        prof.new_pass_entry.insert(0, "NewPass9")
        prof.confirm_pass_entry.insert(0, "NewPass9")
        prof.update_password()
        self.assertIn("incorrect", prof.password_status.get_text().lower())

        # Valid password change
        prof.current_pass_entry.delete(0, "end")
        prof.current_pass_entry.insert(0, "Password1")
        prof.update_password()
        self.assertIn("changed successfully", prof.password_status.get_text().lower())
        self.assertTrue(self.app.auth_service.login_user("sam_a", "NewPass9").success)

        # 2. Weight & BMI page (uses updated 180 cm height -> 81.0 kg = BMI 25.0 Overweight)
        self.app.navigate_to("weight")
        self.app.update_idletasks()
        w_view = self.app.current_page_view

        w_view.entries["weight_kg"].insert(0, "bad")
        w_view.submit_record()
        self.assertIn("valid number", w_view.status_banner.get_text().lower())

        w_view.entries["weight_kg"].delete(0, "end")
        w_view.entries["weight_kg"].insert(0, "81.0")
        w_view.notes_entry.insert(0, "Morning weigh-in")
        w_view.submit_record()
        self.assertIn("saved successfully", w_view.status_banner.get_text().lower())
        self.assertIn("25.0 (Overweight)", w_view.summary_label.cget("text"))

        # Add and delete a second weight record
        w_view.entries["weight_kg"].insert(0, "82.0")
        w_view.submit_record()
        records_before = self.app.health_service.get_records(self.user_a["id"], "weight").data
        self.assertEqual(len(records_before), 2)
        w_view.delete_record(records_before[0]["id"])
        records_after = self.app.health_service.get_records(self.user_a["id"], "weight").data
        self.assertEqual(len(records_after), 1)

        # 3. Blood Pressure page
        self.app.navigate_to("blood_pressure")
        self.app.update_idletasks()
        bp_view = self.app.current_page_view
        bp_view.entries["systolic"].insert(0, "80")
        bp_view.entries["diastolic"].insert(0, "120")
        bp_view.submit_record()
        self.assertIn("higher", bp_view.status_banner.get_text().lower())

        bp_view.entries["systolic"].delete(0, "end")
        bp_view.entries["diastolic"].delete(0, "end")
        bp_view.entries["systolic"].insert(0, "118")
        bp_view.entries["diastolic"].insert(0, "76")
        bp_view.submit_record()
        self.assertIn("saved successfully", bp_view.status_banner.get_text().lower())

        # 4. Heart Rate page
        self.app.navigate_to("heart_rate")
        self.app.update_idletasks()
        hr_view = self.app.current_page_view
        hr_view.entries["bpm"].insert(0, "68")
        hr_view.submit_record()
        self.assertIn("saved successfully", hr_view.status_banner.get_text().lower())

        # 5. Daily Activity page
        self.app.navigate_to("activity")
        self.app.update_idletasks()
        act_view = self.app.current_page_view
        act_view.entries["steps"].insert(0, "9200")
        act_view.entries["active_minutes"].insert(0, "50")
        act_view.entries["sleep_hours"].insert(0, "7.5")
        act_view.entries["calories_burned"].insert(0, "430")
        act_view.submit_record()
        self.assertIn("saved successfully", act_view.status_banner.get_text().lower())

        # 6. Return to Dashboard -> verify all 5 KPI cards show User A's live metrics
        self.app.navigate_to("dashboard")
        self.app.update_idletasks()
        dash = self.app.current_page_view
        self.assertEqual(dash.kpi_cards["weight"].value_label.cget("text"), "81.0 kg")
        self.assertEqual(dash.kpi_cards["bmi"].value_label.cget("text"), "25.0")
        self.assertEqual(dash.kpi_cards["bmi"].badge_label.cget("text"), "Overweight")
        self.assertEqual(dash.kpi_cards["blood_pressure"].value_label.cget("text"), "118/76")
        self.assertEqual(dash.kpi_cards["heart_rate"].value_label.cget("text"), "68 bpm")
        self.assertEqual(dash.kpi_cards["activity"].value_label.cget("text"), "9,200 steps")

        # 7. User isolation: logout and log in as User B -> Dashboard must show zero records
        self.app.logout()
        self.app.on_login_success(self.user_b)
        self.app.update_idletasks()
        dash_b = self.app.current_page_view
        self.assertEqual(dash_b.kpi_cards["weight"].value_label.cget("text"), "No data")
        self.assertEqual(dash_b.kpi_cards["blood_pressure"].value_label.cget("text"), "No data")
        self.assertEqual(dash_b.kpi_cards["heart_rate"].value_label.cget("text"), "No data")
        self.assertEqual(dash_b.kpi_cards["activity"].value_label.cget("text"), "0 steps")


if __name__ == "__main__":
    unittest.main()
