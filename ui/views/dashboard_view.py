"""Dashboard view displaying health KPI summary cards, quick trends, and profile snapshot."""

from datetime import date
from typing import Callable

import customtkinter as ctk

from config.theme import COLORS, FONTS, LAYOUT
from services.health_service import HealthService
from ui.components.cards import SectionCard, StatCard, badge_colors_for_status
from ui.components.charts import build_dashboard_overview_figure, embed_figure


class DashboardView(ctk.CTkScrollableFrame):
    """Compact, responsive Dashboard with 5 KPI cards, trends chart, and snapshot."""

    def __init__(
        self,
        master,
        user: dict,
        health_service: HealthService,
        on_navigate: Callable[[str], None],
    ):
        super().__init__(
            master,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["navy_light"],
        )
        self.user = user
        self.health_service = health_service
        self.on_navigate = on_navigate
        self.kpi_cards: dict[str, StatCard] = {}
        self._ordered_kpi_keys = ["weight", "bmi", "blood_pressure", "heart_rate", "activity"]
        self._layout_mode: str = ""

        self._build_ui()
        self._apply_responsive_layout(width=1120)
        self.bind("<Configure>", self._on_resize)

    def _build_ui(self) -> None:
        user_id = self.user["id"]
        overview = self.health_service.get_dashboard_overview(user_id).data
        profile = overview.get("user", self.user)
        weight_sum = overview.get("weight", {"count": 0})
        bp_sum = overview.get("blood_pressure", {"count": 0})
        hr_sum = overview.get("heart_rate", {"count": 0})
        act_sum = overview.get("activity", {"count": 0})

        today_str = date.today().isoformat()
        today_act_res = self.health_service.get_records(
            user_id, "activity", start_date=today_str, end_date=today_str
        )
        today_records = today_act_res.data if today_act_res.success else []

        # -------------------------------------------------------------------
        # 1. Compact Welcome & Quick-Log Action Bar
        # -------------------------------------------------------------------
        banner = ctk.CTkFrame(
            self,
            fg_color=COLORS["navy_primary"],
            corner_radius=LAYOUT["card_radius"],
        )
        banner.pack(fill="x", pady=(0, 10))

        banner_inner = ctk.CTkFrame(banner, fg_color="transparent")
        banner_inner.pack(fill="x", padx=18, pady=10)

        left_txt = ctk.CTkFrame(banner_inner, fg_color="transparent")
        left_txt.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            left_txt,
            text=f"Hello, {profile.get('full_name', 'User')}",
            font=FONTS["subtitle"],
            text_color=COLORS["text_on_dark"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            left_txt,
            text=f"Today is {today_str}  •  Personal Health Summary",
            font=FONTS["small"],
            text_color=COLORS["teal_border"],
        ).pack(anchor="w")

        actions = ctk.CTkFrame(banner_inner, fg_color="transparent")
        actions.pack(side="right")

        quick_links = [
            ("+ Weight", "weight"),
            ("+ BP", "blood_pressure"),
            ("+ Heart Rate", "heart_rate"),
            ("+ Activity", "activity"),
        ]
        for label, target in quick_links:
            ctk.CTkButton(
                actions,
                text=label,
                height=30,
                width=92,
                corner_radius=7,
                fg_color=COLORS["teal_primary"],
                hover_color=COLORS["teal_hover"],
                text_color=COLORS["text_on_dark"],
                font=FONTS["small_bold"],
                command=lambda t=target: self.on_navigate(t),
            ).pack(side="left", padx=3)

        # -------------------------------------------------------------------
        # 2. Five Health Summary KPI Cards (Responsive Grid)
        # -------------------------------------------------------------------
        self.kpi_container = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_container.pack(fill="x", pady=(0, 10))

        # Card 1: Latest Weight
        if weight_sum.get("count", 0) > 0:
            w_val = f"{weight_sum['latest_weight']} kg"
            target_w = profile.get("target_weight_kg")
            w_sub = (
                f"Target: {target_w} kg  |  {weight_sum['latest_date']}"
                if target_w
                else f"Logged {weight_sum['latest_date']}"
            )
            w_badge = f"{weight_sum['weight_change']:+.1f} kg" if weight_sum["count"] > 1 else "Latest"
        else:
            w_val = "No data"
            w_sub = "Log your first weight"
            w_badge = ""

        self.kpi_cards["weight"] = StatCard(
            self.kpi_container,
            title="LATEST WEIGHT",
            value=w_val,
            subtitle=w_sub,
            badge_text=w_badge,
            accent_color=COLORS["teal_primary"],
        )

        # Card 2: BMI & Category
        latest_bmi = weight_sum.get("latest_bmi")
        bmi_cat = weight_sum.get("bmi_category", "Unknown")
        if latest_bmi:
            bmi_val = f"{latest_bmi}"
            bmi_sub = f"Height: {profile.get('height_cm')} cm" if profile.get("height_cm") else "From profile height"
            b_fg, b_tc = badge_colors_for_status(bmi_cat)
            bmi_badge = bmi_cat
        else:
            bmi_val = "--"
            bmi_sub = "Set height in Profile"
            b_fg, b_tc = COLORS["teal_soft"], COLORS["teal_primary"]
            bmi_badge = "Pending"

        self.kpi_cards["bmi"] = StatCard(
            self.kpi_container,
            title="BMI & STATUS",
            value=bmi_val,
            subtitle=bmi_sub,
            badge_text=bmi_badge,
            badge_fg=b_fg,
            badge_text_color=b_tc,
            accent_color=COLORS["navy_primary"],
        )

        # Card 3: Latest Blood Pressure
        if bp_sum.get("count", 0) > 0:
            bp_val = f"{bp_sum['latest_systolic']}/{bp_sum['latest_diastolic']}"
            bp_cat = bp_sum["latest_category"]
            bp_sub = f"mmHg  |  {bp_sum['latest_date']}"
            bp_fg, bp_tc = badge_colors_for_status(bp_cat)
        else:
            bp_val = "No data"
            bp_cat = ""
            bp_sub = "Log systolic / diastolic"
            bp_fg, bp_tc = COLORS["teal_soft"], COLORS["teal_primary"]

        self.kpi_cards["blood_pressure"] = StatCard(
            self.kpi_container,
            title="BLOOD PRESSURE",
            value=bp_val,
            subtitle=bp_sub,
            badge_text=bp_cat,
            badge_fg=bp_fg,
            badge_text_color=bp_tc,
            accent_color=COLORS["teal_primary"],
        )

        # Card 4: Latest Heart Rate
        if hr_sum.get("count", 0) > 0:
            hr_val = f"{hr_sum['latest_bpm']} bpm"
            hr_sub = f"Avg: {hr_sum['avg_bpm']}  |  {hr_sum['min_bpm']}-{hr_sum['max_bpm']} bpm"
            hr_badge = hr_sum["latest_date"]
        else:
            hr_val = "No data"
            hr_sub = "Log heart rate (bpm)"
            hr_badge = ""

        self.kpi_cards["heart_rate"] = StatCard(
            self.kpi_container,
            title="HEART RATE",
            value=hr_val,
            subtitle=hr_sub,
            badge_text=hr_badge,
            accent_color=COLORS["navy_primary"],
        )

        # Card 5: Today's Activity
        if today_records:
            today_steps = sum(r["steps"] for r in today_records)
            today_cal = sum(r["calories_burned"] for r in today_records)
            today_sleep = today_records[0]["sleep_hours"]
            today_mins = sum(r["active_minutes"] for r in today_records)
            act_val = f"{today_steps:,} steps"
            act_sub = f"{today_mins}m  |  {today_sleep}h sleep  |  {today_cal:,} kcal"
            act_badge = "Today"
        else:
            act_val = "0 steps"
            if act_sum.get("count", 0) > 0:
                act_sub = f"Last: {act_sum['latest_steps']:,} steps ({act_sum['latest_date']})"
            else:
                act_sub = "No activity logged today"
            act_badge = "Today"

        self.kpi_cards["activity"] = StatCard(
            self.kpi_container,
            title="TODAY'S ACTIVITY",
            value=act_val,
            subtitle=act_sub,
            badge_text=act_badge,
            accent_color=COLORS["teal_primary"],
        )

        # -------------------------------------------------------------------
        # 3. Lower Overview: Compact Historical Trends + Profile Snapshot
        # -------------------------------------------------------------------
        self.lower_container = ctk.CTkFrame(self, fg_color="transparent")
        self.lower_container.pack(fill="both", expand=True)

        self.chart_card = SectionCard(
            self.lower_container,
            title="Recent Health Trends",
            subtitle="Last 10 recorded Weight and Heart Rate entries",
        )
        w_df = self.health_service.get_records_df(user_id, "weight").data
        hr_df = self.health_service.get_records_df(user_id, "heart_rate").data
        fig = build_dashboard_overview_figure(w_df, hr_df)
        embed_figure(self.chart_card.body, fig)

        self.snapshot_card = SectionCard(
            self.lower_container,
            title="Profile & Totals",
            subtitle="Local SQLite summary",
        )

        total_entries = (
            weight_sum.get("count", 0)
            + bp_sum.get("count", 0)
            + hr_sum.get("count", 0)
            + act_sum.get("count", 0)
        )
        summary_rows = [
            ("Height", f"{profile['height_cm']} cm" if profile.get("height_cm") else "Not set"),
            (
                "Target Weight",
                f"{profile['target_weight_kg']} kg" if profile.get("target_weight_kg") else "Not set",
            ),
            ("Weight Logs", str(weight_sum.get("count", 0))),
            ("BP Readings", str(bp_sum.get("count", 0))),
            ("Heart Rate Logs", str(hr_sum.get("count", 0))),
            ("Activity Logs", str(act_sum.get("count", 0))),
            ("Total Records", str(total_entries)),
        ]
        for label, val in summary_rows:
            r = ctk.CTkFrame(self.snapshot_card.body, fg_color="transparent")
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=label, font=FONTS["small"], text_color=COLORS["text_secondary"]).pack(side="left")
            ctk.CTkLabel(r, text=val, font=FONTS["small_bold"], text_color=COLORS["navy_primary"]).pack(side="right")

        ctk.CTkButton(
            self.snapshot_card.body,
            text="Update Profile & Height",
            height=34,
            corner_radius=8,
            fg_color=COLORS["navy_primary"],
            hover_color=COLORS["navy_light"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["small_bold"],
            command=lambda: self.on_navigate("profile"),
        ).pack(side="bottom", fill="x", pady=(10, 0))

    # -----------------------------------------------------------------------
    # Responsive Grid Reflow
    # -----------------------------------------------------------------------

    def _on_resize(self, event) -> None:
        if event.width > 100:
            self._apply_responsive_layout(event.width)

    def _apply_responsive_layout(self, width: int) -> None:
        """Reflow KPI cards and lower panels cleanly based on available width."""
        if width >= 920:
            mode = "wide"
        elif width >= 640:
            mode = "medium"
        else:
            mode = "narrow"

        if mode == self._layout_mode:
            return
        self._layout_mode = mode

        for col in range(5):
            self.kpi_container.grid_columnconfigure(col, weight=0, uniform="")
        for card in self.kpi_cards.values():
            card.grid_forget()

        if mode == "wide":
            for col in range(5):
                self.kpi_container.grid_columnconfigure(col, weight=1, uniform="kpi")
            for idx, key in enumerate(self._ordered_kpi_keys):
                pad = (0, 5) if idx == 0 else ((5, 0) if idx == 4 else 5)
                self.kpi_cards[key].grid(row=0, column=idx, sticky="nsew", padx=pad)
        elif mode == "medium":
            for col in range(3):
                self.kpi_container.grid_columnconfigure(col, weight=1, uniform="kpi")
            for idx, key in enumerate(self._ordered_kpi_keys):
                r, c = divmod(idx, 3)
                self.kpi_cards[key].grid(row=r, column=c, sticky="nsew", padx=4, pady=4)
        else:
            for col in range(2):
                self.kpi_container.grid_columnconfigure(col, weight=1, uniform="kpi")
            for idx, key in enumerate(self._ordered_kpi_keys):
                r, c = divmod(idx, 2)
                self.kpi_cards[key].grid(row=r, column=c, sticky="nsew", padx=4, pady=4)

        self.lower_container.grid_columnconfigure(0, weight=0, uniform="")
        self.lower_container.grid_columnconfigure(1, weight=0, uniform="")
        self.chart_card.grid_forget()
        self.snapshot_card.grid_forget()

        if mode in ("wide", "medium"):
            self.lower_container.grid_columnconfigure(0, weight=3)
            self.lower_container.grid_columnconfigure(1, weight=1)
            self.lower_container.grid_rowconfigure(0, weight=1)
            self.chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            self.snapshot_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        else:
            self.lower_container.grid_columnconfigure(0, weight=1)
            self.chart_card.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
            self.snapshot_card.grid(row=1, column=0, sticky="nsew")
