#!/usr/bin/env python3
"""TikTok Content Posting API (Direct Post) - official API only.
Needs publish/secrets/tiktok.json: {"client_key","client_secret","access_token","refresh_token","open_id"}
Usage: python publish_tiktok.py day-NNN [--dry-run] [--privacy SELF_ONLY|PUBLIC_TO_EVERYONE]
Unaudited apps: only SELF_ONLY, and the TikTok account must be private while posting.
Caption source: tiktok/day-NNN_shortNN_caption.txt (max 2200)."""
import argparse, glob, json, math, os, sys, time, requests
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SEC = os.path.join(HERE, "secrets", "tiktok.json"); API = "https://open.tiktokapis.com/v2"

def creds():
    if not os.path.exists(SEC): sys.exit("No secrets/tiktok.json yet - TikTok stays on the browser. See README.")
    c = json.load(open(SEC))
    r = requests.post(f"{API}/oauth/token/", data={"client_key": c["client_key"], "client_secret": c["client_secret"],
        "grant_type": "refresh_token", "refresh_token": c["refresh_token"]}).json()
    if "access_token" in r:
        c.update({k: r[k] for k in ("access_token", "refresh_token", "open_id") if k in r})
        json.dump(c, open(SEC, "w")); os.chmod(SEC, 0o600)
    return c

def post(tok, path, caption, privacy):
    H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"}
    info = requests.post(f"{API}/post/publish/creator_info/query/", headers=H).json()["data"]
    if privacy not in info.get("privacy_level_options", []):
        sys.exit(f"privacy {privacy} not allowed; options {info.get('privacy_level_options')}")
    size = os.path.getsize(path); chunk = min(size, 10_000_000); n = max(1, size // chunk)
    init = requests.post(f"{API}/post/publish/video/init/", headers=H, json={
        "post_info": {"title": caption, "privacy_level": privacy, "disable_duet": False, "disable_comment": False,
                      "disable_stitch": False, "brand_content_toggle": False, "is_aigc": False},
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": n}}).json()
    if init.get("error", {}).get("code") != "ok": sys.exit(f"init failed: {init}")
    pid, url = init["data"]["publish_id"], init["data"]["upload_url"]
    with open(path, "rb") as f:
        for i in range(n):
            start = i * chunk; end = size - 1 if i == n - 1 else start + chunk - 1
            f.seek(start); data = f.read(end - start + 1)
            requests.put(url, data=data, headers={"Content-Type": "video/mp4",
                "Content-Range": f"bytes {start}-{end}/{size}"}).raise_for_status()
    for _ in range(60):
        s = requests.post(f"{API}/post/publish/status/fetch/", headers=H, json={"publish_id": pid}).json()["data"]
        if s.get("status") in ("PUBLISH_COMPLETE", "FAILED"): return pid, s
        time.sleep(5)
    return pid, {"status": "TIMEOUT"}

def main():
    a = argparse.ArgumentParser(); a.add_argument("day"); a.add_argument("--dry-run", action="store_true")
    a.add_argument("--privacy", default="SELF_ONLY"); o = a.parse_args()
    day = os.path.join(ROOT, o.day); pub = os.path.join(day, "upload", "published.txt")
    done = open(pub).read() if os.path.exists(pub) else ""; errs = []; jobs = []
    for s in sorted(glob.glob(os.path.join(day, "shorts", "[0-9]*"))):
        n = os.path.basename(s); mp4 = sorted(glob.glob(os.path.join(s, "exports", "*.mp4")))
        capf = os.path.join(ROOT, "tiktok", f"{o.day}_short{n}_caption.txt")
        cap = open(capf).read().strip() if os.path.exists(capf) else None
        if not mp4: errs.append(f"short {n}: no mp4")
        if not cap: errs.append(f"short {n}: no caption {os.path.relpath(capf, ROOT)}")
        elif len(cap) > 2200: errs.append(f"short {n}: caption > 2200")
        skip = f"[tt] Short {n}:" in done or (f"Short {n} https://www.tiktok.com" in done)
        print(f"- TikTok Short {n}: {'SKIP (done)' if skip else 'to post'} caption[{len(cap or '')}]")
        if not skip and mp4 and cap: jobs.append((n, mp4[-1], cap))
    for e in errs: print("  x", e)
    if o.dry_run: print("DRY RUN TikTok:", "FAIL" if errs else "OK"); return
    c = creds()
    for n, path, cap in jobs:
        pid, s = post(c["access_token"], path, cap, o.privacy)
        ids = s.get("publicaly_available_post_id") or s.get("publicly_available_post_id") or []
        handle = os.environ.get("TIKTOK_HANDLE", "globewake").lstrip("@")
        link = f"https://www.tiktok.com/@{handle}/video/{ids[0]}" if ids else f"publish_id {pid} ({s.get('status')})"
        open(pub, "a").write(f"[tt] Short {n}: {link}\n"); print(f"  Short {n} -> {link}")

if __name__ == "__main__": main()
