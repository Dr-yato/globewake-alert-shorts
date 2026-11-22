#!/usr/bin/env python3
"""Search or download Wikimedia Commons photos with license + author recorded in assets/photos/credits.json.
  search:   python3 scripts/fetch_commons.py search "air traffic control center"
  download: python3 scripts/fetch_commons.py get <key> "File:Exact title.jpg"
Use only Public domain / CC0 / CC BY / CC BY-SA results; skip wire/agency photos (Reuters, AP, Getty, AFP)."""
import json, os, re, sys, urllib.parse, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "GlobewakeBot/1.0"}
API = "https://commons.wikimedia.org/w/api.php?"
def q(params): return json.load(urllib.request.urlopen(urllib.request.Request(API + urllib.parse.urlencode(params), headers=UA)))
def meta(ii):
    m = ii.get("extmetadata", {}); g = lambda f: re.sub("<[^>]+>", "", m.get(f, {}).get("value", "")).strip()
    return dict(artist=g("Artist")[:120], license=g("LicenseShortName"), license_url=g("LicenseUrl"), desc=g("ImageDescription")[:200])
if sys.argv[1] == "search":
    d = q(dict(action="query", format="json", generator="search", gsrnamespace=6, gsrlimit=15, gsrsearch=sys.argv[2], prop="imageinfo", iiprop="url|size|extmetadata"))
    for p in d.get("query", {}).get("pages", {}).values():
        ii = p["imageinfo"][0]; mm = meta(ii)
        if ii["width"] >= 1600: print(p["title"], "|", ii["width"], "x", ii["height"], "|", mm["license"], "|", mm["artist"][:50])
else:
    key, title = sys.argv[2], sys.argv[3]
    d = q(dict(action="query", format="json", titles=title, prop="imageinfo", iiprop="url|extmetadata", iiurlwidth=3000))
    ii = list(d["query"]["pages"].values())[0]["imageinfo"][0]
    os.makedirs(os.path.join(ROOT, "assets/photos"), exist_ok=True)
    open(os.path.join(ROOT, "assets/photos", key + ".jpg"), "wb").write(urllib.request.urlopen(urllib.request.Request(ii.get("thumburl") or ii["url"], headers=UA)).read())
    cp = os.path.join(ROOT, "assets/photos/credits.json"); c = json.load(open(cp)) if os.path.exists(cp) else {}
    c[key] = dict(title=title, page=ii["descriptionurl"], **meta(ii)); json.dump(c, open(cp, "w"), indent=1)
    print("saved", key, c[key]["license"], c[key]["artist"])
