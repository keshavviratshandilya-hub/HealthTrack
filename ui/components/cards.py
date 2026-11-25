"""Reusable UI components for HealthTrack (cards, banners, and record tables).

Maintains the premium light theme (White, Navy Blue, and Teal) across
all views without duplicating layout code.
"""

from typing import Any, Callable, Optional, Sequence

import customtkinter as ctk

from config.theme import COLORS, FONTS, LAYOUT


class StatusBanner:
    """Collapsible inline status banner for success and error feedback."""

    def __init__(self, parent, wraplength: int = 440, pady: tuple[int, int] = (0, 10)):
        self._pady = pady
        self.slot = ctk.CTkFrame(parent, fg_color="transparent", height=0)
        self.slot.pack(fill="x")
        self.label = ctk.CTkLabel(
            self.slot,
            text="",
            font=FONTS["small_bold"],
            corner_radius=8,
            padx=12,
            pady=8,
            wraplength=wraplength,
            justify="left",
        )

    def show(self, message: str, is_success: bool = False) -> None:
        """Display a styled status message (teal/green on success, red on error)."""
        fg = COLORS["success_bg"] if is_success else COLORS["danger_bg"]
        tc = COLORS["success"] if is_success else COLORS["danger"]
        self.label.configure(text=message, fg_color=fg, text_color=tc)
        if not self.label.winfo_manager():
            self.label.pack(fill="x", pady=self._pady)

    def clear(self) -> None:
        """Hide the status banner and collapse its vertical space."""
        self.label.pack_forget()
        self.label.configure(text="")
        self.slot.configure(height=0)

    def get_text(self) -> str:
        """Return the current message text (useful for testing)."""
        return self.label.cget("text")


class SectionCard(ctk.CTkFrame):
    """White card container with Navy Blue title, optional subtitle, and body frame."""

    def __init__(self, master, title: str, subtitle: str = "", **kwargs):
        super().__init__(
            master,
            fg_color=COLORS["bg_card"],
            corner_radius=LAYOUT["card_radius"],
            border_width=1,
            border_color=COLORS["border"],
            **kwargs,
        )
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            header,
            text=title,
            font=FONTS["subtitle"],
            text_color=COLORS["navy_primary"],
        ).pack(anchor="w")

        if subtitle:
            ctk.CTkLabel(
                header,
                text=subtitle,
                font=FONTS["small"],
                text_color=COLORS["text_secondary"],
            ).pack(anchor="w", pady=(1, 0))

        ctk.CTkFrame(self, fg_color=COLORS["divider"], height=1).pack(fill="x", padx=16)

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=16, pady=12)


class StatCard(ctk.CTkFrame):
    """KPI summary card displaying a metric title, large value, badge, and footnote."""

    def __init__(
        self,
        master,
        title: str,
        value: str = "--",
        subtitle: str = "",
        badge_text: str = "",
        badge_fg: str = COLORS["teal_soft"],
        badge_text_color: str = COLORS["teal_primary"],
        accent_color: str = COLORS["teal_primary"],
    ):
        super().__init__(
            master,
            fg_color=COLORS["bg_card"],
            corner_radius=LAYOUT["card_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )

        # Subtle top accent bar
        ctk.CTkFrame(self, fg_color=accent_color, height=3, corner_radius=2).pack(
            fill="x", padx=14, pady=(10, 6)
        )

        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=14)

        ctk.CTkLabel(
            top_row,
            text=title,
            font=FONTS["small_bold"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self.badge_label = ctk.CTkLabel(
            top_row,
            text=badge_text,
            font=FONTS["small_bold"],
            fg_color=badge_fg if badge_text else "transparent",
            text_color=badge_text_color,
            corner_radius=6,
            padx=7,
            pady=2,
        )
        if badge_text:
            self.badge_label.pack(side="right")

        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=FONTS["kpi_value"],
            text_color=COLORS["navy_primary"],
            anchor="w",
        )
        self.value_label.pack(fill="x", padx=14, pady=(4, 2))

        self.subtitle_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            anchor="w",
            wraplength=180,
            justify="left",
        )
        self.subtitle_label.pack(fill="x", padx=14, pady=(0, 10))
        self._last_wrap = 180
        self.bind("<Configure>", self._update_subtitle_wrap)

    def _update_subtitle_wrap(self, event) -> None:
        """Keep KPI card subtitle wrapping aligned with responsive card width."""
        new_wrap = max(120, event.width - 28)
        if abs(new_wrap - self._last_wrap) >= 12:
            self._last_wrap = new_wrap
            self.subtitle_label.configure(wraplength=new_wrap)


def badge_colors_for_status(status: str) -> tuple[str, str]:
    """Return (background_hex, text_hex) for BMI and blood pressure status labels."""
    normalized = (status or "").lower()
    if normalized in ("normal",):
        return COLORS["success_bg"], COLORS["success"]
    if normalized in ("elevated", "overweight", "underweight"):
        return COLORS["warning_bg"], COLORS["warning"]
    if "high" in normalized or normalized in ("obese", "low"):
        return COLORS["danger_bg"], COLORS["danger"]
    return COLORS["teal_soft"], COLORS["teal_primary"]


class RecordsTable(ctk.CTkFrame):
    """Reusable table widget with Navy Blue header and alternating white/slate rows."""

    def __init__(
        self,
        master,
        columns: Sequence[tuple[str, int]],
        on_delete: Optional[Callable[[int], None]] = None,
    ):
        """Initialize the table.

        columns: sequence of (header_label, weight) tuples.
        on_delete: optional callback receiving record_key when Delete is clicked.
        """
        super().__init__(master, fg_color="transparent")
        self.columns = list(columns)
        self.on_delete: Optional[Callable[[Any], None]] = on_delete

        # Header Bar
        header_bar = ctk.CTkFrame(
            self,
            fg_color=COLORS["navy_primary"],
            corner_radius=8,
            height=36,
        )
        header_bar.pack(fill="x", pady=(0, 6))
        header_bar.grid_propagate(False)

        total_cols = len(self.columns) + (1 if self.on_delete else 0)
        for col_idx, (col_name, weight) in enumerate(self.columns):
            header_bar.grid_columnconfigure(col_idx, weight=weight, uniform="tbl")
            ctk.CTkLabel(
                header_bar,
                text=col_name,
                font=FONTS["small_bold"],
                text_color=COLORS["text_on_dark"],
                anchor="w",
            ).grid(row=0, column=col_idx, sticky="ew", padx=10, pady=6)

        if self.on_delete:
            header_bar.grid_columnconfigure(total_cols - 1, weight=1, uniform="tbl")
            ctk.CTkLabel(
                header_bar,
                text="Action",
                font=FONTS["small_bold"],
                text_color=COLORS["text_on_dark"],
                anchor="center",
            ).grid(row=0, column=total_cols - 1, sticky="ew", padx=8, pady=6)

        self.scroll_rows = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["navy_light"],
        )
        self.scroll_rows.pack(fill="both", expand=True)

    def set_rows(self, rows: Sequence[tuple[Any, Sequence[str]]], empty_message: str = "No records found yet.") -> None:
        """Render table rows. Each item is (record_key, [cell_values...])."""
        for child in self.scroll_rows.winfo_children():
            child.destroy()

        if not rows:
            ctk.CTkLabel(
                self.scroll_rows,
                text=empty_message,
                font=FONTS["body"],
                text_color=COLORS["text_secondary"],
                pady=28,
            ).pack(fill="x")
            return

        total_cols = len(self.columns) + (1 if self.on_delete else 0)
        for row_idx, (record_id, values) in enumerate(rows):
            bg = COLORS["bg_card"] if row_idx % 2 == 0 else COLORS["bg_table_alt"]
            row_frame = ctk.CTkFrame(
                self.scroll_rows,
                fg_color=bg,
                corner_radius=6,
                border_width=1,
                border_color=COLORS["border"],
            )
            row_frame.pack(fill="x", pady=3)

            for col_idx, (_col_name, weight) in enumerate(self.columns):
                row_frame.grid_columnconfigure(col_idx, weight=weight, uniform="tbl")
                cell_text = values[col_idx] if col_idx < len(values) else ""
                ctk.CTkLabel(
                    row_frame,
                    text=cell_text,
                    font=FONTS["small"],
                    text_color=COLORS["text_primary"],
                    anchor="w",
                ).grid(row=0, column=col_idx, sticky="ew", padx=10, pady=8)

            if self.on_delete:
                row_frame.grid_columnconfigure(total_cols - 1, weight=1, uniform="tbl")
                ctk.CTkButton(
                    row_frame,
                    text="Delete",
                    width=64,
                    height=26,
                    corner_radius=6,
                    fg_color=COLORS["danger_bg"],
                    hover_color="#FECACA",
                    text_color=COLORS["danger"],
                    font=FONTS["small_bold"],
                    command=lambda rid=record_id: self.on_delete(rid),
                ).grid(row=0, column=total_cols - 1, padx=8, pady=6)
