# 🚀 Enterprise Google Search Console (GSC) Analytics & SEO Intelligence Platform

An enterprise-grade, multi-user Google Search Console (GSC) intelligence and automation platform built with Python, Streamlit, and Google Search Console APIs.

Designed for SEO agencies, digital marketing teams, and website owners to unlock advanced data capabilities beyond standard Search Console limits (25,000 rows pagination, weighted metrics, canonical audit, algorithm impact analysis, and empirical CTR curve forecasting).

---

## ✨ Key Features & SEO Engines

### 1. 🔍 URL Inspection & Canonical Audit Engine
- Direct integration with Google Search Console **URL Inspection API**.
- Real-time index status, crawl verdict, mobile usability, and rich results checks.
- **Canonical Mismatch Detection**: Flags discrepancies where `user_canonical != google_canonical` causing ranking cannibalization.

### 2. ⚡ Google Algorithm Update Impact Analyzer
- Built-in tracking of major Google Core Updates, Helpful Content Updates (HCU), and Spam Updates.
- Calculates exact **Pre-Update vs. Post-Update** impact across Clicks, Impressions, CTR, and Average Position.
- Visualizes winners and losers at page and query levels.

### 3. 📈 Custom Empirical CTR Curve Modeler
- Replaces generic industry CTR averages with a mathematical curve derived directly from your site's actual ranking data.
- **Traffic Opportunity Forecaster**: Simulates organic traffic uplift if underperforming pages improve rankings by +1, +2, or +3 positions.

### 4. 🗺️ Sitemaps Health & Coverage Manager
- Real-time inspection of submitted XML sitemaps via GSC API.
- Monitors submission dates, download errors, warnings, and unsubmitted sitemap discovery.
- In-dashboard one-click sitemap resubmission.

### 5. 🔄 Log File & Crawl Reconciliation Engine
- Reconciles GSC performance data with **Screaming Frog crawl exports** and **server access logs**.
- Detects **Zombie Pages** (crawled by Googlebot but generating zero search clicks).
- Identifies **Orphan URLs** (indexed in Google but missing from internal site architecture).

### 6. 🤖 24/7 Headless Automation & GitHub Actions Generator
- Auto-generates standalone CLI scripts (`gsc_headless_audit.py`) for automated cron execution.
- Generates plug-and-play `.github/workflows/gsc_audit.yml` to run daily audits on GitHub Actions for free.
- Sends automatic email anomaly alerts when performance drops exceed threshold.

### 7. 📄 Executive PDF Reporting & Alerting
- Generates professional multi-page PDF executive performance reports with tables and branding.
- Anomaly detection for sudden CTR drops, high-impression low-click queries, and 404/crawling spikes.

---

## 🔒 Multi-User & Multi-Tenant Architecture
- **Complete Session Isolation**: Each user connects via OAuth 2.0 or Service Account independently. No shared tokens or cross-account data leakage.
- **Support for Both Auth Methods**:
  - **OAuth 2.0 Web Flow**: Multi-user login with standard Google accounts.
  - **Service Account JSON**: Enterprise headless automation without browser interaction.
- **Cloud-Ready**: Native support for environment variables (`GSC_CREDENTIALS_JSON`) for instant deployment on Streamlit Community Cloud, Heroku, or AWS.

---

## 🛠️ Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/sobuzhawlader/-Users-hp-Desktop-gsc-dashboard.git
cd -Users-hp-Desktop-gsc-dashboard
```

### 2. Setup Virtual Environment & Dependencies
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Google Cloud API Credentials Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable the **Google Search Console API**.
3. Go to **APIs & Services > Credentials** and create an **OAuth 2.0 Client ID** (Application type: *Web application*).
4. Add Authorized Redirect URIs:
   - For local development: `http://localhost:8501`
   - For production: `https://<your-app-name>.streamlit.app`
5. Download the credentials and save them as `credentials.json` in the root project folder (see `credentials.json.example`).

### 4. Run the Dashboard
- **Windows (One-Click)**: Double-click `run_dashboard.bat`
- **Manual Command**:
```bash
streamlit run app_ui.py
```
Access the application at `http://localhost:8501`.

---

## ☁️ Deploying to Streamlit Community Cloud (100% Free)

1. Push your repository to GitHub.
2. Visit [share.streamlit.io](https://share.streamlit.io) and log in with GitHub.
3. Click **"New App"** and select:
   - **Repository**: `sobuzhawlader/-Users-hp-Desktop-gsc-dashboard`
   - **Branch**: `main`
   - **Main file path**: `app_ui.py`
4. In **Advanced Settings > Secrets**, paste your `credentials.json` content as:
```toml
GSC_CREDENTIALS_JSON = '''
{
  "web": {
    "client_id": "YOUR_CLIENT_ID",
    "project_id": "YOUR_PROJECT_ID",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["https://<your-app-name>.streamlit.app"]
  }
}
'''
```
5. Click **Deploy**! Your multi-user GSC Dashboard is live worldwide.

---

## 🛡️ Security & Privacy
- Sensitive files (`token.pickle`, `token_b64.txt`, `gsc_data.db`, `.env`) are ignored via `.gitignore` to prevent secret exposure.
- Authentication tokens are maintained within temporary memory sessions and are automatically refreshed.

---

## 📄 License
MIT License. Free for personal, commercial, and agency use.
