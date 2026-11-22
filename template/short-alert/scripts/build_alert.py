#!/usr/bin/env python3
"""Globewake ALERT Short builder (reference: Inside-Geopolitics-style 15 s 'ALERT' card, no voiceover).
alert.json -> index.html + compositions/{map,overlay}.html (HyperFrames, 1080x1920, 30 fps).
Timeline (seconds, all overridable in alert.json "timing"):
  0.00-0.95  yellow bar sweep #1 reveals ALERT (+ faint echoes) over a darkened globe; heavy hit
  0.95-1.50  bar sweep #2 wipes ALERT away and reveals the zoomed map (camera flies in 0.9-1.7); whoosh
  1.15-1.90  BREAKING box (white sweep -> red), headline types out (typing SFX)
  2.40       WHAT HAPPENED paragraph fades in; then hold over drifting map + pulsing lines + drone. Logo top-right throughout."""
import html, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = json.load(open(os.path.join(ROOT, "alert.json")))
W, H = 1080, 1920
TOTAL = float(A.get("duration", 15))
C = dict(ground="#0B0C0E", text="#F2F3F0", accent="#FF3B30", alert="#FFD60A", hl="#FFD60A")
C.update(A.get("colors", {}))
C.setdefault("bar", C["alert"])   # sweep bar colour (Globewake: accent red; reference: yellow)
TM = dict(sweep1=[0.12, 0.74], sweep2=[0.92, 1.80], fly=[0.85, 1.75], box=1.05, box_red=1.55, type=[1.15, 2.05], para=2.4,
          ease1='power2.inOut', ease2='power1.out')   # bar timings measured off the reference reel (frames 0.15-1.5 s)
TM.update(A.get("timing", {}))
E = lambda s: html.escape(str(s), quote=True)

def map_comp():
    M = A["map"]
    cfg = dict(w=W, h=H, R=M.get("R", 640), px=M.get("px", 0.75), cam0=M["cam0"], texture="assets/globe/base.jpg",
               highlights=M.get("highlights", []), arcs=M.get("arcs", []), labels=M.get("labels", []), dots=M.get("dots", []),
               blobs=M.get("blobs", []), tags=M.get("tags", []), colors={"accent": C["accent"], "live": C["accent"]},
               debugBorders=bool(os.environ.get("GW_DEBUG_BORDERS")))
    tp = os.path.join(ROOT, "assets/globe/tiles.json")
    cfg["tiles"] = json.load(open(tp)) if os.path.exists(tp) else []
    f0, f1 = TM["fly"]; js = []
    js.append(f"tl.set(S.veil, {{a:{M.get('intro_veil', .55)}}}, 0).to(S.veil, {{a:0, duration:{f1 - f0:.2f}, ease:'power2.inOut'}}, {f0});")
    js.append(f"tl.to(S.cam, {{...{json.dumps(M['cam1'])}, duration:{f1 - f0:.2f}, ease:'power3.inOut'}}, {f0});")
    if M.get("intro_spin"):   # slow spin of the dark globe during the ALERT card
        js.append(f"tl.to(S.cam, {{lon:'+={M['intro_spin']}', duration:{f0:.2f}, ease:'none'}}, 0);")
    if M.get("drift"):        # slow push/drift for the hold
        js.append(f"tl.to(S.cam, {{...{json.dumps(M['drift'])}, duration:{TOTAL - f1:.2f}, ease:'none'}}, {f1});")
    for h in M.get("highlights", []):
        t = h.get("t", f0 + .35)
        js.append(f"tl.to(S.hl['{h['id']}'], {{a:1, duration:.6, ease:'power2.out'}}, {t});")
        if h.get("emblem"):
            js.append(f"tl.to(S.emb['{h['id']}'], {{a:1, duration:.8, ease:'power2.out'}}, {t + .25}).fromTo(S.emb['{h['id']}'], {{s:.8}}, {{s:1, duration:1.2, ease:'power3.out', immediateRender:false}}, {t + .25});")
    for a in M.get("arcs", []):
        t = a.get("t", f1)
        js.append(f"tl.set(S.arcs['{a['id']}'], {{a:1}}, {t}).fromTo(S.arcs['{a['id']}'], {{p:0}}, {{p:1, duration:{a.get('dur', 1.0)}, ease:'power2.inOut', immediateRender:false}}, {t});")
    for k in ("labels", "tags"):
        for l in M.get(k, []):
            js.append(f"tl.to(S.{k}['{l['id']}'], {{a:1, duration:.5}}, {l.get('t', f1 + .6)});")
    for kind, per in (("dots", 1.3), ("blobs", 1.6)):
        for d in M.get(kind, []):
            t = d.get("t", f1 + .4)
            js.append(f"tl.to(S.{kind}['{d['id']}'], {{a:1, duration:.5}}, {t}).fromTo(S.{kind}['{d['id']}'], {{pulse:0}}, {{pulse:{(TOTAL - t) / per:.2f}, duration:{TOTAL - t:.2f}, ease:'none', immediateRender:false}}, {t});")
    return f"""<template>
  <style>
#gm {{ position:absolute; inset:0; overflow:hidden; background:{C['ground']}; }}
#gm-host canvas {{ filter: brightness({A['map'].get('relief_brightness', .6)}) contrast({A['map'].get('relief_contrast', 1.12)}); }}
#gm .grid {{ position:absolute; inset:0; background-image: linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px); background-size:54px 54px; }}
#gm .vig {{ position:absolute; inset:0; pointer-events:none;
  background: radial-gradient(ellipse 90% 55% at 50% 32%, rgba(8,8,10,0) 50%, rgba(8,8,10,.55) 100%),
              linear-gradient(180deg, rgba(8,8,10,.45) 0px, rgba(8,8,10,0) 230px, rgba(8,8,10,0) 860px, rgba(8,8,10,.86) 1060px, rgba(8,8,10,.97) 1300px); }}
  </style>
  <div id="gm" data-composition-id="map" data-width="{W}" data-height="{H}" data-duration="{TOTAL}">
    <div id="gm-host" style="position:absolute; inset:0"></div>
    <div class="grid"></div>
    <div class="vig"></div>
  </div>
  <script>
  (function() {{
    const tl = gsap.timeline({{ paused: true }});
    const g = GWGlobe(document.getElementById('gm-host'), {json.dumps(cfg)});
    const S = g.S;
{chr(10).join('    ' + j for j in js)}
    tl.fromTo(S.clock, {{t:0}}, {{t:{TOTAL}, duration:{TOTAL}, ease:'none'}}, 0);
    tl.eventCallback('onUpdate', g.draw);
    window.__timelines["map"] = tl;
  }})();
  </script>
</template>
"""

def typed(text):
    """headline -> per-character spans (words kept unbreakable); *words* get the yellow highlight."""
    out, n = [], 0
    for part in re.split(r"(\*[^*]+\*)", text):
        if not part: continue
        hl = part.startswith("*"); part = part.strip("*") if hl else part
        for tok in re.split(r"(\s+)", part):
            if not tok: continue
            if tok.isspace(): out.append('<span class="hc"> </span>'); n += 1; continue
            chars = "".join(f'<span class="hc">{E(ch)}</span>' for ch in tok); n += len(tok)
            out.append(f'<span class="wd{" hl" if hl else ""}">{chars}</span>')
    return "".join(out), n

def overlay():
    word = A.get("alert_word", "ALERT"); s1, s2 = TM["sweep1"], TM["sweep2"]; t0, t1 = TM["type"]
    head, n = typed(A["headline"])
    AS = A.get("alert_size", 205); ES = A.get("echo_step", round(AS * .99))
    para = E(A["what_happened"])
    echoes = "".join(f'<div class="echo" style="top:{y}px; opacity:{o}">{E(word)}</div>' for y, o in ((-2 * ES, .16), (-ES, .30), (ES, .30), (2 * ES, .16)))
    logo = A.get("logo", "assets/brand/globewake-logo-horizontal.svg")
    css = f"""
#ov {{ position:absolute; inset:0; overflow:hidden; font-family:Poppins, sans-serif; }}
#intro {{ position:absolute; inset:0; background:rgba(0,0,0,.25); clip-path: inset(0px 0px 0px 0px); }}
#astack {{ position:absolute; left:0; right:0; top:{A.get('alert_y', 1000)}px; height:0; clip-path: inset(-600px 1080px -600px 0px); }}
#astack .main, #astack .echo {{ position:absolute; left:0; right:0; text-align:center; font-weight:700; font-size:{AS}px; line-height:1; letter-spacing:-2px; color:{C['alert']}; transform:translateY(-50%); }}
#astack .echo {{ color:{C['alert']}; filter:brightness(.62) saturate(.7); }}
#astack .tri {{ position:absolute; width:0; height:0; border-left:11px solid transparent; border-right:11px solid transparent; }}
#bar {{ position:absolute; top:0; left:0; width:{A.get('bar_w', 72)}px; height:{H}px; background:{C['bar']}; transform:translateX(-120px); box-shadow:0 0 44px {C['bar']}66; }}
#logo {{ position:absolute; top:{A.get('logo_top', 250)}px; right:{A.get('logo_right', 84)}px; width:{A.get('logo_w', 300)}px; }}
#txt {{ position:absolute; left:108px; top:{A.get('text_top', 1030)}px; width:{A.get('text_w', 800)}px; display:flex; flex-direction:column; align-items:flex-start; }}
#bk {{ position:relative; width:262px; height:46px; overflow:hidden; }}
#bk .red {{ position:absolute; inset:0; background:{C['accent']}; clip-path: inset(0px 262px 0px 0px); }}
#bk .lbl {{ position:absolute; inset:0; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:600; font-size:25px; letter-spacing:1.5px; opacity:0; }}
#bk .wht {{ position:absolute; inset:0; background:#fff; clip-path: inset(0px 262px 0px 0px); }}
#hd {{ margin-top:22px; font-weight:500; font-size:{A.get('headline_size', 58)}px; line-height:1.13; color:{C['text']}; letter-spacing:-.3px; }}
#hd .wd {{ white-space:nowrap; }}
#hd .hl {{ color:{C['hl']}; }}
#hd .hc {{ opacity:0; }}
#wh {{ margin-top:24px; font-weight:400; font-size:{A.get('para_size', 29)}px; line-height:1.24; color:{C['text']}; width:{A.get('para_w', 740)}px; opacity:0; }}
#wh b {{ font-weight:500; color:{C['hl']}; }}
#src {{ margin-top:16px; font-family:'IBM Plex Mono', monospace; font-size:17px; letter-spacing:1px; color:rgba(242,243,240,.45); opacity:0; text-transform:uppercase; }}
#note {{ position:absolute; left:108px; top:{A.get('note_top', 982)}px; font-family:'IBM Plex Mono', monospace; font-size:15px; letter-spacing:1px; color:rgba(242,243,240,.38); opacity:0; text-transform:uppercase; }}
"""
    ay = 0
    tris = (f'<div class="tri" style="left:{540 + round(AS * 1.30)}px; top:{ay - round(AS * .70)}px; border-top:20px solid {C["alert"]};"></div>'
            f'<div class="tri" style="left:{540 - round(AS * 1.42)}px; top:{ay + round(AS * .55)}px; border-bottom:20px solid {C["alert"]};"></div>')
    body = f"""
    <div id="intro"><div id="astack">{echoes}<div class="main">{E(word)}</div>{tris}</div></div>
    <img id="logo" src="{E(logo)}" alt="">
    <div id="note">{E(A.get('map_note', ''))}</div>
    <div id="txt">
      <div id="bk"><div class="red"></div><div class="lbl">{E(A.get('breaking_label', 'BREAKING'))}</div><div class="wht"></div></div>
      <div id="hd">{head}</div>
      <div id="wh"><b>{E(A.get('what_label', 'WHAT HAPPENED:'))}</b> {para}</div>
      <div id="src">{E(A.get('source_line', ''))}</div>
    </div>
    <div id="bar"></div>"""
    bw = A.get("bar_w", 72)
    js = [
        # sweep 1: bar crosses, ALERT revealed behind it (left of the bar)
        f"tl.fromTo('#bar', {{x:-{bw + 8}}}, {{x:{W + 8}, duration:{s1[1] - s1[0]:.2f}, ease:'{TM['ease1']}'}}, {s1[0]});",
        f"tl.fromTo('#astack', {{clipPath:'inset(-600px 1080px -600px 0px)'}}, {{clipPath:'inset(-600px -8px -600px 0px)', duration:{s1[1] - s1[0]:.2f}, ease:'{TM['ease1']}'}}, {s1[0]});",
        f"tl.fromTo('#astack .main', {{scale:1.06}}, {{scale:1, duration:.9, ease:'power2.out'}}, {s1[0] + .1});",
        # flash: ALERT (and echoes) strobe twice once fully revealed (A.flash=false to disable)
        *([f"tl.to('#astack .main, #astack .echo', {{opacity:.25, duration:.04, yoyo:true, repeat:3, ease:'none'}}, {s1[1] + .01:.2f});"] if A.get("flash", True) else []),
        # sweep 2: bar crosses again, intro card wiped away (right of the bar survives), map underneath
        f"tl.fromTo('#bar', {{x:-{bw + 8}}}, {{x:{W + 8}, duration:{s2[1] - s2[0]:.2f}, ease:'{TM['ease2']}', immediateRender:false}}, {s2[0]});",
        f"tl.fromTo('#intro', {{clipPath:'inset(0px 0px 0px 0px)'}}, {{clipPath:'inset(0px 0px 0px {W + bw}px)', duration:{s2[1] - s2[0]:.2f}, ease:'{TM['ease2']}', immediateRender:false}}, {s2[0]});",
        # BREAKING box: white bar grows, then red wipes in under it while the white slides out
        f"tl.to('#bk .wht', {{clipPath:'inset(0px 0px 0px 0px)', duration:.28, ease:'power2.out'}}, {TM['box']});",
        f"tl.set('#bk .red', {{clipPath:'inset(0px 0px 0px 0px)'}}, {TM['box_red']}).to('#bk .wht', {{clipPath:'inset(0px 0px 0px 262px)', duration:.38, ease:'power2.inOut'}}, {TM['box_red']}).to('#bk .lbl', {{opacity:1, duration:.2}}, {TM['box_red'] + .12});",
        # headline types out
        f"tl.to('#hd .hc', {{opacity:1, duration:.001, stagger:{(t1 - t0) / max(n, 1):.4f}}}, {t0});",
        f"tl.to('#wh', {{opacity:1, duration:.45, ease:'power1.out'}}, {TM['para']}).to('#src', {{opacity:1, duration:.45}}, {TM['para'] + .3}).to('#note', {{opacity:1, duration:.45}}, {TM['para'] + .3});",
    ]
    return f"""<template>
  <style>{css}</style>
  <div id="ov" data-composition-id="overlay" data-width="{W}" data-height="{H}" data-duration="{TOTAL}">
{body}
  </div>
  <script>
  (function() {{
    const tl = gsap.timeline({{ paused: true }});
{chr(10).join('    ' + j for j in js)}
    window.__timelines["overlay"] = tl;
  }})();
  </script>
</template>
"""

def main():
    cdir = os.path.join(ROOT, "compositions"); os.makedirs(cdir, exist_ok=True)
    for f in os.listdir(cdir):
        if f.endswith(".html"): os.remove(os.path.join(cdir, f))
    open(os.path.join(cdir, "map.html"), "w").write(map_comp())
    open(os.path.join(cdir, "overlay.html"), "w").write(overlay())
    hosts = [f'      <div id="map" data-composition-id="map" data-composition-src="compositions/map.html" data-start="0" data-duration="{TOTAL}" data-track-index="1" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:1"></div>',
             f'      <div id="overlay" data-composition-id="overlay" data-composition-src="compositions/overlay.html" data-start="0" data-duration="{TOTAL}" data-track-index="2" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:10"></div>']
    idx = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="assets/lib/gsap.min.js"></script>
    <script src="assets/lib/d3-array.min.js"></script>
    <script src="assets/lib/d3-geo.min.js"></script>
    <script src="assets/lib/topojson-client.min.js"></script>
    <script src="assets/geo/{A.get('geo', 'world-50m.js')}"></script>
    <script src="assets/lib/gw-globe.js"></script>
    <style>
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:{C['ground']}; }}
      #main {{ position:relative; width:{W}px; height:{H}px; background:{C['ground']}; font-family:Poppins, sans-serif; }}
    </style>
  </head>
  <body>
    <div id="main" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="{W}" data-height="{H}">
{chr(10).join(hosts)}
      <audio id="mix" class="clip" src="assets/audio/mix.wav" data-start="0" data-duration="{TOTAL}" data-track-index="5" data-volume="1"></audio>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""
    open(os.path.join(ROOT, "index.html"), "w").write(idx)
    print(f"built alert: {TOTAL}s, headline {len(A['headline'])} chars")

if __name__ == "__main__":
    main()
