"""
Google Webmaster Instant Indexing API Client
Enables instant Googlebot crawl and indexing requests (URL_UPDATED / URL_DELETED).
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build

INDEXING_SCOPE = ['https://www.googleapis.com/auth/indexing']

def get_indexing_service(sa_data: Optional[Any] = None):
    """Initializes Google Indexing API v3 service using Service Account or secrets."""
    try:
        # Check Streamlit secrets first
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'GSC_SERVICE_ACCOUNT_JSON' in st.secrets:
                sa_val = st.secrets['GSC_SERVICE_ACCOUNT_JSON']
                sa_dict = json.loads(sa_val) if isinstance(sa_val, str) else dict(sa_val)
                creds = service_account.Credentials.from_service_account_info(sa_dict, scopes=INDEXING_SCOPE)
                return build('indexing', 'v3', credentials=creds)
        except Exception:
            pass

        # Check parameter
        if sa_data:
            if isinstance(sa_data, dict):
                creds = service_account.Credentials.from_service_account_info(sa_data, scopes=INDEXING_SCOPE)
                return build('indexing', 'v3', credentials=creds)
            elif isinstance(sa_data, str) and os.path.exists(sa_data):
                creds = service_account.Credentials.from_service_account_file(sa_data, scopes=INDEXING_SCOPE)
                return build('indexing', 'v3', credentials=creds)
    except Exception as e:
        print(f"Indexing API service init error: {e}")

    return None


def request_indexing(url: str, action: str = "URL_UPDATED", service = None) -> Dict[str, Any]:
    """
    Submits a URL to Google Indexing API for instant crawl.
    Action: 'URL_UPDATED' (index/re-index) or 'URL_DELETED' (remove from index).
    """
    cleaned_url = url.strip()
    if not cleaned_url or not cleaned_url.startswith('http'):
        return {
            'url': url,
            'status': 'error',
            'message': 'Invalid URL. Must begin with http:// or https://'
        }

    valid_action = "URL_UPDATED" if action.upper() in ["URL_UPDATED", "UPDATE", "INDEX"] else "URL_DELETED"

    if service:
        try:
            payload = {
                'url': cleaned_url,
                'type': valid_action
            }
            resp = service.urlNotifications().publish(body=payload).execute()
            meta = resp.get('urlNotificationMetadata', {})
            return {
                'url': cleaned_url,
                'status': 'success',
                'action': valid_action,
                'notify_time': meta.get('latestUpdate', {}).get('notifyTime', time.strftime('%Y-%m-%d %H:%M:%S UTC')),
                'message': f"✅ Google Indexing API accepted: {valid_action}"
            }
        except Exception as ex:
            return {
                'url': cleaned_url,
                'status': 'error',
                'action': valid_action,
                'message': f"Google API Error: {str(ex)}"
            }

    # Offline simulated / local queue mode
    return {
        'url': cleaned_url,
        'status': 'queued',
        'action': valid_action,
        'notify_time': time.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'message': f"🚀 Indexing request recorded ({valid_action}). Connect Service Account to broadcast live."
    }


def batch_request_indexing(urls: List[str], action: str = "URL_UPDATED", service = None) -> List[Dict[str, Any]]:
    """Submits multiple URLs for indexing with rate limit throttling."""
    results = []
    for u in urls:
        if u.strip():
            res = request_indexing(u.strip(), action=action, service=service)
            results.append(res)
            time.sleep(0.1)
    return results


def get_indexing_status(url: str, service = None) -> Dict[str, Any]:
    """Queries notification metadata for a URL."""
    if service:
        try:
            resp = service.urlNotifications().getMetadata(url=url).execute()
            return {'status': 'success', 'data': resp}
        except Exception as ex:
            return {'status': 'error', 'message': str(ex)}

    return {
        'status': 'info',
        'message': 'Connect Google Service Account with indexing scope to view live notification timestamps.'
    }
