"""Theme configuration for HealthTrack.

Defines the premium light color palette (White, Navy Blue, and Teal),
consistent typography, and layout spacing used across all UI screens
and Matplotlib charts.
"""

# ---------------------------------------------------------------------------
# Color Palette (Premium Light Theme: White, Navy Blue, Teal)
# ---------------------------------------------------------------------------
COLORS = {
    # Surfaces & Backgrounds
    "bg_main": "#F4F7FA",         # Soft off-white main window background
    "bg_card": "#FFFFFF",         # Pure white card / panel background
    "bg_input": "#F8FAFC",        # Subtle cool-white input field background
    "bg_table_alt": "#F1F5F9",    # Alternating table row tint

    # Navy Blue (Structure, Sidebar, Primary Headers)
    "navy_primary": "#0F294A",    # Deep navy blue for sidebar & titles
    "navy_dark": "#091B33",       # Darker navy for active/hover sidebar states
    "navy_light": "#1E3F6B",      # Lighter navy for secondary accents

    # Teal (Primary Actions, Highlights, Health Accents)
    "teal_primary": "#0D9488",    # Signature health teal for primary buttons
    "teal_hover": "#0F766E",      # Darker teal when hovering buttons
    "teal_soft": "#CCFBF1",       # Soft teal tint for pills and active badges
    "teal_border": "#5EEAD4",     # Light teal outline for focused highlights

    # Typography
    "text_primary": "#0F172A",    # Dark slate-navy for main readable text
    "text_secondary": "#475569",  # Muted slate for subtitles and labels
    "text_on_dark": "#FFFFFF",    # Pure white text on navy/teal backgrounds
    "text_muted_light": "#CBD5E1",  # Soft light gray-blue on dark sidebar

    # Borders & Dividers
    "border": "#E2E8F0",          # Subtle card and input border
    "divider": "#E2E8F0",

    # Semantic Status Colors (used for BMI badges, alerts, validation)
    "success": "#16A34A",
    "success_bg": "#DCFCE7",
    "warning": "#D97706",
    "warning_bg": "#FEF3C7",
    "danger": "#DC2626",
    "danger_bg": "#FEE2E2",
    "info": "#0284C7",
    "info_bg": "#E0F2FE",
}

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"

FONTS = {
    "app_brand": (FONT_FAMILY, 20, "bold"),
    "title": (FONT_FAMILY, 24, "bold"),
    "subtitle": (FONT_FAMILY, 16, "bold"),
    "section": (FONT_FAMILY, 14, "bold"),
    "body": (FONT_FAMILY, 13),
    "body_bold": (FONT_FAMILY, 13, "bold"),
    "small": (FONT_FAMILY, 11),
    "small_bold": (FONT_FAMILY, 11, "bold"),
    "kpi_value": (FONT_FAMILY, 22, "bold"),
}

# ---------------------------------------------------------------------------
# Layout & Sizing Constants
# ---------------------------------------------------------------------------
LAYOUT = {
    "window_width": 1280,
    "window_height": 760,
    "min_width": 960,
    "min_height": 640,
    "sidebar_width": 220,
    "card_radius": 12,
    "button_radius": 8,
    "input_radius": 8,
    "pad_outer": 18,
    "pad_card": 14,
}


def apply_ctk_appearance(ctk_module):
    """Configure CustomTkinter to use a clean light appearance."""
    ctk_module.set_appearance_mode("light")
    ctk_module.set_default_color_theme("blue")
