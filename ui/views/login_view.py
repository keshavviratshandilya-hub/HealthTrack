"""Login and Registration views for HealthTrack.

Provides a clean split-panel light-theme authentication screen
connected to AuthService, with clear inline validation messages.
"""

from typing import Callable

import customtkinter as ctk

from config.theme import COLORS, FONTS, LAYOUT
from services.auth_service import AuthService
from services.validators import ALLOWED_GENDERS


class AuthView(ctk.CTkFrame):
    """Container screen that switches cleanly between Login and Registration."""

    def __init__(
        self,
        master,
        auth_service: AuthService,
        on_login_success: Callable[[dict], None],
        initial_notice: str = "",
    ):
        """Initialize the authentication container with Login and Register panels."""
        super().__init__(master, fg_color=COLORS["bg_main"], corner_radius=0)
        self.auth_service = auth_service
        self.on_login_success = on_login_success

        # Center card layout with two columns: Navy branding panel + White form panel
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.card = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
            width=860,
            height=560,
        )
        self.card.grid(row=0, column=0, padx=20, pady=20)
        self.card.grid_propagate(False)
        self.card.grid_rowconfigure(0, weight=1)
        self.card.grid_columnconfigure(0, weight=2)
        self.card.grid_columnconfigure(1, weight=3)

        self._build_brand_panel()

        self.form_host = ctk.CTkFrame(self.card, fg_color=COLORS["bg_card"], corner_radius=0)
        self.form_host.grid(row=0, column=1, sticky="nsew", padx=28, pady=24)
        self.form_host.grid_rowconfigure(0, weight=1)
        self.form_host.grid_columnconfigure(0, weight=1)

        self.login_frame = LoginFrame(
            self.form_host,
            auth_service=self.auth_service,
            on_login_success=self.on_login_success,
            on_switch_to_register=self.show_register,
        )
        self.register_frame = RegisterFrame(
            self.form_host,
            auth_service=self.auth_service,
            on_register_success=self._handle_register_success,
            on_switch_to_login=self.show_login,
        )

        self.active_mode = "login"
        self.show_login(notice=initial_notice, is_success=True if initial_notice else False)

    def _build_brand_panel(self) -> None:
        """Build the left Navy Blue branding & project overview panel."""
        brand_panel = ctk.CTkFrame(
            self.card,
            fg_color=COLORS["navy_primary"],
            corner_radius=14,
        )
        brand_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)

        inner = ctk.CTkFrame(brand_panel, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=28, pady=36)

        badge = ctk.CTkLabel(
            inner,
            text="CSM216 PROJECT",
            font=FONTS["small_bold"],
            text_color=COLORS["navy_primary"],
            fg_color=COLORS["teal_soft"],
            corner_radius=6,
            padx=10,
            pady=4,
        )
        badge.pack(anchor="w", pady=(0, 18))

        ctk.CTkLabel(
            inner,
            text="HealthTrack",
            font=(FONTS["title"][0], 30, "bold"),
            text_color=COLORS["text_on_dark"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            inner,
            text="Personal Health Monitoring System",
            font=FONTS["body_bold"],
            text_color=COLORS["teal_border"],
        ).pack(anchor="w", pady=(4, 24))

        highlights = [
            "Track Weight & automatic BMI",
            "Monitor Blood Pressure & Heart Rate",
            "Log Daily Steps, Sleep & Calories",
            "Explore Visual Reports & History",
            "Export Clean CSV & PDF Summaries",
        ]
        for item in highlights:
            ctk.CTkLabel(
                inner,
                text=f"  •  {item}",
                font=FONTS["body"],
                text_color=COLORS["text_muted_light"],
                anchor="w",
            ).pack(fill="x", pady=5)

        ctk.CTkLabel(
            inner,
            text="Private local SQLite storage.\nYour records stay on your device.",
            font=FONTS["small"],
            text_color=COLORS["text_muted_light"],
            justify="left",
        ).pack(side="bottom", anchor="w")

    def show_login(
        self,
        prefill_identifier: str = "",
        notice: str = "",
        is_success: bool = False,
    ) -> None:
        """Display the Login form."""
        self.active_mode = "login"
        self.register_frame.grid_forget()
        self.login_frame.grid(row=0, column=0, sticky="nsew")
        if prefill_identifier:
            self.login_frame.set_identifier(prefill_identifier)
        if notice:
            self.login_frame.set_status(notice, is_success=is_success)
        else:
            self.login_frame.clear_status()

    def show_register(self) -> None:
        """Display the Registration form."""
        self.active_mode = "register"
        self.login_frame.grid_forget()
        self.register_frame.clear_status()
        self.register_frame.grid(row=0, column=0, sticky="nsew")

    def _handle_register_success(self, username: str) -> None:
        """After registration, switch to Login with username filled and a success note."""
        self.register_frame.clear_fields()
        self.show_login(
            prefill_identifier=username,
            notice="Account created successfully! Please sign in.",
            is_success=True,
        )


class LoginFrame(ctk.CTkFrame):
    """Login form connected to AuthService.login_user."""

    def __init__(
        self,
        master,
        auth_service: AuthService,
        on_login_success: Callable[[dict], None],
        on_switch_to_register: Callable[[], None],
    ):
        super().__init__(master, fg_color="transparent")
        self.auth_service = auth_service
        self.on_login_success = on_login_success
        self.on_switch_to_register = on_switch_to_register

        self._build_ui()

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self,
            text="Welcome Back",
            font=FONTS["title"],
            text_color=COLORS["navy_primary"],
        ).pack(anchor="w", pady=(12, 4))

        ctk.CTkLabel(
            self,
            text="Sign in with your username or email to access your health dashboard.",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(0, 20))

        # Status banner slot (collapses cleanly when empty)
        self.status_slot = ctk.CTkFrame(self, fg_color="transparent", height=0)
        self.status_slot.pack(fill="x")
        self.status_label = ctk.CTkLabel(
            self.status_slot,
            text="",
            font=FONTS["small_bold"],
            corner_radius=8,
            padx=12,
            pady=8,
            wraplength=410,
            justify="left",
        )

        ctk.CTkLabel(
            self,
            text="Username or Email",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(6, 4))

        self.identifier_entry = ctk.CTkEntry(
            self,
            placeholder_text="e.g. alex_fit or alex@example.com",
            height=42,
            corner_radius=LAYOUT["input_radius"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=FONTS["body"],
        )
        self.identifier_entry.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            self,
            text="Password",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 4))

        self.password_entry = ctk.CTkEntry(
            self,
            placeholder_text="Enter your password",
            show="*",
            height=42,
            corner_radius=LAYOUT["input_radius"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=FONTS["body"],
        )
        self.password_entry.pack(fill="x", pady=(0, 8))
        self.password_entry.bind("<Return>", lambda _event: self.submit_login())

        self.show_password_var = ctk.BooleanVar(value=False)
        self.show_pass_check = ctk.CTkCheckBox(
            self,
            text="Show password",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["teal_primary"],
            hover_color=COLORS["teal_hover"],
        )
        self.show_pass_check.pack(anchor="w", pady=(0, 20))

        self.login_button = ctk.CTkButton(
            self,
            text="Sign In",
            command=self.submit_login,
            height=44,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["teal_primary"],
            hover_color=COLORS["teal_hover"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["body_bold"],
        )
        self.login_button.pack(fill="x", pady=(0, 16))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", pady=(4, 0))

        ctk.CTkLabel(
            footer,
            text="Don't have an account yet?",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self.switch_register_btn = ctk.CTkButton(
            footer,
            text="Create Account",
            command=self.on_switch_to_register,
            fg_color="transparent",
            hover_color=COLORS["teal_soft"],
            text_color=COLORS["teal_primary"],
            font=FONTS["body_bold"],
            width=120,
            height=30,
        )
        self.switch_register_btn.pack(side="left", padx=(6, 0))

    def _toggle_password_visibility(self) -> None:
        self.password_entry.configure(show="" if self.show_password_var.get() else "*")

    def set_identifier(self, value: str) -> None:
        self.identifier_entry.delete(0, "end")
        self.identifier_entry.insert(0, value)
        self.password_entry.delete(0, "end")

    def set_status(self, message: str, is_success: bool = False) -> None:
        fg = COLORS["success_bg"] if is_success else COLORS["danger_bg"]
        tc = COLORS["success"] if is_success else COLORS["danger"]
        self.status_label.configure(text=message, fg_color=fg, text_color=tc)
        if not self.status_label.winfo_manager():
            self.status_label.pack(fill="x", pady=(0, 12))

    def clear_status(self) -> None:
        self.status_label.pack_forget()
        self.status_label.configure(text="")
        self.status_slot.configure(height=0)

    def submit_login(self) -> None:
        """Validate inputs and authenticate using AuthService."""
        identifier = self.identifier_entry.get().strip()
        password = self.password_entry.get()

        result = self.auth_service.login_user(identifier, password)
        if not result.success:
            self.set_status(result.message, is_success=False)
            return

        self.clear_status()
        self.password_entry.delete(0, "end")
        self.on_login_success(result.user)


class RegisterFrame(ctk.CTkFrame):
    """Registration form connected to AuthService.register_user."""

    def __init__(
        self,
        master,
        auth_service: AuthService,
        on_register_success: Callable[[str], None],
        on_switch_to_login: Callable[[], None],
    ):
        super().__init__(master, fg_color="transparent")
        self.auth_service = auth_service
        self.on_register_success = on_register_success
        self.on_switch_to_login = on_switch_to_login

        self._build_ui()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(4, 6))

        ctk.CTkLabel(
            header,
            text="Create Account",
            font=FONTS["title"],
            text_color=COLORS["navy_primary"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Fields marked with * are required.",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w")

        self.status_slot = ctk.CTkFrame(self, fg_color="transparent", height=0)
        self.status_slot.pack(fill="x")
        self.status_label = ctk.CTkLabel(
            self.status_slot,
            text="",
            font=FONTS["small_bold"],
            corner_radius=8,
            padx=12,
            pady=8,
            wraplength=400,
            justify="left",
        )

        # Scrollable container so all registration fields remain accessible
        self.scroll_form = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["navy_light"],
        )
        self.scroll_form.pack(fill="both", expand=True, pady=(4, 8))

        self.full_name_entry = self._add_field("Full Name *", "e.g. Alex Johnson")
        self.username_entry = self._add_field("Username *", "3-30 chars, starts with a letter")
        self.email_entry = self._add_field("Email Address *", "e.g. alex@university.edu")
        self.password_entry = self._add_field("Password *", "Min 6 chars, 1 letter & 1 number", show="*")
        self.confirm_password_entry = self._add_field("Confirm Password *", "Re-enter password", show="*")

        # Optional profile details row
        row_frame = ctk.CTkFrame(self.scroll_form, fg_color="transparent")
        row_frame.pack(fill="x", pady=(4, 8))
        row_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(row_frame, text="Age (optional)", font=FONTS["small_bold"], text_color=COLORS["text_secondary"]).grid(row=0, column=0, sticky="w", padx=(0, 6))
        ctk.CTkLabel(row_frame, text="Gender (optional)", font=FONTS["small_bold"], text_color=COLORS["text_secondary"]).grid(row=0, column=1, sticky="w", padx=6)
        ctk.CTkLabel(row_frame, text="Height cm (optional)", font=FONTS["small_bold"], text_color=COLORS["text_secondary"]).grid(row=0, column=2, sticky="w", padx=(6, 0))

        self.age_entry = ctk.CTkEntry(
            row_frame, placeholder_text="22", height=36,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
        )
        self.age_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(2, 0))

        self.gender_menu = ctk.CTkOptionMenu(
            row_frame,
            values=["", *ALLOWED_GENDERS],
            height=36,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["navy_primary"],
            button_hover_color=COLORS["navy_light"],
            text_color=COLORS["text_primary"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_text_color=COLORS["text_primary"],
        )
        self.gender_menu.set("")
        self.gender_menu.grid(row=1, column=1, sticky="ew", padx=6, pady=(2, 0))

        self.height_entry = ctk.CTkEntry(
            row_frame, placeholder_text="172", height=36,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
        )
        self.height_entry.grid(row=1, column=2, sticky="ew", padx=(6, 0), pady=(2, 0))

        self.register_button = ctk.CTkButton(
            self,
            text="Create Account",
            command=self.submit_registration,
            height=42,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["teal_primary"],
            hover_color=COLORS["teal_hover"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["body_bold"],
        )
        self.register_button.pack(fill="x", pady=(4, 8))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x")

        ctk.CTkLabel(
            footer,
            text="Already have an account?",
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left")

        self.switch_login_btn = ctk.CTkButton(
            footer,
            text="Sign In",
            command=self.on_switch_to_login,
            fg_color="transparent",
            hover_color=COLORS["teal_soft"],
            text_color=COLORS["teal_primary"],
            font=FONTS["body_bold"],
            width=90,
            height=28,
        )
        self.switch_login_btn.pack(side="left", padx=(6, 0))

    def _add_field(self, label: str, placeholder: str, show: str = "") -> ctk.CTkEntry:
        """Helper to build consistent labeled entry rows without duplicate code."""
        ctk.CTkLabel(
            self.scroll_form,
            text=label,
            font=FONTS["small_bold"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(2, 2))

        entry = ctk.CTkEntry(
            self.scroll_form,
            placeholder_text=placeholder,
            show=show,
            height=36,
            corner_radius=LAYOUT["input_radius"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=FONTS["body"],
        )
        entry.pack(fill="x", pady=(0, 8))
        return entry

    def set_status(self, message: str, is_success: bool = False) -> None:
        fg = COLORS["success_bg"] if is_success else COLORS["danger_bg"]
        tc = COLORS["success"] if is_success else COLORS["danger"]
        self.status_label.configure(text=message, fg_color=fg, text_color=tc)
        if not self.status_label.winfo_manager():
            self.status_label.pack(fill="x", pady=(0, 6))

    def clear_status(self) -> None:
        self.status_label.pack_forget()
        self.status_label.configure(text="")
        self.status_slot.configure(height=0)

    def clear_fields(self) -> None:
        for entry in (
            self.full_name_entry,
            self.username_entry,
            self.email_entry,
            self.password_entry,
            self.confirm_password_entry,
            self.age_entry,
            self.height_entry,
        ):
            entry.delete(0, "end")
        self.gender_menu.set("")

    def submit_registration(self) -> None:
        """Validate form values and register the new user via AuthService."""
        result = self.auth_service.register_user(
            username=self.username_entry.get(),
            email=self.email_entry.get(),
            password=self.password_entry.get(),
            confirm_password=self.confirm_password_entry.get(),
            full_name=self.full_name_entry.get(),
            age=self.age_entry.get(),
            gender=self.gender_menu.get(),
            height_cm=self.height_entry.get(),
        )
        if not result.success:
            self.set_status(result.message, is_success=False)
            return

        self.clear_status()
        self.on_register_success(result.user["username"])
