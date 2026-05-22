import requests
import pandas as pd
from datetime import datetime
from database import save_alert, load_alerts

# ==============================
# Telegram Configuration
# ==============================
TELEGRAM_BOT_TOKEN = ""  # আপনার Telegram Bot Token এখানে দিন
TELEGRAM_CHAT_ID = ""    # আপনার Chat ID এখানে দিন

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured!")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("Telegram alert sent!")
            return True
    except Exception as e:
        print(f"Telegram error: {e}")
    return False

def check_traffic_drop(df_current, df_previous, site_url, threshold=30):
    if df_current.empty or df_previous.empty:
        return
    
    current_clicks = df_current['clicks'].sum()
    previous_clicks = df_previous['clicks'].sum()
    
    if previous_clicks == 0:
        return
    
    drop_pct = ((previous_clicks - current_clicks) / previous_clicks) * 100
    
    if drop_pct >= threshold:
        message = f"""
🚨 <b>Traffic Drop Alert!</b>
Site: {site_url}
Previous Clicks: {int(previous_clicks)}
Current Clicks: {int(current_clicks)}
Drop: {round(drop_pct, 2)}%
Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        send_telegram(message)
        save_alert(site_url, 'traffic_drop', 
                  f"Traffic dropped {round(drop_pct, 2)}% - From {int(previous_clicks)} to {int(current_clicks)} clicks")

def check_position_drop(df_current, df_previous, site_url, threshold=5):
    if df_current.empty or df_previous.empty:
        return
    
    current_pos = df_current['position'].mean()
    previous_pos = df_previous['position'].mean()
    
    drop = current_pos - previous_pos
    
    if drop >= threshold:
        message = f"""
📉 <b>Position Drop Alert!</b>
Site: {site_url}
Previous Avg Position: {round(previous_pos, 2)}
Current Avg Position: {round(current_pos, 2)}
Drop: {round(drop, 2)} positions
Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        send_telegram(message)
        save_alert(site_url, 'position_drop',
                  f"Average position dropped from {round(previous_pos, 2)} to {round(current_pos, 2)}")

def check_ctr_drop(df_current, df_previous, site_url, threshold=20):
    if df_current.empty or df_previous.empty:
        return
    
    current_ctr = df_current['ctr'].mean()
    previous_ctr = df_previous['ctr'].mean()
    
    if previous_ctr == 0:
        return
    
    drop_pct = ((previous_ctr - current_ctr) / previous_ctr) * 100
    
    if drop_pct >= threshold:
        message = f"""
⚠️ <b>CTR Drop Alert!</b>
Site: {site_url}
Previous CTR: {round(previous_ctr, 2)}%
Current CTR: {round(current_ctr, 2)}%
Drop: {round(drop_pct, 2)}%
Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        send_telegram(message)
        save_alert(site_url, 'ctr_drop',
                  f"CTR dropped {round(drop_pct, 2)}% - From {round(previous_ctr, 2)}% to {round(current_ctr, 2)}%")

def run_all_checks(df_current, df_previous, site_url):
    print(f"Running alert checks for {site_url}...")
    check_traffic_drop(df_current, df_previous, site_url)
    check_position_drop(df_current, df_previous, site_url)
    check_ctr_drop(df_current, df_previous, site_url)
    print("Alert checks complete!")

def get_unread_alerts(site_url=None):
    return load_alerts(site_url)