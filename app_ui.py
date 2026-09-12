import os
import platform
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    generate_mock_gsc_data, parse_gsc_csv
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
# Custom CSS - Modern Dark UI
# ==============================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .main { background: #0f0f1a; }
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: 1px solid rgba(99, 102, 241, 0.3);
    }
    section[data-testid="stSidebar"] .stRadio label {
        color: #e2e8f0 !important;
        font-size: 13px;
        padding: 5px 8px;
        border-radius: 6px;
    }
    .kpi-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(168,85,247,0.1));
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 12px;
        padding: 14px;
        text-align: center;
        backdrop-filter: blur(10px);
        transition: transform 0.2s;
    }
    .kpi-card:hover { transform: translateY(-3px); }
    .kpi-value {
        font-size: 26px;
        font-weight: 700;
        background: linear-gradient(135deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .kpi-label {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 4px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .section-header {
        background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(168,85,247,0.1));
        border-left: 4px solid #6366f1;
        border-radius: 8px;
        padding: 10px 14px;
        margin: 15px 0 12px 0;
        color: #e2e8f0;
        font-size: 15px;
        font-weight: 600;
    }
    .alert-danger {
        background: rgba(239, 68, 68, 0.12);
        border: 1px solid rgba(239, 68, 68, 0.35);
        border-radius: 10px;
        padding: 12px;
        margin: 8px 0;
        color: #fca5a5;
    }
    .alert-warning {
        background: rgba(245, 158, 11, 0.12);
        border: 1px solid rgba(245, 158, 11, 0.35);
        border-radius: 10px;
        padding: 12px;
        margin: 8px 0;
        color: #fcd34d;
    }
    .alert-success {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.35);
        border-radius: 10px;
        padding: 12px;
        margin: 8px 0;
        color: #6ee7b7;
    }
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #a855f7);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 7px 16px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
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
if 'sites' not in st.session_state:
    st.session_state.sites = []
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'current_site' not in st.session_state:
    st.session_state.current_site = None
if 'user_creds' not in st.session_state:
    st.session_state.user_creds = None

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
        st.info("👋 Choose how you want to access Search Console data:")
        auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔑 Service Account", "🚀 1-Click Demo / CSV", "🌐 Google OAuth"])

        with auth_tab1:
            st.caption("🔒 **Industry Standard:** No OAuth popups, no redirect URIs, works 24/7.")
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

        with auth_tab2:
            st.caption("💡 **No Google Cloud Setup Required:** Instant full platform access.")
            if st.button("✨ Load Full Demo SEO Data (90 Days)", use_container_width=True, type="primary"):
                with st.spinner("Generating 1,000+ realistic SEO data points..."):
                    mock_df = generate_mock_gsc_data(site_name="https://mybrand-store.com", days=90)
                    st.session_state.df = mock_df
                    st.session_state.sites = ["https://mybrand-store.com (Demo Property)"]
                    st.session_state.current_site = "https://mybrand-store.com (Demo Property)"
                    st.success("✅ Demo SEO Data Loaded! Explore all engines below.")
                    st.rerun()
            
            st.markdown("---")
            st.markdown("**📂 Or Upload GSC Export (CSV/ZIP):**")
            csv_file = st.file_uploader("Upload GSC Export", type=['csv', 'zip'], key="gsc_csv_uploader")
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

        with auth_tab3:
            st.caption("🌐 **Google OAuth Sign-In:**")
            cfg = load_client_config()
            if cfg:
                default_redirect = resolve_redirect_uri(cfg)
                try:
                    auth_url, _ = get_auth_url(default_redirect, config=cfg)
                    st.link_button("🔗 1. Open Google Login Window", auth_url, use_container_width=True)
                except Exception as ex:
                    st.error(f"OAuth config error: {ex}")
                
                st.markdown("**Manual Code Paste (Alternative):**")
                manual_code = st.text_input("Paste authorization code or redirected URL:", key="manual_oauth_code")
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
    st.markdown("<div class='section-header'>📊 Performance Overview</div>", unsafe_allow_html=True)
    if df.empty:
        st.info("👈 Connect your Google account and click **🚀 Fetch Live**.")
    else:
        overview = get_overview(df)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"<div class='kpi-card'><div class='kpi-value'>{overview.get('total_clicks', 0):,}</div><div class='kpi-label'>Clicks</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='kpi-card'><div class='kpi-value'>{overview.get('total_impressions', 0):,}</div><div class='kpi-label'>Impressions</div></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='kpi-card'><div class='kpi-value'>{overview.get('avg_ctr', 0)}%</div><div class='kpi-label'>Avg CTR</div></div>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<div class='kpi-card'><div class='kpi-value'>{overview.get('avg_position', 0)}</div><div class='kpi-label'>Avg Position</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if 'date' in df.columns:
            st.markdown("<div class='section-header'>📈 Daily Performance Trend</div>", unsafe_allow_html=True)
            daily = df.groupby('date').agg(clicks=('clicks', 'sum'), impressions=('impressions', 'sum')).reset_index().sort_values('date')
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=daily['date'], y=daily['clicks'], name='Clicks', line=dict(color='#6366f1', width=2.5), fill='tozeroy', fillcolor='rgba(99,102,241,0.12)'))
            fig.add_trace(go.Scatter(x=daily['date'], y=daily['impressions'], name='Impressions', line=dict(color='#a855f7', width=2.5), fill='tozeroy', fillcolor='rgba(168,85,247,0.12)', yaxis='y2'))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'), legend=dict(bgcolor='rgba(0,0,0,0)'),
                              yaxis2=dict(overlaying='y', side='right', gridcolor='rgba(255,255,255,0.06)', title="Impressions"),
                              yaxis=dict(gridcolor='rgba(255,255,255,0.06)', title="Clicks"), xaxis=dict(gridcolor='rgba(255,255,255,0.06)'), hovermode='x unified', margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)

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