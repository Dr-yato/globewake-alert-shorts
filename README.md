# Globewake ALERT Shorts

Reusable skill and template for Globewake’s 15-second ALERT-style YouTube Shorts / TikToks: a dark NASA Blue Marble map, a real official seal, a BREAKING tag, a typed headline with yellow highlights, a WHAT HAPPENED paragraph lower on the screen, and the Globewake logo top-right. No CTA. Built to loop.

The full recipe is in [SKILL.md](SKILL.md). This README is the quickstart.

## What is in this repo

- `SKILL.md` — story pick, config, build, emblem rule, map, layout, audio, render/QC, publishing, and pitfalls.
- `template/short-alert/` — HyperFrames project, scripts, brand marks, SFX, and 1:10m Natural Earth borders.
- `examples/sparta-ii/alert.json` and `examples/day-007/*.alert.json` — two worked configs (Sparta II; Riemann / Göttingen, Clay, US Great Seal).
- `examples/contact-sheet.jpg` — example frames of the approved layout.
- `scripts/fetch_music.py` — downloads or trims the official “Hvitserk’s Choice” cue. The wav is not in git.
- `scripts/fetch_bluemarble.py` — NASA Blue Marble rasters. Also not in git.
- `publish/` — YouTube uploader (`publish_youtube.py --shorts-only`). Tokens stay in `publish/secrets/` and are never committed.

## Quickstart

You need: Python 3 with Pillow and numpy, `ffmpeg` / `ffprobe`, Node.js, `npx`, and (for a live music fetch) `yt-dlp`.

```bash
git clone https://github.com/Dr-yato/globewake-alert-shorts.git
cd globewake-alert-shorts
cp -a template/short-alert /tmp/my-alert
cd /tmp/my-alert
cp /path/to/globewake-alert-shorts/examples/sparta-ii/alert.json alert.json

# Music: official SonySoundtracksVEVO upload, cue 2:20.6–2:35.6 (140.6–155.6 s)
python3 /path/to/globewake-alert-shorts/scripts/fetch_music.py assets/audio/bed_hvitserk.wav
# or, if you already have the official track:
#   GW_HVITSERK_WAV=/path/to/hvitserks_choice.wav \
#   python3 .../scripts/fetch_music.py assets/audio/bed_hvitserk.wav

# Map texture
export GW_BM_DIR=/path/to/bluemarble        # dir with bm24000.jpg and bm_clouds8192.jpg
# python3 /path/to/globewake-alert-shorts/scripts/fetch_bluemarble.py
python3 scripts/bake_bluemarble.py . 0

# Official seal (Commons artwork — never a text badge)
python3 scripts/make_seal.py /path/to/official-artwork.png assets/emblems/seal.png --bg auto

python3 scripts/build_alert.py
python3 scripts/mix_alert.py

npx hyperframes@0.9.46 snapshot --at 4,8,14 -o /tmp/alert-qc
npx hyperframes@0.9.46 render --quality looks
bash scripts/finish_alert.sh . exports/my_alert_short.mp4
```

Publishing (YouTube first, then TikTok Studio with the YouTube link in the caption) is documented in `SKILL.md` and `publish/README.md`.

## Rules that are easy to miss

- **Shorts only** always use “Hvitserk’s Choice.” Default ALERT mix is that bed **plus the typing SFX only** — no ALERT hit, no whoosh, no impact. Episodes keep varied beds.
- The centre graphic is a **real official seal or logo** from Commons, wrapped by `make_seal.py`. Never invent a typographic badge.
- Do not commit the score, OAuth tokens, or Blue Marble rasters.
- Pin HyperFrames at `0.9.46`. Render one Short at a time. Target about −14 LUFS, true peak ≤ −1.5 dB on the finished mp4.
- YouTube cannot replace a video file in place; upload a new one and delete or private the old.

## License and third-party material

Globewake brand marks in `template/short-alert/assets/brand/` are for Globewake productions. Natural Earth borders and NASA Blue Marble are public domain (Blue Marble is fetched, not shipped). Official seals in examples are used as official emblems and credited in each `alert.json`. “Hvitserk’s Choice” is © Sony / the rights holders and is **not** distributed in this repository.
