"""Main CustomTkinter application window and sidebar navigation shell."""

from pathlib import Path
from typing import Optional

import customtkinter as ctk

from config.theme import COLORS, FONTS, LAYOUT, apply_ctk_appearance
from database.db_manager import DEFAULT_DB_PATH, DatabaseManager
from services.auth_service import AuthService
from services.export_service import ExportService
from services.health_service import HealthService
from ui.views.dashboard_view import DashboardView
from ui.views.history_view import HistoryView
from ui.views.login_view import AuthView
from ui.views.profile_view import ProfileView
from ui.views.reports_view import ReportsView
from ui.views.tracking_view import METRIC_CONFIGS, TrackingView

# Ordered list of sidebar navigation items: (page_key, display_label, subtitle)
NAV_ITEMS = [
    ("dashboard", "Dashboard", "Your personal health overview at a glance"),
    ("profile", "My Profile", "Manage your personal details, height, and goals"),
    ("weight", "Weight & BMI", "Log body weight and monitor your BMI category"),
    ("blood_pressure", "Blood Pressure", "Track systolic and diastolic readings"),
    ("heart_rate", "Heart Rate", "Record resting and active beats per minute"),
    ("activity", "Daily Activity", "Track daily steps, active minutes, sleep, and calories"),
    ("history", "Health History", "Browse, filter, and export your stored records"),
    ("reports", "Reports", "Visualize trends with Matplotlib charts and summaries"),
]

NAV_LOOKUP = {key: (label, subtitle) for key, label, subtitle in NAV_ITEMS}


class HealthTrackApp(ctk.CTk):
    """Top-level desktop window coordinating AuthView and the Main Shell."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH, start_maximized: bool = True):
        """Initialize services, configure window styling, and open Login."""
        apply_ctk_appearance(ctk)
        super().__init__()

        self.title("HealthTrack – Personal Health Monitoring System")
        self.geometry(f"{LAYOUT['window_width']}x{LAYOUT['window_height']}")
        self.minsize(LAYOUT["min_width"], LAYOUT["min_height"])
        self.configure(fg_color=COLORS["bg_main"])
        self._start_maximized = start_maximized

        # Shared backend services
        self.db_manager = DatabaseManager(db_path)
        self.auth_service = AuthService(self.db_manager)
        self.health_service = HealthService(self.db_manager)
        self.export_service = ExportService(self.health_service)

        # Active session state
        self.current_user: Optional[dict] = None
        self.active_page: str = "dashboard"
        self.nav_buttons: dict[str, ctk.CTkButton] = {}

        # Container references for clean teardown when switching Auth <-> Shell
        self.auth_view: Optional[AuthView] = None
        self.shell_frame: Optional[ctk.CTkFrame] = None
        self.content_area: Optional[ctk.CTkFrame] = None
        self.header_title_label: Optional[ctk.CTkLabel] = None
        self.header_subtitle_label: Optional[ctk.CTkLabel] = None
        self.header_user_label: Optional[ctk.CTkLabel] = None
        self.logout_button: Optional[ctk.CTkButton] = None

        self.sidebar_name_label: Optional[ctk.CTkLabel] = None
        self.current_page_view: Optional[ctk.CTkBaseClass] = None

        self._maximize_after_id: Optional[str] = None
        self.show_auth_screen()
        if self._start_maximized:
            self._maximize_after_id = self.after(20, self._maximize_if_visible)

    def _maximize_if_visible(self) -> None:
        """Maximize the window on launch without disturbing withdrawn test windows."""
        self._maximize_after_id = None
        try:
            if self.state() != "withdrawn":
                self.state("zoomed")
        except Exception:
            pass

    def destroy(self) -> None:
        """Cancel pending startup maximize callback before destroying the window."""
        if self._maximize_after_id is not None:
            try:
                self.after_cancel(self._maximize_after_id)
            except Exception:
                pass
            self._maximize_after_id = None
        super().destroy()

    # -----------------------------------------------------------------------
    # Screen State Transitions (Auth <-> Main Application Shell)
    # -----------------------------------------------------------------------

    def show_auth_screen(self, notice: str = "") -> None:
        """Display the Login/Registration screen and clear any active shell."""
        if self.shell_frame is not None:
            self.shell_frame.destroy()
            self.shell_frame = None
        self.nav_buttons.clear()

        if self.auth_view is not None:
            self.auth_view.destroy()

        self.auth_view = AuthView(
            self,
            auth_service=self.auth_service,
            on_login_success=self.on_login_success,
            initial_notice=notice,
        )
        self.auth_view.pack(fill="both", expand=True)

    def on_login_success(self, user: dict) -> None:
        """Store the logged-in user and launch the main dashboard shell."""
        self.current_user = user
        if self.auth_view is not None:
            self.auth_view.destroy()
            self.auth_view = None

        self._build_main_shell()
        self.navigate_to("dashboard")

    def logout(self) -> None:
        """Clear session state and return the user to the login screen."""
        self.current_user = None
        self.active_page = "dashboard"
        self.show_auth_screen(notice="You have been signed out.")

    # -----------------------------------------------------------------------
    # Main Application Shell (Fixed Navy Sidebar + Top Header + Content)
    # -----------------------------------------------------------------------

    def _build_main_shell(self) -> None:
        """Construct the sidebar, header bar, and content container."""
        self.shell_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_main"], corner_radius=0)
        self.shell_frame.pack(fill="both", expand=True)
        self.shell_frame.grid_rowconfigure(0, weight=1)
        self.shell_frame.grid_columnconfigure(1, weight=1)

        # 1. Fixed Navy Blue Sidebar
        sidebar = ctk.CTkFrame(
            self.shell_frame,
            fg_color=COLORS["navy_primary"],
            width=LAYOUT["sidebar_width"],
            corner_radius=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        brand_box = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand_box.pack(fill="x", padx=20, pady=(24, 16))

        ctk.CTkLabel(
            brand_box,
            text="HealthTrack",
            font=FONTS["app_brand"],
            text_color=COLORS["text_on_dark"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            brand_box,
            text="Personal Health Monitor",
            font=FONTS["small"],
            text_color=COLORS["teal_border"],
        ).pack(anchor="w", pady=(2, 0))

        # Divider
        ctk.CTkFrame(sidebar, fg_color=COLORS["navy_light"], height=1).pack(
            fill="x", padx=18, pady=(0, 14)
        )

        # Navigation Buttons
        nav_container = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_container.pack(fill="both", expand=True, padx=12)

        for key, label, _subtitle in NAV_ITEMS:
            btn = ctk.CTkButton(
                nav_container,
                text=f"  {label}",
                anchor="w",
                height=40,
                corner_radius=8,
                font=FONTS["body_bold"],
                fg_color="transparent",
                hover_color=COLORS["navy_light"],
                text_color=COLORS["text_muted_light"],
                command=lambda target=key: self.navigate_to(target),
            )
            btn.pack(fill="x", pady=3)
            self.nav_buttons[key] = btn

        # Signed-in User Badge at bottom of sidebar
        user_badge = ctk.CTkFrame(
            sidebar,
            fg_color=COLORS["navy_dark"],
            corner_radius=10,
        )
        user_badge.pack(side="bottom", fill="x", padx=14, pady=18)

        full_name = self.current_user["full_name"] if self.current_user else ""
        username = self.current_user["username"] if self.current_user else ""
        self.sidebar_name_label = ctk.CTkLabel(
            user_badge,
            text=full_name,
            font=FONTS["body_bold"],
            text_color=COLORS["text_on_dark"],
            anchor="w",
        )
        self.sidebar_name_label.pack(fill="x", padx=12, pady=(10, 0))
        ctk.CTkLabel(
            user_badge,
            text=f"@{username}",
            font=FONTS["small"],
            text_color=COLORS["teal_border"],
            anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 10))

        # 2. Right Panel (Top Header + Main Content Area)
        right_panel = ctk.CTkFrame(self.shell_frame, fg_color=COLORS["bg_main"], corner_radius=0)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        # Clean White Top Header
        header = ctk.CTkFrame(
            right_panel,
            fg_color=COLORS["bg_card"],
            height=60,
            corner_radius=0,
            border_width=1,
            border_color=COLORS["border"],
        )
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side="left", padx=20, pady=8)

        self.header_title_label = ctk.CTkLabel(
            title_col,
            text="Dashboard",
            font=FONTS["title"],
            text_color=COLORS["navy_primary"],
        )
        self.header_title_label.pack(anchor="w")

        self.header_subtitle_label = ctk.CTkLabel(
            title_col,
            text="",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        )
        self.header_subtitle_label.pack(anchor="w")

        # Right Header Controls: User greeting & Logout button
        controls_col = ctk.CTkFrame(header, fg_color="transparent")
        controls_col.pack(side="right", padx=24)

        self.header_user_label = ctk.CTkLabel(
            controls_col,
            text=f"Signed in as {full_name}",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        )
        self.header_user_label.pack(side="left", padx=(0, 14))

        self.logout_button = ctk.CTkButton(
            controls_col,
            text="Logout",
            command=self.logout,
            width=96,
            height=36,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["navy_primary"],
            hover_color=COLORS["navy_light"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["body_bold"],
        )
        self.logout_button.pack(side="left")

        # Main Page Content Container
        self.content_area = ctk.CTkFrame(right_panel, fg_color=COLORS["bg_main"], corner_radius=0)
        self.content_area.grid(row=1, column=0, sticky="nsew", padx=18, pady=14)

    def navigate_to(self, page_key: str) -> None:
        """Switch the active content page and update sidebar highlighting."""
        if page_key not in NAV_LOOKUP or self.content_area is None:
            return

        self.active_page = page_key
        page_title, page_subtitle = NAV_LOOKUP[page_key]

        # Update top header text
        if self.header_title_label is not None:
            self.header_title_label.configure(text=page_title)
        if self.header_subtitle_label is not None:
            self.header_subtitle_label.configure(text=page_subtitle)

        # Highlight active sidebar button in Teal, reset others
        for key, btn in self.nav_buttons.items():
            if key == page_key:
                btn.configure(
                    fg_color=COLORS["teal_primary"],
                    hover_color=COLORS["teal_hover"],
                    text_color=COLORS["text_on_dark"],
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    hover_color=COLORS["navy_light"],
                    text_color=COLORS["text_muted_light"],
                )

        # Render the requested view inside content_area
        for child in self.content_area.winfo_children():
            child.destroy()

        view = self._create_page_view(page_key, page_title, page_subtitle)
        self.current_page_view = view
        view.pack(fill="both", expand=True)

    def on_user_updated(self, updated_user: dict) -> None:
        """Refresh active user metadata in sidebar and header after profile edits."""
        self.current_user = updated_user
        full_name = updated_user.get("full_name", "")
        if self.sidebar_name_label is not None:
            self.sidebar_name_label.configure(text=full_name)
        if self.header_user_label is not None:
            self.header_user_label.configure(text=f"Signed in as {full_name}")

    def _create_page_view(self, page_key: str, title: str, subtitle: str) -> ctk.CTkFrame:
        """Create and return the live view frame for the requested navigation key."""
        if page_key == "dashboard":
            return DashboardView(
                self.content_area,
                user=self.current_user,
                health_service=self.health_service,
                on_navigate=self.navigate_to,
            )
        if page_key == "profile":
            return ProfileView(
                self.content_area,
                user=self.current_user,
                auth_service=self.auth_service,
                on_user_updated=self.on_user_updated,
            )
        if page_key in METRIC_CONFIGS:
            return TrackingView(
                self.content_area,
                user=self.current_user,
                health_service=self.health_service,
                metric_type=page_key,
            )
        if page_key == "history":
            return HistoryView(
                self.content_area,
                user=self.current_user,
                health_service=self.health_service,
                export_service=self.export_service,
            )
        if page_key == "reports":
            return ReportsView(
                self.content_area,
                user=self.current_user,
                health_service=self.health_service,
                export_service=self.export_service,
            )

        # Fallback frame if an unknown key is requested
        card = ctk.CTkFrame(
            self.content_area,
            fg_color=COLORS["bg_card"],
            corner_radius=LAYOUT["card_radius"],
            border_width=1,
            border_color=COLORS["border"],
        )
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=28, pady=28)

        ctk.CTkLabel(
            inner,
            text=title,
            font=FONTS["subtitle"],
            text_color=COLORS["navy_primary"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            inner,
            text=subtitle,
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(6, 14))

        ctk.CTkLabel(
            inner,
            text=f"Active section key: {page_key}",
            font=FONTS["small_bold"],
            text_color=COLORS["teal_primary"],
            fg_color=COLORS["teal_soft"],
            corner_radius=6,
            padx=12,
            pady=6,
        ).pack(anchor="w")

        return card
