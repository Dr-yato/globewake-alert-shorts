#!/usr/bin/env python3
"""Bake greyscale 'intel' satellite textures from NASA Blue Marble (public domain, Wikimedia Commons copies):
  bm24000.jpg  = File:Whole world - land and oceans 12000.jpg (24000x12000, no clouds)
  bm_clouds8192.jpg = File:Land ocean ice cloud hires.jpg (8192x4096, with clouds)
usage: bake_bluemarble.py <project> [cloud_mix=0.45]          -> assets/globe/base.jpg (8192x4096, faint clouds for wide shots)
       bake_bluemarble.py <project> tile name W S E N         -> full-res cloud-free regional tile + tiles.json entry
Tone: water (blue-dominant) pushed to near black, land to mid grey with contrast (reference 'Inside Geopolitics' look)."""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
Image.MAX_IMAGE_PIXELS = None
def _bm_dir():
    env = os.environ.get("GW_BM_DIR")
    if env and os.path.isdir(env):
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.normpath(os.path.join(here, "..", "..", "..", "tools", "raster", "bluemarble")),
        "/workspace/news-channel/tools/raster/bluemarble",
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[0]
SRC = _bm_dir()
proj = sys.argv[1]; out = os.path.join(proj, "assets/globe"); os.makedirs(out, exist_ok=True)
def tone(rgb, clouds=None, mix=0.0):
    a = np.asarray(rgb).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = .30 * r + .59 * g + .11 * b
    water = np.clip((b - np.maximum(r, g) - 8) / 30, 0, 1)            # blue-dominant pixels = sea / lakes
    land = 28 + 150 * np.clip(lum / 255, 0, 1) ** 0.62          # compressive: forests mid-grey, deserts not blown out
    v = land * (1 - water) + (8 + lum * .18) * water
    if clouds is not None:
        c = np.asarray(clouds).astype(np.float32); cl = np.clip((c.min(axis=2) - 95) / 120, 0, 1)   # white & grey = cloud
        v = v * (1 - cl * mix) + 165 * cl * mix
    return Image.fromarray(np.clip(v, 0, 255).astype(np.uint8))
tp = os.path.join(out, "tiles.json"); tiles = json.load(open(tp)) if os.path.exists(tp) else []
if len(sys.argv) < 3 or sys.argv[2] != "tile":
    mix = float(sys.argv[2]) if len(sys.argv) > 2 else .45
    bm = Image.open(os.path.join(SRC, "bm24000.jpg")).resize((8192, 4096), Image.LANCZOS)
    cl = Image.open(os.path.join(SRC, "bm_clouds8192.jpg")).convert("RGB").resize((8192, 4096))
    tone(bm, cl, mix).save(os.path.join(out, "base.jpg"), quality=90); print("base.jpg")
else:
    name, w, s, e, n = sys.argv[3], *map(float, sys.argv[4:8])
    im = Image.open(os.path.join(SRC, "bm24000.jpg")); W, H = im.size
    box = (int((w + 180) / 360 * W), int((90 - n) / 180 * H), int((e + 180) / 360 * W), int((90 - s) / 180 * H))
    t = tone(im.crop(box)).filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))
    t.save(os.path.join(out, name + ".jpg"), quality=92)
    tiles = [x for x in tiles if x["name"] != name] + [{"name": name, "src": f"assets/globe/{name}.jpg", "bbox": [w, s, e, n]}]
    json.dump(tiles, open(tp, "w"), indent=1); print(name, t.size)
