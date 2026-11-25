"""Graphical Reports view embedding Matplotlib charts and Pandas summaries."""

from tkinter import filedialog
from typing import Callable, Optional

import customtkinter as ctk

from config.theme import COLORS, FONTS, LAYOUT
from services.export_service import ExportService
from services.health_service import HealthService
from ui.components.cards import SectionCard, StatCard, StatusBanner
from ui.components.charts import (
    build_activity_figure,
    build_blood_pressure_figure,
    build_heart_rate_figure,
    build_weight_bmi_figure,
    embed_figure,
)


class ReportsView(ctk.CTkScrollableFrame):
    """Displays Pandas summary stats and 4 Matplotlib trend/bar charts."""

    def __init__(
        self,
        master,
        user: dict,
        health_service: HealthService,
        export_service: Optional[ExportService] = None,
        ask_save_path: Optional[Callable[[str, str], str]] = None,
    ):
        super().__init__(
            master,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["navy_light"],
        )
        self.user = user
        self.health_service = health_service
        self.export_service = export_service or ExportService(health_service)
        self.ask_save_path = ask_save_path or self._default_save_dialog
        self.canvases: list = []
        self._layout_mode: str = ""
        self._summary_cards: list[StatCard] = []
        self._chart_cards: list[SectionCard] = []

        self._build_ui()
        self.refresh_reports()
        self.bind("<Configure>", self._on_resize)

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
        # Top Date Range Filter Card
        # -------------------------------------------------------------------
        filter_card = SectionCard(
            self,
            title="Graphical Health Reports",
            subtitle="Explore historical trends using Pandas summaries and Matplotlib charts.",
        )
        filter_card.pack(fill="x", pady=(0, 14))

        self.status_banner = StatusBanner(filter_card.body, wraplength=650)

        controls = ctk.CTkFrame(filter_card.body, fg_color="transparent")
        controls.pack(fill="x")
        controls.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            controls, text="Start Date (YYYY-MM-DD)", font=FONTS["small_bold"], text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ctk.CTkLabel(
            controls, text="End Date (YYYY-MM-DD)", font=FONTS["small_bold"], text_color=COLORS["text_primary"]
        ).grid(row=0, column=1, sticky="w", padx=8)

        self.start_date_entry = ctk.CTkEntry(
            controls,
            placeholder_text="e.g. 2026-11-01",
            height=36,
            corner_radius=LAYOUT["input_radius"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
        )
        self.start_date_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))

        self.end_date_entry = ctk.CTkEntry(
            controls,
            placeholder_text="e.g. 2026-11-25",
            height=36,
            corner_radius=LAYOUT["input_radius"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
        )
        self.end_date_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=(4, 0))

        self.apply_btn = ctk.CTkButton(
            controls,
            text="Update Charts",
            command=self.refresh_reports,
            width=125,
            height=36,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["teal_primary"],
            hover_color=COLORS["teal_hover"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["small_bold"],
        )
        self.apply_btn.grid(row=1, column=2, padx=(8, 4), pady=(4, 0))

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
        self.reset_btn.grid(row=1, column=3, padx=(4, 6), pady=(4, 0))

        self.export_csv_btn = ctk.CTkButton(
            controls,
            text="Export CSV",
            command=self.export_csv,
            width=102,
            height=36,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["teal_primary"],
            hover_color=COLORS["teal_hover"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["small_bold"],
        )
        self.export_csv_btn.grid(row=1, column=4, padx=(0, 4), pady=(4, 0))

        self.export_pdf_btn = ctk.CTkButton(
            controls,
            text="Export PDF",
            command=self.export_pdf,
            width=102,
            height=36,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["navy_primary"],
            hover_color=COLORS["navy_light"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["small_bold"],
        )
        self.export_pdf_btn.grid(row=1, column=5, padx=(4, 0), pady=(4, 0))

        # -------------------------------------------------------------------
        # Summary Strip Container & 2x2 Charts Container
        # -------------------------------------------------------------------
        self.summary_strip = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_strip.pack(fill="x", pady=(0, 12))

        self.charts_grid = ctk.CTkFrame(self, fg_color="transparent")
        self.charts_grid.pack(fill="both", expand=True)

    def reset_filters(self) -> None:
        self.start_date_entry.delete(0, "end")
        self.end_date_entry.delete(0, "end")
        self.status_banner.clear()
        self.refresh_reports()

    def refresh_reports(self) -> None:
        """Fetch filtered Pandas DataFrames and rebuild summary cards & Matplotlib charts."""
        start_date: Optional[str] = self.start_date_entry.get().strip() or None
        end_date: Optional[str] = self.end_date_entry.get().strip() or None
        user_id = self.user["id"]

        w_res = self.health_service.get_records_df(user_id, "weight", start_date, end_date)
        if not w_res.success:
            self.status_banner.show(w_res.message, is_success=False)
            return

        bp_res = self.health_service.get_records_df(user_id, "blood_pressure", start_date, end_date)
        hr_res = self.health_service.get_records_df(user_id, "heart_rate", start_date, end_date)
        act_res = self.health_service.get_records_df(user_id, "activity", start_date, end_date)

        w_sum = self.health_service.get_metric_summary(user_id, "weight", start_date, end_date).data
        bp_sum = self.health_service.get_metric_summary(user_id, "blood_pressure", start_date, end_date).data
        hr_sum = self.health_service.get_metric_summary(user_id, "heart_rate", start_date, end_date).data
        act_sum = self.health_service.get_metric_summary(user_id, "activity", start_date, end_date).data

        self.status_banner.clear()
        self._render_summary_strip(w_sum, bp_sum, hr_sum, act_sum)
        self._render_charts(w_res.data, bp_res.data, hr_res.data, act_res.data)

    def _render_summary_strip(self, w_sum: dict, bp_sum: dict, hr_sum: dict, act_sum: dict) -> None:
        self._summary_cards.clear()
        for child in self.summary_strip.winfo_children():
            child.destroy()

        w_val = f"{w_sum['avg_weight']} kg" if w_sum.get("count") else "No data"
        w_sub = (
            f"Change: {w_sum['weight_change']:+.1f} kg ({w_sum['count']} logs)"
            if w_sum.get("count")
            else "0 records"
        )
        c1 = StatCard(self.summary_strip, "AVG WEIGHT", w_val, w_sub, accent_color=COLORS["teal_primary"])

        bp_val = f"{bp_sum['avg_systolic']}/{bp_sum['avg_diastolic']}" if bp_sum.get("count") else "No data"
        bp_sub = f"mmHg avg ({bp_sum.get('count', 0)} logs)"
        c2 = StatCard(self.summary_strip, "AVG BLOOD PRESSURE", bp_val, bp_sub, accent_color=COLORS["navy_primary"])

        hr_val = f"{hr_sum['avg_bpm']} bpm" if hr_sum.get("count") else "No data"
        hr_sub = (
            f"Min {hr_sum['min_bpm']} / Max {hr_sum['max_bpm']} ({hr_sum['count']} logs)"
            if hr_sum.get("count")
            else "0 records"
        )
        c3 = StatCard(self.summary_strip, "AVG HEART RATE", hr_val, hr_sub, accent_color=COLORS["teal_primary"])

        act_val = f"{act_sum['total_steps']:,}" if act_sum.get("count") else "0"
        act_sub = (
            f"Total steps | {act_sum['avg_sleep_hours']} hrs avg sleep"
            if act_sum.get("count")
            else "0 records"
        )
        c4 = StatCard(self.summary_strip, "TOTAL STEPS", act_val, act_sub, accent_color=COLORS["navy_primary"])

        self._summary_cards = [c1, c2, c3, c4]

    def _render_charts(self, weight_df, bp_df, hr_df, activity_df) -> None:
        self.canvases.clear()
        self._chart_cards.clear()
        for child in self.charts_grid.winfo_children():
            child.destroy()

        chart_specs = [
            ("Weight & BMI Trend", "Historical weight (kg) and BMI values", build_weight_bmi_figure(weight_df)),
            ("Blood Pressure Trend", "Systolic vs. Diastolic mmHg over time", build_blood_pressure_figure(bp_df)),
            ("Heart Rate Trend", "Beats per minute over time", build_heart_rate_figure(hr_df)),
            ("Daily Activity", "Total steps per recorded date", build_activity_figure(activity_df)),
        ]

        for title, subtitle, fig in chart_specs:
            card = SectionCard(self.charts_grid, title=title, subtitle=subtitle)
            canvas = embed_figure(card.body, fig)
            self.canvases.append(canvas)
            self._chart_cards.append(card)

        self._layout_mode = ""
        current_width = self.winfo_width()
        self._apply_responsive_layout(current_width if current_width > 100 else 1080)

    def _on_resize(self, event) -> None:
        if event.width > 100:
            self._apply_responsive_layout(event.width)

    def _apply_responsive_layout(self, width: int) -> None:
        mode = "wide" if width >= 840 else "narrow"
        if mode == self._layout_mode:
            return
        self._layout_mode = mode

        # Reflow summary KPI strip
        for col in range(4):
            self.summary_strip.grid_columnconfigure(col, weight=0, uniform="")
        for card in self._summary_cards:
            card.grid_forget()

        if mode == "wide":
            for col in range(4):
                self.summary_strip.grid_columnconfigure(col, weight=1, uniform="repsum")
            for idx, card in enumerate(self._summary_cards):
                pad = (0, 6) if idx == 0 else ((6, 0) if idx == 3 else 6)
                card.grid(row=0, column=idx, sticky="nsew", padx=pad)
        else:
            for col in range(2):
                self.summary_strip.grid_columnconfigure(col, weight=1, uniform="repsum")
            for idx, card in enumerate(self._summary_cards):
                r, c = divmod(idx, 2)
                card.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)

        # Reflow 2x2 or 1-column charts grid
        for col in range(2):
            self.charts_grid.grid_columnconfigure(col, weight=0, uniform="")
        for card in self._chart_cards:
            card.grid_forget()

        if mode == "wide":
            self.charts_grid.grid_columnconfigure((0, 1), weight=1, uniform="repchart")
            for idx, card in enumerate(self._chart_cards):
                r, c = divmod(idx, 2)
                pad_x = (0, 8) if c == 0 else (8, 0)
                pad_y = (0, 12) if r == 0 else (0, 0)
                card.grid(row=r, column=c, sticky="nsew", padx=pad_x, pady=pad_y)
        else:
            self.charts_grid.grid_columnconfigure(0, weight=1)
            for idx, card in enumerate(self._chart_cards):
                card.grid(row=idx, column=0, sticky="nsew", pady=(0, 12))

    def export_csv(self) -> None:
        """Save filtered health records to a CSV file."""
        start_date = self.start_date_entry.get().strip() or None
        end_date = self.end_date_entry.get().strip() or None
        output_path = self.ask_save_path(".csv", f"healthtrack_{self.user['username']}_records.csv")
        if not output_path:
            return
        res = self.export_service.export_to_csv(
            self.user, output_path, start_date=start_date, end_date=end_date
        )
        self.status_banner.show(res.message, is_success=res.success)

    def export_pdf(self) -> None:
        """Save the graphical health summary report to a PDF file."""
        start_date = self.start_date_entry.get().strip() or None
        end_date = self.end_date_entry.get().strip() or None
        output_path = self.ask_save_path(".pdf", f"healthtrack_{self.user['username']}_report.pdf")
        if not output_path:
            return
        res = self.export_service.export_to_pdf(
            self.user, output_path, start_date=start_date, end_date=end_date
        )
        self.status_banner.show(res.message, is_success=res.success)
