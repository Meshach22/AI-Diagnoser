"""core/styles.py

Minimalist Professional SaaS Design System:
- Red Accent Palette (#C62828 in light mode, #EF4444 in dark mode)
- Samsung-Inspired Typography ("SamsungOne", "Arial", "Helvetica", sans-serif)
- Functional Light / Dark Mode Tokens
- Clean Left Navigation Sidebar + Bottom System Status Card
- High-Performance, Accessible, Fluid Responsive Layouts (Desktop, Tablet, Mobile)
"""

from typing import Union
import streamlit as st


def inject_clean_theme(dark_mode: Union[bool, str] = False) -> None:
    """Inject dynamic executive CSS swapping tokens between minimalist clean SaaS (#F8F9FA)
    and sleek dark mode (#111315) with restrained red accents (#C62828 / #EF4444).
    """
    if isinstance(dark_mode, str):
        is_dark = dark_mode.lower() == "dark"
    else:
        is_dark = bool(dark_mode)

    if is_dark:
        bg_primary = "#111315"
        bg_card = "#1A1D21"
        bg_elevated = "#22262B"
        bg_subtle = "#1E2227"
        text_primary = "#F3F4F6"
        text_secondary = "#A1A1AA"
        border_soft = "#34383F"
        border_subtle = "#282B32"
        border_focus = "#EF4444"
        accent_red = "#EF4444"
        accent_red_hover = "#DC2626"
        accent_red_subtle = "rgba(239, 68, 68, 0.14)"
        shadow_card = "0 1px 3px rgba(0, 0, 0, 0.3), 0 4px 16px rgba(0, 0, 0, 0.25)"
        shadow_hover = "0 2px 8px rgba(0, 0, 0, 0.4), 0 8px 24px rgba(0, 0, 0, 0.35)"
        sidebar_bg = "#1A1D21"
        status_dot = "#10B981"
    else:
        bg_primary = "#F8F9FA"
        bg_card = "#FFFFFF"
        bg_elevated = "#FFFFFF"
        bg_subtle = "#F1F3F5"
        text_primary = "#171717"
        text_secondary = "#666666"
        border_soft = "#E5E7EB"
        border_subtle = "#F3F4F6"
        border_focus = "#C62828"
        accent_red = "#C62828"
        accent_red_hover = "#A61F24"
        accent_red_subtle = "#FFF1F1"
        shadow_card = "0 1px 3px rgba(0, 0, 0, 0.05), 0 4px 12px rgba(0, 0, 0, 0.03)"
        shadow_hover = "0 4px 12px rgba(0, 0, 0, 0.08), 0 8px 24px rgba(0, 0, 0, 0.04)"
        sidebar_bg = "#FFFFFF"
        status_dot = "#10B981"

    font_family = '"SamsungOne", "Arial", "Helvetica", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'

    css = f"""
    <style>
    :root {{
        --bg-primary: {bg_primary};
        --bg-card: {bg_card};
        --bg-elevated: {bg_elevated};
        --bg-subtle: {bg_subtle};
        --text-color: {text_primary};
        --text-primary: {text_primary};
        --text-secondary: {text_secondary};
        --secondary-text-color: {text_secondary};
        --border-soft: {border_soft};
        --border-subtle: {border_subtle};
        --border-focus: {border_focus};
        --accent-red: {accent_red};
        --accent-red-hover: {accent_red_hover};
        --accent-red-subtle: {accent_red_subtle};
        --shadow-card: {shadow_card};
        --shadow-hover: {shadow_hover};
        --sidebar-bg: {sidebar_bg};
        --font-main: {font_family};
    }}

    /* Global Body and Main Layout */
    html, body, .stApp, [data-testid="stAppViewContainer"] {{
        font-family: var(--font-main) !important;
        background-color: var(--bg-primary) !important;
        color: var(--text-color) !important;
        letter-spacing: -0.01em;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        text-rendering: optimizeLegibility;
    }}

    .stApp {{
        transition: background-color 0.2s ease, color 0.2s ease;
    }}

    /* Main Container Centering & Width Guard */
    .block-container {{
        max-width: 1160px !important;
        margin: 0 auto !important;
        padding-top: 1.25rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }}

    /* Header De-cluttering */
    header[data-testid="stHeader"] {{
        background: transparent !important;
        height: 2.75rem !important;
    }}

    /* Hide Native Clutter */
    [data-testid="stHeaderActionElements"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .stMarkdown a.header-anchor {{
        display: none !important;
    }}

    /* -------------------------------------------------------------
       SLIM LEFT SIDEBAR NAVIGATION
    ------------------------------------------------------------- */
    section[data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid var(--border-soft) !important;
        padding: 0 !important;
        box-shadow: none !important;
    }}

    @media (min-width: 769px) {{
        section[data-testid="stSidebar"] {{
            min-width: 250px !important;
            max-width: 260px !important;
        }}
    }}

    section[data-testid="stSidebar"][aria-expanded="false"] {{
        min-width: 0 !important;
        max-width: 0 !important;
    }}

    section[data-testid="stSidebar"] > div:first-child,
    [data-testid="stSidebarContent"] {{
        padding: 0.5rem 0.85rem 1rem 0.85rem !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        height: 100% !important;
    }}

    [data-testid="stSidebarHeader"] {{
        padding: 0 0.5rem !important;
        min-height: 2.2rem !important;
        height: auto !important;
        margin-bottom: 0 !important;
    }}

    [data-testid="stSidebarUserContent"] {{
        padding: 0 !important;
        margin-top: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        flex: 1 1 auto !important;
    }}

    /* Sidebar Navigation Links */
    .sidebar-nav-container {{
        display: flex;
        flex-direction: column;
        gap: 6px;
        margin-top: 4px;
        margin-bottom: 20px;
    }}

    .sidebar-brand {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 2px 10px 14px 10px;
        border-bottom: 1px solid var(--border-soft);
        margin-top: 0;
        margin-bottom: 12px;
    }}

    .sidebar-brand-title {{
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--text-color);
        letter-spacing: -0.02em;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 6px;
    }}

    .sidebar-brand-badge {{
        font-size: 0.72rem;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 9999px;
        background-color: var(--accent-red-subtle);
        color: var(--accent-red);
        border: 1px solid rgba(198, 40, 40, 0.2);
    }}

    /* Native Streamlit Sidebar Radio Styled as Nav Pills */
    [data-testid="stSidebar"] div[data-testid="stRadio"] > div {{
        gap: 6px !important;
    }}

    [data-testid="stSidebar"] div[data-testid="stRadio"] label,
    [data-testid="stSidebar"] [data-testid="stRadioOption"] {{
        padding: 10px 14px !important;
        border-radius: 10px !important;
        font-size: 0.93rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        transition: all 0.15s ease !important;
        cursor: pointer !important;
        border: 1px solid transparent !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
    }}

    /* Suppress native radio button circle so it behaves like a clean nav link */
    [data-testid="stSidebar"] [data-testid="stRadioOption"] .e1dm8mpf4,
    [data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child,
    [data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:not([data-testid="stMarkdownContainer"]),
    [data-testid="stSidebar"] div[data-testid="stRadio"] label > div > div:first-child,
    [data-testid="stSidebar"] div[data-testid="stRadio"] label input[type="radio"],
    [data-testid="stSidebar"] div[data-testid="stRadio"] label [data-testid="stRadioDot"],
    [data-testid="stSidebar"] div[data-testid="stRadio"] label span:first-child:empty {{
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    [data-testid="stSidebar"] div[data-testid="stRadio"] label:hover,
    [data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {{
        background-color: var(--bg-subtle) !important;
        color: var(--text-color) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"],
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-selected="true"],
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-checked="true"],
    [data-testid="stSidebar"] div[data-testid="stRadio"] [aria-checked="true"] {{
        background-color: var(--accent-red-subtle) !important;
        color: var(--accent-red) !important;
        font-weight: 600 !important;
        border: 1px solid rgba(198, 40, 40, 0.22) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p,
    [data-testid="stSidebar"] div[data-testid="stRadio"] label[data-selected="true"] p,
    [data-testid="stSidebar"] div[data-testid="stRadio"] [aria-checked="true"] p {{
        color: var(--accent-red) !important;
        font-weight: 600 !important;
    }}

    /* Mobile Sidebar Toggle Button Touch-friendliness */
    [data-testid="collapsedControl"],
    button[data-testid="stSidebarCollapseButton"] {{
        color: var(--text-color) !important;
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 8px !important;
        top: 0.65rem !important;
        left: 0.65rem !important;
        z-index: 999999 !important;
        min-width: 40px !important;
        min-height: 40px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: border-color 0.15s ease !important;
    }}

    [data-testid="collapsedControl"]:hover,
    button[data-testid="stSidebarCollapseButton"]:hover {{
        border-color: var(--accent-red) !important;
        color: var(--accent-red) !important;
    }}

    /* Sidebar Status Card */
    .system-status-card {{
        background-color: var(--bg-card);
        border: 1px solid var(--border-soft);
        border-radius: 12px;
        padding: 12px 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: auto;
    }}

    .status-indicator {{
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.82rem;
        font-weight: 500;
        color: var(--text-color);
    }}

    .status-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: {status_dot};
        display: inline-block;
        box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    }}

    .status-version {{
        font-size: 0.76rem;
        color: var(--text-secondary);
        font-weight: 500;
    }}

    /* -------------------------------------------------------------
       TOP NAVIGATION & PRODUCT BRANDING BAR
    ------------------------------------------------------------- */
    .top-navbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 0 20px 0;
        margin-bottom: 12px;
        border-bottom: 1px solid var(--border-soft);
    }}

    .top-brand {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}

    .top-brand-icon {{
        width: 28px;
        height: 28px;
        border-radius: 8px;
        background-color: var(--accent-red-subtle);
        color: var(--accent-red);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        font-weight: 700;
    }}

    .top-brand-title {{
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-color);
        letter-spacing: -0.02em;
        margin: 0;
    }}

    .top-right-actions {{
        display: flex;
        align-items: center;
        gap: 12px;
    }}

    .provider-pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: var(--bg-card);
        border: 1px solid var(--border-soft);
        border-radius: 9999px;
        padding: 5px 12px;
        font-size: 0.82rem;
        font-weight: 500;
        color: var(--text-color);
    }}

    .user-avatar {{
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background-color: #334155;
        color: #FFFFFF;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.85rem;
        font-weight: 600;
    }}

    /* -------------------------------------------------------------
       CENTRAL WORKSPACE CARDS (MATCHING REFERENCE SCREENSHOT)
    ------------------------------------------------------------- */
    .saas-card,
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 16px !important;
        padding: 24px 28px !important;
        margin-bottom: 20px !important;
        box-shadow: var(--shadow-card) !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    }}

    .saas-card:hover,
    div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {{
        border-color: rgba(198, 40, 40, 0.25) !important;
    }}

    /* Hero Banner Card */
    .hero-banner-card {{
        background-color: var(--bg-card);
        border: 1px solid var(--border-soft);
        border-radius: 16px;
        padding: 38px 24px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: var(--shadow-card);
    }}

    .hero-eyebrow {{
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--text-secondary);
        margin-bottom: 8px;
    }}

    .hero-title {{
        font-size: 2.35rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: var(--text-color);
        margin: 0 0 10px 0;
        line-height: 1.2;
    }}

    .hero-title .accent-word {{
        color: var(--accent-red);
    }}

    .hero-subtitle {{
        font-size: 1rem;
        color: var(--text-secondary);
        margin: 0 auto;
        max-width: 620px;
        line-height: 1.5;
    }}

    /* Upload Drop Zone Card */
    .upload-zone-card {{
        background-color: var(--bg-card);
        border: 2px dashed var(--border-soft);
        border-radius: 16px;
        padding: 42px 24px;
        text-align: center;
        margin-bottom: 20px;
        transition: border-color 0.2s ease, background-color 0.2s ease;
    }}

    .upload-zone-card:hover {{
        border-color: var(--accent-red);
        background-color: var(--accent-red-subtle);
    }}

    .upload-zone-icon {{
        width: 48px;
        height: 48px;
        border-radius: 12px;
        background-color: var(--accent-red-subtle);
        color: var(--accent-red);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 1.6rem;
        margin-bottom: 12px;
    }}

    .upload-zone-title {{
        font-size: 1.22rem;
        font-weight: 600;
        color: var(--text-color);
        margin-bottom: 4px;
    }}

    .upload-zone-subtitle {{
        font-size: 0.90rem;
        color: var(--text-secondary);
        margin-bottom: 16px;
    }}

    /* Native File Uploader Dropzone Harmonization (Light & Dark Modes) */
    section[data-testid="stFileUploaderDropzone"],
    section[data-testid="stFileUploadDropzone"],
    [data-testid="stFileUploaderDropzone"] {{
        background-color: var(--bg-card) !important;
        border: 2px dashed var(--border-soft) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        text-align: center !important;
        box-shadow: none !important;
        color: var(--text-color) !important;
        transition: all 0.2s ease !important;
    }}

    section[data-testid="stFileUploaderDropzone"]:hover,
    section[data-testid="stFileUploadDropzone"]:hover,
    [data-testid="stFileUploaderDropzone"]:hover {{
        border-color: var(--accent-red) !important;
        background-color: var(--accent-red-subtle) !important;
    }}

    [data-testid="stFileUploaderDropzone"] button,
    [data-testid="stFileUploadDropzone"] button,
    section[data-testid="stFileUploaderDropzone"] button,
    section[data-testid="stFileUploadDropzone"] button {{
        background-color: var(--accent-red) !important;
        color: #FFFFFF !important;
        border: 1px solid var(--accent-red) !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-family: var(--font-main) !important;
        transition: background-color 0.15s ease !important;
    }}

    [data-testid="stFileUploaderDropzone"] button:hover,
    [data-testid="stFileUploadDropzone"] button:hover {{
        background-color: var(--accent-red-hover) !important;
        border-color: var(--accent-red-hover) !important;
        color: #FFFFFF !important;
    }}

    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzoneInstructions"],
    [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stFileUploaderDropzone"] p,
    [data-testid="stFileUploadDropzone"] span,
    [data-testid="stFileUploadDropzone"] small,
    [data-testid="stFileUploadDropzone"] p {{
        color: var(--text-secondary) !important;
    }}

    [data-testid="stFileUploaderFile"],
    [data-testid="stFileUploader"] ul,
    [data-testid="stFileUploader"] li {{
        background-color: var(--bg-card) !important;
        color: var(--text-color) !important;
        border-color: var(--border-soft) !important;
        border-radius: 8px !important;
    }}

    /* Quick Action Suggestion Chips */
    .suggestion-chip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: var(--bg-subtle);
        border: 1px solid var(--border-soft);
        border-radius: 8px;
        padding: 7px 14px;
        font-size: 0.86rem;
        font-weight: 500;
        color: var(--text-color);
        cursor: pointer;
        transition: all 0.15s ease;
        text-decoration: none;
    }}

    .suggestion-chip:hover {{
        border-color: var(--accent-red);
        background-color: var(--accent-red-subtle);
        color: var(--accent-red);
    }}

    /* Recent Analyses Table List */
    .recent-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 16px;
        border-radius: 10px;
        border: 1px solid var(--border-soft);
        background-color: var(--bg-card);
        margin-bottom: 8px;
        transition: background-color 0.15s ease, border-color 0.15s ease;
    }}

    .recent-row:hover {{
        background-color: var(--bg-subtle);
        border-color: rgba(198, 40, 40, 0.2);
    }}

    .recent-info {{
        display: flex;
        align-items: center;
        gap: 12px;
    }}

    .recent-file-icon {{
        width: 36px;
        height: 36px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
    }}

    .recent-filename {{
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text-color);
        margin: 0;
    }}

    .recent-meta {{
        font-size: 0.80rem;
        color: var(--text-secondary);
        margin: 0;
    }}

    /* -------------------------------------------------------------
       BUTTONS, INPUTS & CONTROLS (RESTRAINED RED ACCENT TOKENS)
    ------------------------------------------------------------- */
    /* Primary Buttons (Red Accent) */
    button[kind="primary"],
    button[data-testid="baseButton-primary"],
    .red-btn,
    section[data-testid="stFileUploadDropzone"] button {{
        background-color: var(--accent-red) !important;
        color: #FFFFFF !important;
        border: 1px solid var(--accent-red) !important;
        border-radius: 8px !important;
        padding: 0.55rem 1.4rem !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        font-family: var(--font-main) !important;
        transition: background-color 0.15s ease, transform 0.1s ease !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    }}

    button[kind="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover,
    .red-btn:hover,
    section[data-testid="stFileUploadDropzone"] button:hover {{
        background-color: var(--accent-red-hover) !important;
        border-color: var(--accent-red-hover) !important;
        color: #FFFFFF !important;
    }}

    button[kind="primary"]:active,
    section[data-testid="stFileUploadDropzone"] button:active {{
        transform: scale(0.98) !important;
    }}

    /* Secondary / Default Neutral Buttons */
    button[kind="secondary"],
    button[data-testid="baseButton-secondary"],
    .stButton > button {{
        background-color: var(--bg-card) !important;
        color: var(--text-color) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 8px !important;
        padding: 0.50rem 1.1rem !important;
        font-weight: 500 !important;
        font-size: 0.90rem !important;
        font-family: var(--font-main) !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03) !important;
    }}

    button[kind="secondary"]:hover,
    button[data-testid="baseButton-secondary"]:hover,
    .stButton > button:hover {{
        border-color: var(--accent-red) !important;
        color: var(--accent-red) !important;
        background-color: var(--accent-red-subtle) !important;
    }}

    /* Circular Send Button */
    div.st-key-home_query_submit button {{
        background-color: var(--accent-red) !important;
        color: #FFFFFF !important;
        border: 1px solid var(--accent-red) !important;
        border-radius: 50% !important;
        width: 44px !important;
        height: 44px !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 1.25rem !important;
        font-weight: 700 !important;
    }}

    div.st-key-home_query_submit button:hover {{
        background-color: var(--accent-red-hover) !important;
        color: #FFFFFF !important;
    }}

    /* Quick Action Suggestion Chips Buttons */
    div.st-key-chip_insights button,
    div.st-key-chip_summary button,
    div.st-key-chip_trends button,
    div.st-key-chip_viz button,
    div.st-key-chip_charts button,
    div.st-key-chip_compare button {{
        background-color: var(--bg-subtle) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 8px !important;
        padding: 6px 12px !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: var(--text-color) !important;
        white-space: nowrap !important;
    }}

    div.st-key-chip_insights button:hover,
    div.st-key-chip_summary button:hover,
    div.st-key-chip_trends button:hover,
    div.st-key-chip_viz button:hover,
    div.st-key-chip_charts button:hover,
    div.st-key-chip_compare button:hover {{
        border-color: var(--accent-red) !important;
        color: var(--accent-red) !important;
        background-color: var(--accent-red-subtle) !important;
    }}

    /* Form Fields, Text Inputs & Selectboxes (High Contrast Light & Dark) */
    .stTextInput div[data-baseweb="input"],
    .stTextInput div[data-baseweb="base-input"],
    .stTextArea div[data-baseweb="textarea"],
    .stTextArea div[data-baseweb="base-input"],
    div.react-aria-TextField > div,
    div:has(> input[data-testid="stTextInputField"]),
    [data-testid="stTextInput"] div:has(> input),
    div[data-testid="stDialog"] div:has(> input) {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 10px !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    }}

    .stTextInput input,
    .stTextArea textarea,
    input[data-testid="stTextInputField"],
    div.react-aria-TextField input,
    div[data-testid="stDialog"] input {{
        background-color: transparent !important;
        color: var(--text-color) !important;
        font-family: var(--font-main) !important;
        font-size: 0.93rem !important;
        padding: 10px 14px !important;
    }}

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder,
    input::placeholder,
    textarea::placeholder,
    [data-testid="stTextInput"] input::placeholder,
    input[data-testid="stTextInputField"]::placeholder {{
        color: var(--text-secondary) !important;
        opacity: 0.85 !important;
        -webkit-text-fill-color: var(--text-secondary) !important;
    }}

    .stTextInput div[data-baseweb="input"]:focus-within,
    .stTextArea div[data-baseweb="textarea"]:focus-within,
    .stTextInput input:focus,
    .stTextArea textarea:focus {{
        border-color: var(--accent-red) !important;
        box-shadow: 0 0 0 3px var(--accent-red-subtle) !important;
    }}

    .stSelectbox div[data-baseweb="select"] > div {{
        background-color: var(--bg-card) !important;
        color: var(--text-color) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 10px !important;
    }}

    .stSelectbox div[data-baseweb="select"]:focus-within {{
        border-color: var(--accent-red) !important;
        box-shadow: 0 0 0 3px var(--accent-red-subtle) !important;
    }}

    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[role="listbox"] {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 10px !important;
        box-shadow: var(--shadow-hover) !important;
    }}

    li[role="option"] {{
        background-color: var(--bg-card) !important;
        color: var(--text-color) !important;
    }}

    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {{
        background-color: var(--accent-red-subtle) !important;
        color: var(--accent-red) !important;
    }}

    /* Dialogs, Modals & Auth Forms */
    div[data-testid="stDialog"] > div,
    div[data-testid="stModal"] > div {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 16px !important;
        color: var(--text-color) !important;
        box-shadow: var(--shadow-hover) !important;
    }}

    div[data-testid="stDialog"] div[data-baseweb="input"],
    div[data-testid="stDialog"] div.react-aria-TextField > div,
    div[data-testid="stDialog"] div:has(> input),
    div[data-testid="stDialog"] input {{
        background-color: var(--bg-subtle) !important;
        border: 1px solid var(--border-soft) !important;
        color: var(--text-color) !important;
    }}

    .auth-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: var(--accent-red-subtle);
        color: var(--accent-red);
        border: 1px solid rgba(198, 40, 40, 0.2);
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
    }}

    /* Popover Menu Styling for User Profile */
    div[data-testid="stPopover"] > button {{
        border-radius: 9999px !important;
        background-color: var(--accent-red-subtle) !important;
        color: var(--accent-red) !important;
        border: 1px solid rgba(198, 40, 40, 0.3) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.35rem 0.75rem !important;
        min-height: 34px !important;
        transition: all 0.15s ease !important;
    }}

    div[data-testid="stPopover"] > button:hover {{
        background-color: rgba(198, 40, 40, 0.18) !important;
        border-color: var(--accent-red) !important;
    }}

    div[data-testid="stPopoverBody"],
    div[data-testid="stPopoverContent"],
    div[data-baseweb="popover"] > div {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 14px !important;
        color: var(--text-color) !important;
        box-shadow: var(--shadow-hover) !important;
    }}

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: transparent;
        border-bottom: 1px solid var(--border-soft);
        margin-bottom: 20px;
    }}

    .stTabs [data-baseweb="tab"] {{
        background-color: transparent !important;
        color: var(--text-secondary) !important;
        font-family: var(--font-main) !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        padding: 10px 16px !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        color: var(--text-color) !important;
    }}

    .stTabs [aria-selected="true"] {{
        color: var(--accent-red) !important;
        border-bottom: 2px solid var(--accent-red) !important;
    }}

    .stTabs [aria-selected="true"] p {{
        font-weight: 600 !important;
        color: var(--accent-red) !important;
    }}

    /* Native Metric Cards */
    div[data-testid="stMetric"] {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        box-shadow: var(--shadow-card) !important;
    }}

    div[data-testid="stMetric"] label {{
        font-size: 0.78rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: var(--text-secondary) !important;
    }}

    div[data-testid="stMetricValue"] {{
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: var(--text-color) !important;
    }}

    /* Expanders */
    div[data-testid="stExpander"] {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-soft) !important;
        border-radius: 12px !important;
        margin-bottom: 16px !important;
    }}

    /* Dataframes & Tables */
    .stDataFrame, div[data-testid="stDataFrame"] {{
        border: 1px solid var(--border-soft) !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }}

    /* -------------------------------------------------------------
       RESPONSIVE BREAKPOINTS (Desktop, Tablet, Mobile)
    ------------------------------------------------------------- */
    /* Tablet (768px to 1199px) */
    @media (max-width: 1199px) {{
        .block-container {{
            max-width: 100% !important;
            padding-left: 1.25rem !important;
            padding-right: 1.25rem !important;
        }}

        .hero-title {{
            font-size: 2.0rem;
        }}

        .saas-card, .hero-banner-card {{
            padding: 24px 20px;
        }}
    }}

    /* Mobile (below 768px down to 360px) */
    @media (max-width: 768px) {{
        .block-container {{
            padding-top: 0.75rem !important;
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
        }}

        .top-navbar {{
            flex-direction: column;
            align-items: flex-start;
            gap: 12px;
            padding-bottom: 14px;
        }}

        .top-right-actions {{
            width: 100%;
            justify-content: space-between;
        }}

        .hero-banner-card {{
            padding: 24px 16px;
        }}

        .hero-title {{
            font-size: 1.65rem;
        }}

        .upload-zone-card {{
            padding: 28px 14px;
        }}

        .recent-row {{
            flex-direction: column;
            align-items: flex-start;
            gap: 10px;
        }}

        .recent-row button {{
            width: 100% !important;
        }}

        /* Ensure chips wrap and do not overflow horizontally */
        .chips-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        /* Strict prevention of horizontal viewport scroll */
        html, body, .stApp {{
            overflow-x: hidden !important;
        }}
    }}

    /* Compact Mobile (360px) */
    @media (max-width: 390px) {{
        .hero-title {{
            font-size: 1.45rem;
        }}

        .hero-subtitle {{
            font-size: 0.88rem;
        }}

        .stButton > button {{
            padding: 0.5rem 1rem !important;
            font-size: 0.85rem !important;
        }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def apply_custom_theme(theme_mode: str = "Light") -> None:
    """Backward-compatible wrapper for inject_clean_theme."""
    is_dark = theme_mode.lower() == "dark" if isinstance(theme_mode, str) else bool(theme_mode)
    inject_clean_theme(dark_mode=is_dark)


def render_interactive_3d_background() -> None:
    """Legacy stub maintained for backward compatibility."""
    pass
