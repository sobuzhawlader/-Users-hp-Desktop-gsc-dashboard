# 🚀 GSC Pro Dashboard - Free Multi-User Web Deployment Guide

This guide explains how to host your **GSC Pro Dashboard** online for **100% FREE**, so clients, team members, or public users can access it from any browser or phone and log in with their own Google Search Console accounts.

---

## 🌟 Method 1: Streamlit Community Cloud (Recommended - 100% Free Forever)

Streamlit Community Cloud gives you a free permanent public URL (e.g., `https://your-gsc-dashboard.streamlit.app`) with automatic HTTPS and free server hosting.

### Step 1: Push Project to GitHub
1. Create a free account on [GitHub](https://github.com).
2. Create a new repository (e.g. `gsc-pro-dashboard`).
3. Upload/push all files from `C:\Users\hp\Desktop\gsc-dashboard\` to your repository.
   *(Note: Do not commit sensitive tokens or passwords).*

### Step 2: Deploy to Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io) and log in with GitHub.
2. Click **"New App"**.
3. Select your repository: `yourusername/gsc-pro-dashboard`.
4. Main file path: `app_ui.py`.
5. Click **"Deploy!"**. Within 1–2 minutes, your dashboard will be live on a public URL!

### Step 3: Configure Google OAuth Redirect URI
1. Open your live app URL (e.g., `https://your-gsc-dashboard.streamlit.app`).
2. Go to the [Google Cloud Console Credentials Page](https://console.cloud.google.com/apis/credentials).
3. Click on your **OAuth 2.0 Client ID**.
4. Under **Authorized redirect URIs**, click **+ Add URI** and add:
   - `https://your-gsc-dashboard.streamlit.app/`
   - `http://localhost:8501/` (for local usage)
5. Under **Authorized JavaScript origins**, add:
   - `https://your-gsc-dashboard.streamlit.app`
6. Click **Save**.
7. Now anyone visiting your public link can click **"🌐 Connect with Google"** and view their own Search Console data securely!

---

## 🌐 Method 2: Render.com (Alternative Free Web Hosting)

1. Sign up on [Render.com](https://render.com).
2. Create a **New Web Service** linked to your GitHub repo.
3. Environment: **Python 3**.
4. Build Command: `pip install -r requirements.txt`.
5. Start Command: `streamlit run app_ui.py --server.port $PORT --server.address 0.0.0.0`.
6. Add your Render domain (`https://your-app.onrender.com/`) to your Google Cloud OAuth **Authorized redirect URIs**.

---

## 🔒 Multi-User Security & Privacy
- **Session Isolation:** Each user's Google tokens and Search Console performance metrics are held strictly in their individual browser session memory (`st.session_state`).
- **No Cross-User Leaks:** User A cannot see User B's verified sites, keywords, clicks, or inspection reports.
