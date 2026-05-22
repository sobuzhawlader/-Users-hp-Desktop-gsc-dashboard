import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from auth_gsc import get_gsc_service, get_sites
from data_fetcher import fetch_gsc_data, get_date_range
from database import init_db, save_data, load_data, load_alerts
from seo_engine import (
    get_overview, get_quick_wins, get_cannibalization,
    get_search_intent, get_long_tail_keywords, get_zero_click_keywords,
    get_content_decay, get_zombie_pages, get_brand_vs_nonbrand,
    get_device_breakdown, get_country_breakdown, get_top_pages,
    get_winning_keywords, get_high_impression_low_ctr
)
from report_generator import generate_pdf_report
from alerts import get_unread_alerts

# ==============================
# Page Config
# ==============================
st.set_page_config(
    page_title="GSC Pro Dashboard",
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
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: 1px solid rgba(99, 102, 241, 0.3);
    }
    
    section[data-testid="stSidebar"] .stRadio label {
        color: #e2e8f0 !important;
        font-size: 14px;
        padding: 8px 12px;
        border-radius: 8px;
        transition: all 0.2s;
    }
    
    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(168,85,247,0.1));
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        backdrop-filter: blur(10px);
        transition: transform 0.2s;
    }
    
    .kpi-card:hover { transform: translateY(-3px); }
    
    .kpi-value {
        font-size: 32px;
        font-weight: 700;
        background: linear-gradient(135deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .kpi-label {
        font-size: 13px;
        color: #94a3b8;
        margin-top: 5px;
        font-weight: 500;
    }
    
    /* Section Headers */
    .section-header {
        background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(168,85,247,0.1));
        border-left: 4px solid #6366f1;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 20px 0 15px 0;
        color: #e2e8f0;
        font-size: 16px;
        font-weight: 600;
    }
    
    /* Alert Cards */
    .alert-danger {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 10px;
        padding: 12px;
        margin: 5px 0;
        color: #fca5a5;
    }
    
    .alert-warning {
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 10px;
        padding: 12px;
        margin: 5px 0;
        color: #fcd34d;
    }
    
    .alert-success {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 10px;
        padding: 12px;
        margin: 5px 0;
        color: #6ee7b7;
    }
    
    /* Dataframe */
    .dataframe { color: #e2e8f0 !important; }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #a855f7);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 8px 20px;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==============================
# Initialize DB
# ==============================
init_db()

# ==============================
# Session State
# ==============================
if 'service' not in st.session_state:
    st.session_state.service = None
if 'sites' not in st.session_state:
    st.session_state.sites = []
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()

# ==============================
# Sidebar
# ==============================
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 20px 0;'>
        <div style='font-size:40px'>🔍</div>
        <div style='font-size:20px; font-weight:700; 
             background: linear-gradient(135deg, #6366f1, #a855f7);
             -webkit-background-clip: text;
             -webkit-text-fill-color: transparent;'>
             GSC Pro
        </div>
        <div style='font-size:11px; color:#64748b;'>Advanced SEO Dashboard</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Connect Button
    if st.button("🔗 Connect Google Account", use_container_width=True):
        with st.spinner("Connecting..."):
            try:
                service = get_gsc_service()
                sites = get_sites(service)
                st.session_state.service = service
                st.session_state.sites = sites
                st.success(f"✅ Connected! {len(sites)} sites found")
            except Exception as e:
                st.error(f"Connection failed: {e}")
    
    # Site Selector
    if st.session_state.sites:
        selected_site = st.selectbox(
            "🌐 Select Site",
            st.session_state.sites
        )
        
        # Date Range
        st.markdown("**📅 Date Range**")
        period = st.radio("", [
            "Last 7 days",
            "Last 30 days", 
            "Last 90 days",
            "Last 6 months",
            "Custom"
        ], index=1)
        
        if period == "Custom":
            start_date = st.date_input("Start Date", 
                datetime.now() - timedelta(days=30))
            end_date = st.date_input("End Date", datetime.now())
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
        else:
            days_map = {
                "Last 7 days": 7,
                "Last 30 days": 30,
                "Last 90 days": 90,
                "Last 6 months": 180
            }
            days = days_map[period]
            end_str = datetime.now().strftime('%Y-%m-%d')
            start_str = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Fetch Data Button
        if st.button("🚀 Fetch Data", use_container_width=True):
            with st.spinner("Fetching data from GSC..."):
                try:
                    df = fetch_gsc_data(
                        st.session_state.service,
                        selected_site,
                        start_str, end_str
                    )
                    if not df.empty:
                        save_data(df, selected_site)
                        st.session_state.df = df
                        st.success(f"✅ {len(df):,} rows fetched!")
                    else:
                        st.warning("No data found!")
                except Exception as e:
                    st.error(f"Error: {e}")
        
        # Load from DB
        if st.button("📂 Load from Database", use_container_width=True):
            df = load_data(selected_site, start_str, end_str)
            if not df.empty:
                st.session_state.df = df
                st.success(f"✅ {len(df):,} rows loaded!")
            else:
                st.warning("No data in database!")
    
    st.divider()
    
    # Navigation
    page = st.radio("📌 Navigation", [
        "📊 Overview",
        "🔍 Keywords",
        "📄 Pages",
        "🌍 Countries & Devices",
        "⚡ Quick Wins",
        "🚨 Alerts",
        "📤 Reports"
    ])

# ==============================
# Main Content
# ==============================
df = st.session_state.df

# ==============================
# PAGE: Overview
# ==============================
if page == "📊 Overview":
    st.markdown("<div class='section-header'>📊 Performance Overview</div>", 
                unsafe_allow_html=True)
    
    if df.empty:
        st.info("👈 Connect your Google account and fetch data to get started!")
    else:
        overview = get_overview(df)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-value'>{overview['total_clicks']:,}</div>
                <div class='kpi-label'>👆 Total Clicks</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-value'>{overview['total_impressions']:,}</div>
                <div class='kpi-label'>👁️ Total Impressions</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-value'>{overview['avg_ctr']}%</div>
                <div class='kpi-label'>🎯 Average CTR</div>
            </div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class='kpi-card'>
                <div class='kpi-value'>{overview['avg_position']}</div>
                <div class='kpi-label'>📍 Avg Position</div>
            </div>""", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Traffic Chart
        if 'date' in df.columns:
            st.markdown("<div class='section-header'>📈 Traffic Trend</div>",
                       unsafe_allow_html=True)
            daily = df.groupby('date').agg(
                clicks=('clicks', 'sum'),
                impressions=('impressions', 'sum')
            ).reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=daily['date'], y=daily['clicks'],
                name='Clicks', line=dict(color='#6366f1', width=2),
                fill='tozeroy', fillcolor='rgba(99,102,241,0.1)'
            ))
            fig.add_trace(go.Scatter(
                x=daily['date'], y=daily['impressions'],
                name='Impressions', line=dict(color='#a855f7', width=2),
                fill='tozeroy', fillcolor='rgba(168,85,247,0.1)',
                yaxis='y2'
            ))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                legend=dict(bgcolor='rgba(0,0,0,0)'),
                yaxis2=dict(overlaying='y', side='right',
                           gridcolor='rgba(255,255,255,0.05)'),
                yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                hovermode='x unified',
                margin=dict(l=0, r=0, t=10, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Device Breakdown
        col1, col2 = st.columns(2)
        with col1:
            if 'device' in df.columns:
                st.markdown("<div class='section-header'>📱 Device Breakdown</div>",
                           unsafe_allow_html=True)
                device_df = get_device_breakdown(df)
                fig = px.pie(device_df, values='clicks', names='device',
                            color_discrete_sequence=['#6366f1', '#a855f7', '#ec4899'])
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0'),
                    legend=dict(bgcolor='rgba(0,0,0,0)'),
                    margin=dict(l=0, r=0, t=10, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'country' in df.columns:
                st.markdown("<div class='section-header'>🌍 Top Countries</div>",
                           unsafe_allow_html=True)
                country_df = get_country_breakdown(df).head(10)
                fig = px.bar(country_df, x='clicks', y='country',
                            orientation='h',
                            color='clicks',
                            color_continuous_scale=['#6366f1', '#a855f7'])
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0'),
                    margin=dict(l=0, r=0, t=10, b=0),
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)

# ==============================
# PAGE: Keywords
# ==============================
elif page == "🔍 Keywords":
    st.markdown("<div class='section-header'>🔍 Keyword Analysis</div>",
               unsafe_allow_html=True)
    
    if df.empty:
        st.info("👈 Fetch data first!")
    else:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏆 Top Keywords",
            "🎯 Search Intent",
            "📏 Long Tail",
            "⚠️ Cannibalization",
            "🚫 Zero Clicks"
        ])
        
        with tab1:
            winning = get_winning_keywords(df)
            if not winning.empty:
                search = st.text_input("🔎 Search keyword...")
                if search:
                    winning = winning[winning['query'].str.contains(
                        search, case=False, na=False)]
                st.dataframe(
                    winning[['query', 'clicks', 'impressions', 'ctr', 'position']],
                    use_container_width=True, height=400
                )
        
        with tab2:
            intent_df = get_search_intent(df.copy())
            if 'intent' in intent_df.columns:
                col1, col2 = st.columns(2)
                with col1:
                    intent_counts = intent_df['intent'].value_counts().reset_index()
                    fig = px.pie(intent_counts, values='count', names='intent',
                                color_discrete_sequence=['#6366f1','#a855f7','#ec4899','#f59e0b'])
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#e2e8f0'),
                        legend=dict(bgcolor='rgba(0,0,0,0)'),
                        margin=dict(l=0, r=0, t=10, b=0)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    selected_intent = st.selectbox("Filter by intent", 
                        ['All', 'Informational', 'Commercial', 'Transactional', 'Navigational'])
                    if selected_intent != 'All':
                        filtered = intent_df[intent_df['intent'] == selected_intent]
                    else:
                        filtered = intent_df
                    st.dataframe(
                        filtered[['query', 'intent', 'clicks', 'impressions', 'position']],
                        use_container_width=True, height=300
                    )
        
        with tab3:
            long_tail = get_long_tail_keywords(df)
            if not long_tail.empty:
                st.dataframe(
                    long_tail[['query', 'word_count', 'clicks', 'impressions', 'position']],
                    use_container_width=True, height=400
                )
        
        with tab4:
            cannibal = get_cannibalization(df)
            if not cannibal.empty:
                st.warning(f"⚠️ Found {len(cannibal)} cannibalized keywords!")
                st.dataframe(cannibal, use_container_width=True, height=400)
            else:
                st.success("✅ No cannibalization detected!")
        
        with tab5:
            zero_clicks = get_zero_click_keywords(df)
            if not zero_clicks.empty:
                st.dataframe(
                    zero_clicks[['query', 'impressions', 'position']],
                    use_container_width=True, height=400
                )

# ==============================
# PAGE: Pages
# ==============================
elif page == "📄 Pages":
    st.markdown("<div class='section-header'>📄 Page Performance</div>",
               unsafe_allow_html=True)
    
    if df.empty:
        st.info("👈 Fetch data first!")
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "🏆 Top Pages",
            "📉 Content Decay",
            "🧟 Zombie Pages",
            "👁️ High Impression Low CTR"
        ])
        
        with tab1:
            top_pages = get_top_pages(df)
            if not top_pages.empty:
                st.dataframe(top_pages, use_container_width=True, height=400)
        
        with tab2:
            decay = get_content_decay(df)
            if not decay.empty:
                st.error(f"🚨 {len(decay)} pages showing content decay!")
                fig = px.bar(decay.head(15), x='decay', y='page',
                            orientation='h', color='decay',
                            color_continuous_scale=['#ef4444', '#f59e0b'])
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0'),
                    margin=dict(l=0, r=0, t=10, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(decay, use_container_width=True)
            else:
                st.success("✅ No content decay detected!")
        
        with tab3:
            zombies = get_zombie_pages(df)
            if not zombies.empty:
                st.warning(f"🧟 Found {len(zombies)} zombie pages!")
                st.dataframe(zombies, use_container_width=True, height=400)
            else:
                st.success("✅ No zombie pages found!")
        
        with tab4:
            high_imp = get_high_impression_low_ctr(df)
            if not high_imp.empty:
                st.dataframe(
                    high_imp[['query', 'impressions', 'ctr', 'position']],
                    use_container_width=True, height=400
                )

# ==============================
# PAGE: Countries & Devices
# ==============================
elif page == "🌍 Countries & Devices":
    st.markdown("<div class='section-header'>🌍 Countries & Devices</div>",
               unsafe_allow_html=True)
    
    if df.empty:
        st.info("👈 Fetch data first!")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<div class='section-header'>📱 Device Performance</div>",
                       unsafe_allow_html=True)
            device_df = get_device_breakdown(df)
            if not device_df.empty:
                st.dataframe(device_df, use_container_width=True)
                fig = px.bar(device_df, x='device', y=['clicks', 'impressions'],
                            barmode='group',
                            color_discrete_sequence=['#6366f1', '#a855f7'])
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0'),
                    legend=dict(bgcolor='rgba(0,0,0,0)'),
                    margin=dict(l=0, r=0, t=10, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("<div class='section-header'>🌍 Country Performance</div>",
                       unsafe_allow_html=True)
            country_df = get_country_breakdown(df)
            if not country_df.empty:
                st.dataframe(country_df, use_container_width=True)
                fig = px.choropleth(country_df, locations='country',
                                   locationmode='country names',
                                   color='clicks',
                                   color_continuous_scale=['#1a1a2e', '#6366f1', '#a855f7'])
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e2e8f0'),
                    margin=dict(l=0, r=0, t=10, b=0),
                    geo=dict(bgcolor='rgba(0,0,0,0)',
                            lakecolor='rgba(0,0,0,0)',
                            landcolor='rgba(26,26,46,0.8)',
                            showframe=False)
                )
                st.plotly_chart(fig, use_container_width=True)

# ==============================
# PAGE: Quick Wins
# ==============================
elif page == "⚡ Quick Wins":
    st.markdown("<div class='section-header'>⚡ Quick Win Opportunities</div>",
               unsafe_allow_html=True)
    
    if df.empty:
        st.info("👈 Fetch data first!")
    else:
        quick_wins = get_quick_wins(df)
        if not quick_wins.empty:
            st.success(f"🎯 Found {len(quick_wins)} quick win opportunities!")
            st.markdown("""
            <div class='alert-success'>
            💡 These keywords are on page 2 (position 11-20). 
            A little SEO push can bring them to page 1!
            </div>
            """, unsafe_allow_html=True)
            
            fig = px.scatter(quick_wins.head(30),
                           x='position', y='impressions',
                           size='clicks', color='ctr',
                           hover_data=['query'],
                           color_continuous_scale=['#6366f1', '#a855f7', '#ec4899'])
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e2e8f0'),
                margin=dict(l=0, r=0, t=10, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(
                quick_wins[['query', 'clicks', 'impressions', 'ctr', 'position']],
                use_container_width=True, height=400
            )
        else:
            st.info("No quick wins found for this period.")

# ==============================
# PAGE: Alerts
# ==============================
elif page == "🚨 Alerts":
    st.markdown("<div class='section-header'>🚨 Alerts & Notifications</div>",
               unsafe_allow_html=True)
    
    alerts_df = get_unread_alerts()
    
    if alerts_df.empty:
        st.success("✅ No active alerts!")
    else:
        st.warning(f"⚠️ {len(alerts_df)} unread alerts!")
        for _, alert in alerts_df.iterrows():
            alert_type = alert.get('alert_type', '')
            if 'drop' in alert_type:
                css_class = 'alert-danger'
                icon = '🔴'
            else:
                css_class = 'alert-warning'
                icon = '🟡'
            
            st.markdown(f"""
            <div class='{css_class}'>
                {icon} <b>{alert.get('alert_type', '').replace('_', ' ').title()}</b><br>
                {alert.get('message', '')}<br>
                <small>{alert.get('created_at', '')}</small>
            </div>
            """, unsafe_allow_html=True)

# ==============================
# PAGE: Reports
# ==============================
elif page == "📤 Reports":
    st.markdown("<div class='section-header'>📤 Generate Reports</div>",
               unsafe_allow_html=True)
    
    if df.empty:
        st.info("👈 Fetch data first!")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📄 PDF Report")
            site_name = st.text_input("Site URL", 
                value=st.session_state.sites[0] if st.session_state.sites else "")
            
            if st.button("📥 Generate PDF Report", use_container_width=True):
                with st.spinner("Generating PDF..."):
                    try:
                        overview = get_overview(df)
                        top_keywords = get_winning_keywords(df)
                        top_pages = get_top_pages(df)
                        quick_wins = get_quick_wins(df)
                        
                        filename = generate_pdf_report(
                            site_name, overview, 
                            top_keywords, top_pages, quick_wins
                        )
                        
                        with open(filename, 'rb') as f:
                            st.download_button(
                                "⬇️ Download PDF",
                                f, filename,
                                mime='application/pdf',
                                use_container_width=True
                            )
                        st.success("✅ PDF Generated!")
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        with col2:
            st.markdown("### 📧 Email Report")
            recipient = st.text_input("Client Email")
            
            if st.button("📨 Send Email Report", use_container_width=True):
                st.info("Configure email in report_generator.py first!")
        
        st.divider()
        
        # CSV Export
        st.markdown("### 📊 Export Data")
        col1, col2 = st.columns(2)
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                csv,
                "gsc_data.csv",
                "text/csv",
                use_container_width=True
            )
        with col2:
            top_pages_df = get_top_pages(df)
            if not top_pages_df.empty:
                csv2 = top_pages_df.to_csv(index=False)
                st.download_button(
                    "📥 Download Top Pages CSV",
                    csv2,
                    "top_pages.csv",
                    "text/csv",
                    use_container_width=True
                )