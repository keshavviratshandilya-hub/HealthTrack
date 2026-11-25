"""Unit tests for Module 1: Theme configuration and Validation helpers."""

from datetime import date, timedelta
import unittest

from config.theme import COLORS, FONTS, LAYOUT
from services.validators import (
    validate_activity,
    validate_age,
    validate_blood_pressure,
    validate_date,
    validate_email,
    validate_full_name,
    validate_gender,
    validate_heart_rate,
    validate_height_cm,
    validate_notes,
    validate_password,
    validate_password_match,
    validate_username,
    validate_weight_kg,
)


class TestThemeConfig(unittest.TestCase):
    """Verify required White, Navy Blue, and Teal theme constants exist."""

    def test_theme_palette_and_fonts(self):
        for key in ("bg_main", "bg_card", "navy_primary", "teal_primary", "text_primary"):
            self.assertIn(key, COLORS)
            self.assertTrue(COLORS[key].startswith("#"))
        self.assertIn("title", FONTS)
        self.assertIn("sidebar_width", LAYOUT)


class TestAccountValidators(unittest.TestCase):
    """Tests for user account and profile input validation."""

    def test_username(self):
        self.assertTrue(validate_username("alex_99").is_valid)
        self.assertFalse(validate_username("").is_valid)
        self.assertFalse(validate_username("1alex").is_valid)
        self.assertFalse(validate_username("ab").is_valid)

    def test_email(self):
        res = validate_email("  Alex.User@University.edu ")
        self.assertTrue(res.is_valid)
        self.assertEqual(res.value, "alex.user@university.edu")
        self.assertFalse(validate_email("not-an-email").is_valid)

    def test_password_and_match(self):
        self.assertTrue(validate_password("Health1").is_valid)
        self.assertFalse(validate_password("short").is_valid)
        self.assertFalse(validate_password("onlyletters").is_valid)
        self.assertFalse(validate_password("123456").is_valid)
        self.assertTrue(validate_password_match("Health1", "Health1").is_valid)
        self.assertFalse(validate_password_match("Health1", "Health2").is_valid)

    def test_profile_fields(self):
        self.assertEqual(validate_full_name("  Jane   Doe ").value, "Jane Doe")
        self.assertFalse(validate_full_name("123").is_valid)
        self.assertEqual(validate_age("22").value, 22)
        self.assertFalse(validate_age("22.5").is_valid)
        self.assertFalse(validate_age("2").is_valid)
        self.assertTrue(validate_gender("Female").is_valid)
        self.assertFalse(validate_gender("Unknown").is_valid)
        self.assertEqual(validate_height_cm("172.34").value, 172.3)
        self.assertFalse(validate_height_cm("30").is_valid)


class TestHealthMetricValidators(unittest.TestCase):
    """Tests for weight, BP, heart rate, activity, date, and notes."""

    def test_weight(self):
        res = validate_weight_kg("68.46")
        self.assertTrue(res.is_valid)
        self.assertEqual(res.value, 68.5)
        self.assertFalse(validate_weight_kg("abc").is_valid)
        self.assertFalse(validate_weight_kg("500").is_valid)

    def test_blood_pressure(self):
        res = validate_blood_pressure("120", "80")
        self.assertTrue(res.is_valid)
        self.assertEqual(res.value, (120, 80))
        self.assertFalse(validate_blood_pressure("80", "120").is_valid)
        self.assertFalse(validate_blood_pressure("120", "120").is_valid)
        self.assertFalse(validate_blood_pressure("300", "80").is_valid)

    def test_heart_rate(self):
        self.assertEqual(validate_heart_rate("72").value, 72)
        self.assertFalse(validate_heart_rate("10").is_valid)
        self.assertFalse(validate_heart_rate("72.5").is_valid)

    def test_activity(self):
        res = validate_activity("8500", "45", "7.5", "420")
        self.assertTrue(res.is_valid)
        self.assertEqual(res.value["steps"], 8500)
        self.assertEqual(res.value["sleep_hours"], 7.5)
        self.assertFalse(validate_activity("0", "0", "0", "0").is_valid)
        self.assertFalse(validate_activity("-10", "30", "7", "200").is_valid)

    def test_date_and_notes(self):
        today_str = date.today().isoformat()
        tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(validate_date(today_str).value, today_str)
        self.assertFalse(validate_date(tomorrow_str).is_valid)
        self.assertFalse(validate_date("25-11-2026").is_valid)
        self.assertTrue(validate_notes("Morning check").is_valid)
        self.assertFalse(validate_notes("a" * 251).is_valid)


if __name__ == "__main__":
    unittest.main()
