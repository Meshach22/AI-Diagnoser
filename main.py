"""main.py

AI Data Analyst / AI-Diagnoser: Enterprise Multimodal SaaS Studio
- Minimalist Professional SaaS Design with restrained Red Accent Palette (#C62828 / #EF4444)
- Samsung-Inspired Typography Stack ("SamsungOne", "Arial", "Helvetica", sans-serif)
- Functional, persistent Light / Dark Mode Toggle
- 6 Streamlined Navigation Destinations:
  1. Home (Matching reference screenshot)
  2. Chat with Data
  3. Upload & Analyze (Integrates Document Analysis + Tabular Analytics)
  4. Image Analysis
  5. n8n Automation
  6. Settings
- Only actually configured AI provider (Google Gemini) shown as primary in header
- Full preservation of FastAPI backend, pipelines, and artifacts
"""

import base64
import io
import json
import os
import streamlit as st
import pandas as pd
from PIL import Image

from core.backend_client import BackendClient
from core.config import MODEL_CATALOG, PROVIDER_PRIMARY_MODELS
from core.llm_router import LLMRouter, get_last_telemetry, encode_image_to_base64
from core.styles import inject_clean_theme
from core.ui_components import (
    export_markdown_to_docx,
    export_markdown_to_pdf,
    render_claude_artifact_workspace,
    render_image_diagnostics_panel,
    render_sidebar_telemetry,
    set_initial_artifact,
)
from pipelines.data_pipeline import (
    create_bar_plot,
    create_correlation_heatmap,
    create_distribution_plot,
    create_line_plot,
    create_scatter_plot,
    generate_data_health_card,
    generate_data_insights,
    load_structured_data,
)
from pipelines.document_pipeline import (
    ask_document_question,
    generate_document_summary,
    load_document,
)
from pipelines.image_pipeline import (
    analyze_image_with_llm,
    extract_dominant_colors,
    extract_image_metadata,
    load_image,
)

# ---------------------------------------------------------------------------
# Streamlit Application Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Data Analyst",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="auto"
)

# ---------------------------------------------------------------------------
# Theme Persistence via Query Params and Session State
# ---------------------------------------------------------------------------
if "dark_mode" not in st.session_state:
    # Check query param first for persistent browser preference
    if "theme" in st.query_params:
        st.session_state.dark_mode = (st.query_params["theme"] == "dark")
    else:
        st.session_state.dark_mode = False  # Default to clean Light mode matching reference

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Dark" if st.session_state.dark_mode else "Light"

if "backend_url" not in st.session_state:
    st.session_state.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

if "execution_mode" not in st.session_state:
    st.session_state.execution_mode = "FastAPI Backend"

if "model_provider" not in st.session_state:
    st.session_state.model_provider = "Google Gemini"

if "nav_selection" not in st.session_state:
    st.session_state.nav_selection = "Home"

# Authentication State
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

# Active Data State Holders
if "active_df" not in st.session_state:
    st.session_state.active_df = None

if "active_df_name" not in st.session_state:
    st.session_state.active_df_name = None

if "active_df_health" not in st.session_state:
    st.session_state.active_df_health = None

if "active_doc_data" not in st.session_state:
    st.session_state.active_doc_data = None

if "active_doc_name" not in st.session_state:
    st.session_state.active_doc_name = None

if "active_image" not in st.session_state:
    st.session_state.active_image = None

if "active_img_meta" not in st.session_state:
    st.session_state.active_img_meta = None

if "active_swatches" not in st.session_state:
    st.session_state.active_swatches = []

if "doc_result" not in st.session_state:
    st.session_state.doc_result = ""

if "vision_result" not in st.session_state:
    st.session_state.vision_result = ""

if "data_result" not in st.session_state:
    st.session_state.data_result = ""

if "home_analysis_result" not in st.session_state:
    st.session_state.home_analysis_result = None

if "active_recent_item" not in st.session_state:
    st.session_state.active_recent_item = None

# Backend Client & Health Probes
backend_client = BackendClient(
    base_url=st.session_state.backend_url,
    token=st.session_state.auth_token,
)
is_backend_online, backend_meta, backend_latency = backend_client.check_health()
router = LLMRouter()

# Validate Existing Session if Token is Present
if st.session_state.auth_token and not st.session_state.auth_user:
    is_valid, user_data, _ = backend_client.get_me(st.session_state.auth_token)
    if is_valid:
        st.session_state.auth_user = user_data
    else:
        st.session_state.auth_token = None

# Verify actually configured providers
is_gemini_configured = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

# ---------------------------------------------------------------------------
# Dynamic Theme Injection
# ---------------------------------------------------------------------------
inject_clean_theme(dark_mode=st.session_state.dark_mode)


@st.dialog("Sign In to AI Data Analyst")
def show_auth_modal():
    """Modal authentication dialog for sign in and registration."""
    tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

    with tab_login:
        st.markdown(
            "<p style='font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 0.8rem;'>"
            "Sign in with your enterprise credentials to access saved analyses and datasets."
            "</p>",
            unsafe_allow_html=True,
        )
        with st.form("auth_login_form", clear_on_submit=False):
            login_email = st.text_input("Work Email", key="auth_login_email", placeholder="analyst@enterprise.local")
            login_password = st.text_input("Password", type="password", key="auth_login_password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

            if submitted:
                if not login_email or not login_password:
                    st.error("Please enter both email and password.")
                else:
                    with st.spinner("Verifying credentials..."):
                        success, token, user, msg = backend_client.login(login_email.strip(), login_password)
                    if success:
                        st.session_state.auth_token = token
                        st.session_state.auth_user = user
                        st.success(f"Welcome back, {user.get('name', 'Analyst')}!")
                        st.rerun()
                    else:
                        st.error(msg or "Invalid email or password.")

    with tab_signup:
        st.markdown(
            "<p style='font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 0.8rem;'>"
            "Create a new analyst account. Password must be at least 12 characters."
            "</p>",
            unsafe_allow_html=True,
        )
        with st.form("auth_signup_form", clear_on_submit=False):
            reg_name = st.text_input("Full Name", key="auth_reg_name", placeholder="Jane Doe")
            reg_email = st.text_input("Work Email", key="auth_reg_email", placeholder="analyst@enterprise.local")
            reg_password = st.text_input("Password (min 12 chars)", type="password", key="auth_reg_password", placeholder="Enterprise-grade password")
            reg_submitted = st.form_submit_button("Create Account", use_container_width=True)

            if reg_submitted:
                if not reg_name or not reg_email or not reg_password:
                    st.error("Please fill in all registration fields.")
                elif len(reg_password) < 12:
                    st.error("Password must be at least 12 characters long.")
                else:
                    with st.spinner("Registering account..."):
                        success, token, user, msg = backend_client.register(reg_email.strip(), reg_name.strip(), reg_password)
                    if success:
                        st.session_state.auth_token = token
                        st.session_state.auth_user = user
                        st.success("Account created successfully!")
                        st.rerun()
                    else:
                        st.error(msg or "Registration could not be completed.")

# ---------------------------------------------------------------------------
# SIDEBAR NAVIGATION (Matching Reference Specification)
# ---------------------------------------------------------------------------
with st.sidebar:
    # Sidebar Product Brand
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="top-brand-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                </svg>
            </div>
            <div class="sidebar-brand-title">
                AI Data Analyst <span class="sidebar-brand-badge">v2.0</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 6-Item Streamlined Navigation
    nav_options = [
        "Home",
        "Chat with Data",
        "Upload & Analyze",
        "Image Analysis",
        "n8n Automation",
        "Settings"
    ]
    
    current_index = 0
    if st.session_state.nav_selection in nav_options:
        current_index = nav_options.index(st.session_state.nav_selection)

    selected_nav = st.radio(
        "Navigation Menu",
        options=nav_options,
        index=current_index,
        format_func=lambda x: {
            "Home": "🏠   Home",
            "Chat with Data": "💬   Chat with Data",
            "Upload & Analyze": "📄   Upload & Analyze",
            "Image Analysis": "🖼️   Image Analysis",
            "n8n Automation": "🕸️   n8n Automation",
            "Settings": "⚙️   Settings"
        }.get(x, x),
        label_visibility="collapsed",
        key="main_nav_radio"
    )

    if selected_nav != st.session_state.nav_selection:
        st.session_state.nav_selection = selected_nav
        st.rerun()

    # Sidebar Bottom Status Card
    status_dot_color = "#10B981" if is_backend_online else "#F59E0B"
    status_text = "All systems running" if is_backend_online else "Direct Core Mode"
    st.markdown(
        f"""
        <div class="system-status-card" style="margin-top: auto; padding-top: 1.5rem;">
            <div class="status-indicator">
                <span class="status-dot" style="background-color: {status_dot_color};"></span>
                <span>{status_text}</span>
            </div>
            <span class="status-version">v2.0.0</span>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------------------------
# TOP NAVIGATION BAR (Product Branding, Configured Provider Pill, Dark Mode Toggle, Auth)
# ---------------------------------------------------------------------------
top_nav_c1, top_nav_c2 = st.columns([1.6, 2.4], vertical_alignment="center")

with top_nav_c1:
    st.markdown(
        """
        <div class="top-brand">
            <div class="top-brand-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                </svg>
            </div>
            <h1 class="top-brand-title">AI Data Analyst <span class="sidebar-brand-badge">v2.0</span></h1>
        </div>
        """,
        unsafe_allow_html=True
    )

with top_nav_c2:
    p_col, t_col, u_col = st.columns([1.8, 1.2, 1.0], vertical_alignment="center")

    with p_col:
        # Show Google Gemini as the operational provider
        gemini_dot_color = "#10B981" if (is_backend_online or is_gemini_configured) else "#F59E0B"
        st.markdown(
            f"""
            <div style="display: flex; justify-content: flex-end;">
                <div class="provider-pill">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm1 14.93V18h-2v-1.07A6 6 0 0 1 6.07 12H7v-2h-.93A6 6 0 0 1 11 4.07V3h2v1.07A6 6 0 0 1 17.93 10H17v2h.93A6 6 0 0 1 13 16.93z"/>
                    </svg>
                    <span>Google Gemini</span>
                    <span class="status-dot" style="background-color: {gemini_dot_color};"></span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with t_col:
        theme_btn_label = "🌙 Dark Mode" if not st.session_state.dark_mode else "☀️ Light Mode"
        if st.button(theme_btn_label, key="top_theme_toggle_btn", use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.session_state.theme_mode = "Dark" if st.session_state.dark_mode else "Light"
            st.query_params["theme"] = "dark" if st.session_state.dark_mode else "light"
            st.rerun()

    with u_col:
        if st.session_state.auth_user is None:
            if st.button("Sign In", key="top_signin_btn", use_container_width=True):
                show_auth_modal()
        else:
            u_name = st.session_state.auth_user.get("name", "Analyst")
            u_email = st.session_state.auth_user.get("email", "")
            name_parts = [p for p in u_name.strip().split() if p]
            if len(name_parts) >= 2:
                initials = f"{name_parts[0][0]}{name_parts[1][0]}".upper()
            elif len(name_parts) == 1:
                initials = name_parts[0][:2].upper()
            else:
                initials = "DA"

            with st.popover(initials, use_container_width=True):
                st.markdown(f"**{u_name}**")
                st.caption(u_email)
                st.markdown("<span class='auth-badge'>Authenticated</span>", unsafe_allow_html=True)
                st.divider()
                if st.button("Sign Out", key="popover_signout_btn", use_container_width=True):
                    backend_client.logout(st.session_state.auth_token)
                    st.session_state.auth_token = None
                    st.session_state.auth_user = None
                    st.rerun()


# ===========================================================================
# VIEW 1: HOME (MATCHING THE REFERENCE SCREENSHOT)
# ===========================================================================
if st.session_state.nav_selection == "Home":

    # Hero Banner Card
    with st.container(border=True):
        st.markdown(
            """
            <div style="text-align: center; padding: 18px 12px 14px 12px;">
                <div class="hero-eyebrow">TURN DATA INTO INSIGHTS</div>
                <h1 class="hero-title">Analyze your data with <span class="accent-word">AI</span></h1>
                <p class="hero-subtitle">Upload your file, ask questions, and get clear insights in seconds.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Upload Drop Zone Card
    with st.container(border=True):
        st.markdown(
            """
            <div style="text-align: center; padding-top: 10px;">
                <div class="upload-zone-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="17 8 12 3 7 8"/>
                        <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                </div>
                <div class="upload-zone-title">Upload your data</div>
                <div class="upload-zone-subtitle">CSV, Excel, PDF or Image</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        home_file = st.file_uploader(
            "Upload dataset, document, or image",
            type=["csv", "xlsx", "xls", "pdf", "docx", "txt", "png", "jpg", "jpeg"],
            label_visibility="collapsed",
            key="home_uploader"
        )
        st.markdown("<div style='text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-top: -6px; margin-bottom: 8px;'>or drag and drop here</div>", unsafe_allow_html=True)

    # Ingestion handler for uploaded file
    if home_file is not None:
        fname = home_file.name
        fext = os.path.splitext(fname)[1].lower()
        fbytes = home_file.getvalue()

        if fext in [".csv", ".xlsx", ".xls"]:
            df = load_structured_data(io.BytesIO(fbytes), fname)
            st.session_state.active_df = df
            st.session_state.active_df_name = fname
            if st.session_state.execution_mode == "FastAPI Backend" and is_backend_online:
                try:
                    health = backend_client.profile_data(fbytes, fname)
                except Exception:
                    health = generate_data_health_card(df, fname)
            else:
                health = generate_data_health_card(df, fname)
            st.session_state.active_df_health = health

            st.success(f"✓ Ingested Tabular Dataset: **{fname}** ({health['total_rows']:,} rows, {health['total_cols']} columns)")

        elif fext in [".pdf", ".docx", ".txt"]:
            if st.session_state.execution_mode == "FastAPI Backend" and is_backend_online:
                try:
                    doc_data = backend_client.parse_document(fbytes, fname)
                except Exception:
                    doc_data = load_document(io.BytesIO(fbytes), fname)
            else:
                doc_data = load_document(io.BytesIO(fbytes), fname)
            st.session_state.active_doc_data = doc_data
            st.session_state.active_doc_name = fname

            st.success(f"✓ Ingested Document: **{fname}** ({doc_data.get('word_count', 0):,} words, ~{doc_data.get('reading_time_min', 1)} min read)")

        elif fext in [".png", ".jpg", ".jpeg"]:
            pil_img = load_image(io.BytesIO(fbytes))
            st.session_state.active_image = pil_img
            meta = extract_image_metadata(pil_img, len(fbytes), fname)
            st.session_state.active_img_meta = meta
            st.session_state.active_swatches = extract_dominant_colors(pil_img, 5)

            st.success(f"✓ Ingested Visual Asset: **{fname}** ({meta.get('dimensions')} - {meta.get('megapixels')} MP)")

    # Natural-Language Question Card
    with st.container(border=True):
        q_hdr_c1, q_hdr_c2 = st.columns([3.8, 1.2], vertical_alignment="center")
        with q_hdr_c1:
            st.markdown("<h3 style='margin: 0; font-size: 1.05rem; font-weight: 600; color: var(--text-color);'>Ask a question about your data</h3>", unsafe_allow_html=True)
        with q_hdr_c2:
            st.markdown("<div style='text-align: right;'><span style='font-size: 0.85rem; color: var(--accent-red); font-weight: 500; cursor: pointer;'>View example questions →</span></div>", unsafe_allow_html=True)

        q_col, btn_col = st.columns([5.3, 0.7], vertical_alignment="center")
        with q_col:
            question_text = st.text_input(
                "Ask anything about your uploaded data...",
                placeholder="Ask anything about your uploaded data...",
                label_visibility="collapsed",
                key="home_query_input"
            )
        with btn_col:
            submit_q = st.button("↑", key="home_query_submit", help="Submit analysis question", type="primary", use_container_width=True)

        # Quick-Action Suggestion Chips
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            chip_insights = st.button("📊 Show key insights", key="chip_insights", use_container_width=True)
        with c2:
            chip_summary = st.button("📄 Create a summary", key="chip_summary", use_container_width=True)
        with c3:
            chip_trends = st.button("📈 Find trends", key="chip_trends", use_container_width=True)
        with c4:
            chip_viz = st.button("⏱️ Visualize this data", key="chip_viz", use_container_width=True)
        with c5:
            chip_charts = st.button("📊 Add charts", key="chip_charts", use_container_width=True)
        with c6:
            chip_compare = st.button("📑 Compare values", key="chip_compare", use_container_width=True)

    # Execution logic for query or quick action
    active_prompt = None
    if submit_q and question_text.strip():
        active_prompt = question_text.strip()
    elif chip_insights:
        active_prompt = "Provide a comprehensive breakdown of the key executive insights, operational risks, and highest-priority opportunities."
    elif chip_summary:
        active_prompt = "Generate an executive briefing summary highlighting total performance metrics and major observations."
    elif chip_trends:
        active_prompt = "Analyze the primary trends, correlations, growth trajectories, and anomalies in this data."
    elif chip_viz:
        active_prompt = "Recommend the top 3 statistical visualizations for this dataset and summarize the distribution of key variables."
    elif chip_charts:
        active_prompt = "Generate chart breakdowns and metric rankings across categories and dimensions."
    elif chip_compare:
        active_prompt = "Compare numerical values across segments, highlighting the highest and lowest variance items."

    if active_prompt:
        with st.spinner("Analyzing with Google Gemini..."):
            # Ensure an active dataset or document exists; if not, auto-load sample data
            if st.session_state.active_df is None and st.session_state.active_doc_data is None:
                demo_csv = os.path.join(os.getcwd(), "sample_data", "sample_business_metrics.csv")
                if os.path.isfile(demo_csv):
                    with open(demo_csv, "rb") as f:
                        b = f.read()
                    df = load_structured_data(io.BytesIO(b), "sample_business_metrics.csv")
                    st.session_state.active_df = df
                    st.session_state.active_df_name = "sales_data.csv"
                    st.session_state.active_df_health = generate_data_health_card(df, "sales_data.csv")
                    st.info("💡 Auto-loaded sample business metrics dataset (`sales_data.csv`) for demonstration.")

            if st.session_state.active_df is not None:
                csv_sample = st.session_state.active_df.head(100).to_csv(index=False)
                if st.session_state.execution_mode == "FastAPI Backend" and is_backend_online:
                    try:
                        res = backend_client.get_data_insights(
                            dataset_csv=csv_sample,
                            user_query=active_prompt,
                            provider=st.session_state.model_provider
                        )
                    except Exception:
                        res = generate_data_insights(st.session_state.active_df, user_query=active_prompt)
                else:
                    res = generate_data_insights(st.session_state.active_df, user_query=active_prompt)
                st.session_state.home_analysis_result = res

            elif st.session_state.active_doc_data is not None:
                full_text = st.session_state.active_doc_data.get("full_text", "")
                if st.session_state.execution_mode == "FastAPI Backend" and is_backend_online:
                    try:
                        res = backend_client.ask_document(
                            text=full_text,
                            question=active_prompt,
                            provider=st.session_state.model_provider
                        )
                    except Exception:
                        res = ask_document_question(full_text, active_prompt)
                else:
                    res = ask_document_question(full_text, active_prompt)
                st.session_state.home_analysis_result = res

    # Render Home Analysis Result if present
    if st.session_state.home_analysis_result:
        st.markdown(
            f"""
            <div class="saas-card" style="padding: 22px 26px; margin-top: 16px; border-left: 4px solid var(--accent-red);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div style="font-weight: 600; font-size: 1.05rem; color: var(--text-color);">
                        ✦ Synthesis Result
                    </div>
                    <span class="sidebar-brand-badge">Google Gemini</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(st.session_state.home_analysis_result)

    # Recent Analyses Card (Matching Reference Layout)
    with st.container(border=True):
        r_hdr_c1, r_hdr_c2 = st.columns([3.8, 1.2], vertical_alignment="center")
        with r_hdr_c1:
            st.markdown("<h3 style='margin: 0; font-size: 1.05rem; font-weight: 600; color: var(--text-color);'>Recent Analyses</h3>", unsafe_allow_html=True)
        with r_hdr_c2:
            st.markdown("<div style='text-align: right;'><span style='font-size: 0.85rem; color: var(--accent-red); font-weight: 500; cursor: pointer;'>View all →</span></div>", unsafe_allow_html=True)

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # Row 1: sales_data.csv
        r1_col1, r1_col2, r1_col3, r1_col4 = st.columns([0.6, 4.2, 1.2, 0.3], vertical_alignment="center")
        with r1_col1:
            st.markdown(
                """
                <div style="width: 38px; height: 38px; border-radius: 8px; background-color: rgba(16, 185, 129, 0.12); display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
                    📊
                </div>
                """,
                unsafe_allow_html=True
            )
        with r1_col2:
            st.markdown(
                """
                <div style="display: flex; flex-direction: column;">
                    <span style="font-size: 0.94rem; font-weight: 600; color: var(--text-color);">sales_data.csv</span>
                    <span style="font-size: 0.80rem; color: var(--text-secondary);">Analyzed • 2 hours ago</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with r1_col3:
            if st.button("View Results", key="recent_sales_data", use_container_width=True):
                demo_csv = os.path.join(os.getcwd(), "sample_data", "sample_business_metrics.csv")
                if os.path.isfile(demo_csv):
                    with open(demo_csv, "rb") as f:
                        b = f.read()
                    df = load_structured_data(io.BytesIO(b), "sales_data.csv")
                    st.session_state.active_df = df
                    st.session_state.active_df_name = "sales_data.csv"
                    st.session_state.active_df_health = generate_data_health_card(df, "sales_data.csv")
                    st.session_state.active_recent_item = "sales_data.csv"
                    st.session_state.nav_selection = "Upload & Analyze"
                    st.rerun()
        with r1_col4:
            st.markdown("<span style='color: var(--text-secondary); font-size: 1.15rem; cursor: pointer;'>⋮</span>", unsafe_allow_html=True)

        # Row 2: chart.png
        r2_col1, r2_col2, r2_col3, r2_col4 = st.columns([0.6, 4.2, 1.2, 0.3], vertical_alignment="center")
        with r2_col1:
            st.markdown(
                """
                <div style="width: 38px; height: 38px; border-radius: 8px; background-color: rgba(124, 58, 237, 0.12); display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
                    🖼️
                </div>
                """,
                unsafe_allow_html=True
            )
        with r2_col2:
            st.markdown(
                """
                <div style="display: flex; flex-direction: column;">
                    <span style="font-size: 0.94rem; font-weight: 600; color: var(--text-color);">chart.png</span>
                    <span style="font-size: 0.80rem; color: var(--text-secondary);">Analyzed • 1 day ago</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with r2_col3:
            if st.button("View Results", key="recent_chart_img", use_container_width=True):
                demo_img = os.path.join(os.getcwd(), "sample_data", "sample_performance_chart.png")
                if os.path.isfile(demo_img):
                    with open(demo_img, "rb") as f:
                        b = f.read()
                    pil_img = load_image(io.BytesIO(b))
                    st.session_state.active_image = pil_img
                    st.session_state.active_img_meta = extract_image_metadata(pil_img, len(b), "chart.png")
                    st.session_state.active_swatches = extract_dominant_colors(pil_img, 5)
                    st.session_state.active_recent_item = "chart.png"
                    st.session_state.nav_selection = "Image Analysis"
                    st.rerun()
        with r2_col4:
            st.markdown("<span style='color: var(--text-secondary); font-size: 1.15rem; cursor: pointer;'>⋮</span>", unsafe_allow_html=True)

        # Row 3: invoice.pdf
        r3_col1, r3_col2, r3_col3, r3_col4 = st.columns([0.6, 4.2, 1.2, 0.3], vertical_alignment="center")
        with r3_col1:
            st.markdown(
                """
                <div style="width: 38px; height: 38px; border-radius: 8px; background-color: rgba(239, 68, 68, 0.12); display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
                    📄
                </div>
                """,
                unsafe_allow_html=True
            )
        with r3_col2:
            st.markdown(
                """
                <div style="display: flex; flex-direction: column;">
                    <span style="font-size: 0.94rem; font-weight: 600; color: var(--text-color);">invoice.pdf</span>
                    <span style="font-size: 0.80rem; color: var(--text-secondary);">Analyzed • 2 days ago</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with r3_col3:
            if st.button("View Results", key="recent_invoice_pdf", use_container_width=True):
                demo_doc = os.path.join(os.getcwd(), "sample_data", "sample_financial_report.txt")
                if os.path.isfile(demo_doc):
                    with open(demo_doc, "rb") as f:
                        b = f.read()
                    doc_data = load_document(io.BytesIO(b), "invoice.pdf")
                    st.session_state.active_doc_data = doc_data
                    st.session_state.active_doc_name = "invoice.pdf"
                    st.session_state.active_recent_item = "invoice.pdf"
                    st.session_state.nav_selection = "Upload & Analyze"
                    st.rerun()
        with r3_col4:
            st.markdown("<span style='color: var(--text-secondary); font-size: 1.15rem; cursor: pointer;'>⋮</span>", unsafe_allow_html=True)



# ===========================================================================
# VIEW 2: CHAT WITH DATA
# ===========================================================================
elif st.session_state.nav_selection == "Chat with Data":
    st.markdown("### 💬 Conversational Intelligence & Artifacts Workspace")
    st.caption("Interact naturally with loaded datasets and documents. Export dynamic reports to Word (.docx) or PDF.")

    # Context Header Card
    ctx_name = st.session_state.active_df_name or st.session_state.active_doc_name or "Sample Context"
    st.markdown(
        f"""
        <div class="saas-card" style="padding: 16px 20px; margin-bottom: 16px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 1.2rem;">📂</span>
                    <div>
                        <div style="font-weight: 600; font-size: 0.98rem; color: var(--text-color);">{ctx_name}</div>
                        <div style="font-size: 0.80rem; color: var(--text-secondary);">Active Context Loaded into Workspace</div>
                    </div>
                </div>
                <span class="sidebar-brand-badge">Google Gemini</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Initial Analysis Content
    if st.session_state.active_df is not None:
        initial_text = st.session_state.data_result or f"### Dataset Profile: {st.session_state.active_df_name}\n\n- Rows: `{len(st.session_state.active_df):,}`\n- Columns: `{len(st.session_state.active_df.columns)}`"
        obs = {
            "Total Rows": f"{len(st.session_state.active_df):,}",
            "Columns": f"{len(st.session_state.active_df.columns)}",
            "Dataset": str(st.session_state.active_df_name)
        }
    elif st.session_state.active_doc_data is not None:
        initial_text = st.session_state.doc_result or st.session_state.active_doc_data.get("full_text", "")
        obs = {
            "Document": str(st.session_state.active_doc_name),
            "Word Count": f"{st.session_state.active_doc_data.get('word_count', 0):,}",
            "Format": str(st.session_state.active_doc_data.get('file_type', 'Document'))
        }
    else:
        initial_text = "### Ready to Analyze\n\nUpload a file from **Home** or **Upload & Analyze** to activate conversational intelligence."
        obs = {"Status": "Standby"}

    set_initial_artifact(
        title="Interactive Intelligence Workspace",
        content=initial_text,
        observations=obs
    )

    render_claude_artifact_workspace(
        router=router,
        preferred_provider=st.session_state.model_provider,
        key_prefix="chat_data_workspace"
    )


# ===========================================================================
# VIEW 3: UPLOAD & ANALYZE (MERGED TABULAR & DOCUMENT WORKFLOWS)
# ===========================================================================
elif st.session_state.nav_selection == "Upload & Analyze":
    st.markdown("### 📄 Upload & Multimodal Analysis Studio")
    st.caption("Unified analysis engine integrating Tabular Data Analytics (CSV, Excel) and Document Intelligence (PDF, DOCX, TXT).")

    ua_tab1, ua_tab2 = st.tabs([
        "📊 Tabular Data Analytics (CSV & Excel)",
        "📄 Document Intelligence (PDF, DOCX, TXT)"
    ])

    # -----------------------------------------------------------------------
    # SUB-TAB 1: TABULAR DATA
    # -----------------------------------------------------------------------
    with ua_tab1:
        data_file = st.file_uploader(
            "Upload Structured Dataset (CSV, XLSX, XLS)",
            type=["csv", "xlsx", "xls"],
            key="ua_data_uploader"
        )

        # Check if already active or demo
        if data_file:
            df_bytes = data_file.getvalue()
            df_name = data_file.name
            df = load_structured_data(io.BytesIO(df_bytes), df_name)
            st.session_state.active_df = df
            st.session_state.active_df_name = df_name
            if st.session_state.execution_mode == "FastAPI Backend" and is_backend_online:
                try:
                    st.session_state.active_df_health = backend_client.profile_data(df_bytes, df_name)
                except Exception:
                    st.session_state.active_df_health = generate_data_health_card(df, df_name)
            else:
                st.session_state.active_df_health = generate_data_health_card(df, df_name)

        if st.session_state.active_df is not None:
            df = st.session_state.active_df
            health = st.session_state.active_df_health or generate_data_health_card(df, st.session_state.active_df_name or "dataset.csv")

            # Health Card Metrics Grid
            st.markdown(
                f"""
                <div class="saas-card" style="padding: 18px 24px; margin: 12px 0 16px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                        <div>
                            <div style="font-size: 0.78rem; text-transform: uppercase; color: var(--text-secondary); font-weight: 600;">Total Rows</div>
                            <div style="font-size: 1.6rem; font-weight: 700; color: var(--accent-red);">{health['total_rows']:,}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.78rem; text-transform: uppercase; color: var(--text-secondary); font-weight: 600;">Columns</div>
                            <div style="font-size: 1.6rem; font-weight: 700; color: var(--text-color);">{health['total_cols']}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.78rem; text-transform: uppercase; color: var(--text-secondary); font-weight: 600;">Missing Cells</div>
                            <div style="font-size: 1.6rem; font-weight: 700; color: {'#EF4444' if health['missing_percentage'] > 5 else '#10B981'};">{health['missing_percentage']}%</div>
                        </div>
                        <div>
                            <div style="font-size: 0.78rem; text-transform: uppercase; color: var(--text-secondary); font-weight: 600;">Duplicates</div>
                            <div style="font-size: 1.6rem; font-weight: 700; color: var(--text-color);">{health['duplicate_rows']} ({health['duplicate_percentage']}%)</div>
                        </div>
                        <div>
                            <div style="font-size: 0.78rem; text-transform: uppercase; color: var(--text-secondary); font-weight: 600;">Memory Usage</div>
                            <div style="font-size: 1.6rem; font-weight: 700; color: var(--text-color);">{health['memory_usage']}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Interactive Plotly Visualizations
            st.markdown("#### 📈 Interactive Statistical Visualizations")
            v_t1, v_t2, v_t3, v_t4 = st.tabs([
                "🔥 Correlation Heatmap",
                "📊 Distribution & Histograms",
                "⚡ Scatter Relationships",
                "📶 Categorical Bar & Trend"
            ])

            with v_t1:
                corr_fig = create_correlation_heatmap(df, dark_mode=st.session_state.dark_mode)
                if corr_fig:
                    st.plotly_chart(corr_fig, use_container_width=True)
                else:
                    st.info("Correlation heatmap requires at least 2 numeric features.")

            with v_t2:
                if health["numeric_columns"]:
                    dcol = st.selectbox("Select Numeric Feature", options=health["numeric_columns"], key="ua_dist_col")
                    dtype = st.radio("Chart Type", ["Histogram", "Box Plot"], horizontal=True, key="ua_dist_type")
                    fig_dist = create_distribution_plot(df, dcol, chart_type="box" if dtype == "Box Plot" else "histogram", dark_mode=st.session_state.dark_mode)
                    st.plotly_chart(fig_dist, use_container_width=True)
                else:
                    st.info("No numeric columns detected.")

            with v_t3:
                if len(health["numeric_columns"]) >= 2:
                    sc1, sc2, sc3 = st.columns(3)
                    with sc1:
                        sx = st.selectbox("X Axis", options=health["numeric_columns"], index=0, key="ua_scat_x")
                    with sc2:
                        sy = st.selectbox("Y Axis", options=health["numeric_columns"], index=1, key="ua_scat_y")
                    with sc3:
                        scolor = st.selectbox("Color Group", options=[None] + health["categorical_columns"], key="ua_scat_c")
                    fig_scat = create_scatter_plot(df, sx, sy, color_col=scolor, dark_mode=st.session_state.dark_mode)
                    st.plotly_chart(fig_scat, use_container_width=True)
                else:
                    st.info("Scatter plot requires at least 2 numeric features.")

            with v_t4:
                b1, b2 = st.columns(2)
                with b1:
                    if health["categorical_columns"]:
                        bx = st.selectbox("Category Dimension", options=health["categorical_columns"], key="ua_bar_cat")
                        by = st.selectbox("Metric to Aggregate", options=[None] + health["numeric_columns"], key="ua_bar_val")
                        fig_bar = create_bar_plot(df, bx, by, aggregation="mean" if by else "count", dark_mode=st.session_state.dark_mode)
                        st.plotly_chart(fig_bar, use_container_width=True)
                with b2:
                    if health["numeric_columns"]:
                        lx = st.selectbox("Trend X Column", options=list(df.columns), key="ua_line_x")
                        ly = st.selectbox("Trend Metric Y", options=health["numeric_columns"], key="ua_line_y")
                        fig_line = create_line_plot(df, lx, ly, dark_mode=st.session_state.dark_mode)
                        st.plotly_chart(fig_line, use_container_width=True)

            # Auto-EDA Query
            st.markdown("#### ⚡ AI Dataset Intelligence & Natural Language Query")
            q_col1, q_col2 = st.columns([4.2, 1.2])
            with q_col1:
                eda_q = st.text_input("Ask about correlations or quantitative anomalies:", placeholder="e.g. Which region achieved highest revenue?", key="ua_eda_q")
            with q_col2:
                btn_eda = st.button("Conduct Auto-EDA", use_container_width=True, type="primary")

            if btn_eda:
                with st.spinner("Synthesizing quantitative insights..."):
                    csv_sample = df.head(100).to_csv(index=False)
                    if st.session_state.execution_mode == "FastAPI Backend" and is_backend_online:
                        st.session_state.data_result = backend_client.get_data_insights(
                            dataset_csv=csv_sample,
                            user_query=eda_q if eda_q.strip() else None,
                            provider=st.session_state.model_provider
                        )
                    else:
                        st.session_state.data_result = generate_data_insights(df=df, user_query=eda_q if eda_q.strip() else None)

            if st.session_state.data_result:
                st.markdown(st.session_state.data_result)

            with st.expander("🔍 Tabular Raw Data Inspector", expanded=False):
                st.dataframe(df, use_container_width=True)
        else:
            st.info("💡 Upload a CSV or Excel dataset above, or select one from 'Recent Analyses' on Home.")

    # -----------------------------------------------------------------------
    # SUB-TAB 2: DOCUMENT INTELLIGENCE
    # -----------------------------------------------------------------------
    with ua_tab2:
        doc_file = st.file_uploader(
            "Upload Document (PDF, DOCX, TXT, MD)",
            type=["pdf", "docx", "txt", "md"],
            key="ua_doc_uploader"
        )

        if doc_file:
            d_bytes = doc_file.getvalue()
            d_name = doc_file.name
            if st.session_state.execution_mode == "FastAPI Backend" and is_backend_online:
                try:
                    st.session_state.active_doc_data = backend_client.parse_document(d_bytes, d_name)
                except Exception:
                    st.session_state.active_doc_data = load_document(io.BytesIO(d_bytes), d_name)
            else:
                st.session_state.active_doc_data = load_document(io.BytesIO(d_bytes), d_name)
            st.session_state.active_doc_name = d_name

        if st.session_state.active_doc_data is not None:
            doc_data = st.session_state.active_doc_data
            doc_name = st.session_state.active_doc_name or "document.txt"

            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 8px; margin: 12px 0 16px 0; flex-wrap: wrap;">
                    <span class="status-badge badge-sage">● Ingested & Verified</span>
                    <span class="status-badge badge-neutral"><b>{doc_name}</b></span>
                    <span class="status-badge badge-terracotta">{doc_data.get('file_type', 'Document')}</span>
                    <span class="status-badge badge-ochre">{doc_data.get('word_count', 0):,} Words</span>
                    <span class="status-badge badge-neutral">~{doc_data.get('reading_time_min', 1)} Min Read</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Neural Intelligence Operations
            st.markdown("#### ⚡ Neural Intelligence Operations")
            act1, act2, act3 = st.columns(3)
            with act1:
                btn_exec = st.button("🎯 Executive Brief", use_container_width=True)
            with act2:
                btn_notes = st.button("📌 Key Takeaways & Actions", use_container_width=True)
            with act3:
                btn_deep = st.button("🔬 Deep-Dive Synthesis", use_container_width=True)

            def run_doc_summary_call(stype: str):
                if st.session_state.execution_mode == "FastAPI Backend" and is_backend_online:
                    return backend_client.summarize_document(
                        text=doc_data["full_text"],
                        summary_type=stype,
                        provider=st.session_state.model_provider
                    )
                else:
                    return generate_document_summary(
                        doc_text=doc_data["full_text"],
                        summary_type=stype,
                        model_provider=st.session_state.model_provider
                    )

            if btn_exec:
                with st.spinner("Synthesizing Executive Brief..."):
                    st.session_state.doc_result = run_doc_summary_call("executive")
            if btn_notes:
                with st.spinner("Extracting Key Notes & Actions..."):
                    st.session_state.doc_result = run_doc_summary_call("key_takeaways")
            if btn_deep:
                with st.spinner("Conducting Deep-Dive Analysis..."):
                    st.session_state.doc_result = run_doc_summary_call("deep_dive")

            # Document Q&A
            st.markdown("#### 💬 Ask the Document")
            dq_c1, dq_c2 = st.columns([4.2, 1.2])
            with dq_c1:
                doc_q = st.text_input("Ask a specific question:", placeholder="e.g. What were the total research expenditures?", key="ua_doc_q_input")
            with dq_c2:
                btn_doc_q = st.button("Query Document", use_container_width=True, type="primary")

            if btn_doc_q and doc_q.strip():
                with st.spinner("Reasoning over document context..."):
                    if st.session_state.execution_mode == "FastAPI Backend" and is_backend_online:
                        st.session_state.doc_result = backend_client.ask_document(
                            text=doc_data["full_text"],
                            question=doc_q,
                            provider=st.session_state.model_provider
                        )
                    else:
                        st.session_state.doc_result = ask_document_question(
                            doc_text=doc_data["full_text"],
                            question=doc_q,
                            model_provider=st.session_state.model_provider
                        )

            # Claude Artifacts Workspace for Document
            obs = {
                "Document": str(doc_name),
                "Format": str(doc_data.get("file_type", "Document")),
                "Words": f"{doc_data.get('word_count', 0):,}"
            }
            analysis_text = st.session_state.doc_result if st.session_state.doc_result else doc_data.get("full_text", "")
            has_new = any([btn_exec, btn_notes, btn_deep, (btn_doc_q and doc_q.strip())])

            set_initial_artifact(
                title="Synthesized Document Analysis",
                content=analysis_text,
                observations=obs,
                force_reset=has_new
            )

            render_claude_artifact_workspace(
                router=router,
                preferred_provider=st.session_state.model_provider,
                key_prefix="ua_doc_artifact"
            )

            with st.expander("📊 Document Properties & Text Inspector", expanded=False):
                st.text_area("Extracted Body Text", doc_data.get("full_text", ""), height=200, disabled=True)
        else:
            st.info("💡 Upload a PDF, DOCX, or TXT file above, or select 'invoice.pdf' from Home.")


# ===========================================================================
# VIEW 4: IMAGE ANALYSIS
# ===========================================================================
elif st.session_state.nav_selection == "Image Analysis":
    st.markdown("### 🖼️ Computer Vision Inspection & OCR Studio")
    st.caption("Inspect image geometry, calculate color palettes, and execute multimodal OCR reasoning.")

    img_file = st.file_uploader(
        "Upload Visual Asset (PNG, JPG, JPEG, WEBP, BMP, TIFF)",
        type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"],
        key="image_analysis_uploader"
    )

    if img_file:
        i_bytes = img_file.getvalue()
        i_name = img_file.name
        pil_img = load_image(io.BytesIO(i_bytes))
        st.session_state.active_image = pil_img
        st.session_state.active_img_meta = extract_image_metadata(pil_img, len(i_bytes), i_name)
        st.session_state.active_swatches = extract_dominant_colors(pil_img, 5)

    if st.session_state.active_image is not None:
        pil_img = st.session_state.active_image
        img_meta = st.session_state.active_img_meta or extract_image_metadata(pil_img, 0, "image.png")
        swatches = st.session_state.active_swatches

        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 8px; margin: 12px 0 16px 0; flex-wrap: wrap;">
                <span class="status-badge badge-sage">● Asset Ingested</span>
                <span class="status-badge badge-neutral"><b>{img_meta['filename']}</b></span>
                <span class="status-badge badge-terracotta">{img_meta['dimensions']}</span>
                <span class="status-badge badge-ochre">{img_meta['megapixels']} MP</span>
                <span class="status-badge badge-neutral">{img_meta['format']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        v_col1, v_col2 = st.columns([1, 1.8])
        with v_col1:
            st.image(pil_img, caption=img_meta["filename"], use_container_width=True)

        with v_col2:
            st.markdown("#### ⚡ Multimodal Vision Operations")
            v_task = st.selectbox(
                "Select Analysis Task",
                options=[
                    ("ocr", "🔤 OCR & Text Transcription"),
                    ("describe", "🖼️ Comprehensive Visual Description"),
                    ("chart_diagram", "📈 Chart & Diagram Extraction"),
                    ("document_audit", "📑 Document & Receipt Audit"),
                    ("custom", "❓ Custom Visual Question")
                ],
                format_func=lambda x: x[1]
            )

            custom_v_query = ""
            if v_task[0] == "custom":
                custom_v_query = st.text_input("Your question about this image:", placeholder="e.g. Which bar represents the highest revenue?")

            btn_vision = st.button("🚀 Execute Vision Analysis", use_container_width=True, type="primary")

        if btn_vision:
            with st.spinner("Analyzing image via Google Gemini..."):
                if st.session_state.execution_mode == "FastAPI Backend" and is_backend_online:
                    b64_str, _ = encode_image_to_base64(pil_img)
                    st.session_state.vision_result = backend_client.analyze_vision(
                        image_base64=b64_str,
                        task_type=v_task[0],
                        custom_prompt=custom_v_query,
                        provider=st.session_state.model_provider
                    )
                else:
                    st.session_state.vision_result = analyze_image_with_llm(
                        image=pil_img,
                        task_type=v_task[0],
                        custom_prompt=custom_v_query,
                        model_provider=st.session_state.model_provider
                    )

        w, h = pil_img.size
        obs = {
            "Asset": str(img_meta.get("filename", "image.png")),
            "Geometry": f"{w}x{h} px ({img_meta.get('megapixels')} MP)",
            "Format": str(img_meta.get("format", "Image"))
        }
        v_text = st.session_state.vision_result or f"### 📷 Visual Asset Ingested: {img_meta['filename']}\n\n- Dimensions: `{w}x{h}` px\n- Resolution: `{img_meta.get('megapixels')} MP`"

        set_initial_artifact(
            title="Synthesized Vision Analysis",
            content=v_text,
            observations=obs,
            force_reset=bool(btn_vision)
        )

        render_claude_artifact_workspace(
            router=router,
            preferred_provider=st.session_state.model_provider,
            key_prefix="img_artifact_workspace"
        )

        st.markdown("<hr class='enterprise-divider' />", unsafe_allow_html=True)
        render_image_diagnostics_panel(
            img_meta=img_meta,
            swatches=swatches,
            image=pil_img,
            expanded=False if st.session_state.vision_result else True
        )
    else:
        st.info("💡 Upload an image above, or select 'chart.png' from Home.")


# ===========================================================================
# VIEW 5: n8n AUTOMATION
# ===========================================================================
elif st.session_state.nav_selection == "n8n Automation":
    st.markdown("### 🕸️ n8n Automation Engine & Multi-Channel Dispatch")
    st.caption("Orchestrate workflows across Webhooks, Diagnostic Reports, Email, Slack, and Scheduled Jobs.")

    st.markdown(
        """
        <div class="saas-card" style="padding: 18px 24px; margin-bottom: 20px;">
            <div style="font-size: 1.05rem; font-weight: 600; margin-bottom: 8px; color: var(--accent-red);">
                🔄 Diagnostic Automation Architecture
            </div>
            <pre style="background: var(--bg-subtle); border: 1px solid var(--border-soft); border-radius: 8px; padding: 12px; font-family: 'JetBrains Mono', monospace; font-size: 0.84rem; line-height: 1.4; margin: 0; overflow-x: auto; color: var(--text-color);">
                         AI Data Analyst Studio
                                   │
                         ┌─────────┴─────────┐
                         │                   │
                     Streamlit            FastAPI
                         │                   │
                         └─────────┬─────────┘
                                   │
                             Core Pipelines
                                   │
                  ┌────────────────┼────────────────┐
                  │                │                │
              Documents          Vision          Data Analytics
                  │                │                │
                  └────────────────┼────────────────┘
                                   │
                               Google Gemini
                                   │
                                  n8n
                                   │
            ┌──────────────┬───────┼────────┬─────────────┐
            │              │       │        │             │
         Webhooks       Reports   Email    Slack       Scheduled Jobs
            </pre>
        </div>
        """,
        unsafe_allow_html=True
    )

    n8n_sub_tabs = st.tabs([
        "🌐 Webhooks Hub",
        "📋 Reports Catalog",
        "✉️ Email Dispatch",
        "💬 Slack Alerts",
        "⏱️ Scheduled Jobs",
        "📦 n8n Workflow Blueprints"
    ])

    # 1. Webhooks Hub
    with n8n_sub_tabs[0]:
        st.markdown("#### 🌐 FastAPI Inbound Webhook Endpoints for n8n")
        base_u = st.session_state.backend_url
        st.code(
            f"POST {base_u}/api/v1/n8n/webhook         # Universal Inbound Webhook\n"
            f"POST {base_u}/api/v1/n8n/webhook/document# Inbound Document Diagnostic\n"
            f"POST {base_u}/api/v1/n8n/webhook/vision  # Inbound Vision Diagnostic\n"
            f"POST {base_u}/api/v1/n8n/webhook/data    # Inbound Tabular Diagnostic",
            language="text"
        )

        st.markdown("##### 🧪 Test Webhook Trigger")
        w_col1, w_col2 = st.columns([1.5, 3])
        with w_col1:
            w_event = st.selectbox("Event Type", ["document.diagnose", "vision.diagnose", "data.diagnose", "batch.audit"])
            w_provider = st.selectbox("Provider to Invoke", ["Google Gemini", "Groq", "OpenAI", "Offline Heuristics"])
        with w_col2:
            w_content = st.text_area(
                "Event Payload Content",
                value="Executive briefing: Q3 operational uptime satisfied 99.99% reliability SLA."
            )

        if st.button("🚀 Fire Test Webhook", type="primary"):
            with st.spinner("Invoking Webhook via FastAPI..."):
                try:
                    res = backend_client.trigger_webhook(event=w_event, content=w_content, provider=w_provider)
                    st.success("Webhook Executed Successfully!")
                    st.json(res)
                except Exception as ex:
                    st.error(f"Webhook test failed: {str(ex)}")

    # 2. Reports Catalog
    with n8n_sub_tabs[1]:
        st.markdown("#### 📋 Diagnostic Reports Catalog")
        rep_col1, rep_col2 = st.columns([3, 1])
        with rep_col1:
            rep_title = st.text_input("Report Title", value="Executive Quarterly Diagnostic Synthesis")
            rep_content = st.text_area("Report Content (Markdown)", value="### Executive Summary\n\nAll operational metrics validated with zero SLA exceptions.")
        with rep_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Generate Report", use_container_width=True, type="primary"):
                try:
                    rep_res = backend_client.generate_report(title=rep_title, content=rep_content)
                    st.success(f"Report Generated! ID: `{rep_res.get('report_id')}`")
                    st.json(rep_res)
                except Exception as ex:
                    st.error(f"Report generation error: {str(ex)}")

    # 3. Email Dispatch
    with n8n_sub_tabs[2]:
        st.markdown("#### ✉️ Email Notification Dispatch via n8n")
        e_col1, e_col2 = st.columns(2)
        with e_col1:
            e_to = st.text_input("Recipient Email", value="diagnostics-lead@enterprise.local")
            e_subj = st.text_input("Subject Line", value="[Alert] AI Data Analyst Report Ready")
        with e_col2:
            e_body = st.text_area("Email Body", value="The latest multimodal diagnostic synthesis has been validated.")

        if st.button("📤 Dispatch Email Notification", type="primary"):
            with st.spinner("Dispatching email..."):
                try:
                    e_res = backend_client.dispatch_email(to_email=e_to, subject=e_subj, body=e_body)
                    st.success("Email Dispatch Triggered!")
                    st.json(e_res)
                except Exception as ex:
                    st.error(f"Email dispatch error: {str(ex)}")

    # 4. Slack Alerts
    with n8n_sub_tabs[3]:
        st.markdown("#### 💬 Slack Alert Simulator")
        s_col1, s_col2 = st.columns(2)
        with s_col1:
            s_chan = st.text_input("Slack Channel", value="#diagnostics-feed")
            s_title = st.text_input("Alert Title", value="Elevated Null Rate Detected in Staging Pipeline")
            s_sev = st.selectbox("Severity Level", ["info", "warning", "critical", "success"])
        with s_col2:
            s_msg = st.text_area("Alert Message Details", value="Table staging_transactions exhibited 14.2% missing values, crossing threshold.")

        if st.button("🚀 Dispatch Slack Alert", type="primary"):
            with st.spinner("Posting Slack message..."):
                try:
                    s_res = backend_client.dispatch_slack(
                        channel=s_chan,
                        title=s_title,
                        message=s_msg,
                        severity=s_sev,
                        metrics={"Threshold": "5.0%", "Observed": "14.2%", "Status": s_sev.upper()}
                    )
                    st.success("Slack Alert Dispatched!")
                    st.json(s_res)
                except Exception as ex:
                    st.error(f"Slack alert error: {str(ex)}")

    # 5. Scheduled Jobs
    with n8n_sub_tabs[4]:
        st.markdown("#### ⏱️ Scheduled Diagnostic Cron Jobs")
        schedules = backend_client.list_schedules()
        if schedules:
            for job in schedules:
                with st.expander(f"🕒 {job['name']} (`{job['cron']}`)", expanded=True):
                    sc1, sc2, sc3 = st.columns([3, 1.5, 1])
                    with sc1:
                        st.write(job['description'])
                        st.caption(f"Service: `{job['target_service'].upper()}` • Next: `{job.get('next_run')}`")
                    with sc2:
                        st.write(f"Status: **{job['status'].upper()}**")
                    with sc3:
                        if st.button("Run Now", key=f"run_{job['job_id']}", use_container_width=True):
                            with st.spinner("Executing job..."):
                                try:
                                    jres = backend_client.trigger_schedule(job['job_id'], provider=st.session_state.model_provider)
                                    st.success(f"Executed! Report ID: `{jres.get('report_id')}`")
                                    st.json(jres)
                                except Exception as ex:
                                    st.error(f"Trigger failed: {str(ex)}")
        else:
            st.info("No registered scheduled jobs found from backend.")

    # 6. Workflow Blueprints
    with n8n_sub_tabs[5]:
        st.markdown("#### 📦 Download Ready-to-Import n8n Workflow JSON Blueprints")
        workflows_dir = os.path.join(os.getcwd(), "n8n", "workflows")
        if os.path.isdir(workflows_dir):
            for fname in os.listdir(workflows_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(workflows_dir, fname)
                    with open(fpath, "r", encoding="utf-8") as wf_file:
                        content_str = wf_file.read()
                        wf_json = json.loads(content_str)
                        wf_name = wf_json.get("name", fname)
                        nodes_count = len(wf_json.get("nodes", []))

                    wcol1, wcol2 = st.columns([3.5, 1.5])
                    with wcol1:
                        st.markdown(f"**{wf_name}** (`{fname}`)")
                        st.caption(f"Contains {nodes_count} orchestrated nodes • Targets AI Data Analyst FastAPI")
                    with wcol2:
                        st.download_button(
                            label=f"⬇️ Download {fname}",
                            data=content_str,
                            file_name=fname,
                            mime="application/json",
                            key=f"dl_{fname}",
                            use_container_width=True
                        )


# ===========================================================================
# VIEW 6: SETTINGS
# ===========================================================================
elif st.session_state.nav_selection == "Settings":
    st.markdown("### ⚙️ System Settings & AI Architecture Configuration")
    st.caption("Manage execution engines, model catalogs, theme preferences, and observability.")

    set_col1, set_col2 = st.columns(2)

    with set_col1:
        st.markdown("#### 🌐 Execution Engine & Backend Probe")
        st.session_state.execution_mode = st.radio(
            "Execution Engine",
            options=["FastAPI Backend", "Direct Core Engine"],
            index=0 if is_backend_online else 1,
            help="FastAPI routes requests through the REST backend. Direct Core executes pipelines locally."
        )

        custom_backend = st.text_input("FastAPI Base URL", value=st.session_state.backend_url)
        if custom_backend != st.session_state.backend_url:
            st.session_state.backend_url = custom_backend
            backend_client = BackendClient(base_url=custom_backend)

        if st.button("🔄 Probe Backend Health & Latency", use_container_width=True):
            ok, meta, lat = backend_client.check_health()
            if ok:
                st.success(f"FastAPI Backend is Online! Latency: {lat}ms")
            else:
                st.warning("FastAPI backend not reachable at this URL.")

        st.markdown("<hr class='enterprise-divider' />", unsafe_allow_html=True)
        st.markdown("#### 🎨 Theme Mode")
        theme_choice = st.radio(
            "Color Theme",
            options=["Light", "Dark"],
            index=1 if st.session_state.dark_mode else 0,
            horizontal=True
        )
        if (theme_choice == "Dark") != st.session_state.dark_mode:
            st.session_state.dark_mode = (theme_choice == "Dark")
            st.session_state.theme_mode = theme_choice
            st.query_params["theme"] = "dark" if st.session_state.dark_mode else "light"
            st.rerun()

        st.markdown("<hr class='enterprise-divider' />", unsafe_allow_html=True)
        st.markdown("#### 👤 Account & Session")
        if st.session_state.auth_user:
            u_name = st.session_state.auth_user.get("name", "Analyst")
            u_email = st.session_state.auth_user.get("email", "")
            st.success(f"Signed in as **{u_name}** (`{u_email}`)")
            if st.button("Sign Out of Account", key="settings_signout_btn", use_container_width=True):
                backend_client.logout(st.session_state.auth_token)
                st.session_state.auth_token = None
                st.session_state.auth_user = None
                st.rerun()
        else:
            st.info("Currently running in Guest session mode.")
            if st.button("Sign In to Enterprise Account", key="settings_signin_btn", use_container_width=True):
                show_auth_modal()

    with set_col2:
        st.markdown("#### 🧠 Configured AI Model Provider")
        st.info("Primary Provider: **Google Gemini** (Gemini 3.8 Flash multimodal reasoning)")

        # Catalog listing derived from backend or local checks
        providers_meta = backend_client.get_providers()
        if providers_meta:
            configured_names = [p["name"] for p in providers_meta if p.get("is_configured")]
        else:
            configured_names = ["Google Gemini", "Offline Heuristics"]

        selected_p = st.selectbox(
            "Active LLM Provider",
            options=configured_names,
            index=configured_names.index(st.session_state.model_provider) if st.session_state.model_provider in configured_names else 0
        )
        st.session_state.model_provider = selected_p

        provider_info = MODEL_CATALOG.get(selected_p, {})
        default_model = provider_info.get("primary_model", "gemini-3.8-flash")
        st.selectbox("Model Tier", options=provider_info.get("models", [default_model]), index=0)

        st.text_input("API Key Override (Optional)", type="password", placeholder="Uses environment or .env if blank")

        st.markdown("<hr class='enterprise-divider' />", unsafe_allow_html=True)
        st.markdown("#### 📁 Instant Demo Datasets Quick-Loader")
        d1, d2, d3 = st.columns(3)
        with d1:
            if st.button("📊 Load Data Demo", use_container_width=True):
                demo_csv = os.path.join(os.getcwd(), "sample_data", "sample_business_metrics.csv")
                if os.path.isfile(demo_csv):
                    with open(demo_csv, "rb") as f:
                        b = f.read()
                    df = load_structured_data(io.BytesIO(b), "sample_business_metrics.csv")
                    st.session_state.active_df = df
                    st.session_state.active_df_name = "sample_business_metrics.csv"
                    st.session_state.active_df_health = generate_data_health_card(df, "sample_business_metrics.csv")
                    st.session_state.nav_selection = "Upload & Analyze"
                    st.rerun()
        with d2:
            if st.button("📄 Load Doc Demo", use_container_width=True):
                demo_doc = os.path.join(os.getcwd(), "sample_data", "sample_financial_report.txt")
                if os.path.isfile(demo_doc):
                    with open(demo_doc, "rb") as f:
                        b = f.read()
                    doc_data = load_document(io.BytesIO(b), "sample_financial_report.txt")
                    st.session_state.active_doc_data = doc_data
                    st.session_state.active_doc_name = "sample_financial_report.txt"
                    st.session_state.nav_selection = "Upload & Analyze"
                    st.rerun()
        with d3:
            if st.button("🖼️ Load Vision Demo", use_container_width=True):
                demo_img = os.path.join(os.getcwd(), "sample_data", "sample_performance_chart.png")
                if os.path.isfile(demo_img):
                    with open(demo_img, "rb") as f:
                        b = f.read()
                    pil_img = load_image(io.BytesIO(b))
                    st.session_state.active_image = pil_img
                    st.session_state.active_img_meta = extract_image_metadata(pil_img, len(b), "sample_performance_chart.png")
                    st.session_state.active_swatches = extract_dominant_colors(pil_img, 5)
                    st.session_state.nav_selection = "Image Analysis"
                    st.rerun()

    st.markdown("<hr class='enterprise-divider' />", unsafe_allow_html=True)
    st.markdown("#### 📊 Observability & System Telemetry")
    render_sidebar_telemetry()
