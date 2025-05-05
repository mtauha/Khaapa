import os
import uuid
from fastapi import APIRouter, Request
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.responses import RedirectResponse
from oauth_sheets import store_credentials
from sheets import log_session as sheet_log_session

config = Config(".env")
oauth = OAuth(config)
oauth.register(
    name="google",
    client_id=config("OAUTH_CLIENT_ID"),
    client_secret=config("OAUTH_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile https://www.googleapis.com/auth/spreadsheets"
    },
)

router = APIRouter()


@router.get("/login")
async def login(request: Request):
    redirect_uri = config("OAUTH_REDIRECT_URI")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get("userinfo") or await oauth.google.parse_id_token(request, token)
    email = user["email"]
    session_key = str(uuid.uuid4())
    store_credentials(session_key, token)
    sheet_log_session(session_key, email)
    resp = RedirectResponse(url="/")
    resp.set_cookie("session_key", session_key, httponly=True)
    return resp
