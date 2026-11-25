"""Automated GUI integration tests for Module 4: Login, Registration & Sidebar Shell."""

from pathlib import Path
import tempfile
import tkinter as tk
import unittest

from config.theme import COLORS
from ui.app import HealthTrackApp, NAV_ITEMS


class TestAuthAndShellUI(unittest.TestCase):
    """Test registration, login, 8-page sidebar navigation, highlighting, and logout."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_ui.db"
        self.app = HealthTrackApp(db_path=self.db_path)
        self.app.withdraw()
        self.app.update_idletasks()

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        self.temp_dir.cleanup()

    def test_registration_login_navigation_and_logout_flow(self):
        # 1. Starts on Login screen with no signed-in user
        self.assertIsNone(self.app.current_user)
        self.assertIsNotNone(self.app.auth_view)
        self.assertEqual(self.app.auth_view.active_mode, "login")

        # 2. Switch to Registration and test invalid input error message
        self.app.auth_view.show_register()
        self.assertEqual(self.app.auth_view.active_mode, "register")
        reg = self.app.auth_view.register_frame
        reg.full_name_entry.insert(0, "Alex Student")
        reg.username_entry.insert(0, "1bad")  # Invalid username
        reg.submit_registration()
        self.assertIn("Username", reg.status_label.cget("text"))

        # 3. Valid registration switches back to Login with prefilled username
        reg.username_entry.delete(0, "end")
        reg.username_entry.insert(0, "alex_csm")
        reg.email_entry.insert(0, "alex@csm216.edu")
        reg.password_entry.insert(0, "Health123")
        reg.confirm_password_entry.insert(0, "Health123")
        reg.age_entry.insert(0, "21")
        reg.gender_menu.set("Male")
        reg.height_entry.insert(0, "175")
        reg.submit_registration()

        self.assertEqual(self.app.auth_view.active_mode, "login")
        login = self.app.auth_view.login_frame
        self.assertEqual(login.identifier_entry.get(), "alex_csm")
        self.assertIn("created successfully", login.status_label.cget("text").lower())

        # 4. Failed login stays on Auth screen and shows error message
        login.password_entry.insert(0, "WrongPass1")
        login.submit_login()
        self.assertIsNone(self.app.current_user)
        self.assertIn("invalid", login.status_label.cget("text").lower())

        # 5. Successful login opens main dashboard shell
        login.password_entry.delete(0, "end")
        login.password_entry.insert(0, "Health123")
        login.submit_login()
        self.app.update_idletasks()

        self.assertIsNotNone(self.app.current_user)
        self.assertEqual(self.app.current_user["username"], "alex_csm")
        self.assertIsNone(self.app.auth_view)
        self.assertIsNotNone(self.app.shell_frame)
        self.assertEqual(self.app.active_page, "dashboard")
        self.assertEqual(self.app.header_title_label.cget("text"), "Dashboard")

        # 6. Verify all 8 sidebar items exist and highlight properly when switched
        self.assertEqual(len(self.app.nav_buttons), 8)
        for key, expected_title, _subtitle in NAV_ITEMS:
            self.app.navigate_to(key)
            self.app.update_idletasks()
            self.assertEqual(self.app.active_page, key)
            self.assertEqual(self.app.header_title_label.cget("text"), expected_title)
            self.assertEqual(
                self.app.nav_buttons[key].cget("fg_color"),
                COLORS["teal_primary"],
            )
            for other_key, other_btn in self.app.nav_buttons.items():
                if other_key != key:
                    self.assertEqual(other_btn.cget("fg_color"), "transparent")

        # 7. Logout clears current_user and returns to Login screen
        self.app.logout()
        self.app.update_idletasks()
        self.assertIsNone(self.app.current_user)
        self.assertIsNone(self.app.shell_frame)
        self.assertIsNotNone(self.app.auth_view)
        self.assertEqual(self.app.auth_view.active_mode, "login")
        self.assertIn("signed out", self.app.auth_view.login_frame.status_label.cget("text").lower())

    def test_window_minsize_and_responsive_dashboard_layouts(self):
        scaling = self.app._get_window_scaling()
        self.assertEqual(
            tk.Tk.minsize(self.app),
            (int(960 * scaling), int(640 * scaling)),
        )

        user = self.app.auth_service.register_user(
            username="resp_user",
            email="resp@csm216.edu",
            password="Health123",
            confirm_password="Health123",
            full_name="Responsive User",
            height_cm="175",
        ).user
        self.app.on_login_success(user)
        self.app.update_idletasks()

        dash = self.app.current_page_view
        self.assertEqual(dash._layout_mode, "wide")

        dash._apply_responsive_layout(760)
        self.assertEqual(dash._layout_mode, "medium")

        dash._apply_responsive_layout(520)
        self.assertEqual(dash._layout_mode, "narrow")

        dash._apply_responsive_layout(1100)
        self.assertEqual(dash._layout_mode, "wide")

        self.app.navigate_to("reports")
        rep = self.app.current_page_view
        rep._apply_responsive_layout(650)
        self.assertEqual(rep._layout_mode, "narrow")
        rep._apply_responsive_layout(1050)
        self.assertEqual(rep._layout_mode, "wide")


if __name__ == "__main__":
    unittest.main()
