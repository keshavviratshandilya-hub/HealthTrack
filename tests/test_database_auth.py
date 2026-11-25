"""Automated tests for Module 2: SQLite Database Manager & Authentication."""

from pathlib import Path
import sqlite3
import tempfile
import unittest

from database.db_manager import DatabaseManager
from services.auth_service import AuthService, hash_password, verify_password


class TestDatabaseAndAuth(unittest.TestCase):
    """Test schema creation, registration, duplicate checks, login, isolation, and persistence."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_healthtrack.db"
        self.db = DatabaseManager(self.db_path)
        self.auth = AuthService(self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_tables_and_foreign_keys_created(self):
        """All 5 core tables exist and foreign keys reject invalid user references."""
        tables = self.db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
        table_names = {row["name"] for row in tables}
        expected_tables = {
            "users",
            "weight_logs",
            "blood_pressure_logs",
            "heart_rate_logs",
            "activity_logs",
        }
        self.assertTrue(expected_tables.issubset(table_names))

        # Verify foreign key enforcement blocks orphaned health records
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute_write(
                """
                INSERT INTO weight_logs (user_id, weight_kg, bmi, recorded_date)
                VALUES (?, ?, ?, ?)
                """,
                (99999, 70.0, 22.5, "2026-11-25"),
            )

    def test_password_hashing_and_verification(self):
        """Passwords are salted PBKDF2-HMAC-SHA256 hashes and verify properly."""
        hashed_a = hash_password("Secure123")
        hashed_b = hash_password("Secure123")

        self.assertIn(":", hashed_a)
        self.assertNotEqual(hashed_a, "Secure123")
        # Unique random salt means identical passwords produce different stored hashes
        self.assertNotEqual(hashed_a, hashed_b)
        self.assertTrue(verify_password("Secure123", hashed_a))
        self.assertFalse(verify_password("WrongPass1", hashed_a))

    def test_user_registration_and_duplicate_prevention(self):
        """Registering succeeds once and blocks duplicate usernames/emails (case-insensitive)."""
        res = self.auth.register_user(
            username="alice_fit",
            email="Alice@Example.com",
            password="Password1",
            confirm_password="Password1",
            full_name="Alice Johnson",
            age="23",
            gender="Female",
            height_cm="165",
            target_weight_kg="60",
        )
        self.assertTrue(res.success)
        self.assertIsNotNone(res.user)
        self.assertEqual(res.user["username"], "alice_fit")
        self.assertEqual(res.user["email"], "alice@example.com")
        self.assertNotIn("password_hash", res.user)

        # Duplicate username (different case)
        dup_user = self.auth.register_user(
            username="ALICE_FIT",
            email="other@example.com",
            password="Password1",
            confirm_password="Password1",
            full_name="Alice Two",
        )
        self.assertFalse(dup_user.success)
        self.assertIn("username", dup_user.message.lower())

        # Duplicate email (different case)
        dup_email = self.auth.register_user(
            username="bob_fit",
            email="ALICE@example.com",
            password="Password1",
            confirm_password="Password1",
            full_name="Bob Smith",
        )
        self.assertFalse(dup_email.success)
        self.assertIn("email", dup_email.message.lower())

    def test_successful_and_failed_login(self):
        """Users can log in via username or email, while wrong credentials fail."""
        self.auth.register_user(
            username="john_doe",
            email="john@university.edu",
            password="MyPassword9",
            confirm_password="MyPassword9",
            full_name="John Doe",
        )

        # Login with username
        ok_username = self.auth.login_user("john_doe", "MyPassword9")
        self.assertTrue(ok_username.success)
        self.assertEqual(ok_username.user["full_name"], "John Doe")
        self.assertNotIn("password_hash", ok_username.user)

        # Login with email (case-insensitive)
        ok_email = self.auth.login_user("JOHN@UNIVERSITY.EDU", "MyPassword9")
        self.assertTrue(ok_email.success)

        # Failed login: wrong password
        bad_pass = self.auth.login_user("john_doe", "WrongPass9")
        self.assertFalse(bad_pass.success)
        self.assertIsNone(bad_pass.user)

        # Failed login: unknown user
        no_user = self.auth.login_user("nobody", "MyPassword9")
        self.assertFalse(no_user.success)

    def test_data_persistence_across_sessions(self):
        """Data remains stored on disk when creating a fresh DatabaseManager and AuthService."""
        reg = self.auth.register_user(
            username="persist_user",
            email="persist@test.com",
            password="KeepData1",
            confirm_password="KeepData1",
            full_name="Persist User",
        )
        self.assertTrue(reg.success)
        user_id = reg.user["id"]

        self.db.execute_write(
            "INSERT INTO heart_rate_logs (user_id, bpm, recorded_date, notes) VALUES (?, ?, ?, ?)",
            (user_id, 68, "2026-11-25", "Resting"),
        )

        # Simulate restarting the application with new instances pointing to the same DB file
        new_db = DatabaseManager(self.db_path)
        new_auth = AuthService(new_db)

        login_res = new_auth.login_user("persist_user", "KeepData1")
        self.assertTrue(login_res.success)

        hr_records = new_db.fetch_user_records("heart_rate_logs", login_res.user["id"])
        self.assertEqual(len(hr_records), 1)
        self.assertEqual(hr_records[0]["bpm"], 68)

    def test_user_data_isolation(self):
        """User B cannot view or delete User A's health records."""
        user_a = self.auth.register_user(
            "user_a", "a@test.com", "Pass1234", "Pass1234", "User A"
        ).user
        user_b = self.auth.register_user(
            "user_b", "b@test.com", "Pass1234", "Pass1234", "User B"
        ).user

        record_id = self.db.execute_write(
            "INSERT INTO weight_logs (user_id, weight_kg, bmi, recorded_date) VALUES (?, ?, ?, ?)",
            (user_a["id"], 72.5, 23.1, "2026-11-25"),
        )

        # User B sees 0 records and cannot delete User A's record
        self.assertEqual(self.db.fetch_user_records("weight_logs", user_b["id"]), [])
        self.assertFalse(self.db.delete_user_record("weight_logs", record_id, user_b["id"]))

        # User A still has the record
        a_records = self.db.fetch_user_records("weight_logs", user_a["id"])
        self.assertEqual(len(a_records), 1)


if __name__ == "__main__":
    unittest.main()
