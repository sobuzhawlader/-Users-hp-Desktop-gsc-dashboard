"""
telegram_alerter.py
24/7 SEO Anomaly Detection & Free Telegram Alert Bot Engine
100% Free - Zero Cost, Uses Official Telegram Botfather API
"""

import requests
import json
from datetime import datetime
import pandas as pd
from database import save_alert, load_alerts

def send_telegram_notification(bot_token: str, chat_id: str, title: str, message: str, severity: str = "INFO") -> dict:
    """
    Dispatches a formatted alert notification to a Telegram Chat or Channel.
    Cost: $0.00 (Official Telegram Bot API)
    """
    if not bot_token or not chat_id:
        return {"success": False, "error": "Bot Token or Chat ID is missing"}

    icon_map = {
        "CRITICAL": "🚨",
        "WARNING": "⚠️",
        "SUCCESS": "✅",
        "OPPORTUNITY": "🚀",
        "INFO": "ℹ️"
    }
    icon = icon_map.get(severity.upper(), "🔔")

    text = f"""
{icon} <b>{title}</b>
<code>────────────────────────</code>
{message}
<code>────────────────────────</code>
📅 <b>Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
⚡ <i>GSC Terminal Enterprise Alert</i>
""".strip()

    url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
    payload = {
        "chat_id": str(chat_id).strip(),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if resp.status_code == 200 and data.get("ok"):
            return {"success": True, "message_id": data.get("result", {}).get("message_id")}
        else:
            err = data.get("description", f"HTTP {resp.status_code}")
            return {"success": False, "error": err}
    except Exception as ex:
        return {"success": False, "error": str(ex)}

def test_telegram_connection(bot_token: str, chat_id: str) -> dict:
    """Sends an instant ping to verify the Telegram Bot credentials."""
    title = "GSC Terminal Telemetry Verified"
    msg = (
        "<b>Status:</b> Connected & Armed 🟢\n"
        "<b>Engine:</b> 24/7 Autonomous Search Anomaly Bot\n"
        "Your Google Search Console anomaly alerts will now stream live to this chat."
    )
    return send_telegram_notification(bot_token, chat_id, title, msg, severity="SUCCESS")

def analyze_gsc_anomalies(df_current: pd.DataFrame, df_previous: pd.DataFrame, site_url: str, bot_token: str = None, chat_id: str = None) -> list:
    """
    Runs automated anomaly heuristics between two comparison periods:
    1. Sudden Traffic Drop (Clicks dropped >= 20%)
    2. Rank Position Degradation (Top keywords dropped >= 3 ranks)
    3. Impression Surge without Clicks (CTR Opportunity)
    """
    alerts = []

    if df_current.empty:
        return alerts

    curr_clicks = int(df_current['clicks'].sum()) if 'clicks' in df_current.columns else 0
    curr_impr = int(df_current['impressions'].sum()) if 'impressions' in df_current.columns else 0
    curr_pos = round(df_current['position'].mean(), 2) if 'position' in df_current.columns else 0.0

    if not df_previous.empty and 'clicks' in df_previous.columns and 'impressions' in df_previous.columns:
        prev_clicks = int(df_previous['clicks'].sum())
        prev_impr = int(df_previous['impressions'].sum())
        prev_pos = round(df_previous['position'].mean(), 2)

        # 1. Traffic Drop Anomaly
        if prev_clicks > 10:
            click_delta_pct = ((curr_clicks - prev_clicks) / prev_clicks) * 100
            if click_delta_pct <= -20.0:
                alert_item = {
                    "site_url": site_url,
                    "type": "TRAFFIC_DROP",
                    "severity": "CRITICAL" if click_delta_pct <= -40.0 else "WARNING",
                    "title": f"Traffic Drop Detected ({round(click_delta_pct, 1)}%)",
                    "message": f"Clicks dropped from <b>{prev_clicks:,}</b> to <b>{curr_clicks:,}</b> ({round(click_delta_pct, 1)}%) on <code>{site_url}</code>."
                }
                alerts.append(alert_item)
                save_alert(site_url, alert_item["type"], alert_item["message"])
                if bot_token and chat_id:
                    send_telegram_notification(bot_token, chat_id, alert_item["title"], alert_item["message"], alert_item["severity"])

        # 2. Position Degradation
        if prev_pos > 0 and (curr_pos - prev_pos) >= 2.5:
            pos_loss = round(curr_pos - prev_pos, 1)
            alert_item = {
                "site_url": site_url,
                "type": "POSITION_DROP",
                "severity": "WARNING",
                "title": f"Average Rank Drop (-{pos_loss} Positions)",
                "message": f"Average position fell from <b>{prev_pos}</b> to <b>{curr_pos}</b> on <code>{site_url}</code>."
            }
            alerts.append(alert_item)
            save_alert(site_url, alert_item["type"], alert_item["message"])
            if bot_token and chat_id:
                send_telegram_notification(bot_token, chat_id, alert_item["title"], alert_item["message"], alert_item["severity"])

    # 3. Quick Win / Opportunity Anomaly (Position 4-15 with high impressions and low CTR)
    if 'query' in df_current.columns and 'position' in df_current.columns and 'impressions' in df_current.columns:
        opp = df_current[
            (df_current['position'] >= 4.0) & 
            (df_current['position'] <= 15.0) & 
            (df_current['impressions'] >= 200) &
            (df_current['clicks'] <= 5)
        ]
        if not opp.empty:
            top_opp = opp.sort_values(by='impressions', ascending=False).iloc[0]
            q_name = top_opp['query']
            q_imp = int(top_opp['impressions'])
            q_pos = round(top_opp['position'], 1)
            alert_item = {
                "site_url": site_url,
                "type": "HIGH_IMPRESSION_OPPORTUNITY",
                "severity": "OPPORTUNITY",
                "title": f"High Impression CTR Opportunity",
                "message": f"Keyword <b>'{q_name}'</b> has <b>{q_imp:,} impressions</b> at position <b>{q_pos}</b> with minimal clicks. Optimize title & meta description to capture immediate traffic!"
            }
            alerts.append(alert_item)

    return alerts
