#!/usr/bin/env python3
"""Download NASA Blue Marble rasters (public domain) into tools/raster/bluemarble/.

These files are large (tens of MB) and are NEVER committed. bake_bluemarble.py
looks here, or in $GW_BM_DIR, or at the box copy under news-channel.

Sources (Wikimedia Commons):
  Whole world - land and oceans 12000.jpg  -> bm24000.jpg (or keep the 12000 px file as bm24000.jpg)
  Land ocean ice cloud 8192.jpg            -> bm_clouds8192.jpg

Usage:
  python3 scripts/fetch_bluemarble.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEST = Path(os_env := __import__("os").environ.get("GW_BM_DIR") or (REPO / "tools" / "raster" / "bluemarble"))

# Commons Special:FilePath follows redirects to the current file.
FILES = {
    "bm24000.jpg": "https://commons.wikimedia.org/wiki/Special:FilePath/Whole%20world%20-%20land%20and%20oceans.jpg",
    "bm_clouds8192.jpg": "https://commons.wikimedia.org/wiki/Special:FilePath/Land%20ocean%20ice%20cloud%208192.jpg",
}


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        out = DEST / name
        if out.is_file() and out.stat().st_size > 1_000_000:
            print(f"already present: {out} ({out.stat().st_size} bytes)")
            continue
        print(f"fetch {name} from Commons…")
        # --location follows the FilePath redirect; timeout is generous
        cmd = [
            "curl", "-L", "--fail", "--retry", "3",
            "-A", "GlobewakeAlertShorts/1.0 (educational; NASA Blue Marble PD)",
            "-o", str(out),
            url,
        ]
        print("+", " ".join(cmd))
        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as e:
            if out.exists():
                out.unlink()
            print(f"failed to fetch {name}: {e}", file=sys.stderr)
            print("Set GW_BM_DIR to a directory that already has bm24000.jpg and bm_clouds8192.jpg.", file=sys.stderr)
            sys.exit(1)
        print(f"wrote {out} ({out.stat().st_size} bytes)")
    print("done. bake with: python3 template/short-alert/scripts/bake_bluemarble.py template/short-alert 0")


if __name__ == "__main__":
    main()
