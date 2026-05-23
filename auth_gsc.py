import os
import pickle
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = 'token.pickle'

def get_gsc_service():
    creds = None
    
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    if not creds or not creds.valid:
        return None
    
    service = build('webmasters', 'v3', credentials=creds)
    return service

def get_sites(service):
    if not service:
        return []
    sites = service.sites().list().execute()
    return [s['siteUrl'] for s in sites.get('siteEntry', [])]