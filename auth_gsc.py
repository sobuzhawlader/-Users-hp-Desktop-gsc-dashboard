import os
import pickle
import json
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/webmasters',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email'
]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, 'token.pickle')
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, 'service_account.json')

def load_client_config():
    """Loads the OAuth client secrets from Streamlit secrets, session, file, or environment variable."""
    # 0. Check per-session uploaded config
    try:
        import streamlit as st
        if 'client_config' in st.session_state and st.session_state.client_config:
            return st.session_state.client_config
    except Exception:
        pass

    # 1. Check Streamlit Cloud secrets
    try:
        import streamlit as st
        if hasattr(st, 'secrets'):
            if 'GSC_CREDENTIALS_JSON' in st.secrets:
                val = st.secrets['GSC_CREDENTIALS_JSON']
                if isinstance(val, dict):
                    return val
                return json.loads(val)
            if 'web' in st.secrets:
                return {'web': dict(st.secrets['web'])}
    except Exception:
        pass

    # 2. Check environment variable
    env_creds = os.environ.get('GSC_CREDENTIALS_JSON')
    if env_creds:
        try:
            return json.loads(env_creds)
        except Exception:
            pass

    # 3. Check local file
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except Exception as e:
            pass

    return None


def get_auth_url(redirect_uri: str, config: dict = None):
    """
    Generates a web OAuth authorization URL for multi-user browser authentication.
    Google will redirect back to redirect_uri with ?code=...
    """
    if not config:
        config = load_client_config()
    if not config:
        raise FileNotFoundError("Missing 'credentials.json' or GSC_CREDENTIALS_JSON in secrets/environment.")

    flow = Flow.from_client_config(
        config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        autogenerate_code_verifier=False
    )
    auth_url, state = flow.authorization_url(
        prompt='select_account consent',
        access_type='offline',
        include_granted_scopes='true'
    )
    return auth_url, state

def exchange_code(code: str, redirect_uri: str, config: dict = None):
    """
    Exchanges the authorization code returned by Google for a user's isolated credentials.
    """
    if not config:
        config = load_client_config()
    if not config:
        raise FileNotFoundError("Missing 'credentials.json'.")

    flow = Flow.from_client_config(
        config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        autogenerate_code_verifier=False
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    # In cloud multi-user environment, NEVER persist token to disk, keep in session state only!
    if not is_cloud_environment():
        save_credentials(creds)
    return creds

import platform

def is_cloud_environment() -> bool:
    """Detects whether the app is running in a multi-user cloud environment (like Streamlit Cloud)."""
    return (
        platform.system() == 'Linux' or 
        'STREAMLIT_SHARING_MODE' in os.environ or 
        'STREAMLIT_SERVER_PORT' in os.environ or
        'STREAMLIT_SERVER_ADDRESS' in os.environ or
        ('HOSTNAME' in os.environ and 'streamlit' in os.environ.get('HOSTNAME', '').lower())
    )

def load_saved_credentials():
    """Loads cached OAuth credentials only for local single-user desktop. Never on cloud!"""
    if is_cloud_environment():
        # Remove any stale shared token from cloud container disk immediately
        if os.path.exists(TOKEN_FILE):
            try:
                os.remove(TOKEN_FILE)
            except Exception:
                pass
        return None

    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'rb') as f:
                creds = pickle.load(f)
            if creds:
                if creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        save_credentials(creds)
                    except Exception:
                        pass
                return creds
        except Exception as ex:
            print(f"Error loading saved credentials: {ex}")
    return None

def save_credentials(creds):
    """Saves OAuth credentials to token.pickle only for local single-user machine. Never on cloud!"""
    if not creds:
        return
    if is_cloud_environment():
        # Ensure any stale token on cloud disk is removed
        if os.path.exists(TOKEN_FILE):
            try:
                os.remove(TOKEN_FILE)
            except Exception:
                pass
        return

    try:
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    except Exception as ex:
        print(f"Error saving credentials: {ex}")

def delete_saved_credentials():
    """Deletes cached credentials file on logout."""
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
    except Exception as ex:
        print(f"Error removing credentials file: {ex}")

def authenticate_local(port=8080):
    """Local server flow for desktop/single-machine usage."""
    config = load_client_config()
    if not config:
        raise FileNotFoundError(f"Missing '{CREDENTIALS_FILE}'.")

    flow = InstalledAppFlow.from_client_config(config, scopes=SCOPES)
    try:
        creds = flow.run_local_server(
            port=port,
            prompt='select_account consent',
            authorization_prompt_message='Please authorize GSC Pro Dashboard in your browser.',
            success_message='Authentication successful! You can close this tab and return to the dashboard.'
        )
    except Exception:
        creds = flow.run_local_server(
            port=0,
            prompt='select_account consent',
            authorization_prompt_message='Please authorize GSC Pro Dashboard in your browser.',
            success_message='Authentication successful! You can close this tab and return to the dashboard.'
        )
    if creds:
        save_credentials(creds)
    return creds

def get_gsc_service(creds):
    """Initializes and returns Webmasters API v3 client from user credentials."""
    if not creds:
        return None
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            return None
    return build('webmasters', 'v3', credentials=creds)

def get_searchconsole_v1_service(creds):
    """Initializes and returns Search Console v1 (URL Inspection) client."""
    if not creds:
        return None
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            return None
    return build('searchconsole', 'v1', credentials=creds)

def authenticate_service_account(sa_data):
    """
    Authenticates using Google Cloud Service Account JSON (dict, json string, or filepath).
    Returns (creds, service, service_v1, sites).
    """
    if isinstance(sa_data, str):
        if os.path.exists(sa_data):
            creds = service_account.Credentials.from_service_account_file(sa_data, scopes=SCOPES)
        else:
            info = json.loads(sa_data)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    elif isinstance(sa_data, dict):
        creds = service_account.Credentials.from_service_account_info(sa_data, scopes=SCOPES)
    else:
        raise ValueError("Invalid service account data provided.")

    svc = get_gsc_service(creds)
    svc_v1 = get_searchconsole_v1_service(creds)
    sites = get_sites(svc)
    return creds, svc, svc_v1, sites

import time

_SITES_CACHE = {}

def clear_sites_cache():
    """Clears the properties in-memory cache."""
    global _SITES_CACHE
    _SITES_CACHE.clear()

def get_sites_detailed(service, force_refresh: bool = False):
    """Fetches list of all verified properties in the connected Google account with permissions."""
    if not service:
        return []

    creds = getattr(service, '_credentials', None)
    cache_token = getattr(creds, 'token', '') or (str(id(service)) if service else 'anon')
    now = time.time()

    if not force_refresh and cache_token in _SITES_CACHE:
        cached_time, cached_entries = _SITES_CACHE[cache_token]
        if now - cached_time < 600:  # 10 minutes cache
            return cached_entries

    try:
        sites = service.sites().list().execute()
        entries = sites.get('siteEntry', [])
        _SITES_CACHE[cache_token] = (now, entries)
        return entries
    except Exception as e:
        print(f"Error fetching GSC sites: {e}")
        if cache_token in _SITES_CACHE:
            return _SITES_CACHE[cache_token][1]
        return []

def get_sites(service, force_refresh: bool = False):
    """Fetches list of all verified properties in the connected Google account."""
    entries = get_sites_detailed(service, force_refresh=force_refresh)
    return [s['siteUrl'] for s in entries if 'siteUrl' in s]

def get_user_email(creds):
    """Attempts to retrieve the email address of the authenticated Google user."""
    if not creds:
        return None
    try:
        # 1. Check id_token JWT payload if available
        id_tok = getattr(creds, 'id_token', None)
        if id_tok and isinstance(id_tok, str):
            import base64
            parts = id_tok.split('.')
            if len(parts) >= 2:
                padded = parts[1] + '=' * (-len(parts[1]) % 4)
                payload = json.loads(base64.b64decode(padded).decode('utf-8'))
                if 'email' in payload:
                    return payload['email']
    except Exception:
        pass

    # 2. Query Google tokeninfo endpoint
    try:
        import requests
        tok = getattr(creds, 'token', None)
        if tok:
            resp = requests.get(f"https://oauth2.googleapis.com/tokeninfo?access_token={tok}", timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                if 'email' in data:
                    return data['email']
    except Exception:
        pass
    return None