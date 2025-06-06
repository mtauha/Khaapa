import streamlit as st
import uuid
import json
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure paths and secrets
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/spreadsheets",
]
REDIRECT_URI = "https://khaapa-pos.streamlit.app/"  # Streamlit runs on this by default

# Fake session store (for dev)
session_store = {}


def google_login():
    if "credentials" not in st.session_state:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        auth_url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true"
        )
        st.session_state["auth_state"] = state
        st.link_button("Log in with Google", url=auth_url)
        st.stop()
    else:
        creds = Credentials(**st.session_state["credentials"])
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds


def handle_oauth_callback():
    # Parse full URL including ?code=...
    query_params = st.query_params
    if "state" in query_params and "code" in query_params:
        state = query_params["state"]
        code = query_params["code"]

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
            state=state
        )
        flow.fetch_token(code=code)

        creds = flow.credentials
        st.session_state["credentials"] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        return creds
    return None


def get_user_email(creds):
    from google.oauth2 import id_token
    from google.auth.transport import requests

    idinfo = id_token.verify_oauth2_token(
        creds.id_token, requests.Request(), creds.client_id
    )
    email = idinfo.get("email")
    return email


def create_session(email):
    session_token = str(uuid.uuid4())
    session_store[session_token] = email
    return session_token


def get_email_from_session(session_token):
    return session_store.get(session_token)
