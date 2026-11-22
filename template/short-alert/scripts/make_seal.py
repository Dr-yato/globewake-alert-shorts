#!/usr/bin/env python3
"""ALERT Short centre graphic: a REAL official emblem, styled like the
Inside Geopolitics reference — the actual artwork (government seal, agency
or institution logo, flag seal, or company logo) in its original colours,
with a white dotted ring and a soft drop shadow, centred over the
highlighted country.

The centre graphic MUST be a real, recognisable emblem tied to the story.
Use the official SVG/PNG from Wikimedia Commons or the organisation's official
site, and record the source + licence in credits.json.

NEVER invent a typographic / text badge (no made-up figures, slogans, or
curved labels such as "17M LINES" or "$1M / CLAY RULES").

usage:
  python3 make_seal.py artwork.png out.png
  python3 make_seal.py artwork.png out.png --bg white    # line-art or a wordmark
  python3 make_seal.py artwork.png out.png --bg none     # already-complete colour seal
  python3 make_seal.py artwork.png out.png --layout stack  # wide logo: symbol above wordmark

Output: 600×600 RGBA PNG.

Deprecated (do not use for the centre graphic): positional TOP/BOTTOM text
arguments, and GW_SEAL_BRIGHT (those turned official art into a made-up
monochrome badge). They are ignored.
"""
from __future__ import annotations
import argparse, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = 600
S = 4
N = OUT * S


def load_art(path: str) -> Image.Image:
    im = Image.open(path)
    if im.mode == "LA":
        l, a = im.split()
        im = Image.merge("RGBA", (l, l, l, a))
    elif im.mode == "L":
        im = im.convert("RGBA")
    else:
        im = im.convert("RGBA")
    return im


def tight_crop(im: Image.Image, alpha_thr: int = 16) -> Image.Image:
    a = np.asarray(im.split()[-1])
    ys, xs = np.where(a > alpha_thr)
    if len(xs) == 0:
        return im
    pad = 2
    box = (max(0, int(xs.min()) - pad), max(0, int(ys.min()) - pad),
           min(im.width, int(xs.max()) + 1 + pad), min(im.height, int(ys.max()) + 1 + pad))
    return im.crop(box)


def circularity_and_tone(im: Image.Image):
    """Return (is_circular, mean_luminance 0-255, chroma, aspect)."""
    a = np.asarray(im)
    alp = a[..., 3]
    mask = alp > 32
    if mask.sum() < 100:
        return False, 0, 0, 1.0
    ys, xs = np.where(mask)
    w = xs.max() - xs.min() + 1
    h = ys.max() - ys.min() + 1
    aspect = w / max(h, 1)
    cx, cy = xs.mean(), ys.mean()
    r = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    r_max = r.max() or 1
    # fraction of the bounding circle that is filled
    yy, xx = np.ogrid[:im.height, :im.width]
    circle = (xx - cx) ** 2 + (yy - cy) ** 2 <= (0.92 * r_max) ** 2
    fill = mask[circle].mean() if circle.any() else 0
    is_circ = 0.82 <= aspect <= 1.22 and fill > 0.72
    rgb = a[..., :3].astype(np.float32)
    lum = (rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114)
    mean_l = float(lum[mask].mean())
    chroma = float((rgb[mask].max(axis=1) - rgb[mask].min(axis=1)).mean())
    return is_circ, mean_l, chroma, aspect


def stack_wide_logo(im: Image.Image) -> Image.Image:
    """For a wide official logo (symbol + wordmark), stack the left symbol
    above the remaining official lettering so it fits a circle. Uses the
    original pixels only — does not redraw any type."""
    im = tight_crop(im, 24)
    a = np.asarray(im)
    alp = a[..., 3] > 32
    rgb = a[..., :3].astype(np.int16)
    # a "symbol" is often more chromatic than the wordmark
    chroma = (rgb.max(axis=2) - rgb.min(axis=2))
    # split vertically at a low-ink column in the mid-right of the left half
    col = alp.mean(axis=0)
    w = im.width
    # look for a gap between symbol (left) and wordmark (right)
    band = col[int(w * 0.25):int(w * 0.70)]
    if band.size == 0:
        return im
    # prefer a column with very little ink
    rel = int(np.argmin(band))
    split = int(w * 0.25) + rel
    if col[split] > 0.08 and band.min() > 0.08:
        # no clean gap — just return (will be fitted)
        return im
    left = tight_crop(im.crop((0, 0, split, im.height)), 24)
    right = tight_crop(im.crop((split, 0, im.width, im.height)), 24)
    # make a square-ish stack: symbol on top, wordmark below, same width
    target_w = max(left.width, right.width)
    def scale_w(src, tw):
        s = tw / src.width
        return src.resize((tw, max(1, int(src.height * s))), Image.LANCZOS)
    left, right = scale_w(left, target_w), scale_w(right, target_w)
    gap = int(target_w * 0.06)
    canvas = Image.new("RGBA", (target_w, left.height + gap + right.height), (0, 0, 0, 0))
    canvas.paste(left, (0, 0), left)
    canvas.paste(right, (0, left.height + gap), right)
    return canvas


def circle_mask(size: int, r: float, cx=None, cy=None) -> Image.Image:
    cx = size / 2 if cx is None else cx
    cy = size / 2 if cy is None else cy
    yy, xx = np.ogrid[:size, :size]
    m = np.clip((r + 1.2) - np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2), 0, 1)
    return Image.fromarray((m * 255).astype(np.uint8), "L")


def make_seal(art: Image.Image, bg: str, layout: str) -> Image.Image:
    art = tight_crop(art, 20)
    is_circ, mean_l, chroma, aspect = circularity_and_tone(art)
    if layout == "stack" or (layout == "auto" and aspect > 1.55):
        art = stack_wide_logo(art)
        art = tight_crop(art, 20)
        is_circ, mean_l, chroma, aspect = circularity_and_tone(art)

    if bg == "auto":
        # Dark line-art (or very dark monochrome) needs a light plate so it
        # reads on a dark map. A already-complete colourful circular seal does not.
        if (chroma < 25 and mean_l < 80) or (is_circ and mean_l < 40):
            bg = "white"
        elif not is_circ:
            bg = "white"
        else:
            bg = "none"

    # Layout on a supersampled canvas. Leave room for dotted ring + shadow.
    ring_outer = N * 0.46          # radius of the dotted ring
    art_r = ring_outer - 18 * S    # artwork / plate radius just inside the ring
    cx = cy = N / 2
    # slight downward shift so the drop shadow isn't clipped
    cy = N / 2 - 6 * S

    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))

    # Soft drop shadow (behind plate + artwork)
    sh = Image.new("L", (N, N), 0)
    sd = ImageDraw.Draw(sh)
    off = 10 * S
    sd.ellipse([cx - art_r + off, cy - art_r + off * 1.4,
                cx + art_r + off, cy + art_r + off * 1.4], fill=200)
    sh = sh.filter(ImageFilter.GaussianBlur(radius=14 * S))
    shadow = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    shadow.putalpha(sh)
    # tone the alpha down
    sa = np.asarray(sh).astype(np.float32)
    shadow.putalpha(Image.fromarray((sa * 0.55).astype(np.uint8)))
    im = Image.alpha_composite(im, shadow)

    plate_r = art_r - 2 * S
    if bg != "none":
        color = (255, 255, 255, 255) if bg in ("white", "auto") else (*_hex(bg), 255)
        plate = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        ImageDraw.Draw(plate).ellipse([cx - plate_r, cy - plate_r, cx + plate_r, cy + plate_r], fill=color)
        im = Image.alpha_composite(im, plate)

    # Fit artwork inside the plate / ring, with a little inner padding
    pad = 0.06 if bg != "none" else 0.012
    inner = int(2 * art_r * (1 - pad))
    art2 = art.copy()
    art2.thumbnail((inner, inner), Image.LANCZOS)
    x = int(cx - art2.width / 2)
    y = int(cy - art2.height / 2)
    layer = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    layer.paste(art2, (x, y), art2)
    im = Image.alpha_composite(im, layer)

    # White dotted ring + a hairline circle, as in the reference
    d = ImageDraw.Draw(im)
    W = (255, 255, 255, 245)
    # thin solid ring just inside the dots
    hair = ring_outer - 9 * S
    d.ellipse([cx - hair, cy - hair, cx + hair, cy + hair], outline=W, width=max(2, int(2.2 * S)))
    dots_n = 72
    dot_r = 3.6 * S
    for i in range(dots_n):
        ang = 2 * math.pi * i / dots_n
        x = cx + ring_outer * math.cos(ang)
        y = cy + ring_outer * math.sin(ang)
        d.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=W)

    return im.resize((OUT, OUT), Image.LANCZOS)


def _hex(s: str):
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("artwork")
    ap.add_argument("out")
    ap.add_argument("--bg", default="auto", help="auto | none | white | #hex")
    ap.add_argument("--layout", default="auto", help="auto | stack | fit")
    # swallow deprecated positional text args so old invocations don't crash
    ap.add_argument("legacy_text", nargs="*", help=argparse.SUPPRESS)
    args = ap.parse_args()
    if os.environ.get("GW_SEAL_BRIGHT") or args.legacy_text:
        print("warning: GW_SEAL_BRIGHT and curved-text arguments are deprecated; "
              "the centre graphic must stay official artwork (no made-up badge).", file=sys.stderr)
    art = load_art(args.artwork)
    out = make_seal(art, args.bg, args.layout)
    out.save(args.out, optimize=True)
    print(args.out)


if __name__ == "__main__":
    main()
