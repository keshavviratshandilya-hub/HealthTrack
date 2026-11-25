"""Authentication and user account service for HealthTrack.

Provides secure password hashing (PBKDF2-HMAC-SHA256), user registration,
login verification, and duplicate account prevention.
"""

import hashlib
import hmac
import os
import sqlite3
from typing import NamedTuple, Optional

from database.db_manager import DatabaseError, DatabaseManager
from services.validators import (
    validate_age,
    validate_email,
    validate_full_name,
    validate_gender,
    validate_height_cm,
    validate_password,
    validate_password_match,
    validate_username,
    validate_weight_kg,
)

PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16


class AuthResult(NamedTuple):
    """Standard response returned by authentication operations."""

    success: bool
    user: Optional[dict]
    message: str


def hash_password(password: str) -> str:
    """Hash a plain-text password using PBKDF2-HMAC-SHA256 with a random salt.

    Returns a string formatted as '<salt_hex>:<derived_key_hex>'.
    """
    salt = os.urandom(SALT_BYTES)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"{salt.hex()}:{derived_key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plain-text password against a stored PBKDF2-HMAC-SHA256 hash."""
    if not password or not stored_hash or ":" not in stored_hash:
        return False

    try:
        salt_hex, expected_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(expected_hex)
    except ValueError:
        return False

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    # hmac.compare_digest prevents timing attacks during comparison
    return hmac.compare_digest(derived_key, expected_key)


def _sanitize_user(user_row: Optional[dict]) -> Optional[dict]:
    """Remove sensitive fields (like password_hash) before returning user data."""
    if user_row is None:
        return None
    clean_user = dict(user_row)
    clean_user.pop("password_hash", None)
    return clean_user


class AuthService:
    """Handles user registration, login, and profile retrieval."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize AuthService with a DatabaseManager instance."""
        self.db = db_manager

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        confirm_password: str,
        full_name: str,
        age: Optional[str | int] = None,
        gender: Optional[str] = None,
        height_cm: Optional[str | float] = None,
        target_weight_kg: Optional[str | float] = None,
    ) -> AuthResult:
        """Validate inputs, check for duplicates, hash password, and create user."""
        # 1. Validate required registration fields
        username_res = validate_username(username)
        if not username_res.is_valid:
            return AuthResult(False, None, username_res.error)

        email_res = validate_email(email)
        if not email_res.is_valid:
            return AuthResult(False, None, email_res.error)

        name_res = validate_full_name(full_name)
        if not name_res.is_valid:
            return AuthResult(False, None, name_res.error)

        pass_res = validate_password(password)
        if not pass_res.is_valid:
            return AuthResult(False, None, pass_res.error)

        match_res = validate_password_match(password, confirm_password)
        if not match_res.is_valid:
            return AuthResult(False, None, match_res.error)

        # 2. Validate optional profile fields when supplied
        parsed_age = None
        if age is not None and str(age).strip() != "":
            age_res = validate_age(age)
            if not age_res.is_valid:
                return AuthResult(False, None, age_res.error)
            parsed_age = age_res.value

        parsed_gender = None
        if gender is not None and str(gender).strip() != "":
            gender_res = validate_gender(gender)
            if not gender_res.is_valid:
                return AuthResult(False, None, gender_res.error)
            parsed_gender = gender_res.value

        parsed_height = None
        if height_cm is not None and str(height_cm).strip() != "":
            height_res = validate_height_cm(height_cm)
            if not height_res.is_valid:
                return AuthResult(False, None, height_res.error)
            parsed_height = height_res.value

        parsed_target_weight = None
        if target_weight_kg is not None and str(target_weight_kg).strip() != "":
            tw_res = validate_weight_kg(target_weight_kg, "Target Weight (kg)")
            if not tw_res.is_valid:
                return AuthResult(False, None, tw_res.error)
            parsed_target_weight = tw_res.value

        # 3. Prevent duplicate usernames and email addresses (case-insensitive)
        try:
            existing_username = self.db.fetch_one(
                "SELECT id FROM users WHERE LOWER(username) = LOWER(?)",
                (username_res.value,),
            )
            if existing_username:
                return AuthResult(False, None, "That username is already taken.")

            existing_email = self.db.fetch_one(
                "SELECT id FROM users WHERE LOWER(email) = LOWER(?)",
                (email_res.value,),
            )
            if existing_email:
                return AuthResult(False, None, "An account with this email already exists.")

            # 4. Insert new user with securely hashed password
            password_hash = hash_password(pass_res.value)
            user_id = self.db.execute_write(
                """
                INSERT INTO users (
                    username, email, password_hash, full_name,
                    age, gender, height_cm, target_weight_kg
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username_res.value,
                    email_res.value,
                    password_hash,
                    name_res.value,
                    parsed_age,
                    parsed_gender,
                    parsed_height,
                    parsed_target_weight,
                ),
            )
            created_user = self.get_user_by_id(user_id)
            return AuthResult(True, created_user, "Account registered successfully.")

        except sqlite3.IntegrityError:
            return AuthResult(False, None, "Username or email already exists.")
        except DatabaseError as exc:
            return AuthResult(False, None, f"Registration failed: {exc}")

    def login_user(self, identifier: str, password: str) -> AuthResult:
        """Verify username/email and password, returning user details on success."""
        clean_identifier = (identifier or "").strip()
        if not clean_identifier:
            return AuthResult(False, None, "Please enter your username or email.")
        if not password:
            return AuthResult(False, None, "Please enter your password.")

        try:
            user_row = self.db.fetch_one(
                """
                SELECT * FROM users
                WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)
                """,
                (clean_identifier, clean_identifier),
            )
        except DatabaseError as exc:
            return AuthResult(False, None, f"Login failed: {exc}")

        if user_row is None or not verify_password(password, user_row["password_hash"]):
            return AuthResult(False, None, "Invalid username/email or password.")

        return AuthResult(True, _sanitize_user(user_row), "Login successful.")

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Fetch a sanitized user record by ID."""
        try:
            user_row = self.db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
            return _sanitize_user(user_row)
        except DatabaseError:
            return None

    def update_profile(
        self,
        user_id: int,
        full_name: str,
        age: Optional[str | int],
        gender: Optional[str],
        height_cm: Optional[str | float],
        target_weight_kg: Optional[str | float] = None,
    ) -> AuthResult:
        """Update profile fields for the authenticated user."""
        name_res = validate_full_name(full_name)
        if not name_res.is_valid:
            return AuthResult(False, None, name_res.error)

        parsed_age = None
        if age is not None and str(age).strip() != "":
            age_res = validate_age(age)
            if not age_res.is_valid:
                return AuthResult(False, None, age_res.error)
            parsed_age = age_res.value

        parsed_gender = None
        if gender is not None and str(gender).strip() != "":
            gender_res = validate_gender(gender)
            if not gender_res.is_valid:
                return AuthResult(False, None, gender_res.error)
            parsed_gender = gender_res.value

        parsed_height = None
        if height_cm is not None and str(height_cm).strip() != "":
            height_res = validate_height_cm(height_cm)
            if not height_res.is_valid:
                return AuthResult(False, None, height_res.error)
            parsed_height = height_res.value

        parsed_target_weight = None
        if target_weight_kg is not None and str(target_weight_kg).strip() != "":
            tw_res = validate_weight_kg(target_weight_kg, "Target Weight (kg)")
            if not tw_res.is_valid:
                return AuthResult(False, None, tw_res.error)
            parsed_target_weight = tw_res.value

        try:
            updated = self.db.execute_update(
                """
                UPDATE users
                SET full_name = ?,
                    age = ?,
                    gender = ?,
                    height_cm = ?,
                    target_weight_kg = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    name_res.value,
                    parsed_age,
                    parsed_gender,
                    parsed_height,
                    parsed_target_weight,
                    user_id,
                ),
            )
            if updated == 0:
                return AuthResult(False, None, "User account not found.")
            return AuthResult(True, self.get_user_by_id(user_id), "Profile updated successfully.")
        except DatabaseError as exc:
            return AuthResult(False, None, f"Could not update profile: {exc}")

    def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
        confirm_password: str,
    ) -> AuthResult:
        """Change a user's password after verifying their current password."""
        if not current_password:
            return AuthResult(False, None, "Current password is required.")

        pass_res = validate_password(new_password)
        if not pass_res.is_valid:
            return AuthResult(False, None, pass_res.error)

        match_res = validate_password_match(new_password, confirm_password)
        if not match_res.is_valid:
            return AuthResult(False, None, match_res.error)

        try:
            user_row = self.db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
            if user_row is None:
                return AuthResult(False, None, "User account not found.")

            if not verify_password(current_password, user_row["password_hash"]):
                return AuthResult(False, None, "Current password is incorrect.")

            new_hash = hash_password(pass_res.value)
            self.db.execute_update(
                "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
                (new_hash, user_id),
            )
            return AuthResult(True, _sanitize_user(user_row), "Password changed successfully.")
        except DatabaseError as exc:
            return AuthResult(False, None, f"Could not change password: {exc}")
