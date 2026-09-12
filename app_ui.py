import os
import platform
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from auth_gsc import (
    get_gsc_service, get_searchconsole_v1_service, get_sites, 
    authenticate_local, get_auth_url, exchange_code, load_client_config,
    authenticate_service_account
)
from data_fetcher import fetch_gsc_data
from database import init_db, save_data, load_data, load_alerts
from seo_engine import (
    get_overview, get_quick_wins, get_cannibalization,
    get_search_intent, get_long_tail_keywords, get_zero_click_keywords,
    get_content_decay, get_zombie_pages, get_brand_vs_nonbrand,
    get_device_breakdown, get_country_breakdown, get_top_pages,
    get_winning_keywords, get_high_impression_low_ctr,
    generate_mock_gsc_data, parse_gsc_csv, generate_centralec_gsc_data
)
from report_generator import generate_pdf_report
from alerts import get_unread_alerts

# Advanced Engines
from inspection_engine import inspect_single_url, inspect_bulk_urls
from algo_analyzer import analyze_algorithm_impact, MAJOR_ALGO_UPDATES
from ctr_modeler import build_empirical_ctr_curve, forecast_traffic_opportunity
from sitemap_engine import list_sitemaps, submit_sitemap
from log_reconciliation import reconcile_crawl_with_gsc, reconcile_server_logs_with_gsc
from automation_generator import generate_automation_bundle, GITHUB_ACTIONS_WORKFLOW, HEADLESS_AUDIT_SCRIPT

# ==============================
# Page Config
# ==============================
st.set_page_config(
    page_title="GSC Pro - Enterprise SEO Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# Custom CSS - Authentic Google Search Console Light UI
# ==============================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; }
    
    .main { 
        background: #ffffff !important; 
    }
    .stApp {
        background: #ffffff !important;
        color: #202124 !important;
    }
    section[data-testid="stSidebar"] {
        background: #f8f9fa !important;
        border-right: 1px solid #dadce0 !important;
    }
    section[data-testid="stSidebar"] .stRadio label {
        color: #3c4043 !important;
        font-size: 13px;
        padding: 6px 10px;
        border-radius: 20px;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label[data-checked="true"] {
        background: #e8f0fe !important;
        color: #1a73e8 !important;
        font-weight: 600 !important;
    }
    
    /* GSC Top Header */
    .gsc-top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 16px;
        background: #ffffff;
        border-bottom: 1px solid #dadce0;
        margin: -4rem -3rem 1.5rem -3rem;
        position: sticky;
        top: 0;
        z-index: 999;
    }
    .gsc-search-pill {
        display: flex;
        align-items: center;
        gap: 12px;
        background: #e8f0fe;
        border-radius: 24px;
        padding: 8px 20px;
        width: 48%;
        max-width: 650px;
        color: #3c4043;
        font-size: 13px;
    }
    
    /* GSC Filter Chips */
    .gsc-chip-group {
        display: inline-flex;
        border: 1px solid #dadce0;
        border-radius: 4px;
        overflow: hidden;
    }
    .gsc-chip {
        padding: 5px 12px;
        font-size: 12px;
        color: #3c4043;
        background: #ffffff;
        border-right: 1px solid #dadce0;
        cursor: pointer;
        font-weight: 500;
    }
    .gsc-chip:last-child {
        border-right: none;
    }
    .gsc-chip-active {
        background: #e8f0fe !important;
        color: #1a73e8 !important;
        font-weight: 600 !important;
    }
    .gsc-filter-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 14px;
        border-radius: 16px;
        border: 1px solid #dadce0;
        font-size: 12px;
        color: #3c4043;
        background: #ffffff;
        font-weight: 500;
    }
    
    /* GSC Scorecard Cards */
    .gsc-tile-wrapper {
        border: 1px solid #dadce0;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 12px;
        background: #ffffff;
    }
    .gsc-card {
        padding: 14px 16px;
        min-height: 155px;
        position: relative;
        transition: all 0.15s ease-in-out;
        border-radius: 0px;
    }
    .gsc-card-clicks-on {
        background: #1a73e8 !important;
        color: #ffffff !important;
    }
    .gsc-card-imps-on {
        background: #5e35b1 !important;
        color: #ffffff !important;
    }
    .gsc-card-ctr-on {
        background: #00897b !important;
        color: #ffffff !important;
    }
    .gsc-card-pos-on {
        background: #e8710a !important;
        color: #ffffff !important;
    }
    .gsc-card-off {
        background: #ffffff !important;
        color: #3c4043 !important;
        border-right: 1px solid #dadce0;
    }
    .gsc-card-off:last-child {
        border-right: none;
    }
    
    .gsc-card-title {
        font-size: 12px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .gsc-card-val-big {
        font-size: 30px;
        font-weight: 600;
        line-height: 1.15;
        margin-top: 6px;
    }
    .gsc-card-sub {
        font-size: 11px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 2px;
        opacity: 0.9;
    }
    .gsc-card-val-comp {
        font-size: 19px;
        font-weight: 600;
        line-height: 1.15;
        margin-top: 8px;
    }
    .gsc-card-info-icon {
        position: absolute;
        bottom: 10px;
        right: 12px;
        font-size: 12px;
        opacity: 0.7;
    }

    /* AI Banner */
    .gsc-ai-banner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #ffffff;
        border: 1px solid #dadce0;
        border-radius: 8px;
        padding: 12px 18px;
        margin: 14px 0 20px 0;
    }

    /* Streamlit dataframe & tabs */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 2px solid #dadce0;
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 13px !important;
        font-weight: 600 !important;
        color: #5f6368 !important;
        padding: 10px 16px !important;
    }
    .stTabs [aria-selected="true"] {
        color: #1a73e8 !important;
        border-bottom: 3px solid #1a73e8 !important;
    }
    
    .stButton > button {
        background: #1a73e8;
        color: white;
        border: none;
        border-radius: 4px;
        font-weight: 500;
        font-size: 13px;
        padding: 6px 16px;
    }
    .stButton > button:hover {
        background: #1765cc;
    }
</style>
""", unsafe_allow_html=True)

# ==============================
# Database & State Initialization (Per-User Session)
# ==============================
init_db()

if 'service' not in st.session_state:
    st.session_state.service = None
if 'service_v1' not in st.session_state:
    st.session_state.service_v1 = None
if 'sites' not in st.session_state or not st.session_state.sites:
    st.session_state.sites = ["https://centralec-electrical.co.uk/"]
if 'current_site' not in st.session_state or not st.session_state.current_site:
    st.session_state.current_site = "https://centralec-electrical.co.uk/"
if 'user_creds' not in st.session_state:
    st.session_state.user_creds = None

if 'df' not in st.session_state or st.session_state.df.empty:
    _df_curr, _df_daily_curr, _df_daily_comp, _metrics = generate_centralec_gsc_data()
    st.session_state.df = _df_curr
    st.session_state.df_daily_curr = _df_daily_curr
    st.session_state.df_daily_comp = _df_daily_comp
    st.session_state.gsc_metrics = _metrics

def resolve_redirect_uri(cfg):
    """Picks the best redirect URI matching cloud or local environment."""
    if not cfg or 'web' not in cfg:
        return 'https://sobuz-gsc-dashboard.streamlit.app/'
    uris = cfg.get('web', {}).get('redirect_uris', ['https://sobuz-gsc-dashboard.streamlit.app/'])
    if not uris:
        return 'https://sobuz-gsc-dashboard.streamlit.app/'
    # Detect Streamlit Cloud (Linux container or cloud environment variables)
    is_cloud = (platform.system() == 'Linux') or ('STREAMLIT_SHARING_MODE' in os.environ)
    if is_cloud:
        for u in uris:
            if 'streamlit.app' in u and u.endswith('/'):
                return u
        for u in uris:
            if 'streamlit.app' in u:
                return u
    else:
        for u in uris:
            if 'localhost' in u or '127.0.0.1' in u:
                return u
    return uris[0]


# ==============================
# Multi-User Web OAuth Callback Handler
# ==============================
query_params = st.query_params
if 'code' in query_params and st.session_state.service is None:
    code = query_params['code']
    try:
        cfg = load_client_config()
        redirect_uri = resolve_redirect_uri(cfg)
        
        creds = exchange_code(code, redirect_uri, config=cfg)
        svc = get_gsc_service(creds)
        svc_v1 = get_searchconsole_v1_service(creds)
        sites = get_sites(svc)
        
        st.session_state.user_creds = creds
        st.session_state.service = svc
        st.session_state.service_v1 = svc_v1
        st.session_state.sites = sites
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Web OAuth Error: {e}")

# ==============================
# Sidebar
# ==============================
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 12px 0 8px 0;'>
        <div style='font-size:32px'>🔍</div>
        <div style='font-size:18px; font-weight:700; 
             background: linear-gradient(135deg, #6366f1, #a855f7);
             -webkit-background-clip: text;
             -webkit-text-fill-color: transparent;'>
             GSC Pro Enterprise
        </div>
        <div style='font-size:11px; color:#94a3b8;'>Multi-User Cloud & Local Ready</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # Connection Status
    is_connected = (st.session_state.service and st.session_state.sites) or not st.session_state.df.empty
    if is_connected:
        status_label = f"Connected ({len(st.session_state.sites)} properties)" if st.session_state.sites else "Data Loaded (Demo/CSV)"
        st.markdown(f"**Status:** <span style='color:#10b981; font-weight:600;'>● {status_label}</span>", unsafe_allow_html=True)
        if st.button("🚪 Logout / Reset Data", use_container_width=True):
            st.session_state.service = None
            st.session_state.service_v1 = None
            st.session_state.sites = []
            st.session_state.df = pd.DataFrame()
            st.session_state.current_site = None
            st.session_state.user_creds = None
            st.rerun()
    else:
        st.markdown("**🔐 Select Connection Mode:**")
        auth_mode = st.radio(
            "Connection Method",
            [
                "🌐 Google OAuth (Sign-In)",
                "🚀 1-Click Demo (Instant View)",
                "📁 Upload GSC CSV / Export",
                "🔑 Service Account Key"
            ],
            index=0,
            label_visibility="collapsed"
        )

        if auth_mode == "🌐 Google OAuth (Sign-In)":
            cfg = load_client_config()
            if cfg:
                default_redirect = resolve_redirect_uri(cfg)
                try:
                    auth_url, _ = get_auth_url(default_redirect, config=cfg)
                    st.link_button("🌐 Connect with Google (Cloud/Web)", auth_url, use_container_width=True, type="primary")
                except Exception as ex:
                    st.error(f"OAuth URL error: {ex}")
                
                with st.expander("📋 Alternative: Manual Code Paste"):
                    manual_code = st.text_input("Paste redirect URL or ?code=...", key="manual_oauth_code")
                    if st.button("🚀 Connect via Code", use_container_width=True):
                        if manual_code.strip():
                            try:
                                raw_code = manual_code.strip()
                                if 'code=' in raw_code:
                                    raw_code = raw_code.split('code=')[1].split('&')[0]
                                from urllib.parse import unquote
                                raw_code = unquote(raw_code)
                                creds = exchange_code(raw_code, default_redirect, config=cfg)
                                svc = get_gsc_service(creds)
                                svc_v1 = get_searchconsole_v1_service(creds)
                                sites = get_sites(svc)
                                st.session_state.user_creds = creds
                                st.session_state.service = svc
                                st.session_state.service_v1 = svc_v1
                                st.session_state.sites = sites
                                st.success("✅ Logged in successfully!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Exchange error: {ex}")
            else:
                st.warning("⚠️ Google Cloud credentials not configured.")
                uploaded_creds = st.file_uploader("Upload credentials.json", type=['json'], key="sidebar_creds_uploader")
                if uploaded_creds:
                    try:
                        loaded_cfg = json.load(uploaded_creds)
                        st.session_state.client_config = loaded_cfg
                        st.success("Credentials saved to session!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Invalid JSON: {ex}")

            if os.path.exists(os.path.join(os.path.dirname(__file__), 'credentials.json')):
                if st.button("💻 Local 1-Click Login (Desktop)", use_container_width=True):
                    with st.spinner("Authorizing in browser..."):
                        try:
                            creds = authenticate_local(port=8080)
                            svc = get_gsc_service(creds)
                            svc_v1 = get_searchconsole_v1_service(creds)
                            sites = get_sites(svc)
                            st.session_state.user_creds = creds
                            st.session_state.service = svc
                            st.session_state.service_v1 = svc_v1
                            st.session_state.sites = sites
                            st.success(f"✅ Connected! Found {len(sites)} sites.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Auth failed: {e}")

        elif auth_mode == "🚀 1-Click Demo (Instant View)":
            st.caption("💡 **Instant Access:** Explore all engines with 1,000+ realistic SEO data points.")
            if st.button("✨ Load Full Demo Data (90 Days)", use_container_width=True, type="primary"):
                with st.spinner("Generating SEO data..."):
                    mock_df = generate_mock_gsc_data(site_name="https://mybrand-store.com", days=90)
                    st.session_state.df = mock_df
                    st.session_state.sites = ["https://mybrand-store.com (Demo Property)"]
                    st.session_state.current_site = "https://mybrand-store.com (Demo Property)"
                    st.success("✅ Demo Data Loaded!")
                    st.rerun()

        elif auth_mode == "📁 Upload GSC CSV / Export":
            st.caption("📂 Upload GSC Performance CSV or ZIP export without any API login.")
            csv_file = st.file_uploader("Upload CSV or ZIP", type=['csv', 'zip'], key="gsc_csv_uploader")
            if csv_file:
                try:
                    parsed_df = parse_gsc_csv(csv_file)
                    if not parsed_df.empty:
                        st.session_state.df = parsed_df
                        st.session_state.sites = [f"{csv_file.name} (Uploaded Data)"]
                        st.session_state.current_site = f"{csv_file.name} (Uploaded Data)"
                        st.success(f"✅ Loaded {len(parsed_df):,} rows from export!")
                        st.rerun()
                    else:
                        st.error("Could not parse rows from CSV.")
                except Exception as e:
                    st.error(f"CSV Parse Error: {e}")

        elif auth_mode == "🔑 Service Account Key":
            st.caption("🔒 **Industry Standard:** Direct JSON key authentication.")
            sa_file = st.file_uploader("Upload service_account.json", type=['json'], key="sa_uploader")
            sa_paste = st.text_area("Or Paste Service Account JSON:", height=90, placeholder='{"type": "service_account", ...}')
            
            local_sa_path = os.path.join(os.path.dirname(__file__), 'service_account.json')
            if os.path.exists(local_sa_path):
                if st.button("📁 Load Local service_account.json", use_container_width=True):
                    try:
                        creds, svc, svc_v1, sites = authenticate_service_account(local_sa_path)
                        st.session_state.user_creds = creds
                        st.session_state.service = svc
                        st.session_state.service_v1 = svc_v1
                        st.session_state.sites = sites if sites else ["Manual Property"]
                        st.success("✅ Service Account connected!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

            if st.button("⚡ Connect Service Account", use_container_width=True):
                target_sa = None
                if sa_file:
                    try:
                        target_sa = json.load(sa_file)
                    except Exception as ex:
                        st.error(f"Invalid JSON file: {ex}")
                elif sa_paste.strip():
                    try:
                        target_sa = json.loads(sa_paste.strip())
                    except Exception as ex:
                        st.error(f"Invalid JSON text: {ex}")
                
                if target_sa:
                    with st.spinner("Authenticating Service Account..."):
                        try:
                            creds, svc, svc_v1, sites = authenticate_service_account(target_sa)
                            st.session_state.user_creds = creds
                            st.session_state.service = svc
                            st.session_state.service_v1 = svc_v1
                            st.session_state.sites = sites if sites else ["https://yourdomain.com/"]
                            st.success("✅ Service Account Connected!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Service Account Error: {e}")
                else:
                    st.warning("Please upload a file or paste your Service Account JSON.")

    st.divider()

    # Property & Date Selectors
    selected_site = None
    start_str = None
    end_str = None

    if st.session_state.sites or not st.session_state.df.empty:
        site_options = list(st.session_state.sites) if st.session_state.sites else [st.session_state.current_site or "Active Property"]
        site_options.append("➕ Enter Custom Property URL")
        selected_choice = st.selectbox("🌐 GSC Property", site_options)
        if selected_choice == "➕ Enter Custom Property URL":
            selected_site = st.text_input("Enter Property URL:", value="https://")
        else:
            selected_site = selected_choice
        if st.session_state.current_site != selected_site:
            st.session_state.current_site = selected_site
            if st.session_state.service:
                st.session_state.df = pd.DataFrame()

        st.markdown("**📅 Date Range**")
        period = st.radio("Period", [
            "Last 7 days", "Last 30 days", "Last 90 days", "Last 6 months", "Custom"
        ], index=1, label_visibility="collapsed")

        if period == "Custom":
            c1, c2 = st.columns(2)
            with c1:
                start_date = st.date_input("Start", datetime.now() - timedelta(days=30))
            with c2:
                end_date = st.date_input("End", datetime.now())
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
        else:
            days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90, "Last 6 months": 180}
            days = days_map[period]
            end_str = datetime.now().strftime('%Y-%m-%d')
            start_str = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("🚀 Fetch Live", use_container_width=True):
                with st.spinner("Fetching GSC API data..."):
                    try:
                        df = fetch_gsc_data(st.session_state.service, selected_site, start_str, end_str)
                        if not df.empty:
                            save_data(df, selected_site)
                            st.session_state.df = df
                            st.success(f"Fetched {len(df):,} rows!")
                        else:
                            st.warning("No data found.")
                    except Exception as e:
                        st.error(f"Error: {e}")
        with col_b2:
            if st.button("📂 Load Saved", use_container_width=True):
                df = load_data(selected_site, start_str, end_str)
                if not df.empty:
                    st.session_state.df = df
                    st.success(f"Loaded {len(df):,} rows!")
                else:
                    st.info("No saved data.")

    st.divider()

    # Navigation Menu
    page = st.radio("📌 Navigation", [
        "📊 Overview",
        "🔍 Keywords",
        "📄 Pages",
        "⚡ Quick Wins",
        "🔬 URL & Canonical Inspector",
        "📉 Algo Update Impact",
        "📈 Custom CTR Curve",
        "🗺️ Sitemaps Manager",
        "🪵 Log Reconciliation",
        "🎯 Intent & Regex",
        "🤖 AEO & Preferred Sources",
        "⚙️ 24/7 Automation",
        "🚨 Alerts",
        "📤 Reports & Export"
    ])

# ==============================
# Main Content
# ==============================
df = st.session_state.df
service = st.session_state.service
service_v1 = st.session_state.service_v1
current_site = st.session_state.current_site

# ----------------------------------------------------
# 1. Performance Overview
# ----------------------------------------------------
if page == "📊 Overview":
    # 1. GSC Top Navigation Header
    st.markdown(f"""
    <div class="gsc-top-bar">
        <div style="display:flex; align-items:center; gap:16px;">
            <span style="font-size:20px; color:#5f6368; cursor:pointer;">☰</span>
            <div style="display:flex; align-items:center; gap:8px;">
                <svg width="24" height="24" viewBox="0 0 48 48">
                    <path fill="#4285F4" d="M43.6 20.1H42V20H24v8h11.3C33.7 33.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8.1 3.1l5.7-5.7C34.4 6.6 29.5 4.8 24 4.8 13.4 4.8 4.8 13.4 4.8 24S13.4 43.2 24 43.2c10.6 0 19.2-8.6 19.2-19.2 0-1.3-.1-2.6-.4-3.9z"/>
                    <path fill="#EA4335" d="M6.3 14.7l6.6 4.8C14.7 16.1 19 13.6 24 13.6c3.1 0 5.9 1.2 8.1 3.1l5.7-5.7C34.4 6.6 29.5 4.8 24 4.8c-7.7 0-14.4 4.3-17.7 9.9z"/>
                    <path fill="#FBBC05" d="M24 43.2c5.3 0 10.1-1.8 13.8-4.9l-6.4-5.3c-2.1 1.4-4.6 2.2-7.4 2.2-5.3 0-9.7-3.6-11.3-8.5l-6.6 5.1C9.5 38.3 16.2 43.2 24 43.2z"/>
                    <path fill="#34A853" d="M43.6 20.1H42V20H24v8h11.3c-.9 2.7-2.6 4.9-4.9 6.5l6.4 5.3c4.7-4.4 7.6-10.8 7.6-18.7 0-1.3-.1-2.6-.4-3.9z"/>
                </svg>
                <span style="font-size:18px; font-weight:500; color:#5f6368; letter-spacing:-0.2px;">Google Search Console</span>
            </div>
        </div>
        <div class="gsc-search-pill">
            <span style="color:#5f6368; font-size:15px;">🔍</span>
            <span style="color:#3c4043; font-size:13px; font-weight:400; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">Inspect any URL in "{current_site or 'https://centralec-electrical.co.uk/'}"</span>
        </div>
        <div style="display:flex; align-items:center; gap:16px;">
            <span style="color:#5f6368; font-size:17px; cursor:pointer;" title="Help">❔</span>
            <span style="color:#5f6368; font-size:17px; cursor:pointer;" title="Feedback">💬</span>
            <div style="position:relative; cursor:pointer;">
                <span style="color:#5f6368; font-size:17px;">🔔</span>
                <span style="position:absolute; top:-4px; right:-6px; background:#d93025; color:white; font-size:10px; font-weight:bold; border-radius:50%; width:15px; height:15px; display:flex; align-items:center; justify-content:center;">0</span>
            </div>
            <span style="color:#5f6368; font-size:17px; cursor:pointer;" title="Google apps">⠿</span>
            <div style="width:30px; height:30px; border-radius:50%; background:#5c6bc0; color:white; display:flex; align-items:center; justify-content:center; font-weight:600; font-size:13px;">S</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. GSC Performance Header
    st.markdown(f"""
    <div style="margin-bottom: 14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
            <span style="font-size:22px; font-weight:400; color:#202124;">Performance</span>
            <div style="display:flex; align-items:center; gap:6px; color:#1a73e8; font-size:13px; font-weight:500; cursor:pointer;">
                <span>📥</span>
                <span>EXPORT</span>
            </div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                <div class="gsc-chip-group">
                    <span class="gsc-chip">24 hours</span>
                    <span class="gsc-chip">7 days</span>
                    <span class="gsc-chip">28 days</span>
                    <span class="gsc-chip">3 months</span>
                    <span class="gsc-chip gsc-chip-active">Compare ▾</span>
                </div>
                <div class="gsc-filter-pill">Search type: Web ▾</div>
                <div class="gsc-filter-pill">+ Add filter</div>
                <span style="background:#1a73e8; color:white; border-radius:50%; width:24px; height:24px; display:inline-flex; align-items:center; justify-content:center; font-size:12px; cursor:pointer;">⚙</span>
                <span style="color:#1a73e8; font-size:12px; font-weight:500; cursor:pointer;">Reset filters</span>
            </div>
            <div style="color:#70757a; font-size:12px;">Last update: 12.5 hours ago</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Metrics calculation
    metrics = st.session_state.get('gsc_metrics', {})
    total_clicks = metrics.get('total_clicks', int(df['clicks'].sum()) if not df.empty and 'clicks' in df.columns else 83)
    comp_clicks = metrics.get('total_clicks_comp', 20)
    total_imps = metrics.get('total_impressions', int(df['impressions'].sum()) if not df.empty and 'impressions' in df.columns else 16600)
    comp_imps = metrics.get('total_impressions_comp', 1020)
    avg_ctr = metrics.get('avg_ctr', round(total_clicks / total_imps * 100, 1) if total_imps > 0 else 0.5)
    comp_ctr = metrics.get('avg_ctr_comp', 2.0)
    avg_pos = metrics.get('avg_position', 33.4)
    comp_pos = metrics.get('avg_position_comp', 52.7)

    # Format numbers (16.6K, 1.02K)
    def fmt_gsc_num(val):
        if val >= 1000000:
            return f"{val/1000000:.1f}M"
        elif val >= 1000:
            return f"{val/1000:.2g}K" if val < 10000 else f"{val/1000:.1f}K"
        return f"{val:,}"

    imps_disp = fmt_gsc_num(total_imps)
    comp_imps_disp = fmt_gsc_num(comp_imps)

    # 3. Authentic 4-Scorecard Connected Container with Toggles
    chk_c1, chk_c2, chk_c3, chk_c4 = st.columns(4)
    with chk_c1:
        show_clicks = st.checkbox("Total clicks", value=True, key="gsc_chk_clicks")
    with chk_c2:
        show_impressions = st.checkbox("Total impressions", value=True, key="gsc_chk_impressions")
    with chk_c3:
        show_ctr = st.checkbox("Average CTR", value=False, key="gsc_chk_ctr")
    with chk_c4:
        show_position = st.checkbox("Average position", value=False, key="gsc_chk_position")

    # Render Connected Scorecards
    sc_col1, sc_col2, sc_col3, sc_col4 = st.columns(4)
    
    with sc_col1:
        card_class = "gsc-card-clicks-on" if show_clicks else "gsc-card-off"
        check_icon = "☑" if show_clicks else "☐"
        st.markdown(f"""
        <div class="gsc-tile-wrapper">
            <div class="gsc-card {card_class}">
                <div class="gsc-card-title">{check_icon} Total clicks</div>
                <div class="gsc-card-val-big">{total_clicks}</div>
                <div class="gsc-card-sub"><span>Last 3 months</span><span style="font-weight:bold; font-size:14px;">—</span></div>
                <div class="gsc-card-val-comp">{comp_clicks}</div>
                <div class="gsc-card-sub"><span>Previous 3 months</span><span style="font-weight:bold; letter-spacing:2px;">- - -</span></div>
                <div class="gsc-card-info-icon">?</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with sc_col2:
        card_class = "gsc-card-imps-on" if show_impressions else "gsc-card-off"
        check_icon = "☑" if show_impressions else "☐"
        st.markdown(f"""
        <div class="gsc-tile-wrapper">
            <div class="gsc-card {card_class}">
                <div class="gsc-card-title">{check_icon} Total impressions</div>
                <div class="gsc-card-val-big">{imps_disp}</div>
                <div class="gsc-card-sub"><span>Last 3 months</span><span style="font-weight:bold; font-size:14px;">—</span></div>
                <div class="gsc-card-val-comp">{comp_imps_disp}</div>
                <div class="gsc-card-sub"><span>Previous 3 months</span><span style="font-weight:bold; letter-spacing:2px;">- - -</span></div>
                <div class="gsc-card-info-icon">?</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with sc_col3:
        card_class = "gsc-card-ctr-on" if show_ctr else "gsc-card-off"
        check_icon = "☑" if show_ctr else "☐"
        st.markdown(f"""
        <div class="gsc-tile-wrapper">
            <div class="gsc-card {card_class}">
                <div class="gsc-card-title">{check_icon} Average CTR</div>
                <div class="gsc-card-val-big">{avg_ctr}%</div>
                <div class="gsc-card-sub"><span>Last 3 months</span></div>
                <div class="gsc-card-val-comp">{comp_ctr}%</div>
                <div class="gsc-card-sub"><span>Previous 3 months</span></div>
                <div class="gsc-card-info-icon">?</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with sc_col4:
        card_class = "gsc-card-pos-on" if show_position else "gsc-card-off"
        check_icon = "☑" if show_position else "☐"
        st.markdown(f"""
        <div class="gsc-tile-wrapper">
            <div class="gsc-card {card_class}">
                <div class="gsc-card-title">{check_icon} Average position</div>
                <div class="gsc-card-val-big">{avg_pos}</div>
                <div class="gsc-card-sub"><span>Last 3 months</span></div>
                <div class="gsc-card-val-comp">{comp_pos}</div>
                <div class="gsc-card-sub"><span>Previous 3 months</span></div>
                <div class="gsc-card-info-icon">?</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Dropdown pill "Daily ▾"
    st.markdown("""
    <div style="display:flex; justify-content:flex-end; margin: 4px 0 2px 0;">
        <span class="gsc-filter-pill" style="border-radius:18px; padding:4px 14px; font-size:12px;">Daily ▾</span>
    </div>
    """, unsafe_allow_html=True)

    # 4. Authentic Multi-Axis Plotly Timeline Chart
    df_daily_curr = st.session_state.get('df_daily_curr', pd.DataFrame())
    df_daily_comp = st.session_state.get('df_daily_comp', pd.DataFrame())

    if df_daily_curr.empty and not df.empty and 'date' in df.columns:
        df_daily_curr = df.groupby('date').agg(
            clicks=('clicks', 'sum'),
            impressions=('impressions', 'sum'),
            position=('position', 'mean')
        ).reset_index().sort_values('date')
        df_daily_curr['ctr'] = np.where(df_daily_curr['impressions'] > 0, (df_daily_curr['clicks'] / df_daily_curr['impressions'] * 100).round(2), 0.0)
        df_daily_curr['day_index'] = list(range(len(df_daily_curr)))

    if not df_daily_curr.empty:
        use_secondary = show_impressions or show_position
        fig = make_subplots(specs=[[{"secondary_y": use_secondary}]])

        # Trace 1: Current Clicks (Solid #1a73e8)
        if show_clicks and 'clicks' in df_daily_curr.columns:
            x_vals = df_daily_curr['day_index'] if 'day_index' in df_daily_curr.columns else df_daily_curr['date']
            fig.add_trace(go.Scatter(
                x=x_vals, y=df_daily_curr['clicks'], name='Clicks',
                line=dict(color='#1a73e8', width=2.4),
                hoverinfo='y+name'
            ), secondary_y=False)

        # Trace 2: Comp Clicks (Dashed #4285f4)
        if show_clicks and not df_daily_comp.empty and 'clicks' in df_daily_comp.columns:
            x_vals = df_daily_comp['day_index'] if 'day_index' in df_daily_comp.columns else df_daily_comp['date']
            fig.add_trace(go.Scatter(
                x=x_vals, y=df_daily_comp['clicks'], name='Clicks (Previous)',
                line=dict(color='#4285f4', width=2.0, dash='dash'),
                hoverinfo='y+name'
            ), secondary_y=False)

        # Trace 3: Current Impressions (Solid #673ab7)
        if show_impressions and 'impressions' in df_daily_curr.columns:
            x_vals = df_daily_curr['day_index'] if 'day_index' in df_daily_curr.columns else df_daily_curr['date']
            fig.add_trace(go.Scatter(
                x=x_vals, y=df_daily_curr['impressions'], name='Impressions',
                line=dict(color='#673ab7', width=2.4),
                hoverinfo='y+name'
            ), secondary_y=True if use_secondary else False)

        # Trace 4: Comp Impressions (Dashed #9575cd)
        if show_impressions and not df_daily_comp.empty and 'impressions' in df_daily_comp.columns:
            x_vals = df_daily_comp['day_index'] if 'day_index' in df_daily_comp.columns else df_daily_comp['date']
            fig.add_trace(go.Scatter(
                x=x_vals, y=df_daily_comp['impressions'], name='Impressions (Previous)',
                line=dict(color='#9575cd', width=2.0, dash='dash'),
                hoverinfo='y+name'
            ), secondary_y=True if use_secondary else False)

        # Trace 5: CTR
        if show_ctr and 'ctr' in df_daily_curr.columns:
            x_vals = df_daily_curr['day_index'] if 'day_index' in df_daily_curr.columns else df_daily_curr['date']
            fig.add_trace(go.Scatter(
                x=x_vals, y=df_daily_curr['ctr'], name='CTR (%)',
                line=dict(color='#00897b', width=2.0),
                hoverinfo='y+name'
            ), secondary_y=False)

        # Trace 6: Position (Inverted)
        if show_position and 'position' in df_daily_curr.columns:
            x_vals = df_daily_curr['day_index'] if 'day_index' in df_daily_curr.columns else df_daily_curr['date']
            fig.add_trace(go.Scatter(
                x=x_vals, y=df_daily_curr['position'], name='Position',
                line=dict(color='#e8710a', width=2.2),
                hoverinfo='y+name'
            ), secondary_y=True)

        fig.update_layout(
            paper_bgcolor='#ffffff',
            plot_bgcolor='#ffffff',
            font=dict(color='#70757a', family='Roboto, Arial, sans-serif', size=11),
            hovermode='x unified',
            showlegend=False,
            margin=dict(l=35, r=35, t=10, b=25),
            height=340
        )
        fig.update_xaxes(
            showgrid=False, linecolor='#dadce0', tickmode='linear', dtick=8,
            title_text=""
        )
        fig.update_yaxes(
            title_text="Clicks" if show_clicks else "",
            secondary_y=False, showgrid=True, gridcolor='#ebebeb',
            linecolor='#dadce0', rangemode='tozero'
        )
        if use_secondary:
            if show_position:
                fig.update_yaxes(title_text="Position", secondary_y=True, autorange="reversed", showgrid=False)
            elif show_impressions:
                fig.update_yaxes(title_text="Impressions", secondary_y=True, showgrid=False, rangemode='tozero')

        st.plotly_chart(fig, use_container_width=True)

    # 5. Generative AI Feature Banner
    st.markdown("""
    <div class="gsc-ai-banner">
        <div style="display:flex; align-items:center; gap:12px;">
            <span style="color:#1a73e8; font-size:18px;">ⓘ</span>
            <span style="color:#3c4043; font-size:13px; font-weight:400;">Get more details on your site's performance in generative AI features on Google Search</span>
        </div>
        <span style="color:#1a73e8; font-size:13px; font-weight:500; cursor:pointer;">Open report &gt;</span>
    </div>
    """, unsafe_allow_html=True)

    # 6. Authentic Google Search Console Tabs
    gsc_t1, gsc_t2, gsc_t3, gsc_t4, gsc_t5 = st.tabs([
        "QUERIES", "PAGES", "COUNTRIES", "DEVICES", "DATES"
    ])

    with gsc_t1:
        q_col1, q_col2 = st.columns([3, 1])
        with q_col1:
            q_search = st.text_input("Filter queries...", key="gsc_q_filter", placeholder="Filter by query...", label_visibility="collapsed")
        q_df = df.groupby('query').agg(
            clicks=('clicks', 'sum'),
            impressions=('impressions', 'sum'),
            position=('position', 'mean')
        ).reset_index()
        q_df['ctr'] = np.where(q_df['impressions'] > 0, (q_df['clicks'] / q_df['impressions'] * 100).round(2), 0.0)
        q_df['position'] = q_df['position'].round(1)
        q_df = q_df.sort_values('clicks', ascending=False)
        if q_search:
            q_df = q_df[q_df['query'].str.contains(q_search, case=False, na=False)]
        with q_col2:
            q_csv = q_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Queries (CSV)", q_csv, "gsc_queries.csv", "text/csv", use_container_width=True)
        st.dataframe(
            q_df[['query', 'clicks', 'impressions', 'ctr', 'position']].rename(columns={
                'query': 'Top queries', 'clicks': 'Clicks', 'impressions': 'Impressions', 'ctr': 'CTR', 'position': 'Position'
            }),
            use_container_width=True, height=420
        )

    with gsc_t2:
        p_col1, p_col2 = st.columns([3, 1])
        with p_col1:
            p_search = st.text_input("Filter pages...", key="gsc_p_filter", placeholder="Filter by URL...", label_visibility="collapsed")
        p_df = df.groupby('page').agg(
            clicks=('clicks', 'sum'),
            impressions=('impressions', 'sum'),
            position=('position', 'mean')
        ).reset_index()
        p_df['ctr'] = np.where(p_df['impressions'] > 0, (p_df['clicks'] / p_df['impressions'] * 100).round(2), 0.0)
        p_df['position'] = p_df['position'].round(1)
        p_df = p_df.sort_values('clicks', ascending=False)
        if p_search:
            p_df = p_df[p_df['page'].str.contains(p_search, case=False, na=False)]
        with p_col2:
            p_csv = p_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Pages (CSV)", p_csv, "gsc_pages.csv", "text/csv", use_container_width=True)
        st.dataframe(
            p_df[['page', 'clicks', 'impressions', 'ctr', 'position']].rename(columns={
                'page': 'Top pages', 'clicks': 'Clicks', 'impressions': 'Impressions', 'ctr': 'CTR', 'position': 'Position'
            }),
            use_container_width=True, height=420
        )

    with gsc_t3:
        c_col1, c_col2 = st.columns([3, 1])
        c_df = df.groupby('country').agg(
            clicks=('clicks', 'sum'),
            impressions=('impressions', 'sum'),
            position=('position', 'mean')
        ).reset_index()
        c_df['ctr'] = np.where(c_df['impressions'] > 0, (c_df['clicks'] / c_df['impressions'] * 100).round(2), 0.0)
        c_df['position'] = c_df['position'].round(1)
        c_df = c_df.sort_values('clicks', ascending=False)
        with c_col2:
            c_csv = c_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Countries (CSV)", c_csv, "gsc_countries.csv", "text/csv", use_container_width=True)
        st.dataframe(
            c_df[['country', 'clicks', 'impressions', 'ctr', 'position']].rename(columns={
                'country': 'Country', 'clicks': 'Clicks', 'impressions': 'Impressions', 'ctr': 'CTR', 'position': 'Position'
            }),
            use_container_width=True, height=420
        )

    with gsc_t4:
        d_col1, d_col2 = st.columns([3, 1])
        d_df = df.groupby('device').agg(
            clicks=('clicks', 'sum'),
            impressions=('impressions', 'sum'),
            position=('position', 'mean')
        ).reset_index()
        d_df['ctr'] = np.where(d_df['impressions'] > 0, (d_df['clicks'] / d_df['impressions'] * 100).round(2), 0.0)
        d_df['position'] = d_df['position'].round(1)
        d_df = d_df.sort_values('clicks', ascending=False)
        with d_col2:
            d_csv = d_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Devices (CSV)", d_csv, "gsc_devices.csv", "text/csv", use_container_width=True)
        st.dataframe(
            d_df[['device', 'clicks', 'impressions', 'ctr', 'position']].rename(columns={
                'device': 'Device', 'clicks': 'Clicks', 'impressions': 'Impressions', 'ctr': 'CTR', 'position': 'Position'
            }),
            use_container_width=True, height=250
        )

    with gsc_t5:
        if not df_daily_curr.empty:
            dt_col1, dt_col2 = st.columns([3, 1])
            with dt_col2:
                dt_csv = df_daily_curr.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Export Dates (CSV)", dt_csv, "gsc_dates.csv", "text/csv", use_container_width=True)
            st.dataframe(
                df_daily_curr[['date', 'clicks', 'impressions', 'ctr', 'position']].rename(columns={
                    'date': 'Date', 'clicks': 'Clicks', 'impressions': 'Impressions', 'ctr': 'CTR', 'position': 'Position'
                }),
                use_container_width=True, height=420
            )


# ----------------------------------------------------
# 2. Keywords
# ----------------------------------------------------
elif page == "🔍 Keywords":
    st.markdown("<div class='section-header'>🔍 Keyword Intelligence</div>", unsafe_allow_html=True)
    if df.empty:
        st.info("👈 Please fetch data first.")
    else:
        t1, t2, t3, t4, t5 = st.tabs(["🏆 Top Ranking", "📏 Long Tail", "⚠️ Cannibalization", "🚫 Zero Clicks", "🏷️ Brand vs Non-Brand"])
        with t1:
            winning = get_winning_keywords(df)
            search_query = st.text_input("🔎 Search keyword...", key="kw_search")
            if not winning.empty:
                if search_query:
                    winning = winning[winning['query'].str.contains(search_query, case=False, na=False)]
                st.dataframe(winning[['query', 'clicks', 'impressions', 'ctr', 'position']], use_container_width=True, height=400)
        with t2:
            long_tail = get_long_tail_keywords(df)
            st.dataframe(long_tail[['query', 'word_count', 'clicks', 'impressions', 'position']], use_container_width=True, height=400)
        with t3:
            cannibal = get_cannibalization(df)
            if not cannibal.empty:
                st.warning(f"⚠️ Found {len(cannibal)} keywords ranking across multiple pages!")
                st.dataframe(cannibal, use_container_width=True, height=400)
            else:
                st.success("✅ No keyword cannibalization detected!")
        with t4:
            zero_clicks = get_zero_click_keywords(df)
            st.dataframe(zero_clicks[['query', 'impressions', 'position']], use_container_width=True, height=400)
        with t5:
            b_in = st.text_input("Brand keywords (comma-separated):", "example, brandname")
            if b_in:
                b_list = [b.strip() for b in b_in.split(",") if b.strip()]
                b_metrics = get_brand_vs_nonbrand(df, b_list)
                c_b1, c_b2 = st.columns(2)
                with c_b1:
                    b_pie = pd.DataFrame({'Type': ['Branded', 'Non-Branded'], 'Clicks': [b_metrics['branded_clicks'], b_metrics['non_branded_clicks']]})
                    fig_b = px.pie(b_pie, values='Clicks', names='Type', color_discrete_sequence=['#10b981', '#6366f1'])
                    fig_b.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
                    st.plotly_chart(fig_b, use_container_width=True)
                with c_b2:
                    st.write(f"**Branded Clicks:** {b_metrics['branded_clicks']:,}")
                    st.write(f"**Non-Branded Clicks:** {b_metrics['non_branded_clicks']:,}")

# ----------------------------------------------------
# 3. Pages
# ----------------------------------------------------
elif page == "📄 Pages":
    st.markdown("<div class='section-header'>📄 Page Level Performance</div>", unsafe_allow_html=True)
    if df.empty:
        st.info("👈 Please fetch data first.")
    else:
        p1, p2, p3, p4 = st.tabs(["🏆 Top Pages", "📉 Content Decay", "🧟 Zombie Pages", "🎯 High Imp / Low CTR"])
        with p1:
            st.dataframe(get_top_pages(df), use_container_width=True, height=450)
        with p2:
            decay = get_content_decay(df)
            if not decay.empty:
                st.error(f"🚨 {len(decay)} pages showing click decay vs previous 30 days!")
                st.dataframe(decay, use_container_width=True)
            else:
                st.success("✅ No content decay detected.")
        with p3:
            zombies = get_zombie_pages(df)
            st.dataframe(zombies, use_container_width=True, height=400)
        with p4:
            st.dataframe(get_high_impression_low_ctr(df), use_container_width=True, height=400)

# ----------------------------------------------------
# 4. Quick Wins
# ----------------------------------------------------
elif page == "⚡ Quick Wins":
    st.markdown("<div class='section-header'>⚡ Quick Wins (Page 2 Striking Distance)</div>", unsafe_allow_html=True)
    if df.empty:
        st.info("👈 Please fetch data first.")
    else:
        qw = get_quick_wins(df)
        if not qw.empty:
            st.success(f"🎯 Found {len(qw)} keywords ranking on Page 2 (pos 11-20) with >100 impressions!")
            fig_qw = px.scatter(qw.head(40), x='position', y='impressions', size='clicks', color='ctr', hover_data=['query'], color_continuous_scale=['#6366f1', '#a855f7', '#ec4899'])
            fig_qw.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
            st.plotly_chart(fig_qw, use_container_width=True)
            st.dataframe(qw[['query', 'clicks', 'impressions', 'ctr', 'position']], use_container_width=True, height=400)
        else:
            st.info("No quick win candidates found.")

# ----------------------------------------------------
# 5. URL & Canonical Inspector (NEW)
# ----------------------------------------------------
elif page == "🔬 URL & Canonical Inspector":
    st.markdown("<div class='section-header'>🔬 Live URL Inspection & Canonical Mismatch Checker</div>", unsafe_allow_html=True)
    if not service_v1 or not current_site:
        st.warning("⚠️ Please connect your Google account and select a site property from the sidebar.")
    else:
        st.markdown("""
        Queries Google's live **URL Inspection API** (up to 2,000 URLs/day free).
        Detects **Canonical Mismatches** (where Google rejects your canonical and picks its own), indexing errors, and last crawl timestamps.
        """)

        tab_single, tab_bulk = st.tabs(["Single URL Inspection", "Bulk URLs Inspection"])

        with tab_single:
            sample_url = current_site.replace('sc-domain:', 'https://') if 'http' not in current_site else current_site
            target_url = st.text_input("Enter exact URL to inspect:", sample_url)

            if st.button("🔎 Inspect Live URL", use_container_width=True):
                with st.spinner("Connecting to GSC URL Inspection API..."):
                    res = inspect_single_url(service_v1, current_site, target_url)
                    c_res1, c_res2 = st.columns(2)
                    with c_res1:
                        st.markdown(f"**Index Verdict:** `{res.get('verdict')}`")
                        st.markdown(f"**Coverage State:** {res.get('coverage_state')}")
                        st.markdown(f"**Indexing Allowed:** `{res.get('indexing_state')}`")
                        st.markdown(f"**Robots.txt:** `{res.get('robots_txt_state')}`")
                    with c_res2:
                        st.markdown(f"**User Canonical:** `{res.get('user_canonical')}`")
                        st.markdown(f"**Google Canonical:** `{res.get('google_canonical')}`")
                        st.markdown(f"**Canonical Status:** **{res.get('canonical_mismatch')}**")
                        st.markdown(f"**Last Crawled:** `{res.get('last_crawl_time')}` ({res.get('crawled_as')})")

        with tab_bulk:
            st.markdown("Paste a list of URLs (one per line) to audit in bulk:")
            urls_text = st.text_area("URLs List", height=150)
            if st.button("🚀 Audit Bulk URLs", use_container_width=True):
                url_list = [u.strip() for u in urls_text.split('\n') if u.strip().startswith('http')]
                if url_list:
                    progress_bar = st.progress(0)
                    with st.spinner(f"Inspecting {len(url_list)} URLs..."):
                        bulk_res = inspect_bulk_urls(service_v1, current_site, url_list, lambda cur, tot: progress_bar.progress(cur / tot))
                        st.success("✅ Inspection complete!")
                        st.dataframe(bulk_res, use_container_width=True)
                else:
                    st.warning("Please paste at least one valid HTTP/HTTPS URL.")

# ----------------------------------------------------
# 6. Algorithm Update Impact (NEW)
# ----------------------------------------------------
elif page == "📉 Algo Update Impact":
    st.markdown("<div class='section-header'>📉 Google Algorithm Update Impact Analyzer (Before vs. After)</div>", unsafe_allow_html=True)
    if not service or not current_site:
        st.warning("⚠️ Please connect your Google account and select a site property.")
    else:
        st.markdown("Compare search visibility **before vs. after** major Google Core Updates or custom dates to find which pages/queries won or lost.")

        col_a1, col_a2 = st.columns([2, 1])
        with col_a1:
            sel_algo = st.selectbox("Select Google Core / Spam Update:", list(MAJOR_ALGO_UPDATES.keys()))
            if sel_algo == "Custom Date":
                algo_date = st.date_input("Update Date:", datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d')
            else:
                algo_date = MAJOR_ALGO_UPDATES[sel_algo]
        with col_a2:
            window_days = st.slider("Comparison Window (Days Before & After):", min_value=7, max_value=30, value=14)

        if st.button("📊 Run Algorithm Impact Analysis", use_container_width=True):
            with st.spinner(f"Analyzing {window_days} days before vs after {algo_date}..."):
                impact = analyze_algorithm_impact(service, current_site, algo_date, window_days)
                if impact.get('status') == 'success':
                    s = impact['summary']
                    p = impact['periods']
                    st.markdown(f"**Period Before:** `{p['before']}` | **Period After:** `{p['after']}`")

                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("Clicks Change", f"{s['clicks_diff']:+,}", f"{s['clicks_pct']:+.1f}%")
                    with c2:
                        st.metric("Impressions Change", f"{s['imp_diff']:+,}", f"{s['imp_pct']:+.1f}%")
                    with c3:
                        st.metric("Avg Position Before", f"{s['pos_before']}")
                    with c4:
                        st.metric("Avg Position After", f"{s['pos_after']}", f"{-s['pos_diff']:+.2f}")

                    t_win, t_lose = st.tabs(["🏆 Winning Pages & Queries", "🔴 Losing Pages & Queries"])
                    with t_win:
                        st.markdown("#### Top Pages That Gained Traffic:")
                        st.dataframe(impact['top_winning_pages'], use_container_width=True)
                        st.markdown("#### Top Queries That Gained Traffic:")
                        st.dataframe(impact['top_winning_queries'], use_container_width=True)
                    with t_lose:
                        st.markdown("#### Top Pages That Lost Traffic:")
                        st.dataframe(impact['top_losing_pages'], use_container_width=True)
                        st.markdown("#### Top Queries That Lost Traffic:")
                        st.dataframe(impact['top_losing_queries'], use_container_width=True)
                else:
                    st.warning(impact.get('message', 'Failed to retrieve data.'))

# ----------------------------------------------------
# 7. Custom CTR Curve & Traffic Forecaster (NEW)
# ----------------------------------------------------
elif page == "📈 Custom CTR Curve":
    st.markdown("<div class='section-header'>📈 Custom Empirical CTR Curve & Traffic Opportunity Forecaster</div>", unsafe_allow_html=True)
    if df.empty:
        st.info("👈 Please fetch performance data first.")
    else:
        st.markdown("Builds your domain's **actual CTR curve by rank** and calculates predicted traffic gains if rankings improve.")

        ctr_curve = build_empirical_ctr_curve(df)
        if not ctr_curve.empty:
            fig_curve = go.Figure()
            fig_curve.add_trace(go.Scatter(x=ctr_curve['serp_rank'], y=ctr_curve['actual_ctr'], name='Your Actual CTR %', line=dict(color='#10b981', width=3), mode='lines+markers'))
            fig_curve.add_trace(go.Scatter(x=ctr_curve['serp_rank'], y=ctr_curve['benchmark_ctr'], name='Industry Benchmark CTR %', line=dict(color='#94a3b8', width=2, dash='dash'), mode='lines'))
            fig_curve.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'),
                                    xaxis=dict(title="SERP Rank (1 - 20)", gridcolor='rgba(255,255,255,0.06)', dtick=1),
                                    yaxis=dict(title="Click-Through Rate (%)", gridcolor='rgba(255,255,255,0.06)'))
            st.plotly_chart(fig_curve, use_container_width=True)
            st.dataframe(ctr_curve[['serp_rank', 'actual_ctr', 'benchmark_ctr', 'total_clicks', 'total_impressions', 'ctr_performance']], use_container_width=True)

            st.markdown("---")
            st.markdown("### 🔮 Traffic Opportunity Forecaster")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                target_pos = st.slider("Target Ranking Goal:", min_value=1, max_value=5, value=3)
            with col_f2:
                min_imp = st.number_input("Minimum Impressions Threshold:", value=100, step=50)

            forecast_df, total_gain = forecast_traffic_opportunity(df, target_rank=target_pos, min_impressions=min_imp)
            if not forecast_df.empty:
                st.success(f"🚀 Moving these {len(forecast_df)} keywords to Rank #{target_pos} will produce an estimated **+{total_gain:,} additional clicks**!")
                st.dataframe(forecast_df, use_container_width=True)
            else:
                st.info("No candidates found below target rank.")

# ----------------------------------------------------
# 8. Sitemaps Manager (NEW)
# ----------------------------------------------------
elif page == "🗺️ Sitemaps Manager":
    st.markdown("<div class='section-header'>🗺️ GSC Sitemaps Manager & Health Inspector</div>", unsafe_allow_html=True)
    if not service or not current_site:
        st.warning("⚠️ Please connect your Google account and select a site property.")
    else:
        st.markdown("View all submitted XML sitemaps, error statuses, and submit new sitemaps directly.")

        c_sub1, c_sub2 = st.columns([3, 1])
        with c_sub1:
            new_sitemap = st.text_input("Enter new sitemap URL to submit:", "https://example.com/sitemap.xml")
        with c_sub2:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("📤 Submit Sitemap", use_container_width=True):
                res_sub = submit_sitemap(service, current_site, new_sitemap)
                if res_sub['success']:
                    st.success(res_sub['message'])
                else:
                    st.error(res_sub['message'])

        st.markdown("### Current Submitted Sitemaps")
        sitemaps_df = list_sitemaps(service, current_site)
        if not sitemaps_df.empty:
            st.dataframe(sitemaps_df, use_container_width=True)
        else:
            st.info("No sitemaps found or property does not have submitted sitemaps.")

# ----------------------------------------------------
# 9. Log & Crawl Reconciliation (NEW)
# ----------------------------------------------------
elif page == "🪵 Log Reconciliation":
    st.markdown("<div class='section-header'>🪵 Server Log & Crawl Reconciliation (Orphan & Waste Finder)</div>", unsafe_allow_html=True)
    if df.empty:
        st.info("👈 Please fetch GSC performance data first.")
    else:
        st.markdown("""
        Cross-reference your live GSC data with **Screaming Frog Internal Crawl CSV** or **Server Access Logs** to detect:
        * **Orphaned Performers:** URLs earning clicks in GSC but having **0 internal links** in your site architecture.
        * **Programmatic Crawl Waste:** URLs receiving heavy Googlebot requests but **0 organic clicks/impressions**.
        """)

        tab_crawl, tab_logs = st.tabs(["Internal Crawl CSV (Orphan Finder)", "Server Access Logs (Crawl Waste Finder)"])

        with tab_crawl:
            crawl_file = st.file_uploader("Upload Screaming Frog Crawl CSV (must contain URL/Address and Inlinks):", type=['csv'])
            if crawl_file:
                try:
                    c_df = pd.read_csv(crawl_file)
                except UnicodeDecodeError:
                    crawl_file.seek(0)
                    c_df = pd.read_csv(crawl_file, encoding='latin1')
                except Exception as ex:
                    st.error(f"Failed to read CSV: {ex}")
                    c_df = pd.DataFrame()

                if not c_df.empty:
                    reconciled = reconcile_crawl_with_gsc(c_df, df)
                    if reconciled['status'] == 'success':
                        st.error(f"🚨 Found **{reconciled['total_orphans_found']} Orphaned Performers** (Ranking in Google with 0 internal links)!")
                        st.dataframe(reconciled['orphaned_performers'], use_container_width=True)
                        st.markdown("#### Heavily Linked Pages with 0 Impressions:")
                        st.dataframe(reconciled['unindexed_inlinked'], use_container_width=True)
                    else:
                        st.warning(reconciled['message'])

        with tab_logs:
            log_file = st.file_uploader("Upload Server Access Log CSV (with URL/Path and Hit count):", type=['csv'], key="log_csv")
            if log_file:
                try:
                    l_df = pd.read_csv(log_file)
                except UnicodeDecodeError:
                    log_file.seek(0)
                    l_df = pd.read_csv(log_file, encoding='latin1')
                except Exception as ex:
                    st.error(f"Failed to read CSV: {ex}")
                    l_df = pd.DataFrame()

                if not l_df.empty:
                    rec_log = reconcile_server_logs_with_gsc(l_df, df)
                    if rec_log['status'] == 'success':
                        st.warning(f"⚠️ Found **{rec_log['total_waste_urls']} Crawl Waste URLs** (Googlebot hits with 0 GSC clicks/impressions):")
                        st.dataframe(rec_log['crawl_waste'], use_container_width=True)
                    else:
                        st.warning(rec_log['message'])

# ----------------------------------------------------
# 10. Intent & Regex
# ----------------------------------------------------
elif page == "🎯 Intent & Regex":
    st.markdown("<div class='section-header'>🎯 Search Intent & RE2 Regex Explorer</div>", unsafe_allow_html=True)
    if df.empty:
        st.info("👈 Please fetch data first.")
    else:
        t1, t2 = st.tabs(["🏷️ Intent Classification", "🧪 Custom RE2 Regex Filter"])
        with t1:
            intent_df = get_search_intent(df.copy())
            if 'intent' in intent_df.columns:
                c1, c2 = st.columns([1, 2])
                with c1:
                    intent_counts = intent_df['intent'].value_counts().reset_index()
                    intent_counts.columns = ['Intent', 'Count']
                    fig_i = px.pie(intent_counts, values='Count', names='Intent', color_discrete_sequence=['#6366f1', '#a855f7', '#ec4899', '#10b981'])
                    fig_i.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
                    st.plotly_chart(fig_i, use_container_width=True)
                with c2:
                    sel_intent = st.selectbox("Filter Intent", ['All'] + list(intent_df['intent'].unique()))
                    filtered_intent = intent_df if sel_intent == 'All' else intent_df[intent_df['intent'] == sel_intent]
                    st.dataframe(filtered_intent[['query', 'intent', 'clicks', 'impressions', 'position']], use_container_width=True, height=350)
        with t2:
            preset = st.selectbox("Choose a Course Preset or Enter Custom:", [
                "Custom Regex",
                "Informational Queries: (?i)^(who|what|where|when|why|how|guide|tutorial|vs|compare|difference)[\" \"].*",
                "Long-tail 7+ words: ^([^\\s]+\\s+){6,}[^\\s]+$",
                "Exclude Archive / Temp: ^(?!.*(?:_archive|\\.tmp|\\.bak)).*$"
            ])
            if "Informational" in preset:
                default_regex = r'(?i)^(who|what|where|when|why|how|guide|tutorial|vs|compare|difference)[" "].*'
            elif "Long-tail" in preset:
                default_regex = r'^([^\s]+\s+){6,}[^\s]+$'
            elif "Exclude" in preset:
                default_regex = r'^(?!.*(?:_archive|\.tmp|\.bak)).*$'
            else:
                default_regex = r'.*'

            custom_pat = st.text_input("Regex Pattern:", default_regex)
            target_col = st.radio("Apply Regex on:", ["query", "page"], horizontal=True)
            if custom_pat and target_col in df.columns:
                try:
                    matched_df = df[df[target_col].str.contains(custom_pat, regex=True, na=False)]
                    st.success(f"Matched **{len(matched_df):,}** out of {len(df):,} rows!")
                    st.dataframe(matched_df[[target_col, 'clicks', 'impressions', 'ctr', 'position']], use_container_width=True, height=400)
                except Exception as ex:
                    st.error(f"Regex Error: {ex}")

# ----------------------------------------------------
# 11. AEO & Preferred Sources
# ----------------------------------------------------
elif page == "🤖 AEO & Preferred Sources":
    st.markdown("<div class='section-header'>🤖 Generative Engine Optimization (GEO/AEO) & Preferred Sources</div>", unsafe_allow_html=True)
    current_domain = current_site or "yourdomain.com"
    clean_domain = current_domain.replace('sc-domain:', '').replace('https://', '').replace('http://', '').strip('/')

    st.markdown(f"""
    ### 🌟 Google Preferred Sources in AI Overviews & AI Mode
    Google lets users add websites to their **Preferred Sources** preferences. Preferred citations gain a distinctive badge and **2x higher CTR**.
    
    #### 🔗 Direct Deep-Link Generator:
    """)
    pref_link = f"https://google.com/preferences/source?q={clean_domain}"
    st.code(pref_link, language="markdown")
    st.markdown(f"[👉 Test Direct Deep Link in Browser]({pref_link})")

# ----------------------------------------------------
# 12. 24/7 Automation Generator (NEW)
# ----------------------------------------------------
elif page == "⚙️ 24/7 Automation":
    st.markdown("<div class='section-header'>⚙️ 24/7 Free Automated Monitoring via GitHub Actions</div>", unsafe_allow_html=True)
    st.markdown("""
    Run nightly GSC SEO audits completely free using **GitHub Actions**.
    No servers or paid subscriptions required. Automatically alerts your **Telegram** bot if weekly traffic drops by 20%+!
    """)

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.markdown("#### 1. Workflow YAML (`.github/workflows/gsc_audit.yml`)")
        st.code(GITHUB_ACTIONS_WORKFLOW, language="yaml")
    with col_w2:
        st.markdown("#### 2. Headless Python Runner (`automated_audit.py`)")
        st.code(HEADLESS_AUDIT_SCRIPT, language="python")

    if st.button("💾 Generate Files in Project Directory", use_container_width=True):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        wf_path, audit_path = generate_automation_bundle(base_dir)
        st.success(f"✅ Generated `{wf_path}` and `{audit_path}`! Commit and push to GitHub to activate.")

# ----------------------------------------------------
# 13. Alerts
# ----------------------------------------------------
elif page == "🚨 Alerts":
    st.markdown("<div class='section-header'>🚨 Recorded Alerts</div>", unsafe_allow_html=True)
    alerts_df = get_unread_alerts(current_site)
    if alerts_df.empty:
        st.success("✅ No active alerts.")
    else:
        st.warning(f"⚠️ {len(alerts_df)} unread alerts recorded.")
        for _, a in alerts_df.iterrows():
            st.markdown(f"<div class='alert-warning'><b>{a.get('alert_type')}</b><br>{a.get('message')}<br><small>{a.get('created_at')}</small></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 14. Reports & Export
# ----------------------------------------------------
elif page == "📤 Reports & Export":
    st.markdown("<div class='section-header'>📤 Branded Client PDF & CSV Exports</div>", unsafe_allow_html=True)
    if df.empty:
        st.info("👈 Please fetch data first.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📄 Branded PDF Client Report")
            site_target = st.text_input("Property Label", value=current_site or "My Website")
            if st.button("📥 Generate Instant PDF Report", use_container_width=True):
                with st.spinner("Compiling PDF..."):
                    try:
                        pdf_file = generate_pdf_report(site_target, get_overview(df), get_winning_keywords(df), get_top_pages(df), get_quick_wins(df))
                        with open(pdf_file, 'rb') as f:
                            st.download_button("⬇️ Download PDF Report", f, file_name=os.path.basename(pdf_file), mime='application/pdf', use_container_width=True)
                        st.success("✅ PDF Ready!")
                    except Exception as e:
                        st.error(f"PDF Error: {e}")
        with c2:
            st.markdown("### 📊 CSV Data Export")
            st.download_button("📥 Download Raw GSC Data (CSV)", df.to_csv(index=False), "gsc_performance_export.csv", "text/csv", use_container_width=True)
            top_p = get_top_pages(df)
            if not top_p.empty:
                st.download_button("📥 Download Top Pages (CSV)", top_p.to_csv(index=False), "top_pages_export.csv", "text/csv", use_container_width=True)