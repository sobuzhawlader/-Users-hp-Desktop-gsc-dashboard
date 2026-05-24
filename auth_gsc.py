import os
import pickle
import base64
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
REDIRECT_URI = 'https://gsc-dashboard-vlyd.onrender.com/oauth2callback'

def get_auth_url():
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        prompt='consent',
        access_type='offline'
    )
    return auth_url, state

def exchange_code(code, state):
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state=state
    )
    flow.fetch_token(code=code)
    return flow.credentials

def get_gsc_service(creds=None):
    if creds is None:
        token_b64 = os.environ.get('TOKEN_B64')
        if token_b64:
            creds = pickle.loads(base64.b64decode(token_b64))
        elif os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as f:
                creds = pickle.load(f)

    if not creds:
        return None

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build('webmasters', 'v3', credentials=creds)

def get_sites(service):
    if not service:
        return []
    sites = service.sites().list().execute()
    return [s['siteUrl'] for s in sites.get('siteEntry', [])]