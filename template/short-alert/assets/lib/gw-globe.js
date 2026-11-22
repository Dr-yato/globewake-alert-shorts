/* Globewake "intel globe" engine v3 (original code) + ALERT extensions (backward compatible):
   highlights: color/stroke/fill_opacity/dash/glow, part_at (pick one polygon of a country, e.g. Crimea), geometry (inline GeoJSON),
   emblem_px (fixed emblem size); arcs: color (hex), dash (null = solid), glow, pulse (opacity breathing), dots:false.
   ONE projection for everything: d3.geoOrthographic().rotate([-lon,-lat]).scale(R*k).translate([cx,cy]).
   Raster: Natural Earth GRAY_HR_SR_OB_DR relief (public domain) reprojected per pixel with the exact inverse of that
   orthographic projection (verified against d3: < 1e-9 px), mip-mapped + trilinear (no shimmer when rotating),
   regional full-res tiles feathered at their edges and cross-faded by zoom (no seams, no popping), antialiased limb.
   Vectors: world-atlas 50m through the same d3 projection, clipped to the visible hemisphere (clipAngle 90).
   All state lives in proxies that GSAP tweens; draw() is pure (same state -> same frame). Async texture decode is
   registered as window.__hf.buildReady['gwglobe'].                                                                */
(function () {
  const NS = 'http://www.w3.org/2000/svg', RAD = Math.PI / 180;
  const mk = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs || {}) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const sstep = (v) => { v = clamp(v, 0, 1); return v * v * (3 - 2 * v); };
  function prep(topo) {
    const fs = topojson.feature(topo, topo.objects.countries).features;
    for (const f of fs) {
      f.c = d3.geoCentroid(f); const b = d3.geoBounds(f);
      f.r = Math.max(d3.geoDistance(f.c, b[0]), d3.geoDistance(f.c, b[1]), d3.geoDistance(f.c, [b[0][0], b[1][1]]), d3.geoDistance(f.c, [b[1][0], b[0][1]]));
      if (f.r > Math.PI / 2 || b[0][0] > b[1][0]) f.r = Math.PI;
    }
    return fs;
  }
  // highlight shape: drop tiny islands (they read as specks), keep the big polygons
  function mainland(f, minArea) {
    if (!f || f.geometry.type !== 'MultiPolygon') return f;
    const polys = f.geometry.coordinates.filter((p) => d3.geoArea({ type: 'Polygon', coordinates: p }) >= minArea);
    return Object.assign({}, f, { geometry: { type: 'MultiPolygon', coordinates: polys.length ? polys : f.geometry.coordinates } });
  }
  const find = (fs, key) => fs.find((f) => String(f.id) === String(key) || (f.properties && f.properties.name === key));
  function loadGrey(src) {
    return new Promise((res, rej) => {
      const im = new Image(); im.onload = () => {
        const c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
        const x = c.getContext('2d'); x.drawImage(im, 0, 0);
        const d = x.getImageData(0, 0, im.width, im.height).data, g = new Float32Array(im.width * im.height);
        for (let i = 0, j = 0; j < g.length; i += 4, j++) g[j] = d[i];
        res({ w: im.width, h: im.height, g });
      }; im.onerror = () => rej(new Error('texture failed: ' + src)); im.src = src;
    });
  }
  function half(t) { // 2x box downsample (mip level)
    const w = t.w >> 1, h = t.h >> 1, g = new Float32Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const i = (2 * y) * t.w + 2 * x; g[y * w + x] = (t.g[i] + t.g[i + 1] + t.g[i + t.w] + t.g[i + t.w + 1]) * .25;
    }
    return { w, h, g };
  }
  // bilinear sample of an equirectangular level (wraps in longitude)
  function sampleEq(L, lon, lat) {
    const u = (lon + 180) / 360 * L.w - .5; let w = (90 - lat) / 180 * L.h - .5;
    if (w < 0) w = 0; if (w > L.h - 1.001) w = L.h - 1.001;
    const iu = Math.floor(u), iw = w | 0, fu = u - iu, fw = w - iw;
    const u0 = ((iu % L.w) + L.w) % L.w, u1 = (u0 + 1) % L.w, r0 = iw * L.w, r1 = r0 + L.w, g = L.g;
    return (g[r0 + u0] * (1 - fu) + g[r0 + u1] * fu) * (1 - fw) + (g[r1 + u0] * (1 - fu) + g[r1 + u1] * fu) * fw;
  }
  function sampleTile(T, lon, lat) {
    const bb = T.bbox, u = (lon - bb[0]) / (bb[2] - bb[0]) * (T.w - 1), w = (bb[3] - lat) / (bb[3] - bb[1]) * (T.h - 1);
    const iu = Math.min(T.w - 2, u | 0), iw = Math.min(T.h - 2, w | 0), fu = u - iu, fw = w - iw, i0 = iw * T.w + iu, g = T.g;
    return (g[i0] * (1 - fu) + g[i0 + 1] * fu) * (1 - fw) + (g[i0 + T.w] * (1 - fu) + g[i0 + T.w + 1] * fu) * fw;
  }

  window.GWGlobe = function (host, cfg) {
    const W = cfg.w || 1080, H = cfg.h || 1920, R = cfg.R || 640, PX = cfg.px || 0.75;
    const RASTER_H = cfg.rasterH || H;
    const C = Object.assign({ ground: '#0E0E0E', text: '#F2F3F0', muted: '#82868D', dim: '#494C52', accent: '#FF3B30', live: '#FF2A2A' }, cfg.colors || {});
    const HI = prep(window.__GW_WORLD_50M);
    const HORIZON = Math.PI / 2;
    // ---- DOM: canvas (relief) + svg (vectors) ----
    const cw = Math.round(W * PX), ch = Math.round(RASTER_H * PX);
    const cv = document.createElement('canvas'); cv.width = cw; cv.height = ch;
    cv.style.cssText = `position:absolute;left:0;top:0;width:${W}px;height:${RASTER_H}px;image-rendering:auto;`;
    host.appendChild(cv); const ctx = cv.getContext('2d'); const img = ctx.createImageData(cw, ch); const buf = img.data;
    const svg = mk('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, 'shape-rendering': 'geometricPrecision', style: 'position:absolute;left:0;top:0;overflow:hidden' }, host);
    const defs = mk('defs', {}, svg);
    defs.innerHTML = `<radialGradient id="gwBlob"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".18" stop-color="${C.accent}" stop-opacity=".95"/><stop offset=".55" stop-color="${C.accent}" stop-opacity=".35"/><stop offset="1" stop-color="${C.accent}" stop-opacity="0"/></radialGradient>
      <filter id="gwGlow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      <radialGradient id="gwAtmo"><stop offset=".92" stop-color="#9aa3b5" stop-opacity="0"/><stop offset=".975" stop-color="#9aa3b5" stop-opacity=".14"/><stop offset="1" stop-color="#9aa3b5" stop-opacity="0"/></radialGradient>`;
    const atmo = mk('circle', { fill: 'url(#gwAtmo)' }, svg);
    const grat = mk('path', { fill: 'none', stroke: C.text, 'stroke-opacity': .07, 'stroke-width': 1.2 }, svg);
    const bord = mk('path', { fill: 'none', stroke: C.text, 'stroke-opacity': .34, 'stroke-width': 1.3, 'stroke-linejoin': 'round' }, svg);
    if (cfg.debugBorders) { bord.setAttribute('stroke', '#00FFFF'); bord.setAttribute('stroke-opacity', 1); bord.setAttribute('stroke-width', 1); }   // alignment check only
    const hlG = mk('g', {}, svg), embG = mk('g', {}, svg), zoneG = mk('g', {}, svg), arcG = mk('g', {}, svg), labG = mk('g', {}, svg), dotG = mk('g', {}, svg), blobG = mk('g', {}, svg), movG = mk('g', {}, svg), impG = mk('g', {}, svg), tagG = mk('g', {}, svg);
    // ---- state ----
    const cam = Object.assign({ lon: 0, lat: 20, k: 1, cx: W / 2, cy: 640 }, cfg.cam0 || {});
    const S = { cam, veil: { a: 0 }, hl: {}, emb: {}, arcs: {}, labels: {}, dots: {}, blobs: {}, tags: {}, movers: {}, impacts: {}, zones: {}, clock: { t: 0 } };
    (cfg.highlights || []).forEach((h) => {
      let f0 = h.geometry ? { type: 'Feature', properties: {}, geometry: h.geometry } : find(HI, h.country);
      if (!f0) { console.warn('GWGlobe: unknown country', h.country); return; }
      if (h.part_at && f0.geometry.type === 'MultiPolygon') {   // one polygon of a country (e.g. a peninsula)
        const poly = f0.geometry.coordinates.find((c) => d3.geoContains({ type: 'Polygon', coordinates: c }, h.part_at));
        if (poly) f0 = { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: poly } };
      }
      if (!f0.c) f0.c = d3.geoCentroid(f0);
      const f = h.part_at || h.geometry ? f0 : mainland(f0, h.min_area == null ? 4e-4 : h.min_area);
      const g = mk('g', { opacity: 0 }, hlG);
      const solid = h.style === 'solid', hatch = h.style === 'muted';
      const pf = mk('path', { fill: h.color || (hatch ? C.text : C.accent), 'fill-opacity': h.fill_opacity != null ? h.fill_opacity : hatch ? .10 : solid ? .5 : .26, 'fill-rule': 'evenodd' }, g);
      const ps = mk('path', { fill: 'none', stroke: h.stroke || h.color || (hatch ? C.text : C.accent), 'stroke-opacity': .95, 'stroke-width': h.width || 2.4, 'stroke-dasharray': h.dash || (hatch ? '7 6' : 'none'), 'stroke-linejoin': 'round' }, g);
      if (h.glow) ps.setAttribute('filter', 'url(#gwGlow)');
      S.hl[h.id] = { a: 0, f, g, pf, ps };
      if (h.emblem) {
        const e = mk('image', { href: h.emblem, opacity: 0, preserveAspectRatio: 'xMidYMid meet' }, embG);
        S.emb[h.id] = { a: 0, s: 1, el: e, at: h.emblem_at || f0.c, size: h.emblem_size || 0.5, max: h.emblem_max || 360, px: h.emblem_px || 0, h };
      }
    });
    (cfg.arcs || []).forEach((a) => {
      const g = mk('g', { opacity: 0 }, arcG);
      const col = a.color === 'white' ? C.text : a.color && a.color[0] === '#' ? a.color : C.accent;
      const p = mk('path', { fill: 'none', stroke: col, 'stroke-width': a.width || 3, 'stroke-dasharray': a.dash === null ? 'none' : (a.dash || '12 9'), 'stroke-linecap': 'round' }, g);
      if (a.glow) p.setAttribute('filter', 'url(#gwGlow)');
      const end = mk('circle', { r: a.end_r || 7, fill: col }, g);
      const st = mk('circle', { r: 6, fill: 'none', stroke: C.text, 'stroke-width': 2.2 }, g);
      if (a.dots === false) { end.setAttribute('r', 0); st.setAttribute('r', 0); }
      S.arcs[a.id] = { a: 0, p: 0, g, path: p, end, st, interp: d3.geoInterpolate(a.from, a.to), def: a };
    });
    (cfg.labels || []).forEach((l) => {
      const big = l.style === 'country', sea = l.style === 'sea';
      const t = mk('text', { 'text-anchor': 'middle', 'font-family': big ? 'Poppins, sans-serif' : sea ? 'Poppins, sans-serif' : 'IBM Plex Mono, monospace', 'font-weight': big ? 700 : sea ? 400 : 600, 'font-style': sea ? 'italic' : 'normal', 'font-size': l.size || (big ? 34 : 20), fill: l.color || (sea ? '#9FC3E8' : C.text), 'fill-opacity': l.opacity || (big ? .92 : .85), 'letter-spacing': big ? '6' : sea ? '3' : '1.4', opacity: 0, style: 'text-transform:uppercase', 'paint-order': 'stroke', stroke: 'rgba(10,10,12,.6)', 'stroke-width': big ? 6 : 4 }, labG);
      t.textContent = l.text.toUpperCase();
      let at = l.at; if (!at && l.country) { const f = find(HI, l.country); at = f ? f.c : [0, 0]; }
      S.labels[l.id] = { a: 0, s: 1, t, at, def: l };
    });
    (cfg.dots || []).forEach((d) => {
      const g = mk('g', { opacity: 0 }, dotG);
      const r1 = mk('circle', { r: 10, fill: 'none', stroke: C.live, 'stroke-width': 2.5 }, g);
      mk('circle', { r: d.r || 7, fill: C.live }, g);
      S.dots[d.id] = { a: 0, pulse: 0, g, r1, def: d };
    });
    (cfg.blobs || []).forEach((b) => {
      const g = mk('g', { opacity: 0 }, blobG);
      mk('circle', { r: b.r || 54, fill: 'url(#gwBlob)' }, g);
      const c2 = mk('circle', { r: (b.r || 54) * .5, fill: 'none', stroke: C.accent, 'stroke-width': 2 }, g);
      S.blobs[b.id] = { a: 0, pulse: 0, g, c2, def: b };
    });
    (cfg.tags || []).forEach((t) => {
      const g = mk('g', { opacity: 0 }, tagG);
      const fmt = (v, p, n) => Math.abs(v).toFixed(2) + '°' + (v >= 0 ? p : n);
      const l1 = t.coord || `${fmt(t.at[1], 'N', 'S')} ${fmt(t.at[0], 'E', 'W')}`, l2 = (t.label || '').toUpperCase();
      const w1 = l1.length * 12.3 + 24, w2 = l2.length * 12.9 + 24;
      const box = mk('g', {}, g);
      mk('rect', { x: 0, y: 0, width: w1, height: 36, fill: 'rgba(10,10,10,.78)', stroke: C.accent, 'stroke-opacity': .6, 'stroke-width': 1.5 }, box);
      const a = mk('text', { x: 12, y: 25, 'font-family': 'IBM Plex Mono, monospace', 'font-weight': 400, 'font-size': 20, fill: C.accent, 'letter-spacing': '1.1' }, box); a.textContent = l1;
      mk('rect', { x: 0, y: 42, width: w2, height: 36, fill: C.accent }, box);
      const b = mk('text', { x: 12, y: 67, 'font-family': 'IBM Plex Mono, monospace', 'font-weight': 600, 'font-size': 20, fill: '#0B0B0B', 'letter-spacing': '1.2' }, box); b.textContent = l2;
      const corners = mk('g', {}, g);
      const s = 34, L = 13;
      corners.innerHTML = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([x, y]) => `<path d="M ${x * s} ${y * s - y * L} L ${x * s} ${y * s} L ${x * s - x * L} ${y * s}" fill="none" stroke="${C.accent}" stroke-width="3"/>`).join('');
      if (t.reticle === false) corners.setAttribute('opacity', 0);
      const lead = mk('path', { fill: 'none', stroke: C.accent, 'stroke-opacity': .8, 'stroke-width': 1.5 }, g);
      S.tags[t.id] = { a: 0, s: 1, g, box, corners, lead, def: t, w: Math.max(w1, w2) };
    });
    const ICON = {   // top-down silhouettes pointing +x, unit ~ 1 = size/2
      ship: 'M 1 0 L 0.55 -0.28 L -1 -0.28 L -1 0.28 L 0.55 0.28 Z',
      drone: 'M 1 0 L -0.7 -0.85 L -0.35 0 L -0.7 0.85 Z' };
    (cfg.movers || []).forEach((m) => {
      const g = mk('g', { opacity: 0 }, movG), sz = (m.size || 34) / 2, col = m.color || (m.icon === 'drone' ? C.accent : C.text);
      const halo = mk('circle', { r: sz * 1.25, fill: col, 'fill-opacity': .18, filter: 'url(#gwGlow)' }, g);
      const ic = mk('path', { d: ICON[m.icon || 'ship'], transform: `scale(${sz})`, fill: col, stroke: '#0B0C0E', 'stroke-width': 0.08, 'stroke-linejoin': 'round' }, g);
      if (m.icon === 'drone') ic.setAttribute('filter', 'url(#gwGlow)');
      const trail = mk('path', { fill: 'none', stroke: col, 'stroke-width': m.trail_w || 2, 'stroke-opacity': .7, 'stroke-dasharray': m.trail_dash || 'none', 'stroke-linecap': 'round' }, movG);
      if (m.trail === false) trail.setAttribute('stroke-width', 0);
      S.movers[m.id] = { a: 0, p: 0, g, ic, trail, interp: d3.geoInterpolate(m.from, m.to), def: m };
    });
    (cfg.impacts || []).forEach((m) => {
      const g = mk('g', { opacity: 0 }, impG), r = m.r || 70;
      const flash = mk('circle', { r: 0, fill: 'url(#gwBlob)' }, g);
      const r1 = mk('circle', { r: 0, fill: 'none', stroke: '#FFFFFF', 'stroke-width': 4 }, g);
      const r2 = mk('circle', { r: 0, fill: 'none', stroke: C.accent, 'stroke-width': 3 }, g);
      const spikes = mk('path', { fill: 'none', stroke: '#FFD9A0', 'stroke-width': 3, 'stroke-linecap': 'round' }, g);
      S.impacts[m.id] = { a: 0, p: 0, g, flash, r1, r2, spikes, r, def: m };
    });
    (cfg.zones || []).forEach((z) => {
      const g = mk('g', { opacity: 0 }, zoneG);
      const pf = mk('path', { fill: z.color || C.accent, 'fill-opacity': z.fill_opacity == null ? .08 : z.fill_opacity, stroke: z.color || C.accent, 'stroke-width': z.width || 2.5, 'stroke-dasharray': z.dash || '10 8' }, g);
      S.zones[z.id] = { a: 0, p: 1, g, pf, circ: d3.geoCircle().center(z.at).radius(z.radius_deg || .12), def: z };
    });
    const veil = mk('rect', { x: 0, y: 0, width: W, height: H, fill: C.ground, opacity: 0 }, svg);

    // ---- textures ----
    const mips = []; const tiles = [];
    const ready = (async () => {
      let L = await loadGrey(cfg.texture); mips.push(L);
      while (L.w > 512) { L = half(L); mips.push(L); }
      for (const t of cfg.tiles || []) { const g = await loadGrey(t.src); tiles.push(Object.assign(g, { bbox: t.bbox, tpd: g.w / (t.bbox[2] - t.bbox[0]) })); }
    })();

    // per-frame relief raster: exact inverse of the d3 orthographic projection used for the vectors
    function raster(scale) {
      buf.fill(0);
      if (!mips.length) return;
      const rot = d3.geoRotation([-cam.lon, -cam.lat, 0]);
      const cart = (ll) => { const l = ll[0] * RAD, p = ll[1] * RAD, c = Math.cos(p); return [c * Math.cos(l), c * Math.sin(l), Math.sin(p)]; };
      const ex = cart(rot.invert([0, 0])), ey = cart(rot.invert([90, 0])), ez = cart(rot.invert([0, 90]));
      const sx = scale * PX, cx = cam.cx * PX, cy = cam.cy * PX;
      // mip level from screen density at the disc centre (texels per screen pixel), trilinear blend
      const ppd = sx * RAD;                       // raster pixels per degree at centre
      const lod = clamp(Math.log2((mips[0].w / 360) / ppd), 0, mips.length - 1.001);
      const l0 = Math.floor(lod), lf = lod - l0, M0 = mips[l0], M1 = mips[l0 + 1] || M0;
      // tiles: fade in only when they are not minified (tpd/ppd <= 2), feather 0.6 deg at their edges
      const act = [];
      for (const T of tiles) { const wz = sstep((2.6 - T.tpd / ppd) / 1.2); if (wz > 0.001) act.push([T, wz]); }
      const x0 = Math.max(0, Math.floor(cx - sx - 1)), x1 = Math.min(cw - 1, Math.ceil(cx + sx + 1));
      const y0 = Math.max(0, Math.floor(cy - sx - 1)), y1 = Math.min(ch - 1, Math.ceil(cy + sx + 1));
      for (let py = y0; py <= y1; py++) {
        const y = (cy - (py + .5)) / sx;
        let o = (py * cw + x0) * 4;
        for (let px = x0; px <= x1; px++, o += 4) {
          const x = ((px + .5) - cx) / sx;
          const r2 = x * x + y * y; if (r2 >= 1) continue;
          const X = Math.sqrt(1 - r2);
          const gx = ex[0] * X + ey[0] * x + ez[0] * y, gy = ex[1] * X + ey[1] * x + ez[1] * y, gz = ex[2] * X + ey[2] * x + ez[2] * y;
          const lat = Math.asin(gz > 1 ? 1 : gz < -1 ? -1 : gz) / RAD, lon = Math.atan2(gy, gx) / RAD;
          let v = sampleEq(M0, lon, lat);
          if (lf > 0.002) v = v * (1 - lf) + sampleEq(M1, lon, lat) * lf;
          for (let k = 0; k < act.length; k++) {
            const T = act[k][0], bb = T.bbox;
            if (lon > bb[0] && lon < bb[2] && lat > bb[1] && lat < bb[3]) {
              const e = Math.min(lon - bb[0], bb[2] - lon, lat - bb[1], bb[3] - lat);
              const w = sstep(e / 0.6) * act[k][1];
              v = v * (1 - w) + sampleTile(T, lon, lat) * w;
            }
          }
          const sh = 0.36 + 0.64 * Math.pow(X, 0.6);           // limb darkening
          const val = v * sh;
          const edge = (1 - Math.sqrt(r2)) * sx;              // distance to the limb in pixels -> antialiased edge
          buf[o] = val; buf[o + 1] = val; buf[o + 2] = val * 1.02 + 1; buf[o + 3] = edge >= 1 ? 255 : 255 * edge;
        }
      }
      ctx.putImageData(img, 0, 0);
    }

    function draw() {
      const scale = R * cam.k;
      raster(scale);
      const proj = d3.geoOrthographic().rotate([-cam.lon, -cam.lat]).scale(scale).translate([cam.cx, cam.cy]).clipAngle(90).precision(0.25);
      const path = d3.geoPath(proj); const ctr = [cam.lon, cam.lat];
      // visibility with a soft fade towards the limb (no popping)
      const vf = (ll) => sstep((HORIZON - d3.geoDistance(ll, ctr)) / 0.14);
      atmo.setAttribute('cx', cam.cx); atmo.setAttribute('cy', cam.cy); atmo.setAttribute('r', scale * 1.06);
      grat.setAttribute('d', path(d3.geoGraticule10()) || '');
      const feats = HI.filter((f) => f.r >= Math.PI || d3.geoDistance(f.c, ctr) - f.r < HORIZON + 0.05);
      bord.setAttribute('d', feats.map((f) => path(f) || '').join(''));
      for (const id in S.hl) {
        const o = S.hl[id]; if (o.a <= .001) { o.g.setAttribute('opacity', 0); continue; }
        const d = path(o.f) || ''; o.pf.setAttribute('d', d); o.ps.setAttribute('d', d); o.g.setAttribute('opacity', o.a);
      }
      for (const id in S.emb) {
        const o = S.emb[id], f = vf(o.at); if (o.a <= .001 || f <= 0.001) { o.el.setAttribute('opacity', 0); continue; }
        const b = path.bounds(S.hl[id].f);
        const dim = (o.px || Math.min(o.max, Math.max(90, Math.min(b[1][0] - b[0][0], b[1][1] - b[0][1]) * o.size))) * o.s;
        const p = proj(o.at);
        o.el.setAttribute('x', p[0] - dim / 2); o.el.setAttribute('y', p[1] - dim / 2); o.el.setAttribute('width', dim); o.el.setAttribute('height', dim);
        o.el.setAttribute('opacity', o.a * f * (o.h.opacity || .7));
      }
      for (const id in S.arcs) {
        const o = S.arcs[id]; if (o.a <= .001 || o.p <= 0) { o.g.setAttribute('opacity', 0); continue; }
        const n = 96, pts = []; for (let i = 0; i <= n; i++) pts.push(o.interp((i / n) * o.p));
        o.path.setAttribute('d', path({ type: 'LineString', coordinates: pts }) || '');   // d3 clips at the horizon
        o.path.setAttribute('stroke-dashoffset', -S.clock.t * (o.def.flow || 40));
        const last = pts[pts.length - 1], fe = vf(last), fs = vf(o.def.from);
        if (fe > 0) { const q = proj(last); o.end.setAttribute('cx', q[0]); o.end.setAttribute('cy', q[1]); } o.end.setAttribute('opacity', fe);
        if (fs > 0) { const q = proj(o.def.from); o.st.setAttribute('cx', q[0]); o.st.setAttribute('cy', q[1]); } o.st.setAttribute('opacity', fs);
        const pu = o.def.pulse ? 1 - o.def.pulse * (0.5 + 0.5 * Math.sin(S.clock.t * (o.def.pulse_speed || 2.4) + (o.def.phase || 0))) : 1;
        o.g.setAttribute('opacity', o.a * pu * (o.def.opacity == null ? 1 : o.def.opacity));
      }
      for (const id in S.labels) {
        const o = S.labels[id], d = o.def;
        const fk = (d.maxk ? sstep((d.maxk - cam.k) / 0.35) : 1) * (d.mink ? sstep((cam.k - d.mink) / 0.35) : 1);
        const f = o.a * vf(o.at) * fk; if (f <= .001) { o.t.setAttribute('opacity', 0); continue; }
        const p = proj(o.at); o.t.setAttribute('transform', `translate(${p[0] + (d.dx || 0)},${p[1] + (d.dy || 0)}) scale(${o.s})`); o.t.setAttribute('opacity', f);
      }
      for (const id in S.dots) {
        const o = S.dots[id], ll = [o.def.lon, o.def.lat], f = o.a * vf(ll); if (f <= .001) { o.g.setAttribute('opacity', 0); continue; }
        const p = proj(ll); o.g.setAttribute('transform', `translate(${p[0]},${p[1]})`); o.g.setAttribute('opacity', f);
        const ph = o.pulse % 1; o.r1.setAttribute('r', 8 + ph * 26); o.r1.setAttribute('stroke-opacity', (1 - ph) * .9);
      }
      for (const id in S.blobs) {
        const o = S.blobs[id], ll = [o.def.lon, o.def.lat], f = o.a * vf(ll); if (f <= .001) { o.g.setAttribute('opacity', 0); continue; }
        const p = proj(ll), ph = o.pulse % 1; o.g.setAttribute('transform', `translate(${p[0]},${p[1]}) scale(${1 + .18 * Math.sin(ph * Math.PI * 2)})`);
        o.c2.setAttribute('r', (o.def.r || 54) * (.4 + ph * 1.3)); o.c2.setAttribute('stroke-opacity', 1 - ph); o.g.setAttribute('opacity', f);
      }
      for (const id in S.tags) {
        const o = S.tags[id], f = o.a * vf(o.def.at); if (f <= .001) { o.g.setAttribute('opacity', 0); continue; }
        const p = proj(o.def.at); o.corners.setAttribute('transform', `translate(${p[0]},${p[1]}) scale(${o.s})`);
        const left = o.def.side === 'left' || (o.def.side == null && p[0] > W * .6);
        const tx = left ? p[0] - 60 - o.w : p[0] + 60, ty = p[1] - 39 + (o.def.dy || 0);
        o.box.setAttribute('transform', `translate(${tx},${ty})`);
        o.lead.setAttribute('d', `M ${p[0] + (left ? -34 : 34) * o.s} ${p[1]} L ${left ? tx + o.w : tx} ${ty + 18}`);
        o.g.setAttribute('opacity', f);
      }
      for (const id in S.movers) {
        const o = S.movers[id]; if (o.a <= .001 || o.p <= 0) { o.g.setAttribute('opacity', 0); o.trail.setAttribute('d', ''); continue; }
        const ll = o.interp(o.p), f = o.a * vf(ll), q = proj(ll), q2 = proj(o.interp(Math.min(1, o.p + .01))), q0 = proj(o.interp(Math.max(0, o.p - .01)));
        const ang = Math.atan2(q2[1] - q0[1], q2[0] - q0[0]) / RAD;
        o.g.setAttribute('transform', `translate(${q[0]},${q[1]}) rotate(${ang})`); o.g.setAttribute('opacity', f);
        const n = 40, pts = []; for (let i = 0; i <= n; i++) pts.push(o.interp((i / n) * o.p));
        o.trail.setAttribute('d', path({ type: 'LineString', coordinates: pts }) || ''); o.trail.setAttribute('opacity', f * (o.def.trail_opacity == null ? .8 : o.def.trail_opacity));
      }
      for (const id in S.impacts) {
        const o = S.impacts[id], f = o.a * vf(o.def.at); if (f <= .001) { o.g.setAttribute('opacity', 0); continue; }
        const q = proj(o.def.at), p = o.p, r = o.r;
        o.g.setAttribute('transform', `translate(${q[0]},${q[1]})`); o.g.setAttribute('opacity', f);
        const fl = clamp(p / .5, 0, 1); o.flash.setAttribute('r', r * (.3 + 1.1 * Math.sqrt(fl))); o.flash.setAttribute('opacity', (1 - fl) * (1 - fl));
        const a1 = clamp(p / .7, 0, 1); o.r1.setAttribute('r', r * (.2 + 1.6 * a1)); o.r1.setAttribute('stroke-opacity', 1 - a1);
        const a2 = clamp((p - .12) / .88, 0, 1); o.r2.setAttribute('r', r * (2.4 * a2)); o.r2.setAttribute('stroke-opacity', (1 - a2) * .9);
        const sp = clamp(p / .35, 0, 1); let d = '';
        for (let i = 0; i < 10; i++) { const an = i * 36 * RAD + .3, r0 = r * (.25 + .5 * sp), r1 = r * (.45 + .75 * sp); d += `M ${r0 * Math.cos(an)} ${r0 * Math.sin(an)} L ${r1 * Math.cos(an)} ${r1 * Math.sin(an)} `; }
        o.spikes.setAttribute('d', d); o.spikes.setAttribute('stroke-opacity', 1 - sp);
      }
      for (const id in S.zones) {
        const o = S.zones[id]; if (o.a <= .001) { o.g.setAttribute('opacity', 0); continue; }
        o.pf.setAttribute('d', path(o.circ()) || ''); o.pf.setAttribute('stroke-dashoffset', -S.clock.t * 14); o.g.setAttribute('opacity', o.a);
      }
      veil.setAttribute('opacity', S.veil.a);
    }
    window.__hf = window.__hf || {}; window.__hf.buildReady = window.__hf.buildReady || {};
    window.__hf.buildReady['gwglobe'] = ready.then(() => draw());
    return { S, draw, ready, debug: { proj: () => d3.geoOrthographic().rotate([-cam.lon, -cam.lat]).scale(R * cam.k).translate([cam.cx, cam.cy]).clipAngle(90) } };
  };
})();
