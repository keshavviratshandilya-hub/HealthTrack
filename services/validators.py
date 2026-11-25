"""Input validation and error-handling helpers for HealthTrack.

Every validator returns a ValidationResult(is_valid, value, error):
- is_valid: True if input passed all checks, False otherwise.
- value: Cleaned/parsed Python value (e.g., float, int, trimmed str) or None.
- error: Clear user-friendly error message (empty string when valid).
"""

from datetime import date, datetime
import re
from typing import Any, NamedTuple


class ValidationResult(NamedTuple):
    """Standard return container for all validation functions."""

    is_valid: bool
    value: Any
    error: str


ALLOWED_GENDERS = ("Male", "Female", "Other", "Prefer not to say")

# Pre-compiled regular expressions for text formats
_USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,29}$")
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z\s.'-]{1,59}$")


def _ok(value: Any) -> ValidationResult:
    """Create a successful ValidationResult."""
    return ValidationResult(True, value, "")


def _fail(message: str) -> ValidationResult:
    """Create a failed ValidationResult."""
    return ValidationResult(False, None, message)


def _validate_number_range(
    raw_value: Any,
    field_name: str,
    min_val: float,
    max_val: float,
    cast_type=float,
) -> ValidationResult:
    """Parse a numeric value and ensure it falls within [min_val, max_val].

    Shared helper to keep all numeric health metric validations consistent.
    """
    if raw_value is None:
        return _fail(f"{field_name} is required.")

    text = str(raw_value).strip()
    if not text:
        return _fail(f"{field_name} is required.")

    try:
        if cast_type is int:
            # Reject decimal strings like "70.5" when an integer is expected
            parsed_float = float(text)
            if not parsed_float.is_integer():
                return _fail(f"{field_name} must be a whole number.")
            number = int(parsed_float)
        else:
            number = float(text)
    except ValueError:
        return _fail(f"{field_name} must be a valid number.")

    if number < min_val or number > max_val:
        return _fail(f"{field_name} must be between {min_val} and {max_val}.")

    return _ok(number)


# ---------------------------------------------------------------------------
# Account & Profile Validators
# ---------------------------------------------------------------------------

def validate_username(raw_username: str) -> ValidationResult:
    """Validate username: 3-30 chars, starts with a letter, letters/digits/_."""
    username = (raw_username or "").strip()
    if not username:
        return _fail("Username is required.")
    if not _USERNAME_RE.match(username):
        return _fail(
            "Username must be 3-30 characters, start with a letter, and use only letters, numbers, or underscores."
        )
    return _ok(username)


def validate_email(raw_email: str) -> ValidationResult:
    """Validate email address format."""
    email = (raw_email or "").strip().lower()
    if not email:
        return _fail("Email address is required.")
    if not _EMAIL_RE.match(email):
        return _fail("Please enter a valid email address (e.g. name@example.com).")
    return _ok(email)


def validate_password(raw_password: str) -> ValidationResult:
    """Validate password strength: min 6 chars, at least 1 letter and 1 digit."""
    password = raw_password or ""
    if not password:
        return _fail("Password is required.")
    if len(password) < 6:
        return _fail("Password must be at least 6 characters long.")
    if not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
        return _fail("Password must contain at least one letter and one number.")
    return _ok(password)


def validate_password_match(password: str, confirm_password: str) -> ValidationResult:
    """Ensure password and confirmation password match."""
    if password != confirm_password:
        return _fail("Passwords do not match.")
    return _ok(password)


def validate_full_name(raw_name: str) -> ValidationResult:
    """Validate user's display full name."""
    name = " ".join((raw_name or "").strip().split())
    if not name:
        return _fail("Full name is required.")
    if not _NAME_RE.match(name):
        return _fail("Full name must be 2-60 characters and contain only letters and spaces.")
    return _ok(name)


def validate_age(raw_age: Any) -> ValidationResult:
    """Validate age in years (5 to 120)."""
    return _validate_number_range(raw_age, "Age", 5, 120, cast_type=int)


def validate_gender(raw_gender: str) -> ValidationResult:
    """Validate gender selection against allowed choices."""
    gender = (raw_gender or "").strip()
    if gender not in ALLOWED_GENDERS:
        return _fail(f"Gender must be one of: {', '.join(ALLOWED_GENDERS)}.")
    return _ok(gender)


def validate_height_cm(raw_height: Any) -> ValidationResult:
    """Validate height in centimeters (50.0 to 260.0 cm)."""
    result = _validate_number_range(raw_height, "Height (cm)", 50.0, 260.0, cast_type=float)
    if result.is_valid:
        return _ok(round(result.value, 1))
    return result


# ---------------------------------------------------------------------------
# Health Metric Validators
# ---------------------------------------------------------------------------

def validate_weight_kg(raw_weight: Any, field_label: str = "Weight (kg)") -> ValidationResult:
    """Validate body weight in kilograms (15.0 to 350.0 kg)."""
    result = _validate_number_range(raw_weight, field_label, 15.0, 350.0, cast_type=float)
    if result.is_valid:
        return _ok(round(result.value, 1))
    return result


def validate_blood_pressure(raw_systolic: Any, raw_diastolic: Any) -> ValidationResult:
    """Validate systolic and diastolic blood pressure readings (mmHg)."""
    sys_res = _validate_number_range(raw_systolic, "Systolic BP", 60, 260, cast_type=int)
    if not sys_res.is_valid:
        return sys_res

    dia_res = _validate_number_range(raw_diastolic, "Diastolic BP", 30, 160, cast_type=int)
    if not dia_res.is_valid:
        return dia_res

    if sys_res.value <= dia_res.value:
        return _fail("Systolic blood pressure must be higher than diastolic pressure.")

    return _ok((sys_res.value, dia_res.value))


def validate_heart_rate(raw_bpm: Any) -> ValidationResult:
    """Validate heart rate in beats per minute (30 to 230 bpm)."""
    return _validate_number_range(raw_bpm, "Heart Rate (bpm)", 30, 230, cast_type=int)


def validate_activity(
    raw_steps: Any,
    raw_active_minutes: Any,
    raw_sleep_hours: Any,
    raw_calories: Any,
) -> ValidationResult:
    """Validate daily activity metrics (steps, active minutes, sleep, calories)."""
    steps_res = _validate_number_range(raw_steps, "Steps", 0, 100000, cast_type=int)
    if not steps_res.is_valid:
        return steps_res

    mins_res = _validate_number_range(raw_active_minutes, "Active Minutes", 0, 1440, cast_type=int)
    if not mins_res.is_valid:
        return mins_res

    sleep_res = _validate_number_range(raw_sleep_hours, "Sleep Hours", 0.0, 24.0, cast_type=float)
    if not sleep_res.is_valid:
        return sleep_res

    cal_res = _validate_number_range(raw_calories, "Calories Burned", 0, 15000, cast_type=int)
    if not cal_res.is_valid:
        return cal_res

    if (
        steps_res.value == 0
        and mins_res.value == 0
        and sleep_res.value == 0.0
        and cal_res.value == 0
    ):
        return _fail("Please enter at least one activity value greater than zero.")

    return _ok(
        {
            "steps": steps_res.value,
            "active_minutes": mins_res.value,
            "sleep_hours": round(sleep_res.value, 1),
            "calories_burned": cal_res.value,
        }
    )


def validate_date(raw_date: str, allow_future: bool = False) -> ValidationResult:
    """Validate a date string in YYYY-MM-DD format."""
    text = (raw_date or "").strip()
    if not text:
        return _fail("Date is required (YYYY-MM-DD).")

    try:
        parsed_date = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return _fail("Date must follow the YYYY-MM-DD format (e.g. 2026-11-25).")

    if not allow_future and parsed_date > date.today():
        return _fail("Date cannot be in the future.")

    return _ok(parsed_date.isoformat())


def validate_notes(raw_notes: str, max_length: int = 250) -> ValidationResult:
    """Validate optional notes text."""
    notes = (raw_notes or "").strip()
    if len(notes) > max_length:
        return _fail(f"Notes must be {max_length} characters or fewer.")
    return _ok(notes)
