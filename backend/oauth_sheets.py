import os
from threading import Lock
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

_creds_store = {}
_store_lock = Lock()


def store_credentials(session_key: str, token: dict):
    creds = Credentials(
        token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("OAUTH_CLIENT_ID"),
        client_secret=os.getenv("OAUTH_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    with _store_lock:
        _creds_store[session_key] = creds


def get_sheets_service(session_key: str):
    with _store_lock:
        creds = _creds_store.get(session_key)
    if not creds:
        raise Exception("No OAuth credentials for this session")
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with _store_lock:
            _creds_store[session_key] = creds
    return build("sheets", "v4", credentials=creds)
