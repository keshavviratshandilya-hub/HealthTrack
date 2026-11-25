"""My Profile view for editing personal health details and changing passwords."""

from typing import Callable

import customtkinter as ctk

from config.theme import COLORS, FONTS, LAYOUT
from services.auth_service import AuthService
from services.validators import ALLOWED_GENDERS
from ui.components.cards import SectionCard, StatusBanner


class ProfileView(ctk.CTkScrollableFrame):
    """Allows the logged-in user to view/edit profile info and change password."""

    def __init__(
        self,
        master,
        user: dict,
        auth_service: AuthService,
        on_user_updated: Callable[[dict], None],
    ):
        super().__init__(
            master,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["navy_light"],
        )
        self.user = user
        self.auth_service = auth_service
        self.on_user_updated = on_user_updated

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure((0, 1), weight=1, uniform="prof")

        # -------------------------------------------------------------------
        # Left Card: Profile Information & Targets
        # -------------------------------------------------------------------
        profile_card = SectionCard(
            self,
            title="Personal Profile",
            subtitle="Height is used automatically to compute your BMI.",
        )
        profile_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.profile_status = StatusBanner(profile_card.body)

        # Read-only account summary pill
        meta_box = ctk.CTkFrame(
            profile_card.body,
            fg_color=COLORS["bg_input"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        meta_box.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            meta_box,
            text=f"Username: @{self.user['username']}   |   Email: {self.user['email']}",
            font=FONTS["small_bold"],
            text_color=COLORS["navy_primary"],
        ).pack(anchor="w", padx=12, pady=10)

        self.full_name_entry = self._add_labeled_entry(
            profile_card.body, "Full Name *", self.user.get("full_name") or ""
        )

        # Age & Gender row
        row_ag = ctk.CTkFrame(profile_card.body, fg_color="transparent")
        row_ag.pack(fill="x", pady=(0, 10))
        row_ag.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(row_ag, text="Age", font=FONTS["small_bold"], text_color=COLORS["text_primary"]).grid(row=0, column=0, sticky="w", padx=(0, 6))
        ctk.CTkLabel(row_ag, text="Gender", font=FONTS["small_bold"], text_color=COLORS["text_primary"]).grid(row=0, column=1, sticky="w", padx=(6, 0))

        self.age_entry = ctk.CTkEntry(
            row_ag,
            placeholder_text="e.g. 22",
            height=38,
            corner_radius=LAYOUT["input_radius"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
        )
        if self.user.get("age") is not None:
            self.age_entry.insert(0, str(self.user["age"]))
        self.age_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(4, 0))

        self.gender_menu = ctk.CTkOptionMenu(
            row_ag,
            values=["", *ALLOWED_GENDERS],
            height=38,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["navy_primary"],
            button_hover_color=COLORS["navy_light"],
            text_color=COLORS["text_primary"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_text_color=COLORS["text_primary"],
        )
        self.gender_menu.set(self.user.get("gender") or "")
        self.gender_menu.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))

        # Height & Target Weight row
        row_hw = ctk.CTkFrame(profile_card.body, fg_color="transparent")
        row_hw.pack(fill="x", pady=(0, 16))
        row_hw.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(row_hw, text="Height (cm)", font=FONTS["small_bold"], text_color=COLORS["text_primary"]).grid(row=0, column=0, sticky="w", padx=(0, 6))
        ctk.CTkLabel(row_hw, text="Target Weight (kg)", font=FONTS["small_bold"], text_color=COLORS["text_primary"]).grid(row=0, column=1, sticky="w", padx=(6, 0))

        self.height_entry = ctk.CTkEntry(
            row_hw,
            placeholder_text="e.g. 172.5",
            height=38,
            corner_radius=LAYOUT["input_radius"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
        )
        if self.user.get("height_cm") is not None:
            self.height_entry.insert(0, str(self.user["height_cm"]))
        self.height_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(4, 0))

        self.target_weight_entry = ctk.CTkEntry(
            row_hw,
            placeholder_text="e.g. 68.0",
            height=38,
            corner_radius=LAYOUT["input_radius"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
        )
        if self.user.get("target_weight_kg") is not None:
            self.target_weight_entry.insert(0, str(self.user["target_weight_kg"]))
        self.target_weight_entry.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))

        self.save_profile_btn = ctk.CTkButton(
            profile_card.body,
            text="Save Profile Changes",
            command=self.save_profile,
            height=42,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["teal_primary"],
            hover_color=COLORS["teal_hover"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["body_bold"],
        )
        self.save_profile_btn.pack(fill="x", pady=(6, 0))

        # -------------------------------------------------------------------
        # Right Card: Change Password
        # -------------------------------------------------------------------
        security_card = SectionCard(
            self,
            title="Account Security",
            subtitle="Change your password using PBKDF2-HMAC-SHA256 verification.",
        )
        security_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self.password_status = StatusBanner(security_card.body)

        self.current_pass_entry = self._add_labeled_entry(
            security_card.body, "Current Password *", "", show="*"
        )
        self.new_pass_entry = self._add_labeled_entry(
            security_card.body, "New Password *", "", show="*",
            placeholder="Min 6 chars, at least 1 letter & 1 number"
        )
        self.confirm_pass_entry = self._add_labeled_entry(
            security_card.body, "Confirm New Password *", "", show="*"
        )

        self.change_password_btn = ctk.CTkButton(
            security_card.body,
            text="Update Password",
            command=self.update_password,
            height=42,
            corner_radius=LAYOUT["button_radius"],
            fg_color=COLORS["navy_primary"],
            hover_color=COLORS["navy_light"],
            text_color=COLORS["text_on_dark"],
            font=FONTS["body_bold"],
        )
        self.change_password_btn.pack(fill="x", pady=(12, 0))

    def _add_labeled_entry(
        self, parent, label: str, initial_value: str, show: str = "", placeholder: str = ""
    ) -> ctk.CTkEntry:
        ctk.CTkLabel(
            parent,
            text=label,
            font=FONTS["small_bold"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 4))

        entry = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            show=show,
            height=38,
            corner_radius=LAYOUT["input_radius"],
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
        )
        if initial_value:
            entry.insert(0, initial_value)
        entry.pack(fill="x", pady=(0, 12))
        return entry

    def save_profile(self) -> None:
        """Validate and persist profile changes via AuthService.update_profile."""
        result = self.auth_service.update_profile(
            user_id=self.user["id"],
            full_name=self.full_name_entry.get(),
            age=self.age_entry.get(),
            gender=self.gender_menu.get(),
            height_cm=self.height_entry.get(),
            target_weight_kg=self.target_weight_entry.get(),
        )
        if not result.success:
            self.profile_status.show(result.message, is_success=False)
            return

        self.user = result.user
        self.on_user_updated(result.user)
        self.profile_status.show(result.message, is_success=True)

    def update_password(self) -> None:
        """Validate and update the user's password via AuthService.change_password."""
        result = self.auth_service.change_password(
            user_id=self.user["id"],
            current_password=self.current_pass_entry.get(),
            new_password=self.new_pass_entry.get(),
            confirm_password=self.confirm_pass_entry.get(),
        )
        if not result.success:
            self.password_status.show(result.message, is_success=False)
            return

        for entry in (self.current_pass_entry, self.new_pass_entry, self.confirm_pass_entry):
            entry.delete(0, "end")
        self.password_status.show(result.message, is_success=True)
