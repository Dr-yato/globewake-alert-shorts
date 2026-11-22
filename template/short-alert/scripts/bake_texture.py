#!/usr/bin/env python3
"""Bake the greyscale relief globe textures from Natural Earth GRAY_HR_SR_OB_DR (public domain, 21600x10800).
Source tif: news-channel/tools/raster/gray10m/GRAY_HR_SR_OB_DR.tif (download: naciscdn.org/naturalearth/10m/raster/GRAY_HR_SR_OB_DR.zip).
usage: bake_texture.py <project>                       -> assets/globe/base.jpg (8192x4096)
       bake_texture.py <project> name W S E N         -> assets/globe/<name>.jpg full-res regional tile + tiles.json entry
Tone: ocean -> near black, land -> light grey relief (the dark 'intel globe' look)."""
import json, os, sys
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
SRC = os.environ.get("GW_RELIEF_TIF", "/workspace/news-channel/tools/raster/gray10m/GRAY_HR_SR_OB_DR.tif")
proj = sys.argv[1]; out = os.path.join(proj, "assets/globe"); os.makedirs(out, exist_ok=True)
im = Image.open(os.path.normpath(SRC))
x = np.arange(256, dtype=np.float32)
lut = np.clip(14 + (x - 80) * 1.30, 6, 255)
lut = (255 * (lut / 255) ** 1.08).astype(np.uint8)
def tone(img): return Image.fromarray(lut[np.asarray(img)])
tp = os.path.join(out, "tiles.json"); tiles = json.load(open(tp)) if os.path.exists(tp) else []
if len(sys.argv) == 2:
    tone(im.resize((8192, 4096), Image.LANCZOS)).save(os.path.join(out, "base.jpg"), quality=88)
    print("base.jpg written")
else:
    name, w, s, e, n = sys.argv[2], *map(float, sys.argv[3:7])
    W, H = im.size
    box = (int((w + 180) / 360 * W), int((90 - n) / 180 * H), int((e + 180) / 360 * W), int((90 - s) / 180 * H))
    tone(im.crop(box)).save(os.path.join(out, name + ".jpg"), quality=90)
    tiles = [t for t in tiles if t["name"] != name] + [{"name": name, "src": f"assets/globe/{name}.jpg", "bbox": [w, s, e, n]}]
    json.dump(tiles, open(tp, "w"), indent=1); print(name, box)
