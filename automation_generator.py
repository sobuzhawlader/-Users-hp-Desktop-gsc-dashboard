import os

GITHUB_ACTIONS_WORKFLOW = """name: Daily Free GSC SEO Audit

on:
  schedule:
    - cron: '0 6 * * *'  # Runs every day at 06:00 UTC
  workflow_dispatch:      # Allows manual trigger anytime

jobs:
  seo_audit:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install google-api-python-client google-auth pandas requests

      - name: Run Headless GSC Audit
        env:
          GSC_TOKEN_B64: ${{ secrets.GSC_TOKEN_B64 }}
          GSC_SITE_URL: ${{ secrets.GSC_SITE_URL }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          python automated_audit.py
"""

HEADLESS_AUDIT_SCRIPT = """import os
import base64
import pickle
import requests
import pandas as pd
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SITE_URL = os.environ.get('GSC_SITE_URL', '')
TOKEN_B64 = os.environ.get('GSC_TOKEN_B64', '')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

def get_service():
    if not TOKEN_B64:
        raise ValueError("Missing GSC_TOKEN_B64 secret.")
    creds_bytes = base64.b64decode(TOKEN_B64)
    creds = pickle.loads(creds_bytes)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('webmasters', 'v3', credentials=creds)

def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured. Log message:\\n", text)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}
    requests.post(url, json=payload)

def run_audit():
    service = get_service()
    today = datetime.now()
    
    # 7 days current vs 7 days previous
    curr_end = (today - timedelta(days=2)).strftime('%Y-%m-%d')
    curr_start = (today - timedelta(days=9)).strftime('%Y-%m-%d')
    
    prev_end = (today - timedelta(days=10)).strftime('%Y-%m-%d')
    prev_start = (today - timedelta(days=17)).strftime('%Y-%m-%d')

    body_curr = {'startDate': curr_start, 'endDate': curr_end, 'dimensions': ['date']}
    body_prev = {'startDate': prev_start, 'endDate': prev_end, 'dimensions': ['date']}

    res_c = service.searchanalytics().query(siteUrl=SITE_URL, body=body_curr).execute()
    res_p = service.searchanalytics().query(siteUrl=SITE_URL, body=body_prev).execute()

    clicks_curr = sum(r.get('clicks', 0) for r in res_c.get('rows', []))
    clicks_prev = sum(r.get('clicks', 0) for r in res_p.get('rows', []))

    print(f"Audit completed: Current={clicks_curr} clicks, Prev={clicks_prev} clicks")

    if clicks_prev > 0:
        drop_pct = ((clicks_prev - clicks_curr) / clicks_prev) * 100
        if drop_pct >= 20.0:
            msg = f"🚨 <b>GSC SEO Alert: Traffic Drop Detected!</b>\\n\\nSite: {SITE_URL}\\nPrev 7d: {clicks_prev} clicks\\nCurr 7d: {clicks_curr} clicks\\nDrop: <b>{drop_pct:.1f}%</b>\\nAudit Date: {today.strftime('%Y-%m-%d')}"
            send_telegram(msg)
        else:
            print(f"Traffic stable (change: {-drop_pct:.1f}%)")

if __name__ == '__main__':
    run_audit()
"""

def generate_automation_bundle(output_dir: str):
    """Writes the GitHub Actions workflow and automated audit script to disk."""
    wf_dir = os.path.join(output_dir, '.github', 'workflows')
    os.makedirs(wf_dir, exist_ok=True)

    wf_file = os.path.join(wf_dir, 'gsc_audit.yml')
    with open(wf_file, 'w', encoding='utf-8') as f:
        f.write(GITHUB_ACTIONS_WORKFLOW)

    audit_file = os.path.join(output_dir, 'automated_audit.py')
    with open(audit_file, 'w', encoding='utf-8') as f:
        f.write(HEADLESS_AUDIT_SCRIPT)

    return wf_file, audit_file
