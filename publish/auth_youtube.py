#!/usr/bin/env python3
"""One-time YouTube OAuth. Needs publish/secrets/client_secret.json (Desktop client).
Prints a consent URL; paste back the code or the full redirect URL (http://localhost/?code=...)."""
import json, os, sys
from google_auth_oauthlib.flow import InstalledAppFlow
from urllib.parse import urlparse, parse_qs
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets")
CS, TOK = os.path.join(D, "client_secret.json"), os.path.join(D, "youtube_token.json")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube",
          "https://www.googleapis.com/auth/youtube.force-ssl"]
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
if not os.path.exists(CS):
    sys.exit(f"Missing {CS}. See README.md (Create OAuth client).")
flow = InstalledAppFlow.from_client_secrets_file(CS, SCOPES, redirect_uri="http://localhost")
hint = os.environ.get("GLOBEWAKE_YT_LOGIN")
url, _ = flow.authorization_url(access_type="offline", prompt="consent",
                                **({"login_hint": hint} if hint else {}))
print("Open this URL, sign in as the channel Google account, choose the channel, allow:\n\n" + url +
      "\n\nThe browser then lands on a 'can't connect to localhost' page; copy that whole URL.")
raw = (sys.argv[1] if len(sys.argv) > 1 else input("Paste code or redirect URL: ")).strip()
code = parse_qs(urlparse(raw).query).get("code", [raw])[0] if raw.startswith("http") else raw
flow.fetch_token(code=code)
os.makedirs(D, exist_ok=True)
with open(TOK, "w") as f: f.write(flow.credentials.to_json())
os.chmod(TOK, 0o600)
from googleapiclient.discovery import build
ch = build("youtube", "v3", credentials=flow.credentials).channels().list(part="snippet", mine=True).execute()
for it in ch.get("items", []): print("Authorized channel:", it["id"], it["snippet"]["title"])
print("Saved", TOK)
