---
name: Globewake ALERT Short production
description: Use when making or publishing a Globewake ALERT-style news Short (15 s breaking-news card, official emblem on a Blue Marble map, YouTube + TikTok).
---

# Globewake ALERT Shorts

A 15-second, no-VO, 9:16 breaking-news card: dark NASA Blue Marble map, a real official seal in the centre, a BREAKING tag, a headline typed with yellow highlights, a WHAT HAPPENED paragraph lower on the screen, and the Globewake logo top-right. There is no CTA. The piece should loop cleanly.

This skill packages the format used for the Sparta II sample and the day-007 Riemann Shorts (22 Nov 2026). Use it whenever the brief is an ALERT-style Short, not a talking-head or a long episode.

**Music rule (standing, 22 Nov 2026): Shorts only always use Trevor Morris, “Hvitserk’s Choice.” Episodes keep varied, subject-matched beds. This rule overrides any “vary the music” guidance for Shorts only.**

## Story pick

- Pick one story that can go viral with ordinary people: a concrete event, a named prize or leak, a clearly visual place, one surprising number.
- The claim must be sourced. Keep a short source list in `alert.json` `credits` (wire, paper, official statement, Commons file for the emblem).
- One story per Short. Do not pack a whole episode into 15 seconds.
- Write the headline so the payoff is in the first line. The WHAT HAPPENED paragraph is the context, not a second hook.
- If you cannot find a real official seal or logo for the institution at the centre of the story, do not invent a badge — pick a different emblem (the country, the university, the agency) that is official and story-accurate.

## Config (`alert.json`)

The project is driven by one JSON file at the root of a HyperFrames project (copy `template/short-alert/` and edit `alert.json`). Then run `scripts/build_alert.py`, which writes `compositions/` and `index.html`.

Important fields:

| Field | Role |
| --- | --- |
| `slug`, `title_yt`, `desc_yt`, `tags` | Publishing metadata. Title should work as a YouTube Short title. |
| `duration` | Always `15`. |
| `layout` | Optional overrides. Defaults already match the approved card: logo top-right (`logo_top` 250, `logo_right` 84, `logo_w` 300), text block left 108 / `text_top` 1030, BREAKING 262×46, headline ~58 px, WHAT HAPPENED paragraph lower on screen. Do not add a CTA field. |
| `headline` | String. Wrap the words that should flash yellow in `*asterisks*`, e.g. `MATHEMATICIANS *CRACK* THE *RIEMANN* HYPOTHESIS`. |
| `happened` | One short paragraph, two or three sentences max. |
| `map.geo` | `"world-10m"` — 1:10m Natural Earth borders (needed for small land such as Kaliningrad). Do not drop to 50m for a finished Short. |
| `map.px` | `1.0` for the finished render (slow). `0.5` is only for a layout draft. |
| `map.cam0`, `map.cam1`, `map.drift` | Start wide on the land, then a slow push-in. Keep the motion gentle; this is a card, not a fly-through. |
| `map.highlights` | ISO country codes to tint, plus optional `emblem_at` / `emblem_px` for the centre seal position and size. |
| `map.arcs`, `map.labels`, `map.dots` | Optional routes, place labels, and pulses. Labels must stay inside the safe text box (roughly x 70–930). |
| `audio.bed` | `bed_hvitserk.wav` (fetched, never committed). |
| `audio.bed_start` | `0` when the file is the pre-trimmed 16 s cue from `scripts/fetch_music.py`. Use `140.6` only if the file is the full official track. |
| `audio.bed_gain`, `audio.bed_fade_in` | Defaults `0.42` and `0.3`. |
| `audio.cues` | Quieter SFX than the first drafts: alert hit `0.55`, whoosh `0.35`, impact `0.30`, typing `0.35`. |
| `credits` | Sources, map attribution, emblem Commons file, and the music credit below. |

The template `alert.json` is the Sparta II story (Finland / NATO / wreck of *Sparta II*). Worked day-007 configs are in `examples/day-007/`.

## Build

From a project directory that is a copy of `template/short-alert/`:

```bash
# 1. Music cue (16 s wav, not in git)
python3 /path/to/repo/scripts/fetch_music.py assets/audio/bed_hvitserk.wav
# or: export GW_HVITSERK_WAV=/path/to/full-official-track.wav

# 2. Official emblem (see next section)
python3 scripts/make_seal.py /path/to/official-artwork.png assets/emblems/seal.png --bg auto

# 3. Blue Marble texture (greyscale intel tone)
export GW_BM_DIR=/path/to/bluemarble   # dir with bm24000.jpg and bm_clouds8192.jpg
python3 scripts/bake_bluemarble.py . 0

# 4. HTML + mix
python3 scripts/build_alert.py
python3 scripts/mix_alert.py
```

`build_alert.py` is the only HTML writer. Do not hand-edit `compositions/` for a one-off layout change — change `alert.json` and rebuild. Pin HyperFrames at `npx hyperframes@0.9.46` (do not use a global 0.8.x).

## Emblem rule

The centre graphic is a **real official seal or logo**, never a typographic badge.

- Source the official artwork from Wikimedia Commons (or another public-domain / official publication). Record the Commons file name in `credits`.
- Run `scripts/make_seal.py`. It places the official art on a circular plate, draws a white dotted ring, and adds a soft drop shadow.
- `--bg white|none|auto` and `--layout stack|fit|auto`. Use `--bg white` for black line-art (it will vanish on a dark map otherwise — this bit the University of Göttingen Siegel). Use `--layout stack` only when the official mark is already a stacked lockup; do not let it split a full-width wordmark (the Clay Mathematics Institute logo had to be restacked by hand, then `--layout fit --bg white`).
- Deprecated: `GW_SEAL_BRIGHT` and any curved-text arguments. Those produced invented badges such as “17M LEAN PROOF / 175,187 FILES.” Never do that.
- Small monochrome country emblems under `assets/emblems/` (us, cn, ru, …) are map-pin art, not a substitute for the centre seal.

Worked examples from day-007:

- Short 01 — official University of Göttingen seal (`File:Uni Göttingen Siegel.svg`, PD), `--bg white`.
- Short 02 — official Clay Mathematics Institute logo (`File:Clay Mathematics Institute CMI Logo.svg`, PD), restacked knot + CMI + wordmark, `--layout fit --bg white`.
- Short 03 — Great Seal of the United States, obverse (U.S. Government, PD).

## Map

- Texture: NASA Blue Marble, baked to a greyscale intel tone by `bake_bluemarble.py`. The rasters are public domain and **not committed** (tens of megabytes). Fetch with `scripts/fetch_bluemarble.py` or set `GW_BM_DIR`.
- Borders: 1:10m Natural Earth (`world-10m.js` in the template). The 50m file is only a fallback.
- Tint the story’s country (or countries), keep labels short, and use a slow push-in: land starts wide in `cam0`, `cam1` eases closer, `drift` is slight.
- `map.px 1.0` for delivery. It is slower to render; do not ship a 0.5 preview.

## Layout

Approved defaults, already compiled into `build_alert.py`:

- Dark ground (`#0E0E0E` / `#0B0C0E`), text `#F2F3F0`, accent `#FF3B30`. Poppins + IBM Plex Mono (this is the map/ALERT exception to the light episode brand lock).
- **BREAKING** tag at the top of the text block.
- Headline types on with yellow highlights from `*asterisks*`.
- **WHAT HAPPENED** paragraph sits lower on the screen (`text_top` 1030, paragraph in at 2.40 s).
- Globewake logo top-right. Do not move it to a lower-third or end card.
- No CTA, no “follow,” no subscribe bug, no end slate. Hold the last frame so the Short can loop.

Safe text: keep copy and labels roughly between x 70 and 930. Do not cover the emblem or the logo.

An example contact sheet is at `examples/contact-sheet.jpg`.

## Audio

Standing bed for **every** ALERT Short (and every Globewake Short — not episodes):

- Track: Trevor Morris, “Hvitserk’s Choice” (Vikings: The Final Season / Sony Classical).
- Official source only: the SonySoundtracksVEVO upload https://www.youtube.com/watch?v=Dpx9JStb1ko
- Section: **2:20.6–2:35.6** (140.6–155.6 s of that upload). A cross-check against a finished mix put the cue start at 140.598 s; use **140.6**.
- The track itself is **not committed**. `scripts/fetch_music.py` writes a 16 s, 48 kHz stereo cue to `assets/audio/bed_hvitserk.wav` (extra second so the 0.35 s fade-out does not undershoot 15 s). Set `GW_HVITSERK_WAV` to skip a live YouTube download when a local copy of the official track already exists.
- SFX are original and live in the template (`sfx_alert_hit`, `sfx_whoosh2`, `sfx_impact`, `sfx_typing`). Use the quieter gains above so the score can sit near the loudness target without the opening hit clipping.
- Mix: `scripts/mix_alert.py` → `assets/audio/mix.wav`. Target about **−14 LUFS**, true peak **≤ −1.5 dB** on the finished mp4. The loudnorm filter is `I=-14:TP=-3` so AAC overshoot still lands under −1.5 dB (TP −2 on the wav was lifting the AAC file to about −1.1 dBTP).
- Duck the bed under VO if a Short ever has VO (standard ALERT cards do not).
- YouTube Content ID claims on this cue are expected and accepted.
- On TikTok, do **not** also attach the official sound if the track is already in the file — it doubles.

## Render and QC

Renders are one-at-a-time. HyperFrames takes a lock at `/home/box/.cache/hyperframes/locks/render.lock`. A 15 s ALERT at `map.px 1.0` typically takes 8–14 minutes. Do not start a second render while one is running.

```bash
npx hyperframes@0.9.46 snapshot --at 4,8,14 -o /tmp/alert-qc
# inspect the contact sheet and the 8 s frame (emblem, headline, WHAT HAPPENED, logo)

npx hyperframes@0.9.46 render --quality looks   # CRF 16, 1080×1920, 30 fps

bash scripts/finish_alert.sh . exports/<slug>_alert_short.mp4
```

`finish_alert.sh` two-pass encodes the picture and **remuxes `assets/audio/mix.wav`** (do not ship the raw render’s audio). It uses `renders/raw.mp4` if present, otherwise the newest `renders/*.mp4` that HyperFrames just wrote. It then prints:

- 1080×1920, SAR 1:1, 9:16, 30 fps, duration 15.000 s
- decode OK
- EBU R128 summary (about −14 LUFS, true peak ≤ −1.5 dBFS)
- cropdetect (no letterbox) and black-frame detect
- md5

Snapshot at 4, 8, and 14 s is the fast layout/emblem QC (~18 s). Always look at the 8 s frame before a full render.

## Publishing

YouTube first, then TikTok with the YouTube link in the caption.

```bash
# tokens live in publish/secrets/ (chmod 600, never commit)
python3 publish/publish_youtube.py --dry-run --shorts-only --synthetic --shorts-at ISO,ISO
python3 publish/publish_youtube.py --shorts-only --synthetic --shorts-at ISO,ISO
```

`publish_youtube.py` is idempotent via `upload/published.txt` lines like `[yt] Short 01: https://youtube.com/shorts/…`. A few traps learned the hard way:

- `collect()` takes the last alphabetically-sorted `exports/*.mp4`. Move backups (for example `*_dronebed.mp4`) out of `exports/` or they win.
- Any non-`[yt]` line in `published.txt` that merely contains `youtube.com/shorts/` is treated as “already published.” Do not leave old Short URLs in comments.
- YouTube cannot replace video bytes. To fix a published Short, upload a new file and delete or private the old one. `videos.insert` costs ~1600 quota units; the default daily cap is 10k (~4–5 uploads). Deletes can look eventually-consistent for a minute.
- There is no API for a pinned comment, Test & Compare thumbnails, or the Related video link — those are Studio-only.
- OAuth is set up with `publish/auth_youtube_local.py` on port 8765. Testing-mode refresh tokens expire in about seven days. Channel: UCI4iVou66W4j4C-HvkB4mcQ.

After the Short is on YouTube, write a TikTok caption that includes the Short URL (and the episode URL when there is one), then post the same mp4 through **TikTok Studio**. Do not attach the official sound on top. Do not post to TikTok from this repo’s scripts unless the user explicitly asked to post that Short.

## Pitfalls learned 22 Nov 2026

- Official emblems only. A made-up circular typographic badge looks cheap and was rejected.
- Black line-art seals need `--bg white` or they disappear on the dark map (Göttingen).
- Do not let `--layout stack` slice a horizontal wordmark (Clay / CMI). Restack the official pixels, then `--layout fit`.
- Never commit “Hvitserk’s Choice” or NASA Blue Marble rasters. Fetch scripts only.
- The cue starts at **140.6 s**, not 143 s (an earlier cross-correlation was wrong because the mix window started at 2.5 s).
- The music rule is **Shorts only**. Do not re-bed a finished episode with Hvitserk’s Choice.
- Accept YouTube claims. Do not double-attach the sound on TikTok.
- Quieter SFX (hit 0.55 / whoosh 0.35 / typing 0.35 / impact 0.30). Louder defaults with the same loudnorm still came out around −14.9 LUFS with a hot opening.
- Judge true peak on the AAC file (≤ −1.5 dB). The mixer aims at −3 dBTP so AAC overshoot still clears the cap.
- Remux `mix.wav` in `finish_alert.sh`. Shipping `raw.mp4` audio is a bug.
- HyperFrames: one render at a time, pin `0.9.46`, `map.px 1.0` is slow, snapshot first.
- Publish: backups in `exports/`, stray Short URLs in `published.txt`, no in-place YouTube replace, quota, Testing-mode OAuth expiry.
- 1:10m borders matter for small land (Kaliningrad was missing or ugly at 50m).
- Layout lock: no CTA, logo top-right, WHAT HAPPENED lower, text x 70–930, camera land-wide then a slow push-in.

## Quick command path

```bash
git clone git@github.com:Dr-yato/globewake-alert-shorts.git
cd globewake-alert-shorts
cp -a template/short-alert /tmp/my-alert && cd /tmp/my-alert
cp /path/to/this-repo/examples/sparta-ii/alert.json alert.json   # or write your own
python3 /path/to/this-repo/scripts/fetch_music.py assets/audio/bed_hvitserk.wav
export GW_BM_DIR=/path/to/bluemarble
python3 scripts/bake_bluemarble.py . 0
python3 scripts/make_seal.py /path/to/official.png assets/emblems/seal.png --bg auto
python3 scripts/build_alert.py
python3 scripts/mix_alert.py
npx hyperframes@0.9.46 snapshot --at 4,8,14 -o /tmp/alert-qc
npx hyperframes@0.9.46 render --quality looks
bash scripts/finish_alert.sh . exports/my_alert_short.mp4
```
