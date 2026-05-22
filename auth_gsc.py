import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'

def get_gsc_service():
    creds = None
    
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    from googleapiclient.discovery import build
    service = build('webmasters', 'v3', credentials=creds)
    return service

def get_sites(service):
    sites = service.sites().list().execute()
    return [s['siteUrl'] for s in sites.get('siteEntry', [])]

if __name__ == '__main__':
    print("Google GSC connecting...")
    service = get_gsc_service()
    sites = get_sites(service)
    print(f"Connected! {len(sites)} sites found:")
    for site in sites:
        print(f"  - {site}")