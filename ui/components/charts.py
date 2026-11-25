"""Reusable Matplotlib chart builders styled for HealthTrack's light theme.

Uses Matplotlib's object-oriented Figure API (no global pyplot state)
and plots strictly historical user data (no ML or AI prediction).
"""

from datetime import timedelta

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import pandas as pd

from config.theme import COLORS


def embed_figure(parent, fig: Figure) -> FigureCanvasTkAgg:
    """Embed a Matplotlib Figure inside a CustomTkinter parent widget cleanly."""
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    widget = canvas.get_tk_widget()
    widget.configure(bg=COLORS["bg_card"], highlightthickness=0)
    widget.pack(fill="both", expand=True)
    return canvas


def _style_axis(ax, title: str, ylabel: str) -> None:
    """Apply consistent White, Navy Blue, and Teal styling to a Matplotlib axis."""
    ax.set_facecolor(COLORS["bg_card"])
    ax.set_title(title, fontsize=11, fontweight="bold", color=COLORS["navy_primary"], pad=10)
    ax.set_ylabel(ylabel, fontsize=9, color=COLORS["text_secondary"])
    ax.tick_params(colors=COLORS["text_secondary"], labelsize=8)
    ax.grid(True, linestyle="--", alpha=0.4, color=COLORS["border"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLORS["border"])
    ax.spines["bottom"].set_color(COLORS["border"])


def _show_empty_state(ax, message: str) -> None:
    """Render a clean centered empty-data message inside an axis."""
    ax.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        transform=ax.transAxes,
        color=COLORS["text_secondary"],
        fontsize=9,
    )
    ax.set_xticks([])
    ax.set_yticks([])


def _configure_date_xaxis(ax, dates: pd.Series) -> None:
    """Format date x-axis cleanly for both single-point and multi-point series."""
    if len(dates) == 1:
        single_dt = pd.Timestamp(dates.iloc[0])
        ax.set_xlim(single_dt - timedelta(days=1), single_dt + timedelta(days=1))
        ax.set_xticks([single_dt])
    else:
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.tick_params(axis="x", rotation=22)


def build_dashboard_overview_figure(weight_df: pd.DataFrame, hr_df: pd.DataFrame) -> Figure:
    """Build a compact two-panel historical overview chart for the Dashboard."""
    fig = Figure(figsize=(7.2, 2.8), dpi=100, facecolor=COLORS["bg_card"])
    fig.subplots_adjust(wspace=0.26, bottom=0.22, top=0.84, left=0.08, right=0.98)

    ax1 = fig.add_subplot(1, 2, 1)
    _style_axis(ax1, "Recent Weight Trend", "kg")
    if not weight_df.empty:
        recent_w = weight_df.tail(10)
        ax1.plot(
            recent_w["recorded_date"],
            recent_w["weight_kg"],
            marker="o",
            linewidth=2.2,
            color=COLORS["teal_primary"],
            markersize=5,
        )
        _configure_date_xaxis(ax1, recent_w["recorded_date"])
    else:
        _show_empty_state(ax1, "No weight logs yet")

    ax2 = fig.add_subplot(1, 2, 2)
    _style_axis(ax2, "Recent Heart Rate", "bpm")
    if not hr_df.empty:
        recent_hr = hr_df.tail(10)
        ax2.plot(
            recent_hr["recorded_date"],
            recent_hr["bpm"],
            marker="s",
            linewidth=2.2,
            color=COLORS["navy_primary"],
            markersize=5,
        )
        _configure_date_xaxis(ax2, recent_hr["recorded_date"])
    else:
        _show_empty_state(ax2, "No heart rate logs yet")

    return fig


def build_weight_bmi_figure(weight_df: pd.DataFrame) -> Figure:
    """Build the Weight (kg) & BMI trend line chart."""
    fig = Figure(figsize=(5.4, 3.0), dpi=100, facecolor=COLORS["bg_card"])
    fig.subplots_adjust(bottom=0.22, top=0.85, left=0.12, right=0.88)

    ax = fig.add_subplot(1, 1, 1)
    _style_axis(ax, "Weight & BMI Trend", "Weight (kg)")

    if weight_df.empty:
        _show_empty_state(ax, "No weight records found for selected period")
        return fig

    line_w = ax.plot(
        weight_df["recorded_date"],
        weight_df["weight_kg"],
        marker="o",
        linewidth=2.2,
        color=COLORS["teal_primary"],
        label="Weight (kg)",
        markersize=5,
    )
    _configure_date_xaxis(ax, weight_df["recorded_date"])

    # Plot BMI on a secondary axis when BMI values are available
    bmi_valid = weight_df.dropna(subset=["bmi"]) if "bmi" in weight_df.columns else pd.DataFrame()
    lines = list(line_w)
    if not bmi_valid.empty:
        ax_bmi = ax.twinx()
        ax_bmi.set_ylabel("BMI", fontsize=9, color=COLORS["navy_primary"])
        ax_bmi.tick_params(colors=COLORS["navy_primary"], labelsize=8)
        ax_bmi.spines["top"].set_visible(False)
        ax_bmi.spines["right"].set_color(COLORS["border"])
        line_b = ax_bmi.plot(
            bmi_valid["recorded_date"],
            bmi_valid["bmi"],
            marker="^",
            linestyle="--",
            linewidth=1.8,
            color=COLORS["navy_primary"],
            label="BMI",
            markersize=5,
        )
        lines.extend(line_b)

    labels = [line.get_label() for line in lines]
    ax.legend(lines, labels, loc="upper left", frameon=True, fontsize=8)
    return fig


def build_blood_pressure_figure(bp_df: pd.DataFrame) -> Figure:
    """Build the Systolic & Diastolic Blood Pressure trend line chart."""
    fig = Figure(figsize=(5.4, 3.0), dpi=100, facecolor=COLORS["bg_card"])
    fig.subplots_adjust(bottom=0.22, top=0.85, left=0.12, right=0.95)

    ax = fig.add_subplot(1, 1, 1)
    _style_axis(ax, "Blood Pressure Trend (Systolic / Diastolic)", "mmHg")

    if bp_df.empty:
        _show_empty_state(ax, "No blood pressure records found for selected period")
        return fig

    ax.plot(
        bp_df["recorded_date"],
        bp_df["systolic"],
        marker="o",
        linewidth=2.2,
        color=COLORS["navy_primary"],
        label="Systolic (mmHg)",
        markersize=5,
    )
    ax.plot(
        bp_df["recorded_date"],
        bp_df["diastolic"],
        marker="s",
        linewidth=2.2,
        color=COLORS["teal_primary"],
        label="Diastolic (mmHg)",
        markersize=5,
    )
    _configure_date_xaxis(ax, bp_df["recorded_date"])
    ax.legend(loc="upper left", frameon=True, fontsize=8)
    return fig


def build_heart_rate_figure(hr_df: pd.DataFrame) -> Figure:
    """Build the Heart Rate (bpm) trend line chart."""
    fig = Figure(figsize=(5.4, 3.0), dpi=100, facecolor=COLORS["bg_card"])
    fig.subplots_adjust(bottom=0.22, top=0.85, left=0.12, right=0.95)

    ax = fig.add_subplot(1, 1, 1)
    _style_axis(ax, "Heart Rate Trend", "BPM")

    if hr_df.empty:
        _show_empty_state(ax, "No heart rate records found for selected period")
        return fig

    ax.plot(
        hr_df["recorded_date"],
        hr_df["bpm"],
        marker="o",
        linewidth=2.2,
        color=COLORS["teal_primary"],
        label="Heart Rate (bpm)",
        markersize=5,
    )

    if len(hr_df) > 1:
        avg_bpm = float(hr_df["bpm"].mean())
        ax.axhline(
            avg_bpm,
            color=COLORS["navy_light"],
            linestyle=":",
            linewidth=1.4,
            label=f"Mean ({avg_bpm:.1f} bpm)",
        )

    _configure_date_xaxis(ax, hr_df["recorded_date"])
    ax.legend(loc="upper left", frameon=True, fontsize=8)
    return fig


def build_activity_figure(activity_df: pd.DataFrame) -> Figure:
    """Build the Daily Activity bar chart (steps per logged date)."""
    fig = Figure(figsize=(5.4, 3.0), dpi=100, facecolor=COLORS["bg_card"])
    fig.subplots_adjust(bottom=0.24, top=0.85, left=0.14, right=0.95)

    ax = fig.add_subplot(1, 1, 1)
    _style_axis(ax, "Daily Activity (Steps)", "Steps")

    if activity_df.empty:
        _show_empty_state(ax, "No daily activity records found for selected period")
        return fig

    # Aggregate steps by date using Pandas in case multiple logs exist on one day
    grouped = (
        activity_df.groupby(activity_df["recorded_date"].dt.strftime("%Y-%m-%d"), as_index=False)[
            "steps"
        ]
        .sum()
        .sort_values("recorded_date")
    )

    x_labels = grouped["recorded_date"].tolist()
    y_steps = grouped["steps"].tolist()
    bar_colors = [
        COLORS["teal_primary"] if idx % 2 == 0 else COLORS["navy_primary"]
        for idx in range(len(x_labels))
    ]
    ax.bar(x_labels, y_steps, color=bar_colors, width=0.55)
    ax.tick_params(axis="x", rotation=25)
    return fig
