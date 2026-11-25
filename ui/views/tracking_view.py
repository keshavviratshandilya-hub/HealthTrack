"""Health metric tracking views (Weight & BMI, Blood Pressure, Heart Rate, Activity).

Uses a single parameterized TrackingView driven by METRIC_CONFIGS so all four
tracking screens share consistent validation, persistence, summary stats, and
record deletion without duplicated UI code.
"""

from datetime import date
from typing import Any

import customtkinter as ctk

from config.theme import COLORS, FONTS, LAYOUT
from services.health_service import (
    HealthService,
    calculate_bmi,
    classify_blood_pressure,
    classify_bmi,
)
from ui.components.cards import RecordsTable, SectionCard, StatusBanner

# Declarative configuration for the 4 tracking pages
METRIC_CONFIGS: dict[str, dict[str, Any]] = {
    "weight": {
        "form_title": "Log Weight & BMI",
        "form_subtitle": "BMI is calculated automatically from your profile height.",
        "list_title": "Recent Weight Records",
        "fields": [
            ("weight_kg", "Weight (kg) *", "e.g. 68.5"),
        ],
        "columns": [
            ("Date", 2),
            ("Weight (kg)", 2),
            ("BMI", 2),
            ("Category", 2),
            ("Notes", 3),
        ],
    },
    "blood_pressure": {
        "form_title": "Log Blood Pressure",
        "form_subtitle": "Enter systolic and diastolic pressure in mmHg.",
        "list_title": "Recent Blood Pressure Records",
        "fields": [
            ("systolic", "Systolic (mmHg) *", "e.g. 120"),
            ("diastolic", "Diastolic (mmHg) *", "e.g. 80"),
        ],
        "columns": [
            ("Date", 2),
            ("Reading", 2),
            ("Category", 2),
            ("Notes", 3),
        ],
    },
    "heart_rate": {
        "form_title": "Log Heart Rate",
        "form_subtitle": "Enter beats per minute (30–230 bpm).",
        "list_title": "Recent Heart Rate Records",
        "fields": [
            ("bpm", "Heart Rate (bpm) *", "e.g. 72"),
        ],
        "columns": [
            ("Date", 2),
            ("BPM", 2),
            ("Notes", 4),
        ],
    },
    "activity": {
        "form_title": "Log Daily Activity",
        "form_subtitle": "Track daily steps, active minutes, sleep duration, and calories.",
        "list_title": "Recent Activity Records",
        "fields": [
            ("steps", "Steps *", "e.g. 8500"),
            ("active_minutes", "Active Minutes *", "e.g. 45"),
            ("sleep_hours", "Sleep Duration (hours) *", "e.g. 7.5"),
            ("calories_burned", "Calories Burned *", "e.g. 400"),
        ],
        "columns": [
            ("Date", 2),
            ("Steps", 2),
            ("Active", 2),
            ("Sleep", 2),
            ("Calories", 2),
        ],
    },
}


class TrackingView(ctk.CTkFrame):
    """Unified, data-driven screen for adding and managing a health metric."""

    def __init__(self, master, user: dict, health_service: HealthService, metric_type: str):
        super().__init__(master, fg_color="transparent")
        if metric_type not in METRIC_CONFIGS:
            raise ValueError(f"Unsupported metric_type: {metric_type}")

        self.user = user
        self.health_service = health_service
        self.metric_type = metric_type
        self.config_data = METRIC_CONFIGS[metric_type]
        self.entries: dict[str, ctk.CTkEntry] = {}

        self._build_ui()
        self.refresh_records()

    def _build_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=2, uniform="track")
        self.grid_columnconfigure(1, weight=3, uniform="track")

        # -------------------------------------------------------------------
        # Left Card: Entry Form
        # -------------------------------------------------------------------
        form_card = SectionCard(
            self,
            title=self.config_data["form_title"],
            subtitle=self.config_data["form_subtitle"],
        )
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.status_banner = StatusBanner(form_card.body, wraplength=340)

        # Helpful height reminder on the Weight & BMI page
        if self.metric_type == "weight":
            height_cm = self.user.get("height_cm")
            tip_text = (
                f"Profile Height: {height_cm} cm (BMI auto-calculates on save)"
                if height_cm
                else "Tip: Set your height in My Profile to enable automatic BMI calculation."
            )
            tip_fg = COLORS["teal_soft"] if height_cm else COLORS["warning_bg"]
            tip_tc = COLORS["teal_primary"] if height_cm else COLORS["warning"]
            self.bmi_tip_label = ctk.CTkLabel(
                form_card.body,
                text=tip_text,
                font=FONTS["small_bold"],
                fg_color=tip_fg,
                text_color=tip_tc,
                corner_radius=8,
                padx=10,
                pady=6,
                wraplength=340,
                justify="left",
            )
            self.bmi_tip_label.pack(fill="x", pady=(0, 10))

        # Metric-specific inputs
        for field_key, label_text, placeholder in self.config_data["fields"]:
            entry = self._add_input(form_card.body, label_text, placeholder)
            self.entries[field_key] = entry

        # Live BMI preview on weight entry
        if self.metric_type == "weight":
            self.live_bmi_label = ctk.CTkLabel(
                form_card.body,
                text="Estimated BMI: --",
                font=FONTS["small_bold"],
                text_color=COLORS["navy_primary"],
            )
            self.live_bmi_label.pack(anchor="w", pady=(0, 8))
            self.entries["weight_kg"].bind("<KeyRelease>", self._update_live_bmi_preview)

        # Shared Date and Notes fields
        self.date_entry = self._add_input(
            form_card.body,
            "Date (YYYY-MM-DD) *",
            date.today().isoformat(),
            initial_value=date.today().isoformat(),
        )
        self.notes_entry = self._add_input(
            form_card.body, "Notes (optional)", "e.g. Morning check, after walk"
        )

        btn_row = ctk.CTkFrame(form_card.body, fg_color="transparent")
        btn_row.pack(fill="x", pady=(8, 0))
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.save_button = ctk.CTkButton(
            btn_row,
            text="Save Record",
            command=self.submit_record,
            height=40,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["teal_primary"],
            hover_color=COLORS["teal_hover"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["body_bold"],
        )
        self.save_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.clear_button = ctk.CTkButton(
            btn_row,
            text="Clear",
            command=self.clear_form,
            height=40,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            font=FONTS["body_bold"],
        )
        self.clear_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # -------------------------------------------------------------------
        # Right Card: Summary Bar + Recent Records Table
        # -------------------------------------------------------------------
        list_card = SectionCard(
            self,
            title=self.config_data["list_title"],
            subtitle="Only your personal records are shown here.",
        )
        list_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self.summary_label = ctk.CTkLabel(
            list_card.body,
            text="",
            font=FONTS["small_bold"],
            text_color=COLORS["navy_primary"],
            fg_color=COLORS["bg_input"],
            corner_radius=8,
            padx=12,
            pady=8,
            anchor="w",
        )
        self.summary_label.pack(fill="x", pady=(0, 12))

        self.table = RecordsTable(
            list_card.body,
            columns=self.config_data["columns"],
            on_delete=self.delete_record,
        )
        self.table.pack(fill="both", expand=True)

    def _add_input(
        self, parent, label: str, placeholder: str, initial_value: str = ""
    ) -> ctk.CTkEntry:
        ctk.CTkLabel(
            parent,
            text=label,
            font=FONTS["small_bold"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 3))

        entry = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            height=36,
            corner_radius=LAYOUT["input_radius"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
        )
        if initial_value:
            entry.insert(0, initial_value)
        entry.pack(fill="x", pady=(0, 9))
        return entry

    def _update_live_bmi_preview(self, _event=None) -> None:
        """Show an instant BMI preview while the user types a weight."""
        height_cm = self.user.get("height_cm")
        if not height_cm:
            self.live_bmi_label.configure(text="Estimated BMI: Set height in My Profile")
            return
        try:
            weight_val = float(self.entries["weight_kg"].get().strip())
            bmi = calculate_bmi(weight_val, height_cm)
            if bmi:
                self.live_bmi_label.configure(
                    text=f"Estimated BMI: {bmi} ({classify_bmi(bmi)})"
                )
                return
        except ValueError:
            pass
        self.live_bmi_label.configure(text="Estimated BMI: --")

    def submit_record(self) -> None:
        """Validate inputs and save the record through HealthService."""
        user_id = self.user["id"]
        rec_date = self.date_entry.get().strip()
        notes = self.notes_entry.get().strip()

        if self.metric_type == "weight":
            res = self.health_service.add_weight_log(
                user_id,
                self.entries["weight_kg"].get(),
                recorded_date=rec_date,
                notes=notes,
            )
        elif self.metric_type == "blood_pressure":
            res = self.health_service.add_blood_pressure_log(
                user_id,
                self.entries["systolic"].get(),
                self.entries["diastolic"].get(),
                recorded_date=rec_date,
                notes=notes,
            )
        elif self.metric_type == "heart_rate":
            res = self.health_service.add_heart_rate_log(
                user_id,
                self.entries["bpm"].get(),
                recorded_date=rec_date,
                notes=notes,
            )
        else:
            res = self.health_service.add_activity_log(
                user_id,
                self.entries["steps"].get(),
                self.entries["active_minutes"].get(),
                self.entries["sleep_hours"].get(),
                self.entries["calories_burned"].get(),
                recorded_date=rec_date,
                notes=notes,
            )

        if not res.success:
            self.status_banner.show(res.message, is_success=False)
            return

        self.clear_form(keep_status=True)
        self.status_banner.show(res.message, is_success=True)
        self.refresh_records()

    def clear_form(self, keep_status: bool = False) -> None:
        """Reset all input fields back to defaults."""
        for entry in self.entries.values():
            entry.delete(0, "end")
        self.notes_entry.delete(0, "end")
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, date.today().isoformat())
        if self.metric_type == "weight":
            self._update_live_bmi_preview()
        if not keep_status:
            self.status_banner.clear()

    def delete_record(self, record_id: int) -> None:
        """Delete a record belonging to the current user and refresh the table."""
        res = self.health_service.delete_record(self.user["id"], self.metric_type, record_id)
        if not res.success:
            self.status_banner.show(res.message, is_success=False)
            return
        self.status_banner.show(res.message, is_success=True)
        self.refresh_records()

    def refresh_records(self) -> None:
        """Reload the summary banner and recent records table from SQLite."""
        user_id = self.user["id"]
        sum_res = self.health_service.get_metric_summary(user_id, self.metric_type)
        summary = sum_res.data if sum_res.success else {"count": 0}
        self.summary_label.configure(text=self._format_summary_banner(summary))

        rec_res = self.health_service.get_records(user_id, self.metric_type, limit=25)
        records = rec_res.data if rec_res.success else []
        formatted_rows = [
            (rec["id"], self._format_table_cells(rec)) for rec in records
        ]
        self.table.set_rows(formatted_rows)

    def _format_summary_banner(self, s: dict) -> str:
        if s.get("count", 0) == 0:
            return "Total Records: 0  |  Add your first entry on the left."

        if self.metric_type == "weight":
            bmi_txt = f"{s['latest_bmi']} ({s['bmi_category']})" if s.get("latest_bmi") else "N/A"
            return (
                f"Records: {s['count']}  |  Latest: {s['latest_weight']} kg  |  "
                f"Avg: {s['avg_weight']} kg  |  BMI: {bmi_txt}"
            )
        if self.metric_type == "blood_pressure":
            return (
                f"Records: {s['count']}  |  Latest: {s['latest_systolic']}/{s['latest_diastolic']} mmHg "
                f"({s['latest_category']})  |  Avg: {s['avg_systolic']}/{s['avg_diastolic']}"
            )
        if self.metric_type == "heart_rate":
            return (
                f"Records: {s['count']}  |  Latest: {s['latest_bpm']} bpm  |  "
                f"Avg: {s['avg_bpm']} bpm  |  Min/Max: {s['min_bpm']}/{s['max_bpm']}"
            )
        return (
            f"Records: {s['count']}  |  Total Steps: {s['total_steps']:,}  |  "
            f"Avg Sleep: {s['avg_sleep_hours']} hrs  |  Total Calories: {s['total_calories']:,} kcal"
        )

    def _format_table_cells(self, rec: dict) -> list[str]:
        if self.metric_type == "weight":
            bmi_val = str(rec["bmi"]) if rec.get("bmi") is not None else "--"
            bmi_cat = classify_bmi(rec.get("bmi")) if rec.get("bmi") is not None else "Set height"
            return [
                rec["recorded_date"],
                f"{rec['weight_kg']} kg",
                bmi_val,
                bmi_cat,
                rec.get("notes") or "-",
            ]
        if self.metric_type == "blood_pressure":
            cat = classify_blood_pressure(rec["systolic"], rec["diastolic"])
            return [
                rec["recorded_date"],
                f"{rec['systolic']}/{rec['diastolic']} mmHg",
                cat,
                rec.get("notes") or "-",
            ]
        if self.metric_type == "heart_rate":
            return [
                rec["recorded_date"],
                f"{rec['bpm']} bpm",
                rec.get("notes") or "-",
            ]
        return [
            rec["recorded_date"],
            f"{rec['steps']:,}",
            f"{rec['active_minutes']} min",
            f"{rec['sleep_hours']} hrs",
            f"{rec['calories_burned']:,} kcal",
        ]
