"""Health History view showing a unified, filterable table of all records."""

from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk

from config.theme import COLORS, FONTS, LAYOUT
from services.export_service import ExportService
from services.health_service import HealthService
from ui.components.cards import RecordsTable, SectionCard, StatusBanner

METRIC_FILTER_OPTIONS = {
    "All Metrics": "all",
    "Weight & BMI": "weight",
    "Blood Pressure": "blood_pressure",
    "Heart Rate": "heart_rate",
    "Daily Activity": "activity",
}


def _default_confirm_delete(metric_label: str, recorded_date: str) -> bool:
    """Show a confirmation dialog before deleting a health record."""
    return messagebox.askyesno(
        "Confirm Deletion",
        f"Delete this {metric_label} record from {recorded_date}?\nThis action cannot be undone.",
    )


class HistoryView(ctk.CTkFrame):
    """Displays unified health records with metric/date filters and confirmed deletion."""

    def __init__(
        self,
        master,
        user: dict,
        health_service: HealthService,
        export_service: Optional[ExportService] = None,
        confirm_delete: Optional[Callable[[str, str], bool]] = None,
        ask_save_path: Optional[Callable[[str, str], str]] = None,
    ):
        super().__init__(master, fg_color="transparent")
        self.user = user
        self.health_service = health_service
        self.export_service = export_service or ExportService(health_service)
        self.confirm_delete = confirm_delete or _default_confirm_delete
        self.ask_save_path = ask_save_path or self._default_save_dialog
        self._row_lookup: dict[tuple[str, int], dict] = {}

        self._build_ui()
        self.apply_filters()

    @staticmethod
    def _default_save_dialog(ext: str, default_name: str) -> str:
        filetypes = (
            [("CSV files", "*.csv")] if ext == ".csv" else [("PDF files", "*.pdf")]
        )
        return filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=filetypes,
            initialfile=default_name,
            title=f"Save HealthTrack {ext.upper().lstrip('.')} Export",
        )

    def _build_ui(self) -> None:
        # -------------------------------------------------------------------
        # Filter Bar Card
        # -------------------------------------------------------------------
        filter_card = SectionCard(
            self,
            title="Filter Health History",
            subtitle="Filter your stored records by metric type and date range.",
        )
        filter_card.pack(fill="x", pady=(0, 14))

        self.status_banner = StatusBanner(filter_card.body, wraplength=650)

        controls = ctk.CTkFrame(filter_card.body, fg_color="transparent")
        controls.pack(fill="x")
        controls.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            controls, text="Metric Type", font=FONTS["small_bold"], text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ctk.CTkLabel(
            controls, text="Start Date (YYYY-MM-DD)", font=FONTS["small_bold"], text_color=COLORS["text_primary"]
        ).grid(row=0, column=1, sticky="w", padx=8)
        ctk.CTkLabel(
            controls, text="End Date (YYYY-MM-DD)", font=FONTS["small_bold"], text_color=COLORS["text_primary"]
        ).grid(row=0, column=2, sticky="w", padx=8)

        self.metric_menu = ctk.CTkOptionMenu(
            controls,
            values=list(METRIC_FILTER_OPTIONS.keys()),
            height=36,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["navy_primary"],
            button_hover_color=COLORS["navy_light"],
            text_color=COLORS["text_primary"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_text_color=COLORS["text_primary"],
        )
        self.metric_menu.set("All Metrics")
        self.metric_menu.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))

        self.start_date_entry = ctk.CTkEntry(
            controls,
            placeholder_text="e.g. 2026-11-01",
            height=36,
            corner_radius=LAYOUT["input_radius"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
        )
        self.start_date_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=(4, 0))

        self.end_date_entry = ctk.CTkEntry(
            controls,
            placeholder_text="e.g. 2026-11-25",
            height=36,
            corner_radius=LAYOUT["input_radius"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
        )
        self.end_date_entry.grid(row=1, column=2, sticky="ew", padx=8, pady=(4, 0))

        self.apply_btn = ctk.CTkButton(
            controls,
            text="Apply Filter",
            command=self.apply_filters,
            width=115,
            height=36,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["teal_primary"],
            hover_color=COLORS["teal_hover"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["small_bold"],
        )
        self.apply_btn.grid(row=1, column=3, padx=(8, 4), pady=(4, 0))

        self.reset_btn = ctk.CTkButton(
            controls,
            text="Reset",
            command=self.reset_filters,
            width=82,
            height=36,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["border"],
            font=FONTS["small_bold"],
        )
        self.reset_btn.grid(row=1, column=4, padx=(4, 0), pady=(4, 0))

        # -------------------------------------------------------------------
        # Unified History Table Card
        # -------------------------------------------------------------------
        table_card = SectionCard(
            self,
            title="Unified Health Records",
            subtitle="All weight, blood pressure, heart rate, and daily activity entries.",
        )
        table_card.pack(fill="both", expand=True)

        summary_bar = ctk.CTkFrame(table_card.body, fg_color="transparent")
        summary_bar.pack(fill="x", pady=(0, 12))

        self.summary_label = ctk.CTkLabel(
            summary_bar,
            text="",
            font=FONTS["small_bold"],
            text_color=COLORS["navy_primary"],
            fg_color=COLORS["bg_input"],
            corner_radius=8,
            padx=12,
            pady=8,
            anchor="w",
        )
        self.summary_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.export_csv_btn = ctk.CTkButton(
            summary_bar,
            text="Export CSV",
            command=self.export_csv,
            width=110,
            height=34,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["teal_primary"],
            hover_color=COLORS["teal_hover"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["small_bold"],
        )
        self.export_csv_btn.pack(side="left", padx=(0, 6))

        self.export_pdf_btn = ctk.CTkButton(
            summary_bar,
            text="Export PDF",
            command=self.export_pdf,
            width=110,
            height=34,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["navy_primary"],
            hover_color=COLORS["navy_light"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["small_bold"],
        )
        self.export_pdf_btn.pack(side="left")

        self.table = RecordsTable(
            table_card.body,
            columns=[
                ("Date", 2),
                ("Metric", 2),
                ("Reading / Details", 5),
                ("Notes", 3),
            ],
            on_delete=self.handle_delete,
        )
        self.table.pack(fill="both", expand=True)

    def apply_filters(self) -> None:
        """Load filtered unified records using HealthService & Pandas."""
        selected_label = self.metric_menu.get()
        metric_filter = METRIC_FILTER_OPTIONS.get(selected_label, "all")
        start_date = self.start_date_entry.get().strip() or None
        end_date = self.end_date_entry.get().strip() or None

        res = self.health_service.get_unified_history_df(
            self.user["id"],
            metric_filter=metric_filter,
            start_date=start_date,
            end_date=end_date,
        )
        if not res.success:
            self.status_banner.show(res.message, is_success=False)
            return

        self.status_banner.clear()
        df = res.data
        self._row_lookup.clear()

        rows = []
        for _, row in df.iterrows():
            key = (str(row["metric_type"]), int(row["id"]))
            self._row_lookup[key] = {
                "metric_label": str(row["metric_label"]),
                "recorded_date": str(row["recorded_date"]),
            }
            rows.append(
                (
                    key,
                    [
                        str(row["recorded_date"]),
                        str(row["metric_label"]),
                        str(row["summary"]),
                        str(row["notes"]) or "-",
                    ],
                )
            )

        self.summary_label.configure(
            text=f"Showing {len(df)} record(s)  |  Filter: {selected_label}"
        )
        self.table.set_rows(rows, empty_message="No health records match the current filter.")

    def reset_filters(self) -> None:
        """Clear filter inputs and reload all user records."""
        self.metric_menu.set("All Metrics")
        self.start_date_entry.delete(0, "end")
        self.end_date_entry.delete(0, "end")
        self.status_banner.clear()
        self.apply_filters()

    def handle_delete(self, record_key: tuple[str, int]) -> None:
        """Confirm with the user, then delete the selected record from SQLite."""
        metric_type, record_id = record_key
        meta = self._row_lookup.get(record_key, {"metric_label": metric_type, "recorded_date": ""})
        confirmed = self.confirm_delete(meta["metric_label"], meta["recorded_date"])
        if not confirmed:
            return

        res = self.health_service.delete_record(self.user["id"], metric_type, record_id)
        if not res.success:
            self.status_banner.show(res.message, is_success=False)
            return

        self.apply_filters()
        self.status_banner.show("Record deleted successfully.", is_success=True)

    def export_csv(self) -> None:
        """Ask for a save path and export the filtered history to CSV."""
        selected_label = self.metric_menu.get()
        metric_filter = METRIC_FILTER_OPTIONS.get(selected_label, "all")
        start_date = self.start_date_entry.get().strip() or None
        end_date = self.end_date_entry.get().strip() or None

        default_name = f"healthtrack_{self.user['username']}_history.csv"
        output_path = self.ask_save_path(".csv", default_name)
        if not output_path:
            return

        res = self.export_service.export_to_csv(
            self.user,
            output_path,
            metric_filter=metric_filter,
            start_date=start_date,
            end_date=end_date,
        )
        self.status_banner.show(res.message, is_success=res.success)

    def export_pdf(self) -> None:
        """Ask for a save path and generate a full PDF health report."""
        start_date = self.start_date_entry.get().strip() or None
        end_date = self.end_date_entry.get().strip() or None

        default_name = f"healthtrack_{self.user['username']}_report.pdf"
        output_path = self.ask_save_path(".pdf", default_name)
        if not output_path:
            return

        res = self.export_service.export_to_pdf(
            self.user,
            output_path,
            start_date=start_date,
            end_date=end_date,
        )
        self.status_banner.show(res.message, is_success=res.success)
