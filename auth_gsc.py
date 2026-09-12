import os
import pickle
import json
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/webmasters']
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
        redirect_uri=redirect_uri
    )
    auth_url, state = flow.authorization_url(
        prompt='consent',
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
        redirect_uri=redirect_uri
    )
    flow.fetch_token(code=code)
    return flow.credentials

def authenticate_local(port=8080):
    """Local server flow for desktop/single-machine usage."""
    config = load_client_config()
    if not config:
        raise FileNotFoundError(f"Missing '{CREDENTIALS_FILE}'.")

    flow = InstalledAppFlow.from_client_config(config, scopes=SCOPES)
    try:
        creds = flow.run_local_server(
            port=port,
            prompt='consent',
            authorization_prompt_message='Please authorize GSC Pro Dashboard in your browser.',
            success_message='Authentication successful! You can close this tab and return to the dashboard.'
        )
    except Exception:
        creds = flow.run_local_server(
            port=0,
            prompt='consent',
            authorization_prompt_message='Please authorize GSC Pro Dashboard in your browser.',
            success_message='Authentication successful! You can close this tab and return to the dashboard.'
        )
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

def get_sites(service):
    """Fetches list of all verified properties in the connected Google account."""
    if not service:
        return []
    try:
        sites = service.sites().list().execute()
        return [s['siteUrl'] for s in sites.get('siteEntry', [])]
    except Exception as e:
        print(f"Error fetching GSC sites: {e}")
        return []