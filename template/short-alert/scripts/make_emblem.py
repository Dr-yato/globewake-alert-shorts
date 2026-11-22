#!/usr/bin/env python3
"""PD emblem render (PNG, transparent bg) -> clean white line-art PNG with alpha, for the globe overlay.
v3: no body fill and no outer silhouette/shield outline (those read as 'boxes' on video); interior strokes only,
thresholded and antialiased by supersampled downscale.  usage: make_emblem.py in.png out.png [inset_px|alpha]"""
import sys
import numpy as np
from PIL import Image, ImageFilter
im = Image.open(sys.argv[1]).convert("RGBA")
inset = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != "alpha" else 10
ALPHA = len(sys.argv) > 3 and sys.argv[3] == "alpha"   # emblem is already single-colour line-art: use its silhouette
a = np.asarray(im.getchannel("A")).astype(np.float32) / 255
rgb = np.asarray(im.convert("RGB")).astype(np.float32)
lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) * a + 0 * (1 - a)
# colour-difference edges (hue changes matter, e.g. gold on red)
def grad(ch):
    gx = np.zeros_like(ch); gy = np.zeros_like(ch)
    gx[:, 1:-1] = ch[:, 2:] - ch[:, :-2]; gy[1:-1, :] = ch[2:, :] - ch[:-2, :]
    return np.hypot(gx, gy)
g = np.maximum.reduce([grad(rgb[..., i] * a) for i in range(3)] + [grad(lum)])
mask = Image.fromarray(((a > .5) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(2 * inset + 1))
inner = np.asarray(mask) > 0
e = np.clip((g - 40) / 60, 0, 1) * inner
A8 = Image.fromarray((a * 255).astype(np.uint8))
E = Image.fromarray(np.clip(np.asarray(A8).astype(int) - np.asarray(A8.filter(ImageFilter.MinFilter(7))).astype(int), 0, 255).astype(np.uint8)) if ALPHA else Image.fromarray((e * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
out = Image.new("RGBA", im.size, (255, 255, 255, 0)); out.putalpha(E)
bb = E.getbbox(); out = out.crop(bb) if bb else out
out.thumbnail((600, 600), Image.LANCZOS); out.save(sys.argv[2], optimize=True)
print(sys.argv[2], out.size)
