#!/usr/bin/env python3
"""Publish a Globewake day folder to YouTube via the official Data API v3.
Usage: python publish_youtube.py day-NNN [--dry-run] [--shorts-at ISO,ISO] [--episode-at ISO]
       [--playlist NAME_OR_ID] [--no-shorts] [--synthetic/--no-synthetic]
Idempotent: anything already listed in upload/published.txt is skipped."""
import argparse, glob, json, os, re, sys, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets", "youtube_token.json")
# Channel comes from the OAuth token in publish/secrets/youtube_token.json (not hardcoded).
LIM = {"title": 100, "desc": 5000, "tags": 500}

def rd(p, default=None):
    if os.path.exists(p):
        return open(p, encoding="utf-8").read().strip()
    return default

def tags_of(p):
    t = rd(p, "") or ""
    return [x.strip().lstrip("#") for x in re.split(r"[,\n]", t) if x.strip()]

def tags_len(tags):  # YouTube counts quotes around tags containing spaces + commas
    return sum(len(t) + (2 if " " in t else 0) for t in tags) + max(len(tags) - 1, 0)

def pick_thumb(day):
    for c in ["thumbnail/a.png", "thumbnails/thumb_A.png", "thumbnail/thumb_A.png", "upload/thumbnail.png"]:
        p = os.path.join(day, c)
        if os.path.exists(p): return p
    g = sorted(glob.glob(os.path.join(day, "thumbnail*/*.png")) + glob.glob(os.path.join(day, "thumbnail*/*.jpg")))
    return g[0] if g else None

def collect(day):
    items, errs = [], []
    def item(kind, base, key):
        mp4 = sorted(glob.glob(os.path.join(base, "exports", "*.mp4")))
        mp4 = [m for m in mp4 if "_raw" not in m and "draft" not in m]
        title = rd(os.path.join(base, "upload", "title.txt"))
        desc = rd(os.path.join(base, "upload", "description.txt"), "")
        tags = tags_of(os.path.join(base, "upload", "tags.txt"))
        if kind == "short" and title and "#shorts" not in title.lower() and "#shorts" not in desc.lower():
            title = (title + " #Shorts") if len(title) + 8 <= 100 else title
            if "#shorts" not in title.lower(): desc = desc + "\n#Shorts"
        it = dict(kind=kind, key=key, file=mp4[-1] if mp4 else None, title=title, desc=desc, tags=tags)
        if not mp4: errs.append(f"{key}: no exports/*.mp4")
        elif len(mp4) > 1: it["note"] = f"{len(mp4)} mp4s, using newest-named {os.path.basename(mp4[-1])}"
        if not title: errs.append(f"{key}: missing upload/title.txt")
        elif len(title) > LIM["title"]: errs.append(f"{key}: title {len(title)} > 100")
        if len(desc) > LIM["desc"]: errs.append(f"{key}: description {len(desc)} > 5000")
        if "<" in desc or ">" in desc: errs.append(f"{key}: description contains < or > (API rejects)")
        if tags_len(tags) > LIM["tags"]: errs.append(f"{key}: tags {tags_len(tags)} > 500")
        items.append(it)
    item("episode", day, "Episode")
    for s in sorted(glob.glob(os.path.join(day, "shorts", "[0-9]*"))):
        item("short", s, f"Short {os.path.basename(s)}")
    return items, errs

def published_text(day):
    return rd(os.path.join(day, "upload", "published.txt"), "") or ""

def already(day, key):
    for line in published_text(day).splitlines():
        if line.startswith(f"[yt] {key}:"): return line.split(": ", 1)[1]
    # legacy (browser) format
    txt = published_text(day)
    if key == "Episode" and re.search(r"^Episode: https://youtu", txt, re.M): return "legacy"
    legacy = [l for l in txt.splitlines() if not l.startswith("[yt]")]
    if key.startswith("Short") and any("youtube.com/shorts/" in l for l in legacy): return "legacy"
    return None

def record(day, line):
    p = os.path.join(day, "upload", "published.txt")
    with open(p, "a", encoding="utf-8") as f: f.write(line + "\n")

def yt():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    if not os.path.exists(TOK): sys.exit("No token. Run: python auth_youtube.py (see README).")
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
        with open(TOK, "w") as f: f.write(c.to_json())
        os.chmod(TOK, 0o600)
    return build("youtube", "v3", credentials=c, cache_discovery=False)

def upload(y, it, publish_at, synthetic):
    from googleapiclient.http import MediaFileUpload
    status = {"privacyStatus": "private" if publish_at else "public", "selfDeclaredMadeForKids": False,
              "embeddable": True, "license": "youtube", "containsSyntheticMedia": synthetic}
    if publish_at: status["publishAt"] = publish_at
    body = {"snippet": {"title": it["title"], "description": it["desc"], "tags": it["tags"], "categoryId": "25",
                        "defaultLanguage": "en", "defaultAudioLanguage": "en"}, "status": status}
    req = y.videos().insert(part="snippet,status", body=body, notifySubscribers=True,
                            media_body=MediaFileUpload(it["file"], chunksize=8 * 1024 * 1024, resumable=True,
                                                       mimetype="video/mp4"))
    resp = None
    while resp is None:
        st, resp = req.next_chunk(num_retries=5)
        if st: print(f"  {it['key']}: {int(st.progress() * 100)}%", flush=True)
    return resp["id"]

def playlist_id(y, name):
    if re.fullmatch(r"PL[\w-]{10,}", name): return name
    tok = None
    while True:
        r = y.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=tok).execute()
        for p in r["items"]:
            if p["snippet"]["title"].strip().lower() == name.strip().lower(): return p["id"]
        tok = r.get("nextPageToken")
        if not tok: return None

def main():
    a = argparse.ArgumentParser()
    a.add_argument("day"); a.add_argument("--dry-run", action="store_true")
    a.add_argument("--episode-at", help="ISO time to schedule episode (else public now)")
    a.add_argument("--shorts-at", help="comma-separated ISO times, one per Short (else public now)")
    a.add_argument("--playlist", help="playlist name or id (default: status.json published.playlist)")
    a.add_argument("--no-shorts", action="store_true")
    a.add_argument("--shorts-only", action="store_true",
                   help="upload only shorts/NN (no episode, thumbnail, comment); stage unchanged")
    a.add_argument("--synthetic", action=argparse.BooleanOptionalAction, default=False,
                   help="status.containsSyntheticMedia (altered/synthetic content). Default false.")
    o = a.parse_args()
    day = o.day if os.path.isabs(o.day) else os.path.join(ROOT, o.day)
    if not os.path.isdir(day): sys.exit(f"No folder {day}")
    sj = os.path.join(day, "status.json")
    status = json.load(open(sj)) if os.path.exists(sj) else {}
    items, errs = collect(day)
    if o.no_shorts: items = [i for i in items if i["kind"] == "episode"]
    if o.shorts_only:
        items = [i for i in items if i["kind"] == "short"]
        errs = [e for e in errs if not e.startswith("Episode")]
        thumb, comment = None, None
    else:
        thumb = pick_thumb(day)
        if not thumb: errs.append("Episode: no thumbnail png/jpg found")
        elif os.path.getsize(thumb) > 2 * 1024 * 1024: errs.append(f"thumbnail {thumb} > 2 MB (API limit)")
        comment = rd(os.path.join(day, "upload", "pinned_comment.txt"))
        if not comment: errs.append("Episode: missing upload/pinned_comment.txt")
    shorts_at = (o.shorts_at or "").split(",") if o.shorts_at else []
    pl = o.playlist or (status.get("published") or {}).get("playlist")
    print(f"== {os.path.basename(day)}  (stage: {status.get('stage')})")
    for it in items:
        done = already(day, it["key"])
        sz = f"{os.path.getsize(it['file'])/1e6:.1f} MB" if it["file"] else "-"
        print(f"- {it['key']}: {'SKIP (already published: ' + done + ')' if done else 'to upload'}")
        print(f"    file: {it['file'] and os.path.relpath(it['file'], day)} ({sz})")
        print(f"    title[{len(it['title'] or '')}]: {it['title']}")
        print(f"    desc[{len(it['desc'])}] tags[{len(it['tags'])} / {tags_len(it['tags'])} chars]")
        if it.get("note"): print("    note:", it["note"])
    print(f"- thumbnail: {thumb and os.path.relpath(thumb, day)}  comment[{len(comment or '')}]  playlist: {pl}")
    if errs:
        print("PROBLEMS:"); [print("  x", e) for e in errs]
    if o.dry_run:
        print("DRY RUN: nothing uploaded. Result:", "FAIL" if errs else "OK"); sys.exit(1 if errs else 0)
    if errs: sys.exit("Fix problems above first.")
    y = yt(); out = {}
    si = 0
    for it in items:
        if it["kind"] == "short":
            at = shorts_at[si].strip() if si < len(shorts_at) else None; si += 1
        else: at = o.episode_at
        if already(day, it["key"]): continue
        vid = upload(y, it, at, o.synthetic)
        url = f"https://youtu.be/{vid}" if it["kind"] == "episode" else f"https://youtube.com/shorts/{vid}"
        record(day, f"[yt] {it['key']}: {url}" + (f" (scheduled {at})" if at else ""))
        out[it["key"]] = (vid, url); print(f"  {it['key']} -> {url}")
        if it["kind"] == "episode":
            y.thumbnails().set(videoId=vid, media_body=thumb).execute(); print("  thumbnail set")
            y.commentThreads().insert(part="snippet", body={"snippet": {"videoId": vid, "topLevelComment": {
                "snippet": {"textOriginal": comment}}}}).execute()
            record(day, f"[yt] Comment posted on {vid} (NOT pinned: no API, pin in Studio)")
        if pl:
            pid = playlist_id(y, pl)
            if pid:
                y.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": pid,
                    "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
            else: print(f"  playlist '{pl}' not found, skipped")
    ep = already(day, "Episode")
    if not o.shorts_only: status["stage"] = "published"
    status["updated_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    p = status.setdefault("published", {})
    if ep and ep != "legacy": p["episode_url"] = ep.split(" ")[0]
    p["short_urls"] = [already(day, i["key"]).split(" ")[0] for i in items
                       if i["kind"] == "short" and already(day, i["key"]) not in (None, "legacy")]
    if not o.shorts_only: p["pinned_comment"] = "posted via API, not pinned"
    json.dump(status, open(sj, "w"), indent=2, ensure_ascii=False)
    print("\nSTILL NEEDS BROWSER (YouTube Studio, authuser=1): pin the comment; Test & Compare thumbnails "
          "(B/C); Shorts 'related video' link to the episode.")

if __name__ == "__main__": main()
