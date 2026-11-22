# Publish helpers

Copy of the Globewake YouTube publisher used for ALERT Shorts. Put OAuth files in `secrets/` (`chmod 600`); never commit them. For Shorts: `python3 publish/publish_youtube.py --dry-run --shorts-only` then the same command without `--dry-run`. TikTok is posted by hand in TikTok Studio with the YouTube Short link in the caption — see the root SKILL.md.

---

# Globewake publish automation (official APIs only)

## Daily use
    cd /workspace/news-channel/publish
    python3 publish_youtube.py day-NNN --dry-run      # validate, uploads nothing
    python3 publish_youtube.py day-NNN                # episode public now + Shorts public now
    python3 publish_youtube.py day-NNN --shorts-at 2026-11-17T15:00:00+02:00,2026-11-17T19:00:00+02:00
    python3 publish_tiktok.py day-NNN --dry-run       # (real posting only once TikTok API approved)
    python3 publish_youtube.py day-NNN --shorts-only --synthetic   # only shorts/NN, episode untouched, stage unchanged
Options: --shorts-only, --episode-at ISO, --playlist NAME|ID (default status.json published.playlist), --no-shorts, --synthetic.

publish_youtube.py: resumable upload (public, not for kids, category 25 News & Politics, en, tags, desc),
custom thumbnail (thumbnail/a.png or thumbnails/thumb_A.png, ≤2 MB), Shorts get "#Shorts", scheduled publishAt,
pinned_comment.txt posted as top-level comment, playlist add, links appended to upload/published.txt
as `[yt] Episode: …` / `[yt] Short 01: …`, status.json stage=published. Re-running skips anything already
in published.txt (also the older browser-format lines). `status.containsSyntheticMedia` (the altered-content
flag) is set via the API: false by default, `--synthetic` sets true.

Limits checked in dry run: title ≤100, description ≤5000 (no < >), tags ≤500 chars, mp4/title/comment/thumbnail present.

**Still needs the browser (no API):** pinning the comment, Test & Compare thumbnails (B/C), Shorts "related video" link.

Quota: videos.insert ≈1600 units (+50 thumbnail, +50 comment, +50 playlist). Default 10,000 units/day → ~4–5 uploads/day
(1 episode + 2–3 Shorts fits). More needs a quota increase request in Google Cloud.

## One-time YouTube setup (≈10 min, as the channel Google account)
1. https://console.cloud.google.com → new project "Globewake Publisher".
2. APIs & Services → Library → "YouTube Data API v3" → Enable.
3. OAuth consent screen (Google Auth Platform) → External, app name Globewake Publisher, your email → Audience: keep **Testing**, add the channel Google account as a test user.
4. Clients → Create client → **Desktop app** → Download JSON → save as `publish/secrets/client_secret.json` (or send it to the bot).
5. `python3 auth_youtube.py` → open the URL, pick the Globewake channel, Allow → paste the final localhost URL. Token saved to `secrets/youtube_token.json` (600).
Note: in Testing mode Google refresh tokens expire after 7 days → re-run step 5 weekly, or Publish the app (unverified is fine for own use; you'll click "Advanced → continue") so the token lasts.
The current videos reference says uploads from unverified API projects are no longer forced private.
Still, test with one upload first.

## TikTok (Content Posting API, Direct Post)
- Register at developers.tiktok.com, create an app, add Login Kit + Content Posting API, request scope `video.publish` (needs app review incl. a demo video, privacy policy and ToS URLs).
- Unaudited apps: posts only `SELF_ONLY`, account must be private while posting, ≤5 users/24 h. Public posting needs a separate Direct Post audit (UX rules: privacy dropdown with no default, interaction toggles, music-usage declaration, preview). Reports: days to several weeks, often rejected first time.
- Token: OAuth v2 (authorize → code → /v2/oauth/token/), access token 24 h, refresh token 365 days. Save `secrets/tiktok.json` with client_key, client_secret, access_token, refresh_token, open_id.
- Cap ~15 posts/day/creator. Until audited, TikTok posting stays in the browser.
Sources: developers.tiktok.com/doc/content-sharing-guidelines · developers.tiktok.com/docs/en/content-posting-api-reference-direct-post · developers.tiktok.com/docs/en/content-posting-api-get-started
