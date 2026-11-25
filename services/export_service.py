"""CSV and PDF export service for HealthTrack.

Exports strictly the authenticated user's own health records using
Pandas (CSV) and fpdf2 (PDF with profile, BMI summary, statistics,
embedded Matplotlib charts, and record tables). No ML or AI is used.
"""

from datetime import datetime
from pathlib import Path
import tempfile
from typing import Any, NamedTuple, Optional

from fpdf import FPDF

from services.health_service import HealthService
from ui.components.charts import (
    build_activity_figure,
    build_blood_pressure_figure,
    build_heart_rate_figure,
    build_weight_bmi_figure,
)

# RGB color tuples matching config/theme.py (White, Navy Blue, Teal)
NAVY_RGB = (15, 41, 74)       # #0F294A
TEAL_RGB = (13, 148, 136)     # #0D9488
SLATE_RGB = (71, 85, 105)     # #475569
DARK_TEXT_RGB = (15, 23, 42)  # #0F172A
ALT_ROW_RGB = (241, 245, 249) # #F1F5F9
BORDER_RGB = (226, 232, 240)  # #E2E8F0


class ExportResult(NamedTuple):
    """Standard return object for CSV and PDF export operations."""

    success: bool
    file_path: str
    message: str


def _safe_pdf_text(value: Any) -> str:
    """Convert text to Latin-1-safe string for fpdf2's built-in Helvetica font."""
    text = str(value if value is not None else "")
    replacements = {
        "–": "-",
        "—": "-",
        "•": "-",
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class _HealthReportPDF(FPDF):
    """Custom FPDF subclass with consistent HealthTrack header and page footer."""

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*SLATE_RGB)
        self.cell(
            0,
            8,
            f"HealthTrack Personal Health Report  |  Page {self.page_no()} of {{nb}}",
            align="C",
        )


class ExportService:
    """Generates user-scoped CSV files and PDF reports from HealthService data."""

    def __init__(self, health_service: HealthService):
        self.health_service = health_service

    def export_to_csv(
        self,
        user: dict,
        output_path: str | Path,
        metric_filter: str = "all",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ExportResult:
        """Export the authenticated user's health records to CSV using Pandas."""
        if not user or "id" not in user:
            return ExportResult(False, "", "No authenticated user provided.")
        if not output_path or not str(output_path).strip():
            return ExportResult(False, "", "No output file path selected.")

        res = self.health_service.get_unified_history_df(
            user["id"],
            metric_filter=metric_filter,
            start_date=start_date,
            end_date=end_date,
        )
        if not res.success:
            return ExportResult(False, "", res.message)

        df = res.data
        if df.empty:
            return ExportResult(
                False,
                "",
                "No health records found to export for the selected filter.",
            )

        export_df = df[["recorded_date", "metric_label", "summary", "notes"]].rename(
            columns={
                "recorded_date": "Date",
                "metric_label": "Metric",
                "summary": "Details",
                "notes": "Notes",
            }
        )

        target_path = Path(output_path)
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            export_df.to_csv(target_path, index=False, encoding="utf-8-sig")
            return ExportResult(
                True,
                str(target_path),
                f"Exported {len(export_df)} record(s) to {target_path.name}.",
            )
        except OSError as exc:
            return ExportResult(False, "", f"Failed to write CSV file: {exc}")

    def export_to_pdf(
        self,
        user: dict,
        output_path: str | Path,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ExportResult:
        """Generate a formatted PDF health report with profile, BMI, stats, charts, and table."""
        if not user or "id" not in user:
            return ExportResult(False, "", "No authenticated user provided.")
        if not output_path or not str(output_path).strip():
            return ExportResult(False, "", "No output file path selected.")

        user_id = user["id"]

        # Fetch all user-scoped data and validate any date range first
        history_res = self.health_service.get_unified_history_df(
            user_id, metric_filter="all", start_date=start_date, end_date=end_date
        )
        if not history_res.success:
            return ExportResult(False, "", history_res.message)

        w_sum = self.health_service.get_metric_summary(user_id, "weight", start_date, end_date).data
        bp_sum = self.health_service.get_metric_summary(user_id, "blood_pressure", start_date, end_date).data
        hr_sum = self.health_service.get_metric_summary(user_id, "heart_rate", start_date, end_date).data
        act_sum = self.health_service.get_metric_summary(user_id, "activity", start_date, end_date).data

        w_df = self.health_service.get_records_df(user_id, "weight", start_date, end_date).data
        bp_df = self.health_service.get_records_df(user_id, "blood_pressure", start_date, end_date).data
        hr_df = self.health_service.get_records_df(user_id, "heart_rate", start_date, end_date).data
        act_df = self.health_service.get_records_df(user_id, "activity", start_date, end_date).data

        pdf = _HealthReportPDF(orientation="P", unit="mm", format="A4")
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.add_page()

        # 1. Navy & Teal Title Banner
        self._draw_report_banner(pdf, start_date, end_date)

        # 2. User Profile & BMI Summary
        self._draw_profile_and_bmi_section(pdf, user, w_sum)

        # 3. Health Statistics Summary
        self._draw_statistics_section(pdf, w_sum, bp_sum, hr_sum, act_sum)

        # 4. Embedded Matplotlib Charts (rendered to temporary PNGs)
        with tempfile.TemporaryDirectory() as tmp_dir:
            chart_paths = self._render_chart_images(
                Path(tmp_dir), w_df, bp_df, hr_df, act_df
            )
            self._draw_charts_section(pdf, chart_paths)

        # 5. Health Records Table
        self._draw_records_table(pdf, history_res.data)

        target_path = Path(output_path)
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            pdf.output(str(target_path))
            return ExportResult(
                True,
                str(target_path),
                f"PDF report saved to {target_path.name}.",
            )
        except OSError as exc:
            return ExportResult(False, "", f"Failed to write PDF file: {exc}")

    # -----------------------------------------------------------------------
    # PDF Section Builders
    # -----------------------------------------------------------------------

    def _draw_report_banner(
        self, pdf: FPDF, start_date: Optional[str], end_date: Optional[str]
    ) -> None:
        pdf.set_fill_color(*NAVY_RGB)
        pdf.rect(10, 10, 190, 24, style="F")
        pdf.set_fill_color(*TEAL_RGB)
        pdf.rect(10, 34, 190, 2, style="F")

        pdf.set_xy(15, 13)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, "HealthTrack - Personal Health Report", new_x="LMARGIN", new_y="NEXT")

        period_txt = (
            f"Period: {start_date or 'Beginning'} to {end_date or 'Present'}"
            if (start_date or end_date)
            else "Period: All Recorded Dates"
        )
        generated_txt = datetime.now().strftime("%Y-%m-%d %H:%M")
        pdf.set_x(15)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(203, 213, 225)
        pdf.cell(
            0,
            6,
            _safe_pdf_text(f"Generated: {generated_txt}   |   {period_txt}"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_y(42)

    def _draw_section_heading(self, pdf: FPDF, title: str) -> None:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*NAVY_RGB)
        pdf.cell(0, 7, _safe_pdf_text(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*TEAL_RGB)
        pdf.set_line_width(0.5)
        y = pdf.get_y()
        pdf.line(10, y, 200, y)
        pdf.ln(3)

    def _draw_profile_and_bmi_section(
        self, pdf: FPDF, user: dict, w_sum: dict
    ) -> None:
        self._draw_section_heading(pdf, "User Profile & BMI Summary")

        height_txt = f"{user['height_cm']} cm" if user.get("height_cm") else "Not set"
        target_txt = (
            f"{user['target_weight_kg']} kg" if user.get("target_weight_kg") else "Not set"
        )
        age_txt = str(user["age"]) if user.get("age") is not None else "Not set"
        gender_txt = user.get("gender") or "Not set"

        latest_weight = (
            f"{w_sum['latest_weight']} kg" if w_sum.get("count", 0) > 0 else "No data"
        )
        latest_bmi = (
            f"{w_sum['latest_bmi']} ({w_sum['bmi_category']})"
            if w_sum.get("latest_bmi")
            else "N/A"
        )

        rows = [
            ("Full Name:", user.get("full_name", ""), "Username:", f"@{user.get('username', '')}"),
            ("Email:", user.get("email", ""), "Age / Gender:", f"{age_txt} / {gender_txt}"),
            ("Height:", height_txt, "Target Weight:", target_txt),
            ("Latest Weight:", latest_weight, "Latest BMI:", latest_bmi),
        ]

        for l1, v1, l2, v2 in rows:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*SLATE_RGB)
            pdf.cell(30, 6, _safe_pdf_text(l1))
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*DARK_TEXT_RGB)
            pdf.cell(65, 6, _safe_pdf_text(v1))

            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*SLATE_RGB)
            pdf.cell(30, 6, _safe_pdf_text(l2))
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*DARK_TEXT_RGB)
            pdf.cell(65, 6, _safe_pdf_text(v2), new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)

    def _draw_statistics_section(
        self, pdf: FPDF, w_sum: dict, bp_sum: dict, hr_sum: dict, act_sum: dict
    ) -> None:
        self._draw_section_heading(pdf, "Health Statistics Overview")

        stat_lines = [
            (
                "Weight",
                f"Records: {w_sum.get('count', 0)} | Avg: {w_sum['avg_weight']} kg | "
                f"Min/Max: {w_sum['min_weight']}/{w_sum['max_weight']} kg | Change: {w_sum['weight_change']:+.1f} kg"
                if w_sum.get("count", 0) > 0
                else "No weight records logged in this period.",
            ),
            (
                "Blood Pressure",
                f"Records: {bp_sum.get('count', 0)} | Latest: {bp_sum['latest_systolic']}/{bp_sum['latest_diastolic']} mmHg ({bp_sum['latest_category']}) | "
                f"Avg: {bp_sum['avg_systolic']}/{bp_sum['avg_diastolic']} mmHg"
                if bp_sum.get("count", 0) > 0
                else "No blood pressure records logged in this period.",
            ),
            (
                "Heart Rate",
                f"Records: {hr_sum.get('count', 0)} | Latest: {hr_sum['latest_bpm']} bpm | "
                f"Avg: {hr_sum['avg_bpm']} bpm | Min/Max: {hr_sum['min_bpm']}/{hr_sum['max_bpm']} bpm"
                if hr_sum.get("count", 0) > 0
                else "No heart rate records logged in this period.",
            ),
            (
                "Daily Activity",
                f"Records: {act_sum.get('count', 0)} | Total Steps: {act_sum['total_steps']:,} | "
                f"Avg Sleep: {act_sum['avg_sleep_hours']} hrs | Total Calories: {act_sum['total_calories']:,} kcal"
                if act_sum.get("count", 0) > 0
                else "No activity records logged in this period.",
            ),
        ]

        for label, summary in stat_lines:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*TEAL_RGB)
            pdf.cell(32, 6, _safe_pdf_text(f"{label}:"))
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*DARK_TEXT_RGB)
            pdf.cell(0, 6, _safe_pdf_text(summary), new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)

    def _render_chart_images(
        self, tmp_dir: Path, w_df, bp_df, hr_df, act_df
    ) -> list[Path]:
        """Render non-empty health charts to temporary PNG files for PDF embedding."""
        specs = [
            ("weight_bmi.png", w_df, build_weight_bmi_figure),
            ("blood_pressure.png", bp_df, build_blood_pressure_figure),
            ("heart_rate.png", hr_df, build_heart_rate_figure),
            ("activity.png", act_df, build_activity_figure),
        ]
        paths: list[Path] = []
        for filename, df, builder in specs:
            if df is None or df.empty:
                continue
            fig = builder(df)
            img_path = tmp_dir / filename
            fig.savefig(img_path, dpi=135, bbox_inches="tight", facecolor="white")
            paths.append(img_path)
        return paths

    def _draw_charts_section(self, pdf: FPDF, chart_paths: list[Path]) -> None:
        self._draw_section_heading(pdf, "Graphical Health Trends")

        if not chart_paths:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*SLATE_RGB)
            pdf.cell(
                0,
                7,
                "No chart data available for the selected date range.",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            pdf.ln(4)
            return

        # Place up to 2 charts per row (92mm wide each)
        col_x = [10, 106]
        idx = 0
        while idx < len(chart_paths):
            if pdf.get_y() > 215:
                pdf.add_page()
            row_y = pdf.get_y()
            for col in range(2):
                if idx + col < len(chart_paths):
                    pdf.image(str(chart_paths[idx + col]), x=col_x[col], y=row_y, w=92)
            pdf.set_y(row_y + 60)
            idx += 2

        pdf.ln(3)

    def _draw_records_table(self, pdf: FPDF, history_df) -> None:
        if pdf.get_y() > 240:
            pdf.add_page()

        self._draw_section_heading(pdf, f"Health Records ({len(history_df)} total)")

        if history_df.empty:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*SLATE_RGB)
            pdf.cell(
                0,
                7,
                "No health records were logged during this period.",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            return

        col_widths = [26, 32, 86, 46]
        headers = ["Date", "Metric", "Reading / Details", "Notes"]

        def draw_header() -> None:
            pdf.set_fill_color(*NAVY_RGB)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 9)
            for width, h_text in zip(col_widths, headers):
                pdf.cell(width, 7, h_text, border=0, fill=True)
            pdf.ln()

        draw_header()

        pdf.set_font("Helvetica", "", 8)
        for row_idx, (_, row) in enumerate(history_df.iterrows()):
            if pdf.get_y() > 270:
                pdf.add_page()
                draw_header()
                pdf.set_font("Helvetica", "", 8)

            fill = row_idx % 2 == 1
            if fill:
                pdf.set_fill_color(*ALT_ROW_RGB)
            else:
                pdf.set_fill_color(255, 255, 255)

            pdf.set_text_color(*DARK_TEXT_RGB)
            cells = [
                _safe_pdf_text(row["recorded_date"])[:12],
                _safe_pdf_text(row["metric_label"])[:18],
                _safe_pdf_text(row["summary"])[:52],
                _safe_pdf_text(row["notes"] or "-")[:26],
            ]
            for width, val in zip(col_widths, cells):
                pdf.cell(width, 6, val, border=0, fill=True)
            pdf.ln()
