# ALERT Short template

This is the HyperFrames project for a Globewake ALERT Short. The full production recipe — story pick, official-emblem rule, Hvitserk’s Choice cue (2:20.6–2:35.6 of the official SonySoundtracksVEVO upload), quieter SFX, render/QC, and publishing — lives in the repo root [`SKILL.md`](../../SKILL.md). Quickstart is in the root [`README.md`](../../README.md).

Standing rules: real official seal (never a text badge); music on Shorts only; do not commit `bed_hvitserk.wav` or Blue Marble rasters; remux `assets/audio/mix.wav` in `finish_alert.sh`.

---

# short-alert: 15 s "ALERT" breaking-news card (no voiceover)
Reference style: Inside Geopolitics ALERT reels. Everything is driven by `alert.json` (headline with *highlight*, paragraph, source line, map camera, highlights/emblem, arcs, dots, labels, audio cues).
1. Copy this folder to `<story>/project`.
2. Textures: `python3 scripts/bake_bluemarble.py . 0` (base) and `python3 scripts/bake_bluemarble.py . tile <name> W S E N` (full-res regional tile). Needs NASA Blue Marble (Wikimedia Commons "Whole world - land and oceans 12000.jpg") in tools/raster/bluemarble. Older greyscale relief: scripts/bake_texture.py.
3. **Centre graphic = a real official emblem** (government seal, agency/institution logo, flag seal, or company logo) tied to the story. Use the official artwork from Wikimedia Commons or the organisation's site. Style: circular, white dotted ring, soft shadow, centred over the highlighted country. `python3 scripts/make_seal.py official.png assets/emblems/seal_xx.png` (add `--bg white` for dark line-art or a wordmark; `--bg none` for an already-complete colour seal). Record source + licence in credits.json. **Never invent a typographic / text badge.** The old `GW_SEAL_BRIGHT` + curved-text arguments are deprecated.
4. `python3 scripts/build_alert.py && python3 scripts/mix_alert.py` (-14 LUFS; `bed_loop` keeps the drone up to the end).
5. `npx hyperframes@0.9.46 render . -o renders/raw.mp4 -f 30 -q delivery` then `bash scripts/finish_alert.sh . ../exports/out.mp4` (two-pass, QC).
Borders: `"geo": "world-10m.js"` (Natural Earth 1:10m) for sharp coastlines at regional zoom; `map.px: 1.0` for full-density raster (slower render, ~16 min).
