# Local credentials (do not commit)

Place only on the machine that publishes:

- `client_secret.json` — Google OAuth Desktop client (chmod 600)
- `youtube_token.json` — written by `auth_youtube_local.py` (chmod 600)
- `tiktok.json` — only after the TikTok app is audited; see `publish/README.md`

Directory permissions: `chmod 700 publish/secrets`.
