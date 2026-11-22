#!/usr/bin/env python3
"""One-time YouTube OAuth using a local callback server on the box (port 8765).
Open the printed URL in the box browser; the redirect to localhost:8765 is captured automatically."""
import os, sys
from google_auth_oauthlib.flow import InstalledAppFlow
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets")
CS, TOK = os.path.join(D, "client_secret.json"), os.path.join(D, "youtube_token.json")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube",
          "https://www.googleapis.com/auth/youtube.force-ssl"]
flow = InstalledAppFlow.from_client_secrets_file(CS, SCOPES)
kw = dict(host="localhost", port=8765, open_browser=False,
    authorization_prompt_message="AUTH_URL: {url}", access_type="offline", prompt="consent",
    success_message="Authorized. You can close this tab.")
if os.environ.get("GLOBEWAKE_YT_LOGIN"):
    kw["login_hint"] = os.environ["GLOBEWAKE_YT_LOGIN"]
creds = flow.run_local_server(**kw)
with open(TOK, "w") as f: f.write(creds.to_json())
os.chmod(TOK, 0o600)
from googleapiclient.discovery import build
ch = build("youtube", "v3", credentials=creds).channels().list(part="snippet", mine=True).execute()
for it in ch.get("items", []): print("Authorized channel:", it["id"], it["snippet"]["title"])
print("Saved", TOK)
