"""Core health tracking, BMI calculation, and Pandas analytics service.

All calculations use deterministic formulas and Pandas aggregations
(no Machine Learning or AI prediction). Every query is strictly scoped
to the authenticated user_id.
"""

from datetime import date
from typing import Any, NamedTuple, Optional

import pandas as pd

from database.db_manager import DatabaseError, DatabaseManager
from services.validators import (
    validate_activity,
    validate_blood_pressure,
    validate_date,
    validate_heart_rate,
    validate_notes,
    validate_weight_kg,
)

# Maps friendly metric keys to SQLite table names
METRIC_TABLES = {
    "weight": "weight_logs",
    "blood_pressure": "blood_pressure_logs",
    "heart_rate": "heart_rate_logs",
    "activity": "activity_logs",
}


class ServiceResult(NamedTuple):
    """Standard return object for health service operations."""

    success: bool
    data: Any
    message: str


# ---------------------------------------------------------------------------
# Pure Health Formulas (BMI & Blood Pressure Classification)
# ---------------------------------------------------------------------------

def calculate_bmi(weight_kg: Optional[float], height_cm: Optional[float]) -> Optional[float]:
    """Calculate Body Mass Index using weight (kg) / (height (m))^2.

    Returns None if weight or height is missing or non-positive.
    """
    if weight_kg is None or height_cm is None:
        return None
    if weight_kg <= 0 or height_cm <= 0:
        return None

    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m ** 2)
    return round(bmi, 1)


def classify_bmi(bmi: Optional[float]) -> str:
    """Classify a BMI value into standard WHO adult categories."""
    if bmi is None or bmi <= 0:
        return "Unknown"
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25.0:
        return "Normal"
    if bmi < 30.0:
        return "Overweight"
    return "Obese"


def classify_blood_pressure(systolic: int, diastolic: int) -> str:
    """Return a standard descriptive blood pressure range label."""
    if systolic < 90 or diastolic < 60:
        return "Low"
    if systolic >= 140 or diastolic >= 90:
        return "High (Stage 2)"
    if systolic >= 130 or diastolic >= 80:
        return "High (Stage 1)"
    if 120 <= systolic <= 129 and diastolic < 80:
        return "Elevated"
    return "Normal"


class HealthService:
    """Manages health records, BMI updates, date filtering, and Pandas summaries."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize HealthService with a DatabaseManager instance."""
        self.db = db_manager

    def _verify_user_exists(self, user_id: int) -> Optional[dict]:
        """Return the user row if user_id exists, else None."""
        if not isinstance(user_id, int) or user_id <= 0:
            return None
        return self.db.fetch_one(
            "SELECT id, username, full_name, height_cm, target_weight_kg FROM users WHERE id = ?",
            (user_id,),
        )

    def _validate_date_and_notes(
        self, recorded_date: Optional[str], notes: str
    ) -> tuple[bool, Optional[str], Optional[str], str]:
        """Shared helper to validate log date (defaults to today if None) and notes."""
        raw_date = date.today().isoformat() if recorded_date is None else recorded_date
        date_res = validate_date(raw_date)
        if not date_res.is_valid:
            return False, None, None, date_res.error

        notes_res = validate_notes(notes)
        if not notes_res.is_valid:
            return False, None, None, notes_res.error

        return True, date_res.value, notes_res.value, ""

    def _validate_date_filters(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> tuple[bool, Optional[str], Optional[str], str]:
        """Validate optional start_date and end_date filter strings."""
        clean_start = None
        clean_end = None

        if start_date is not None and str(start_date).strip() != "":
            res = validate_date(start_date, allow_future=True)
            if not res.is_valid:
                return False, None, None, f"Start date error: {res.error}"
            clean_start = res.value

        if end_date is not None and str(end_date).strip() != "":
            res = validate_date(end_date, allow_future=True)
            if not res.is_valid:
                return False, None, None, f"End date error: {res.error}"
            clean_end = res.value

        if clean_start and clean_end and clean_start > clean_end:
            return False, None, None, "Start date cannot be later than end date."

        return True, clean_start, clean_end, ""

    # -----------------------------------------------------------------------
    # Create (Add) Health Records
    # -----------------------------------------------------------------------

    def add_weight_log(
        self,
        user_id: int,
        weight_kg: Any,
        recorded_date: Optional[str] = None,
        notes: str = "",
    ) -> ServiceResult:
        """Validate and save a weight entry, automatically computing BMI if height is set."""
        user = self._verify_user_exists(user_id)
        if not user:
            return ServiceResult(False, None, "User account not found.")

        weight_res = validate_weight_kg(weight_kg)
        if not weight_res.is_valid:
            return ServiceResult(False, None, weight_res.error)

        ok, clean_date, clean_notes, err = self._validate_date_and_notes(recorded_date, notes)
        if not ok:
            return ServiceResult(False, None, err)

        bmi_value = calculate_bmi(weight_res.value, user.get("height_cm"))

        try:
            record_id = self.db.execute_write(
                """
                INSERT INTO weight_logs (user_id, weight_kg, bmi, recorded_date, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, weight_res.value, bmi_value, clean_date, clean_notes),
            )
            record = self.db.fetch_one(
                "SELECT * FROM weight_logs WHERE id = ? AND user_id = ?",
                (record_id, user_id),
            )
            return ServiceResult(True, record, "Weight record saved successfully.")
        except DatabaseError as exc:
            return ServiceResult(False, None, f"Could not save weight record: {exc}")

    def add_blood_pressure_log(
        self,
        user_id: int,
        systolic: Any,
        diastolic: Any,
        recorded_date: Optional[str] = None,
        notes: str = "",
    ) -> ServiceResult:
        """Validate and save a blood pressure reading (systolic/diastolic mmHg)."""
        if not self._verify_user_exists(user_id):
            return ServiceResult(False, None, "User account not found.")

        bp_res = validate_blood_pressure(systolic, diastolic)
        if not bp_res.is_valid:
            return ServiceResult(False, None, bp_res.error)

        ok, clean_date, clean_notes, err = self._validate_date_and_notes(recorded_date, notes)
        if not ok:
            return ServiceResult(False, None, err)

        sys_val, dia_val = bp_res.value
        try:
            record_id = self.db.execute_write(
                """
                INSERT INTO blood_pressure_logs (user_id, systolic, diastolic, recorded_date, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, sys_val, dia_val, clean_date, clean_notes),
            )
            record = self.db.fetch_one(
                "SELECT * FROM blood_pressure_logs WHERE id = ? AND user_id = ?",
                (record_id, user_id),
            )
            return ServiceResult(True, record, "Blood pressure record saved successfully.")
        except DatabaseError as exc:
            return ServiceResult(False, None, f"Could not save blood pressure record: {exc}")

    def add_heart_rate_log(
        self,
        user_id: int,
        bpm: Any,
        recorded_date: Optional[str] = None,
        notes: str = "",
    ) -> ServiceResult:
        """Validate and save a heart rate reading (bpm)."""
        if not self._verify_user_exists(user_id):
            return ServiceResult(False, None, "User account not found.")

        hr_res = validate_heart_rate(bpm)
        if not hr_res.is_valid:
            return ServiceResult(False, None, hr_res.error)

        ok, clean_date, clean_notes, err = self._validate_date_and_notes(recorded_date, notes)
        if not ok:
            return ServiceResult(False, None, err)

        try:
            record_id = self.db.execute_write(
                """
                INSERT INTO heart_rate_logs (user_id, bpm, recorded_date, notes)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, hr_res.value, clean_date, clean_notes),
            )
            record = self.db.fetch_one(
                "SELECT * FROM heart_rate_logs WHERE id = ? AND user_id = ?",
                (record_id, user_id),
            )
            return ServiceResult(True, record, "Heart rate record saved successfully.")
        except DatabaseError as exc:
            return ServiceResult(False, None, f"Could not save heart rate record: {exc}")

    def add_activity_log(
        self,
        user_id: int,
        steps: Any,
        active_minutes: Any,
        sleep_hours: Any,
        calories_burned: Any,
        recorded_date: Optional[str] = None,
        notes: str = "",
    ) -> ServiceResult:
        """Validate and save a daily activity log."""
        if not self._verify_user_exists(user_id):
            return ServiceResult(False, None, "User account not found.")

        act_res = validate_activity(steps, active_minutes, sleep_hours, calories_burned)
        if not act_res.is_valid:
            return ServiceResult(False, None, act_res.error)

        ok, clean_date, clean_notes, err = self._validate_date_and_notes(recorded_date, notes)
        if not ok:
            return ServiceResult(False, None, err)

        vals = act_res.value
        try:
            record_id = self.db.execute_write(
                """
                INSERT INTO activity_logs (
                    user_id, steps, active_minutes, sleep_hours, calories_burned, recorded_date, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    vals["steps"],
                    vals["active_minutes"],
                    vals["sleep_hours"],
                    vals["calories_burned"],
                    clean_date,
                    clean_notes,
                ),
            )
            record = self.db.fetch_one(
                "SELECT * FROM activity_logs WHERE id = ? AND user_id = ?",
                (record_id, user_id),
            )
            return ServiceResult(True, record, "Daily activity record saved successfully.")
        except DatabaseError as exc:
            return ServiceResult(False, None, f"Could not save activity record: {exc}")

    # -----------------------------------------------------------------------
    # Read (View & Filter) and Delete Operations
    # -----------------------------------------------------------------------

    def get_records(
        self,
        user_id: int,
        metric_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> ServiceResult:
        """Fetch records of a given metric_type strictly for user_id, with optional date filter."""
        if metric_type not in METRIC_TABLES:
            return ServiceResult(False, [], f"Unsupported metric type: {metric_type}")

        ok, clean_start, clean_end, err = self._validate_date_filters(start_date, end_date)
        if not ok:
            return ServiceResult(False, [], err)

        table_name = METRIC_TABLES[metric_type]
        try:
            records = self.db.fetch_user_records(
                table_name,
                user_id=user_id,
                start_date=clean_start,
                end_date=clean_end,
                limit=limit,
            )
            return ServiceResult(True, records, f"Loaded {len(records)} record(s).")
        except DatabaseError as exc:
            return ServiceResult(False, [], f"Failed to load records: {exc}")

    def get_records_df(
        self,
        user_id: int,
        metric_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ServiceResult:
        """Return user's filtered records as a chronological Pandas DataFrame."""
        res = self.get_records(user_id, metric_type, start_date=start_date, end_date=end_date)
        if not res.success:
            return ServiceResult(False, pd.DataFrame(), res.message)

        if not res.data:
            return ServiceResult(True, pd.DataFrame(), "No records found.")

        df = pd.DataFrame(res.data)
        df["recorded_date"] = pd.to_datetime(df["recorded_date"])
        df = df.sort_values(by=["recorded_date", "id"], ascending=[True, True]).reset_index(drop=True)
        return ServiceResult(True, df, f"Loaded {len(df)} record(s) into DataFrame.")

    def delete_record(self, user_id: int, metric_type: str, record_id: int) -> ServiceResult:
        """Delete a health record only if it belongs to user_id."""
        if metric_type not in METRIC_TABLES:
            return ServiceResult(False, None, f"Unsupported metric type: {metric_type}")
        if not isinstance(record_id, int) or record_id <= 0:
            return ServiceResult(False, None, "Invalid record ID.")

        table_name = METRIC_TABLES[metric_type]
        try:
            deleted = self.db.delete_user_record(table_name, record_id, user_id)
            if not deleted:
                return ServiceResult(False, None, "Record not found or access denied.")
            return ServiceResult(True, None, "Record deleted successfully.")
        except DatabaseError as exc:
            return ServiceResult(False, None, f"Could not delete record: {exc}")

    # -----------------------------------------------------------------------
    # Pandas Summaries, Statistics & Unified History
    # -----------------------------------------------------------------------

    def get_metric_summary(
        self,
        user_id: int,
        metric_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ServiceResult:
        """Compute descriptive statistics for a metric using Pandas."""
        df_res = self.get_records_df(user_id, metric_type, start_date=start_date, end_date=end_date)
        if not df_res.success:
            return ServiceResult(False, {}, df_res.message)

        df = df_res.data
        if df.empty:
            return ServiceResult(True, {"count": 0}, "No records available for summary.")

        summary: dict[str, Any] = {"count": int(len(df))}

        if metric_type == "weight":
            latest_row = df.iloc[-1]
            first_row = df.iloc[0]
            user = self._verify_user_exists(user_id)
            height_cm = user.get("height_cm") if user else None
            latest_weight = float(latest_row["weight_kg"])
            # Use stored BMI or recompute from current profile height if needed
            latest_bmi = (
                float(latest_row["bmi"])
                if pd.notna(latest_row["bmi"])
                else calculate_bmi(latest_weight, height_cm)
            )
            summary.update(
                {
                    "latest_weight": round(latest_weight, 1),
                    "min_weight": round(float(df["weight_kg"].min()), 1),
                    "max_weight": round(float(df["weight_kg"].max()), 1),
                    "avg_weight": round(float(df["weight_kg"].mean()), 1),
                    "weight_change": round(latest_weight - float(first_row["weight_kg"]), 1),
                    "latest_bmi": latest_bmi,
                    "bmi_category": classify_bmi(latest_bmi),
                    "latest_date": latest_row["recorded_date"].strftime("%Y-%m-%d"),
                }
            )
        elif metric_type == "blood_pressure":
            latest_row = df.iloc[-1]
            latest_sys = int(latest_row["systolic"])
            latest_dia = int(latest_row["diastolic"])
            summary.update(
                {
                    "latest_systolic": latest_sys,
                    "latest_diastolic": latest_dia,
                    "avg_systolic": round(float(df["systolic"].mean()), 1),
                    "avg_diastolic": round(float(df["diastolic"].mean()), 1),
                    "min_systolic": int(df["systolic"].min()),
                    "max_systolic": int(df["systolic"].max()),
                    "latest_category": classify_blood_pressure(latest_sys, latest_dia),
                    "latest_date": latest_row["recorded_date"].strftime("%Y-%m-%d"),
                }
            )
        elif metric_type == "heart_rate":
            latest_row = df.iloc[-1]
            summary.update(
                {
                    "latest_bpm": int(latest_row["bpm"]),
                    "avg_bpm": round(float(df["bpm"].mean()), 1),
                    "min_bpm": int(df["bpm"].min()),
                    "max_bpm": int(df["bpm"].max()),
                    "latest_date": latest_row["recorded_date"].strftime("%Y-%m-%d"),
                }
            )
        elif metric_type == "activity":
            latest_row = df.iloc[-1]
            summary.update(
                {
                    "latest_steps": int(latest_row["steps"]),
                    "total_steps": int(df["steps"].sum()),
                    "avg_steps": round(float(df["steps"].mean()), 0),
                    "total_active_minutes": int(df["active_minutes"].sum()),
                    "avg_sleep_hours": round(float(df["sleep_hours"].mean()), 1),
                    "total_calories": int(df["calories_burned"].sum()),
                    "latest_date": latest_row["recorded_date"].strftime("%Y-%m-%d"),
                }
            )

        return ServiceResult(True, summary, "Summary calculated successfully.")

    def get_dashboard_overview(self, user_id: int) -> ServiceResult:
        """Build a combined summary dictionary for the Dashboard view."""
        user = self._verify_user_exists(user_id)
        if not user:
            return ServiceResult(False, {}, "User account not found.")

        overview: dict[str, Any] = {
            "user": user,
            "weight": self.get_metric_summary(user_id, "weight").data,
            "blood_pressure": self.get_metric_summary(user_id, "blood_pressure").data,
            "heart_rate": self.get_metric_summary(user_id, "heart_rate").data,
            "activity": self.get_metric_summary(user_id, "activity").data,
        }
        return ServiceResult(True, overview, "Dashboard overview ready.")

    def get_unified_history_df(
        self,
        user_id: int,
        metric_filter: str = "all",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ServiceResult:
        """Combine selected health records into one normalized Pandas DataFrame."""
        if metric_filter != "all" and metric_filter not in METRIC_TABLES:
            return ServiceResult(False, pd.DataFrame(), f"Invalid metric filter: {metric_filter}")

        ok, clean_start, clean_end, err = self._validate_date_filters(start_date, end_date)
        if not ok:
            return ServiceResult(False, pd.DataFrame(), err)

        metrics_to_load = (
            list(METRIC_TABLES.keys()) if metric_filter == "all" else [metric_filter]
        )

        rows: list[dict[str, Any]] = []
        for m_type in metrics_to_load:
            res = self.get_records(
                user_id, m_type, start_date=clean_start, end_date=clean_end
            )
            if not res.success:
                return ServiceResult(False, pd.DataFrame(), res.message)

            for rec in res.data:
                rows.append(self._format_history_row(m_type, rec))

        columns = ["id", "metric_type", "metric_label", "recorded_date", "summary", "notes"]
        if not rows:
            return ServiceResult(True, pd.DataFrame(columns=columns), "No records found.")

        df = pd.DataFrame(rows, columns=columns)
        df = df.sort_values(by=["recorded_date", "id"], ascending=[False, False]).reset_index(
            drop=True
        )
        return ServiceResult(True, df, f"Loaded {len(df)} history record(s).")

    @staticmethod
    def _format_history_row(metric_type: str, rec: dict) -> dict[str, Any]:
        """Format a single raw database row into a readable unified history row."""
        if metric_type == "weight":
            bmi_part = f" | BMI: {rec['bmi']} ({classify_bmi(rec['bmi'])})" if rec.get("bmi") else ""
            summary = f"{rec['weight_kg']} kg{bmi_part}"
            label = "Weight & BMI"
        elif metric_type == "blood_pressure":
            bp_cat = classify_blood_pressure(rec["systolic"], rec["diastolic"])
            summary = f"{rec['systolic']}/{rec['diastolic']} mmHg ({bp_cat})"
            label = "Blood Pressure"
        elif metric_type == "heart_rate":
            summary = f"{rec['bpm']} bpm"
            label = "Heart Rate"
        else:
            summary = (
                f"{rec['steps']} steps | {rec['active_minutes']} min | "
                f"{rec['sleep_hours']} hrs sleep | {rec['calories_burned']} kcal"
            )
            label = "Daily Activity"

        return {
            "id": rec["id"],
            "metric_type": metric_type,
            "metric_label": label,
            "recorded_date": rec["recorded_date"],
            "summary": summary,
            "notes": rec.get("notes") or "",
        }
