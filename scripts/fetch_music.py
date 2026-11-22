#!/usr/bin/env python3
"""Fetch the official 'Hvitserk's Choice' cue and write a 48 kHz stereo WAV.

Source (official SonySoundtracksVEVO upload, the only approved source):
  https://www.youtube.com/watch?v=Dpx9JStb1ko

Cue used on every Globewake ALERT Short: 2:20.6–2:35.6
(140.6–155.6 s of that upload). A 16 s file is written so mix_alert.py
can fade the last 0.35 s without running short of a 15 s Short.

The track itself is NEVER committed to git. Prefer a local copy
(GW_HVITSERK_WAV or a previously fetched wav) over a live YouTube download.

Usage:
  python3 scripts/fetch_music.py [out.wav]
Default out: template/short-alert/assets/audio/bed_hvitserk.wav
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO / "template" / "short-alert" / "assets" / "audio" / "bed_hvitserk.wav"
OFFICIAL_URL = "https://www.youtube.com/watch?v=Dpx9JStb1ko"
CUE_START = 140.6
CUE_DUR = 16.0

KNOWN_FULL = [
    os.environ.get("GW_HVITSERK_WAV", ""),
    "/workspace/news-channel/brand/music/hvitserks_choice.wav",
    "/workspace/news-channel/alert-sample-01/music/hvitserks_choice.wav",
    str(REPO / "tools" / "music" / "hvitserks_choice.wav"),
]


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.check_call(cmd, **kw)


def find_ytdlp() -> str | None:
    for c in (shutil.which("yt-dlp"), str(Path.home() / ".local/bin/yt-dlp"), "/usr/local/bin/yt-dlp"):
        if c and Path(c).is_file():
            return c
    return None


def find_source() -> str | None:
    for p in KNOWN_FULL:
        if p and Path(p).is_file() and Path(p).stat().st_size > 100_000:
            return p
    return None


def download_official(tmpdir: Path) -> Path:
    ytdlp = find_ytdlp()
    if not ytdlp:
        raise SystemExit(
            "yt-dlp not found and no local GW_HVITSERK_WAV. "
            "Install yt-dlp or set GW_HVITSERK_WAV to the official track."
        )
    out = tmpdir / "hvitserks_choice.%(ext)s"
    run([
        ytdlp, "-f", "bestaudio/best",
        "--no-playlist",
        "-o", str(out),
        OFFICIAL_URL,
    ])
    hits = list(tmpdir.glob("hvitserks_choice.*"))
    if not hits:
        raise SystemExit("yt-dlp finished but wrote no file")
    return hits[0]


def write_cue(src: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-v", "error",
        "-ss", str(CUE_START), "-t", str(CUE_DUR),
        "-i", str(src),
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
        str(dest),
    ])
    print(f"wrote {dest}  ({CUE_START}s + {CUE_DUR}s @ 48 kHz stereo)", flush=True)


def main():
    dest = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_OUT
    src = find_source()
    if src:
        print(f"using local source: {src}", flush=True)
        write_cue(Path(src), dest)
        return
    with tempfile.TemporaryDirectory(prefix="hvit-") as td:
        raw = download_official(Path(td))
        write_cue(raw, dest)


if __name__ == "__main__":
    main()
