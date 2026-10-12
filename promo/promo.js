'use strict';
// 30-second promo for Python to EXE Converter.
// Every frame is a pure function of time: window.renderFrame(t) sets the DOM
// and canvases for second t, so render.mjs can capture any frame in any order.

const W = 1920, H = 1080;
const SS = '../docs/screenshots/';
const IC = '../py2exe_gui/icons/';

const layer = document.getElementById('layer');
const bg = document.getElementById('bg').getContext('2d');
const fx = document.getElementById('fx').getContext('2d');
const gr = document.getElementById('grain').getContext('2d');
const flashEl = document.getElementById('flash');
const blackEl = document.getElementById('black');
const camEl = document.getElementById('cam');

// ---------------------------------------------------------------- math
const clamp = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v);
const P = (t, a, b) => clamp((t - a) / (b - a));
const lerp = (a, b, k) => a + (b - a) * k;
const oExpo = x => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x));
const iExpo = x => (x <= 0 ? 0 : Math.pow(2, 10 * x - 10));
const ioCubic = x => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const oCubic = x => 1 - Math.pow(1 - x, 3);
const oBack = (x, s = 1.70158) => { const c3 = s + 1; return 1 + c3 * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2); };
const hash = n => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const mixRGB = (a, b, k) => a.map((v, i) => Math.round(lerp(v, b[i], k)));

// ---------------------------------------------------------------- icons
const ICONS = {};
const ICON_NAMES = ['hammer', 'stethoscope', 'gauge', 'cpu', 'globe', 'rocket', 'key', 'shield-check',
  'circle-check', 'circle-x', 'triangle-alert', 'package', 'terminal', 'monitor', 'git-branch',
  'layers', 'languages', 'loader', 'tag', 'scroll-text', 'upload', 'flask-conical', 'file-text', 'palette'];
async function loadIcons() {
  await Promise.all(ICON_NAMES.map(async n => {
    try { ICONS[n] = await (await fetch(IC + n + '.svg')).text(); } catch (e) { ICONS[n] = ''; }
  }));
}
function ico(name, color, size, sw = 2) {
  let s = ICONS[name] || '';
  s = s.replace(/<!--.*?-->/, '').replace(/currentColor/g, color).replace(/stroke-width="2"/, `stroke-width="${sw}"`);
  return `<span class="icon" style="display:inline-block;width:${size}px;height:${size}px;flex:none">${s}</span>`;
}
const WIN_LOGO = c => `<svg viewBox="0 0 24 24" width="100%" height="100%"><path fill="${c}" d="M2 4.5 10.5 3.3v8.1H2zM11.6 3.1 22 1.6v9.8H11.6zM2 12.6h8.5v8.1L2 19.5zM11.6 12.6H22v9.8l-10.4-1.5z"/></svg>`;

// ---------------------------------------------------------------- DOM helpers
const E = {};
function mk(id, cls, html, css) {
  const d = document.createElement('div');
  d.id = id; d.className = 'el ' + (cls || '');
  if (html != null) d.innerHTML = html;
  if (css) Object.assign(d.style, css);
  d._disp = (css && css.display) || (/\bchip\b/.test(cls || '') ? 'flex' : 'block');
  layer.appendChild(d); E[id] = d;
  return d;
}
const chars = (text, cls = '') => [...text].map(c => `<span class="ch ${cls}">${c === ' ' ? ' ' : esc(c)}</span>`).join('');
function cacheChars(id) { E[id].chs = [...E[id].querySelectorAll('.ch')]; }
function card(id, src, w, h, extra = '') {
  mk(id, 'card', `<img src="${SS + src}" style="width:${w}px;height:${h}px">${extra}<div class="sheen"></div>`,
    { width: w + 'px', height: h + 'px' });
}
function crop(id, src, iw, ih, cx, cy, cw, ch, sc) {
  mk(id, 'card', `<img src="${SS + src}" style="width:${iw * sc}px;height:${ih * sc}px;left:${-cx * sc}px;top:${-cy * sc}px"><div class="sheen"></div>`,
    { width: cw * sc + 'px', height: ch * sc + 'px' });
}
function sheen(id, k) { const s = E[id].querySelector('.sheen'); if (s) s.style.backgroundPosition = `${lerp(130, -30, k)}% 0`; }
function setHTML(el, html) { if (el._h !== html) { el.innerHTML = html; el._h = html; } }

// Group transform: a scene sets G once, and every place() and canvas draw in it
// follows, so transitions (whips, zoom-throughs) move the whole scene together.
let G;
function resetG() { G = { dx: 0, dy: 0, ds: 1, blur: 0, o: 1 }; }
const gx = x => 960 + (x - 960) * G.ds + G.dx;
const gy = y => 540 + (y - 540) * G.ds + G.dy;

function place(id, o = {}) {
  const d = E[id]; d.style.display = d._disp;
  const x = gx(o.x ?? 960), y = gy(o.y ?? 540), s = (o.s ?? 1) * G.ds;
  d.style.transform = `translate3d(${x.toFixed(2)}px,${y.toFixed(2)}px,${o.z || 0}px) translate(-50%,-50%) ` +
    `rotateX(${o.rx || 0}deg) rotateY(${o.ry || 0}deg) rotateZ(${o.rz || 0}deg) scale(${s * (o.sx ?? 1)},${s * (o.sy ?? 1)})`;
  d.style.opacity = clamp((o.o ?? 1) * G.o);
  const blur = (o.blur || 0) + G.blur;
  d.style.filter = blur > 0.15 ? `blur(${blur.toFixed(2)}px)` : 'none';
  return d;
}
// Screen position of a point (px, py) inside an element of size w×h placed with o.
function proj(o, w, h, px, py) {
  const x0 = gx(o.x ?? 960), y0 = gy(o.y ?? 540), z0 = o.z || 0, s = (o.s ?? 1) * G.ds;
  let X = (px - w / 2) * s, Y = (py - h / 2) * s, Z = 0;
  const rz = (o.rz || 0) * Math.PI / 180, ry = (o.ry || 0) * Math.PI / 180, rx = (o.rx || 0) * Math.PI / 180;
  let a = X * Math.cos(rz) - Y * Math.sin(rz), b = X * Math.sin(rz) + Y * Math.cos(rz); X = a; Y = b;
  a = X * Math.cos(ry) + Z * Math.sin(ry); b = -X * Math.sin(ry) + Z * Math.cos(ry); X = a; Z = b;
  a = Y * Math.cos(rx) - Z * Math.sin(rx); b = Y * Math.sin(rx) + Z * Math.cos(rx); Y = a; Z = b;
  X += x0; Y += y0; Z += z0;
  const k = 1800 / (1800 - Z);
  return [960 + (X - 960) * k, 540 + (Y - 540) * k];
}

// Per-character entrance/exit.
function charsIn(id, t, tin, o = {}) {
  const chs = E[id].chs, st = o.st ?? 0.03, dur = o.dur ?? 0.5, tout = o.tout ?? 1e9;
  const dy = o.dy ?? 80, bl = o.blur ?? 8;
  for (let i = 0; i < chs.length; i++) {
    const a = oExpo(P(t, tin + i * st, tin + i * st + dur));
    const b = iExpo(P(t, tout + i * st * 0.4, tout + i * st * 0.4 + 0.3));
    const ty = (1 - a) * dy - b * 70;
    const sc = 1 + (1 - a) * (o.sc ?? 0);
    const rot = (1 - a) * (o.rot ?? 0);
    const c = chs[i].style;
    c.transform = `translateY(${ty.toFixed(1)}px) scale(${sc.toFixed(3)}) rotate(${rot.toFixed(1)}deg)`;
    c.opacity = (a * (1 - b)).toFixed(3);
    const f = (1 - a) * bl + b * 8;
    c.filter = f > 0.3 ? `blur(${f.toFixed(1)}px)` : 'none';
  }
}
// A word that slams in: big, blurred and see-through to crisp.
function slam(t, t0, dur = 0.35, amt = 0.9) {
  const a = oExpo(P(t, t0, t0 + dur));
  return { s: 1 + (1 - a) * amt, o: P(t, t0, t0 + 0.06), blur: (1 - a) * 14 };
}
function styleSlam(el, t, t0) {
  const k = slam(t, t0);
  el.style.transform = `scale(${k.s.toFixed(3)})`;
  el.style.opacity = k.o;
  el.style.filter = k.blur > 0.3 ? `blur(${k.blur.toFixed(1)}px)` : 'none';
}

// ---------------------------------------------------------------- canvas helpers
function glowDot(ctx, x, y, r, rgb, a = 1) {
  if (r <= 0 || a <= 0) return;
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, `rgba(${rgb},${a})`); g.addColorStop(0.35, `rgba(${rgb},${a * 0.35})`); g.addColorStop(1, `rgba(${rgb},0)`);
  ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2);
}
function ring(x, y, r, w, rgb, a) {
  if (a <= 0 || r <= 0) return;
  fx.save(); fx.strokeStyle = `rgba(${rgb},${a})`; fx.lineWidth = w; fx.shadowColor = `rgba(${rgb},${a})`; fx.shadowBlur = 30;
  fx.beginPath(); fx.arc(x, y, r, 0, Math.PI * 2); fx.stroke(); fx.restore();
}
function shockwave(t, t0, x, y, max = 1100, rgb = '255,212,59') {
  if (t < t0 || t > t0 + 1) return;
  const k = oExpo(P(t, t0, t0 + 0.8));
  ring(x, y, k * max, 26 * (1 - k) + 1, rgb, 1 - P(t, t0, t0 + 0.8));
  const k2 = oExpo(P(t, t0 + 0.07, t0 + 0.9));
  ring(x, y, k2 * max * 0.75, 12 * (1 - k2) + 1, '120,170,255', 0.8 * (1 - P(t, t0 + 0.07, t0 + 0.9)));
}
function sparks(t, t0, x, y, n = 36, dist = 500, rgb = '255,230,150', seed = 0) {
  if (t < t0 || t > t0 + 0.8) return;
  const k = oExpo(P(t, t0, t0 + 0.7)), a = 1 - P(t, t0, t0 + 0.7);
  fx.save(); fx.lineCap = 'round'; fx.strokeStyle = `rgba(${rgb},${a})`; fx.lineWidth = 3;
  fx.shadowColor = `rgba(${rgb},1)`; fx.shadowBlur = 12;
  for (let i = 0; i < n; i++) {
    const ang = i / n * Math.PI * 2 + hash(i + seed) * 0.4;
    const d = k * dist * (0.5 + hash(i + seed + 50) * 0.7);
    const d0 = d * (0.75 + 0.2 * k);
    fx.beginPath(); fx.moveTo(x + Math.cos(ang) * d0, y + Math.sin(ang) * d0); fx.lineTo(x + Math.cos(ang) * d, y + Math.sin(ang) * d); fx.stroke();
  }
  fx.restore();
}

// ---------------------------------------------------------------- background
const PARTS = [...Array(150)].map((_, i) => ({ x: hash(i) * W, y: hash(i + 99) * H, z: 0.3 + hash(i + 7) * 1.3, r: 0.6 + hash(i + 3) * 1.6, v: hash(i + 5) }));
function drawBG(t) {
  bg.globalAlpha = 1;
  bg.fillStyle = '#04060d'; bg.fillRect(0, 0, W, H);
  const blobs = [[0.22, 0.28, '55,118,171', 0.55, 760], [0.8, 0.72, '255,212,59', 0.14, 620], [0.62, 0.18, '130,90,255', 0.22, 680], [0.3, 0.85, '40,90,200', 0.25, 600]];
  blobs.forEach((b, i) => {
    const x = W * (b[0] + 0.09 * Math.sin(t * 0.33 + i * 2.1)), y = H * (b[1] + 0.09 * Math.cos(t * 0.29 + i * 1.3));
    const g = bg.createRadialGradient(x, y, 0, x, y, b[4]);
    g.addColorStop(0, `rgba(${b[2]},${b[3]})`); g.addColorStop(1, `rgba(${b[2]},0)`);
    bg.fillStyle = g; bg.fillRect(0, 0, W, H);
  });
  // dot grid, slowly drifting
  bg.fillStyle = 'rgba(150,180,240,0.09)';
  const ox = (t * 16) % 48, oy = (t * 8) % 48;
  for (let x = -48; x < W + 48; x += 48) for (let y = -48; y < H + 48; y += 48) bg.fillRect(x + ox, y + oy, 2, 2);
  // particles
  for (const p of PARTS) {
    const x = ((p.x + t * 24 * p.z) % W + W) % W, y = ((p.y - t * 14 * p.z) % H + H) % H;
    const a = (0.12 + 0.4 * (0.5 + 0.5 * Math.sin(t * 2 + p.v * 20))) * Math.min(1, p.z);
    bg.fillStyle = `rgba(190,215,255,${a.toFixed(3)})`;
    bg.beginPath(); bg.arc(x, y, p.r * p.z, 0, Math.PI * 2); bg.fill();
  }
}

// ---------------------------------------------------------------- grain
const GRAIN = [];
function makeGrain() {
  for (let k = 0; k < 6; k++) {
    const c = document.createElement('canvas'); c.width = c.height = 256;
    const x = c.getContext('2d'), d = x.createImageData(256, 256);
    for (let i = 0; i < d.data.length; i += 4) { const v = Math.floor(hash(i * 0.37 + k * 1000) * 255); d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 255; }
    x.putImageData(d, 0, 0); GRAIN.push(c);
  }
}
function drawGrain(t) {
  const f = Math.floor(t * 30);
  const c = GRAIN[f % GRAIN.length];
  gr.fillStyle = gr.createPattern(c, 'repeat');
  gr.save(); gr.translate(-Math.floor(hash(f) * 256), -Math.floor(hash(f + 1) * 256));
  gr.fillRect(0, 0, W + 256, H + 256); gr.restore();
}

// ---------------------------------------------------------------- build DOM
function label(id, num, text) {
  mk(id, 'label', `<b>${num}</b>${text}`, { width: '900px', textAlign: 'left' });
}
function buildDOM() {
  // 1 — hook
  const face = 'position:absolute;inset:0;backface-visibility:hidden;border-radius:24px;clip-path:polygon(0 0,70% 0,100% 22%,100% 100%,0 100%);display:flex;flex-direction:column;align-items:center;justify-content:center;';
  const fold = c => `<div style="position:absolute;right:0;top:0;width:30%;height:22%;background:${c};clip-path:polygon(0 0,100% 100%,0 100%);border-bottom-left-radius:14px"></div>`;
  mk('file', '', `
    <div style="${face}background:linear-gradient(160deg,#5b9bd5,#1f4e7a)">${fold('#9cc6ef')}
      <div style="font-size:76px;font-weight:900;letter-spacing:-.03em">.py</div>
      <div class="mono" style="font-size:20px;opacity:.75;margin-top:6px">app.py</div></div>
    <div style="${face}background:linear-gradient(160deg,#ffe873,#ffb000);color:#1d1600;transform:rotateY(180deg)">${fold('#fff3b0')}
      <div style="font-size:76px;font-weight:900;letter-spacing:-.03em">.exe</div>
      <div class="mono" style="font-size:20px;opacity:.75;margin-top:6px">app.exe</div></div>`,
    { width: '230px', height: '290px', transformStyle: 'preserve-3d' });
  mk('t1', 'h1', chars('Python ') + chars('→ ', 'yellow') + chars('EXE', 'yellow'), { fontSize: '150px' }); cacheChars('t1');
  mk('t1sub', 'label', 'One-click Python packaging', { fontSize: '26px', color: '#b9c9ea' });

  // 2 — build
  label('lab2', '01', 'One-click build');
  card('cBuild', '2.1/build_en.png', 1080, 800, `<img id="runImg" src="${SS}2.1/build_running_en.png" style="width:1080px;height:800px;opacity:0">`);
  mk('oneclick', 'h1', chars('One click.'), { fontSize: '128px', width: '760px', textAlign: 'left' }); cacheChars('oneclick');
  mk('done', 'h1', 'Done.', { fontSize: '150px', width: '760px', textAlign: 'left', color: '#FFD43B' });
  mk('cursor', '', `<svg viewBox="0 0 24 24" width="46" height="46"><path d="M4 2l15 11.5-6.6 1.2 3.9 7.2-2.8 1.5-3.9-7.3L4 20.5z" fill="#fff" stroke="#0b1020" stroke-width="1.4" stroke-linejoin="round"/></svg>`,
    { width: '46px', height: '46px', filter: 'drop-shadow(0 6px 10px rgba(0,0,0,.5))' });
  mk('prog', 'glass', `
    <div style="display:flex;align-items:center;gap:16px;padding:26px 30px 0">
      <span id="progIcon">${ico('hammer', '#8fb8ff', 34)}</span>
      <span id="progLabel" style="font-size:30px;font-weight:700;flex:1">Analyzing app.py</span>
      <span id="progPct" class="mono" style="font-size:34px;font-weight:700;color:#FFD43B">0%</span></div>
    <div style="margin:22px 30px 0;height:22px;border-radius:11px;background:rgba(255,255,255,.08);position:relative;overflow:hidden">
      <div id="progFill" style="position:absolute;left:0;top:0;bottom:0;width:0;border-radius:11px;background:linear-gradient(90deg,#3776AB,#4B8BBE,#FFD43B);box-shadow:0 0 24px rgba(255,212,59,.7)"></div></div>`,
    { width: '720px', height: '160px' });

  // 3 — doctor
  label('lab3', '02', 'Project doctor');
  card('cCheck', '2.1/check_en.png', 1080, 800);
  const issues = ['Data file not bundled — config.json', 'Relative path breaks once frozen', 'multiprocessing without freeze_support()'];
  issues.forEach((s, i) => mk('iss' + i, 'glass chip', `<span class="st"></span><span>${esc(s)}</span>`, { width: '600px' }));
  mk('doc1', 'h1', chars('Fixes what breaks your EXE'), { fontSize: '80px' }); cacheChars('doc1');
  mk('doc2', 'h1', '— before you even build.', { fontSize: '40px', fontWeight: '700', color: '#FFD43B', letterSpacing: '0' });

  // 4 — size lab
  label('lab4', '03', 'Size lab');
  mk('size1', 'h1', chars('See every MB.'), { fontSize: '100px', width: '700px', textAlign: 'left' }); cacheChars('size1');
  mk('size2', 'h1', chars('Trim the rest.', 'yellow'), { fontSize: '100px', width: '700px', textAlign: 'left' }); cacheChars('size2');
  mk('sizeCap', '', 'Real example: a Pillow app went from 30.1 MB to 14.2 MB with an isolated build environment and one-click exclusions.',
    { width: '660px', fontSize: '26px', lineHeight: '1.45', color: '#a9b6d3', textAlign: 'left' });
  const leg = [['Pillow', '#4B8BBE'], ['Python runtime', '#FFD43B'], ['Tcl/Tk', '#9b7bff'], ['Unused modules', '#ff6b8b']];
  mk('legend', '', leg.map(([n, c], i) => `<span id="leg${i}" style="display:inline-flex;align-items:center;gap:10px;margin-right:28px"><i style="width:14px;height:14px;border-radius:4px;background:${c};display:inline-block"></i>${n}</span>`).join(''),
    { width: '700px', fontSize: '22px', fontWeight: '600', textAlign: 'left', whiteSpace: 'nowrap' });
  mk('badge53', 'h1', '−53%', { fontSize: '76px', color: '#1d1600', background: '#FFD43B', padding: '14px 30px', borderRadius: '22px', boxShadow: '0 0 60px rgba(255,212,59,.6)' });

  // 5 — engines
  label('lab5', '04', 'Two engines');
  mk('panL', '', '', { height: '1080px', zIndex: '-1', background: 'linear-gradient(160deg,#0d2547,#163f73)' });
  mk('panR', '', '', { height: '1080px', zIndex: '-1', background: 'linear-gradient(200deg,#2b1145,#4f1f73)' });
  mk('divline', '', '', { width: '6px', height: '1080px', zIndex: '-1', background: '#fff', boxShadow: '0 0 30px #fff, 0 0 80px #8fb8ff' });
  mk('nmL', 'h1', chars('PyInstaller'), { fontSize: '100px' }); cacheChars('nmL');
  mk('nmR', 'h1', chars('Nuitka'), { fontSize: '100px' }); cacheChars('nmR');
  mk('tgL', 'label', 'Widest compatibility · fastest builds', { fontSize: '22px', color: '#b9d3ff', letterSpacing: '.18em' });
  mk('tgR', 'label', 'Compiled to C · harder to extract', { fontSize: '22px', color: '#e2c6ff', letterSpacing: '.18em' });
  const stats = [['Size on disk', 'MB'], ['Build time', 's'], ['Start-up', 'ms']];
  ['L', 'R'].forEach(side => stats.forEach(([n], i) =>
    mk(`st${side}${i}`, 'glass', `<div style="font-size:20px;letter-spacing:.2em;text-transform:uppercase;color:#9fb0d0">${n}</div><div class="v mono" style="font-size:52px;font-weight:700;margin-top:6px">0</div>`,
      { width: '420px', height: '120px', boxSizing: 'border-box', padding: '18px 28px', textAlign: 'left' })));
  crop('cCmp', '2.0/m3_compare_en.png', 1080, 1050, 40, 418, 987, 404, 1.18);
  mk('eng3', 'h1', chars('Measured side by side. Pick the winner.'), { fontSize: '50px' }); cacheChars('eng3');

  // 6 — platforms
  label('lab6', '05', 'Every platform');
  mk('plat', 'h1', ['Windows.', 'macOS.', 'Linux.'].map((w, i) => `<span id="pw${i}" style="display:inline-block;margin:0 18px">${w}</span>`).join(''), { fontSize: '80px' });
  mk('plat2', 'h1', chars('One project file. Three platforms.', 'yellow'), { fontSize: '34px', fontWeight: '700', letterSpacing: '0' }); cacheChars('plat2');
  card('cPlat', '2.0/m4_platforms_ci_en.png', 1180, 900);
  const osB = [['osW', WIN_LOGO('#7fc4ff'), 'Windows'], ['osM', ico('monitor', '#ffffff', 56), 'macOS'], ['osL', ico('terminal', '#FFD43B', 56), 'Linux']];
  osB.forEach(([id, g, n]) => mk(id, 'glass', `<div style="width:56px;height:56px">${g}</div><div style="font-size:18px;font-weight:700;margin-top:8px">${n}</div>`,
    { width: '140px', height: '140px', borderRadius: '70px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', boxSizing: 'border-box' }));
  [['.exe', 'Windows', '#7fc4ff'], ['.dmg', 'macOS', '#ffffff'], ['.AppImage', 'Linux', '#FFD43B'], ['.deb', 'Linux', '#FFD43B']].forEach(([e, n, c], i) =>
    mk('fc' + i, 'glass chip', `${ico('package', c, 26)}<span class="mono" style="font-size:28px;font-weight:700;color:${c}">${e}</span><span style="color:#9fb0d0;font-size:18px">${n}</span>`, {}));
  mk('yaml', 'glass', `<div style="display:flex;align-items:center;gap:12px;padding:16px 22px;border-bottom:1px solid rgba(255,255,255,.1)">
      <i style="width:13px;height:13px;border-radius:7px;background:#ff5f57;display:inline-block"></i><i style="width:13px;height:13px;border-radius:7px;background:#febc2e;display:inline-block"></i><i style="width:13px;height:13px;border-radius:7px;background:#28c840;display:inline-block"></i>
      <span style="margin-left:12px">${ico('git-branch', '#8fb8ff', 22)}</span><span class="mono" style="font-size:19px;color:#c8d6f0">.github/workflows/p2e-release.yml</span></div>
      <pre id="yamlPre" class="mono" style="margin:0;padding:18px 26px;font-size:21px;line-height:1.5;color:#e8eefc;white-space:pre"></pre>`,
    { width: '660px', height: '500px', textAlign: 'left', overflow: 'hidden' });

  // 7 — ship
  label('lab7', '06', 'Ship it');
  mk('ship', 'h1', ['Sign.', 'Package.', 'Release.'].map((w, i) => `<span id="sw${i}" style="display:inline-block;margin:0 18px">${w}</span>`).join(''), { fontSize: '80px' });
  card('cDist', '2.1/distribute_en.png', 1080, 800);
  const steps = [['tag', 'Bump the version'], ['scroll-text', 'Draft release notes from git'], ['flask-conical', 'Build + smoke test'], ['shield-check', 'Sign the EXE'], ['package', 'Inno Setup installer'], ['upload', 'Publish the GitHub release']];
  steps.forEach(([ic, s], i) => mk('pl' + i, 'glass chip', `<span class="st" style="width:30px;height:30px;display:inline-block"></span>${ico(ic, '#8fb8ff', 26)}<span>${s}</span>`, { width: '600px', height: '62px' }));
  mk('plTrack', '', '<div id="plFill" style="position:absolute;left:0;top:0;width:100%;background:linear-gradient(#4B8BBE,#3ddc97);box-shadow:0 0 14px #3ddc97"></div>',
    { width: '4px', height: '410px', background: 'rgba(255,255,255,.12)', borderRadius: '2px', overflow: 'hidden' });
  mk('seal', '', `<div style="width:250px;height:250px;border-radius:50%;border:8px solid #3ddc97;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(10,40,30,.85);box-shadow:0 0 50px rgba(61,220,151,.6),inset 0 0 0 6px rgba(61,220,151,.25)">
      ${ico('shield-check', '#3ddc97', 70, 2.2)}<div style="font-size:34px;font-weight:900;letter-spacing:.12em;color:#3ddc97;margin-top:6px">SIGNED</div>
      <div class="mono" style="font-size:18px;color:#c9f5e2">Setup.exe</div></div>`, {});

  // 8 — licensing
  label('lab8', '07', 'Offline licensing');
  crop('cLic', '2.0/m5_license_tab_en.png', 1180, 860, 28, 382, 1112, 300, 1.0);
  mk('key', 'glass', `<span id="keyIco">${ico('key', '#FFD43B', 54)}</span><span id="keyText" class="mono" style="font-size:62px;font-weight:700;letter-spacing:.02em"></span>`,
    { display: 'flex', alignItems: 'center', gap: '28px', padding: '26px 44px', borderRadius: '26px', whiteSpace: 'nowrap' });
  mk('licCap', 'h1', chars('Ed25519-signed licence keys. Checked fully offline.'), { fontSize: '40px', fontWeight: '700', letterSpacing: '0' }); cacheChars('licCap');
  [['layers', 'Isolated build environment'], ['file-text', 'Reproducible lock file'], ['languages', 'Arabic + English UI']].forEach(([ic, s], i) =>
    mk('lc' + i, 'glass chip', `${ico(ic, '#FFD43B', 26)}<span>${s}</span>`, {}));

  // 9 — montage
  const MONT = [['2.1/settings_en.png', 1080, 800], ['2.1/build_ar.png', 1080, 800], ['2.1/projects_en.png', 1080, 800], ['2.1/check_ar.png', 1080, 800], ['2.0/m6_home_en.png', 1080, 800], ['2.0/m2_main_nuitka_ar.png', 1080, 1050]];
  MONT.forEach(([src, w, h], i) => { card('m' + i, src, w, h); E['m' + i].fit = 780 / h; });
  mk('mcap', 'glass chip', '', { fontSize: '30px', height: '64px', fontWeight: '800' });
  mk('term', 'glass', `<div style="display:flex;align-items:center;gap:10px;padding:16px 22px;border-bottom:1px solid rgba(255,255,255,.1)">${ico('terminal', '#8fb8ff', 24)}<span style="font-size:20px;font-weight:700;letter-spacing:.2em;color:#8fb8ff">HEADLESS CLI · NO QT NEEDED</span></div>
      <pre id="termPre" class="mono" style="margin:0;padding:22px 30px;font-size:34px;line-height:1.5;white-space:pre;color:#e8eefc"></pre>`,
    { width: '1120px', height: '360px', textAlign: 'left', overflow: 'hidden' });

  // 10 — end card
  mk('logo', '', `<div style="position:absolute;inset:0;border-radius:52px;background:linear-gradient(145deg,#4B8BBE 0%,#2b5f93 45%,#6b3fd6 100%);box-shadow:0 30px 80px rgba(0,0,0,.6),0 0 90px rgba(75,139,190,.55),inset 0 2px 0 rgba(255,255,255,.3)"></div>
      <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center">
        <div class="mono" style="font-size:40px;font-weight:700;color:#FFD43B">.py</div>
        <div style="font-size:40px;font-weight:900;line-height:.8;color:#fff">↓</div>
        <div style="font-size:66px;font-weight:900;letter-spacing:-.03em;color:#fff">.exe</div></div>
      <div style="position:absolute;inset:0;border-radius:52px;overflow:hidden"><div id="glint" style="position:absolute;top:-20%;bottom:-20%;width:40%;background:linear-gradient(100deg,transparent,rgba(255,255,255,.55),transparent);transform:skewX(-20deg)"></div></div>`,
    { width: '230px', height: '230px' });
  mk('endT', 'h1', chars('Python to EXE Converter'), { fontSize: '96px' }); cacheChars('endT');
  mk('endTag', '', 'From <span style="color:#FFD43B">.py</span> to <span style="color:#FFD43B">.exe</span> — without the pain.', { fontSize: '40px', fontWeight: '600', color: '#c9d6f2', whiteSpace: 'nowrap' });
  mk('endUrl', 'glass chip mono', `${ico('git-branch', '#8fb8ff', 26)}<span>github.com/abosalehg-ui/python_to_exe</span>`, { fontSize: '26px', height: '62px' });
}

// ================================================================ scenes
// 1 · hook (0–3): a snake of light collapses into a .py file that flips into .exe on the drop.
const snakePt = u => [140 + 1640 * u, 500 + 190 * Math.sin(u * Math.PI * 2.4 + 0.6) * (1 - 0.35 * u)];
function s1(t) {
  const ex = iExpo(P(t, 2.72, 3.0));
  G.ds = 1 + ex * 1.8; G.blur = ex * 18; G.o = 1 - ex;
  const C = [960, 470];
  const u1 = oCubic(P(t, 0.15, 1.3)), u0 = ioCubic(P(t, 0.55, 1.35)) * 0.8;
  const col = iExpo(P(t, 1.3, 1.62));
  if (t < 1.64 && u1 > u0) {
    const pts = [], N = 180;
    for (let i = 0; i <= N; i++) { const [x, y] = snakePt(u0 + (u1 - u0) * i / N); pts.push([lerp(x, C[0], col), lerp(y, C[1], col)]); }
    const g = fx.createLinearGradient(140, 0, 1780, 0);
    g.addColorStop(0, '#3776AB'); g.addColorStop(0.5, '#6aa8e0'); g.addColorStop(1, '#FFD43B');
    fx.lineCap = 'round'; fx.lineJoin = 'round';
    [[38, 0.07], [18, 0.22], [6, 1]].forEach(([w, a]) => {
      fx.globalAlpha = a; fx.strokeStyle = g; fx.lineWidth = w * (1 - col * 0.6);
      fx.beginPath(); pts.forEach((p, i) => (i ? fx.lineTo(p[0], p[1]) : fx.moveTo(p[0], p[1]))); fx.stroke();
    });
    fx.globalAlpha = 1;
    const h = pts[pts.length - 1]; glowDot(fx, h[0], h[1], 46, '255,240,170', 1);
  }
  if (t > 1.3 && t < 2.3) glowDot(fx, C[0], C[1], (60 + 260 * col) * (1 - P(t, 1.7, 2.3)), '140,185,255', 0.9);

  if (t >= 1.6) {
    const pop = oBack(P(t, 1.6, 1.95), 2.2);
    const flip = oBack(P(t, 2.0, 2.4), 1.3) * 180;
    const rise = oExpo(P(t, 2.0, 2.5));
    const s = Math.max(0.001, pop * (1 - 0.25 * rise)), y = C[1] - 90 * rise;
    glowDot(bg, gx(960), gy(y), 300 * s * G.ds, flip > 90 ? '255,212,59' : '75,139,190', 0.5 * G.o);
    place('file', { x: 960, y, s, ry: flip + Math.sin(t * 2.2) * 5, rz: Math.sin(t * 1.6) * 2 }).style.filter = 'none'; // a filter would flatten the 3D flip
  }
  shockwave(t, 2.0, gx(960), gy(430));
  sparks(t, 2.0, gx(960), gy(430), 40, 650);
  place('t1', { x: 960, y: 760 }); charsIn('t1', t, 2.06, { st: 0.035, dur: 0.5, dy: 130, blur: 12, sc: 0.4 });
  const sub = oExpo(P(t, 2.4, 2.8));
  place('t1sub', { x: 960, y: 870, o: sub }).style.letterSpacing = lerp(0.9, 0.32, sub) + 'em';
}

// 2 · one-click build (3–7)
function s2(t) {
  const ent = oExpo(P(t, 3, 3.45));
  G.ds = lerp(0.8, 1, ent); G.blur = (1 - ent) * 14; G.o = P(t, 3, 3.12);
  const ex = iExpo(P(t, 6.72, 7.0)); G.dx = -ex * 1500; G.blur += ex * 16;

  place('lab2', { x: 570, y: 96, o: oExpo(P(t, 3.15, 3.5)) });
  const k = oExpo(P(t, 3.05, 3.85)), push = ioCubic(P(t, 4.6, 6.6));
  const cO = { x: lerp(1500, 1190, k), y: lerp(660, 540, k), z: lerp(-1400, 0, k), rx: lerp(30, 5, k), ry: lerp(-55, -10, k) + 4 * push + Math.sin(t * 0.9) * 1.2, rz: lerp(-8, 0, k), s: 0.8 + 0.05 * push };
  place('cBuild', cO); sheen('cBuild', P(t, 3.5, 4.4));
  document.getElementById('runImg').style.opacity = P(t, 4.48, 4.54);

  place('oneclick', { x: 500, y: 470 }); charsIn('oneclick', t, 3.3, { st: 0.04, dur: 0.5, tout: 5.8, dy: 110 });
  if (t >= 6.15) place('done', { x: 500, y: 470, ...slam(t, 6.15, 0.4, 1.1) });

  // cursor → Start Build → click
  const btn = proj(cO, 1080, 800, 292, 753);
  if (t > 3.7 && t < 5.0) {
    const m = ioCubic(P(t, 3.75, 4.35));
    const cx = lerp(1700, btn[0], m), cy = lerp(1010, btn[1], m) + Math.sin(m * Math.PI) * -60;
    const dip = 1 - 0.2 * Math.sin(Math.PI * P(t, 4.4, 4.56));
    place('cursor', { x: cx + 19, y: cy + 19, s: dip, o: P(t, 3.7, 3.8) * (1 - P(t, 4.8, 5.0)) });
  }
  if (t > 4.45 && t < 5.0) {
    const r = oExpo(P(t, 4.45, 4.95));
    ring(btn[0], btn[1], 20 + r * 140, 6 * (1 - r) + 1, '255,255,255', (1 - r) * G.o);
  }
  // progress callout popping out of the real progress bar
  if (t >= 4.7) {
    const bar = proj(cO, 1080, 800, 938, 753);
    const m = oExpo(P(t, 4.7, 5.05)), pk = oBack(P(t, 4.7, 5.05), 1.6);
    const done = t >= 6.1;
    const v = ioCubic(P(t, 4.95, 6.1)) * 100;
    const el = place('prog', { x: lerp(bar[0], 1190, m), y: lerp(bar[1], 905, m), z: 120, s: lerp(0.3, 1, pk) * (1 + 0.06 * (1 - oExpo(P(t, 6.1, 6.4))) * (done ? 1 : 0)), o: P(t, 4.7, 4.78), ry: -6 });
    document.getElementById('progFill').style.width = v.toFixed(2) + '%';
    document.getElementById('progFill').style.background = done ? 'linear-gradient(90deg,#1fa36a,#3ddc97)' : 'linear-gradient(90deg,#3776AB,#4B8BBE,#FFD43B)';
    setHTML(document.getElementById('progPct'), Math.round(v) + '%');
    const lbl = done ? 'notes.exe is ready' : v < 30 ? 'Analyzing app.py' : v < 62 ? 'Analyzing imports' : v < 82 ? 'Building PYZ' : 'Building EXE';
    setHTML(document.getElementById('progLabel'), lbl);
    setHTML(document.getElementById('progIcon'), done ? ico('circle-check', '#3ddc97', 34, 2.4) : ico('hammer', '#8fb8ff', 34));
    el.style.borderColor = done ? 'rgba(61,220,151,.9)' : 'rgba(255,255,255,.14)';
    el.style.boxShadow = done ? `0 30px 70px rgba(0,0,0,.55), 0 0 ${lerp(90, 30, P(t, 6.1, 6.6))}px rgba(61,220,151,.6)` : '';
  }
}

// 3 · project doctor (7–11)
function score(t) {
  let v = 62 * oExpo(P(t, 7.35, 7.95));
  v += 16 * oBack(P(t, 8.3, 8.55)) + 13 * oBack(P(t, 8.7, 8.95)) + 9 * oBack(P(t, 9.1, 9.35));
  return Math.min(v, 100);
}
function scoreRGB(v) {
  return v < 70 ? mixRGB([255, 84, 112], [255, 176, 32], clamp(v / 70)) : mixRGB([255, 176, 32], [61, 220, 151], clamp((v - 70) / 30));
}
const FIX_T = [8.3, 8.7, 9.1];
function s3(t) {
  const ent = oExpo(P(t, 7, 7.4)); G.dx = (1 - ent) * 1500; G.blur = (1 - ent) * 16;
  const exE = iExpo(P(t, 10.7, 11)); const gO = 1 - exE;
  G.o = gO; G.ds = 1 - 0.08 * exE;

  place('lab3', { x: 570, y: 96 });
  const cO = { x: 640, y: 500, rx: 4, ry: 12 + Math.sin(t * 0.8) * 1.5, s: 0.74 };
  place('cCheck', cO); sheen('cCheck', P(t, 7.3, 8.2));

  // gauge — morphs into the size-lab donut on the way out
  const m = ioCubic(P(t, 10.7, 11));
  const v = score(t);
  const cx = lerp(gx(1440), 700, m), cy = lerp(gy(400), 560, m), R = lerp(170, 250, m), LW = lerp(22, 70, m);
  const a0 = lerp(Math.PI * 0.75, -Math.PI / 2, m), sweep = lerp(Math.PI * 1.5, Math.PI * 2, m);
  fx.save(); fx.lineCap = 'round';
  fx.strokeStyle = `rgba(255,255,255,${lerp(0.08, 0.06, m)})`; fx.lineWidth = LW;
  fx.beginPath(); fx.arc(cx, cy, R, a0, a0 + sweep); fx.stroke();
  const [r, g, b] = scoreRGB(v), va = 1 - m;
  if (v > 0.5 && va > 0) {
    fx.strokeStyle = `rgba(${r},${g},${b},${va})`; fx.shadowColor = `rgb(${r},${g},${b})`; fx.shadowBlur = 40;
    fx.beginPath(); fx.arc(cx, cy, R, a0, a0 + sweep * v / 100); fx.stroke();
  }
  fx.restore();
  if (va > 0) {
    fx.save(); fx.globalAlpha = va * P(t, 7.2, 7.4); fx.textAlign = 'center'; fx.fillStyle = '#fff';
    fx.font = '800 120px Inter'; fx.fillText(Math.round(v), cx, cy + 38);
    fx.font = '600 22px Inter'; fx.fillStyle = '#9fb0d0'; fx.fillText('R E A D I N E S S', cx, cy - 72);
    fx.font = '700 28px Inter'; fx.fillText('/ 100', cx, cy + 92);
    fx.restore();
  }
  if (t > 9.1 && t < 9.9) glowDot(fx, cx, cy, 260 * (1 - P(t, 9.1, 9.9)), '61,220,151', 0.6);
  shockwave(t, 9.15, cx, cy, 420, '61,220,151');

  // issues get fixed one by one, then fly away
  for (let i = 0; i < 3; i++) {
    const tin = 7.45 + i * 0.1, a = oExpo(P(t, tin, tin + 0.45));
    const out = iExpo(P(t, 9.4 + i * 0.05, 9.75 + i * 0.05));
    if (t < tin || out >= 1) continue;
    const fixed = t >= FIX_T[i];
    const el = place('iss' + i, { x: 1440 + (1 - a) * 260, y: 670 + i * 68 - out * 120, o: a * (1 - out), s: 1 + 0.08 * (fixed ? 1 - oExpo(P(t, FIX_T[i], FIX_T[i] + 0.3)) : 0) });
    setHTML(el.querySelector('.st'), fixed ? ico('circle-check', '#3ddc97', 28, 2.4) : ico('triangle-alert', '#ffb020', 28));
    el.style.background = fixed ? 'linear-gradient(180deg,rgba(20,70,52,.95),rgba(12,46,34,.95))' : '';
    el.style.borderColor = fixed ? 'rgba(61,220,151,.6)' : 'rgba(255,176,32,.45)';
  }
  // highlight the real readiness line in the screenshot and wire it to the gauge
  if (t > 9.15 && t < 10.75) {
    const pts = [[203, 149], [327, 149], [327, 172], [203, 172]].map(p => proj(cO, 1080, 800, p[0], p[1]));
    const a = P(t, 9.15, 9.3) * gO;
    fx.save(); fx.strokeStyle = `rgba(61,220,151,${a})`; fx.lineWidth = 3; fx.shadowColor = '#3ddc97'; fx.shadowBlur = 18;
    fx.beginPath(); pts.forEach((p, i) => (i ? fx.lineTo(p[0] + (i === 1 || i === 2 ? 6 : -6), p[1] + (i >= 2 ? 5 : -5)) : fx.moveTo(p[0] - 6, p[1] - 5))); fx.closePath(); fx.stroke();
    const from = [pts[1][0] + 6, (pts[1][1] + pts[2][1]) / 2], to = [cx - R - 30, cy];
    const d = oExpo(P(t, 9.2, 9.6));
    fx.setLineDash([8, 8]); fx.lineDashOffset = -t * 60;
    fx.beginPath(); fx.moveTo(from[0], from[1]); fx.lineTo(lerp(from[0], to[0], d), lerp(from[1], to[1], d)); fx.stroke();
    fx.restore();
  }
  if (t >= 9.45) { place('doc1', { x: 960, y: 905 }); charsIn('doc1', t, 9.45, { st: 0.018, dur: 0.45, dy: 70 }); }
  if (t >= 9.75) { const a = oExpo(P(t, 9.75, 10.15)); place('doc2', { x: 960, y: 985 + (1 - a) * 30, o: a }); }
}

// 4 · size lab (11–14)
const SEGS = [{ f: 0.25, c: '75,139,190' }, { f: 0.222, c: '255,212,59' }, { f: 0.28, c: '155,123,255', out: 12.0 }, { f: 0.248, c: '255,107,139', out: 12.25 }];
function s4(t) {
  const ex = iExpo(P(t, 13.7, 14));
  G.o = 1 - ex;
  const C = [700, 560], R = 250 * (1 - ex), LW = 70 * (1 - ex * 0.7), rot = ex * 2.2;
  fx.save(); fx.lineCap = 'butt';
  fx.strokeStyle = `rgba(255,255,255,${0.06 * (1 - ex)})`; fx.lineWidth = LW;
  fx.beginPath(); fx.arc(C[0], C[1], Math.max(R, 1), 0, Math.PI * 2); fx.stroke();
  let start = -Math.PI / 2 + rot;
  SEGS.forEach((s, i) => {
    const k = oExpo(P(t, 11.05 + i * 0.12, 11.6 + i * 0.12));
    const rem = s.out ? oExpo(P(t, s.out, s.out + 0.45)) : 0;
    const a1 = start + 0.02, a2 = start + s.f * Math.PI * 2 * k - 0.02;
    const mid = (a1 + a2) / 2, off = rem * 140;
    if (a2 > a1 && rem < 1 && R > 1) {
      fx.strokeStyle = `rgba(${s.c},${(1 - rem) * (1 - ex)})`; fx.lineWidth = LW * (1 - 0.6 * rem);
      fx.shadowColor = `rgba(${s.c},0.8)`; fx.shadowBlur = 30;
      fx.beginPath(); fx.arc(C[0] + Math.cos(mid) * off, C[1] + Math.sin(mid) * off, R, a1, a2); fx.stroke();
    }
    if (s.out) sparks(t, s.out, C[0] + Math.cos(mid) * (R + 20), C[1] + Math.sin(mid) * (R + 20), 18, 160, s.c, i * 10);
    start += s.f * Math.PI * 2;
  });
  if (t > 12.5 && R > 1) {
    const kept = SEGS[0].f + SEGS[1].f;
    fx.shadowBlur = 0; fx.setLineDash([10, 12]); fx.lineDashOffset = -t * 40;
    fx.strokeStyle = `rgba(255,212,59,${0.55 * P(t, 12.5, 12.8) * (1 - ex)})`; fx.lineWidth = 3;
    fx.beginPath(); fx.arc(C[0], C[1], R + LW / 2 + 12, -Math.PI / 2 + rot + kept * Math.PI * 2, Math.PI * 1.5 + rot); fx.stroke();
  }
  fx.restore();
  // counter
  const up = oExpo(P(t, 11.05, 11.7)), down = oCubic(P(t, 12.0, 12.9));
  const mb = lerp(30.1 * up, 14.2, down);
  fx.save(); fx.globalAlpha = 1 - ex; fx.textAlign = 'center';
  fx.font = '600 22px Inter'; fx.fillStyle = '#9fb0d0'; fx.fillText('E X E   S I Z E', C[0], C[1] - 62);
  fx.font = '800 96px Inter'; fx.fillStyle = t >= 12.9 ? '#FFD43B' : '#fff'; fx.fillText(mb.toFixed(1), C[0], C[1] + 30);
  fx.font = '700 30px Inter'; fx.fillStyle = '#c9d6f2'; fx.fillText('MB', C[0], C[1] + 78);
  fx.restore();
  if (t >= 13.0) place('badge53', { x: 1075, y: 255, rz: -8, ...slam(t, 13.0, 0.35, 1.4) });
  shockwave(t, 13.0, 1075, 255, 520);

  place('lab4', { x: 570, y: 96 });
  place('size1', { x: 1530, y: 400 }); charsIn('size1', t, 11.25, { st: 0.03, dur: 0.45 });
  if (t >= 12.0) { place('size2', { x: 1530, y: 510 }); charsIn('size2', t, 12.0, { st: 0.03, dur: 0.45 }); }
  const cap = oExpo(P(t, 12.45, 12.9)); place('sizeCap', { x: 1510, y: 660 + (1 - cap) * 30, o: cap });
  const lg = oExpo(P(t, 11.6, 12.0)); place('legend', { x: 1530, y: 800 + (1 - lg) * 30, o: lg });
  [2, 3].forEach(i => { const s = document.getElementById('leg' + i).style; const off = t >= SEGS[i].out; s.opacity = off ? 0.35 : 1; s.textDecoration = off ? 'line-through' : 'none'; });
  // the divider of the next scene starts drawing here
  if (t > 13.72) {
    const d = oExpo(P(t, 13.72, 14));
    fx.save(); fx.fillStyle = '#fff'; fx.shadowColor = '#8fb8ff'; fx.shadowBlur = 40;
    fx.fillRect(957, 540 - 540 * d, 6, 1080 * d); fx.restore();
  }
}

// 5 · two engines (14–17)
const ENG = { L: [7.9, 10.6, 227], R: [5.3, 45.3, 131] }, UNIT = [' MB', ' s', ' ms'], DEC = [1, 1, 0];
const WIN = ['R', 'L', 'R'];
function s5(t) {
  const ex = iExpo(P(t, 16.72, 17)); G.ds = 1 + ex * 1.6; G.blur = ex * 18; G.o = 1 - ex;
  const inL = oExpo(P(t, 14, 14.4)), inR = oExpo(P(t, 14.05, 14.45));
  const div = t > 14.4 ? 960 + 130 * Math.sin((t - 14.4) * 5) * Math.exp(-(t - 14.4) * 1.6) : 960;
  place('panL', { x: div / 2, y: 540 - (1 - inL) * 1080 }).style.width = div + 'px';
  place('panR', { x: div + (1920 - div) / 2, y: 540 + (1 - inR) * 1080 }).style.width = (1920 - div) + 'px';
  place('divline', { x: div, y: 540 });
  place('lab5', { x: 570, y: 70 });

  const mv = ioCubic(P(t, 15.35, 15.75));
  const lx = div / 2, rx = div + (1920 - div) / 2;
  place('nmL', { x: lx, y: lerp(300, 150, mv), s: lerp(1, 0.62, mv) }); charsIn('nmL', t, 14.25, { st: 0.035, dy: 100 });
  place('nmR', { x: rx, y: lerp(300, 150, mv), s: lerp(1, 0.62, mv) }); charsIn('nmR', t, 14.35, { st: 0.035, dy: 100 });
  const tg = oExpo(P(t, 14.6, 14.95)) * (1 - mv);
  place('tgL', { x: lx, y: 390, o: tg }); place('tgR', { x: rx, y: 390, o: tg });
  const out = iExpo(P(t, 15.3, 15.55));
  ['L', 'R'].forEach(side => ENG[side].forEach((val, i) => {
    const k = oCubic(P(t, 14.6 + i * 0.08, 15.0 + i * 0.08));
    const a = oExpo(P(t, 14.55 + i * 0.1, 14.95 + i * 0.1));
    const el = place(`st${side}${i}`, { x: side === 'L' ? lx : rx, y: 500 + i * 140 + (1 - a) * 60 + out * 80, o: a * (1 - out) });
    const v = el.querySelector('.v'); setHTML(v, (val * k).toFixed(DEC[i]) + UNIT[i]);
    const win = t >= 15.15 && WIN[i] === side;
    v.style.color = win ? '#3ddc97' : '#fff';
    el.style.borderColor = win ? 'rgba(61,220,151,.75)' : 'rgba(255,255,255,.14)';
  }));
  const rise = oExpo(P(t, 15.45, 16.0));
  if (t >= 15.45) { place('cCmp', { x: 960, y: lerp(1350, 590, rise), rx: lerp(45, 6, rise) + Math.sin(t) * 1, s: 1 }); sheen('cCmp', P(t, 15.8, 16.6)); }
  if (t >= 16.0) { place('eng3', { x: 960, y: 960 }); charsIn('eng3', t, 16.0, { st: 0.015, dur: 0.4, dy: 60 }); }
}

// 6 · every platform (17–21)
const YAML = [
  [['k', 'name'], ['p', ': '], ['s', 'p2e-release']],
  [['k', 'on'], ['p', ':']],
  [['p', '  '], ['k', 'push'], ['p', ': { '], ['k', 'tags'], ['p', ': ['], ['s', '"v*"'], ['p', '] }']],
  [['k', 'jobs'], ['p', ':']],
  [['p', '  '], ['k', 'build'], ['p', ':']],
  [['p', '    '], ['k', 'strategy'], ['p', ':']],
  [['p', '      '], ['k', 'matrix'], ['p', ':']],
  [['p', '        '], ['k', 'os'], ['p', ': ['], ['s', 'windows-latest'], ['p', ',']],
  [['p', '              '], ['s', 'macos-latest'], ['p', ',']],
  [['p', '              '], ['s', 'ubuntu-latest'], ['p', ']']],
  [['p', '    '], ['k', 'steps'], ['p', ':']],
  [['p', '      - '], ['k', 'run'], ['p', ': '], ['c', 'py2exe-gui release --yes']],
];
const YCOL = { k: '#7fb8ff', p: '#c8d2e6', s: '#FFD43B', c: '#3ddc97' };
const YTOTAL = YAML.reduce((n, l) => n + l.reduce((m, [, s]) => m + s.length, 0) + 1, 0);
function yamlHTML(n) {
  let out = '', left = n;
  for (const line of YAML) {
    for (const [c, s] of line) { if (left <= 0) break; const part = s.slice(0, left); left -= part.length; out += `<span style="color:${YCOL[c]}">${esc(part)}</span>`; }
    if (left <= 0) break; left -= 1; out += '\n';
  }
  return out;
}
function s6(t) {
  const ent = oExpo(P(t, 17, 17.45));
  G.ds = lerp(0.72, 1, ent); G.blur = (1 - ent) * 14; G.o = P(t, 17, 17.1);
  const ex = iExpo(P(t, 20.72, 21)); G.dy = -ex * 1300; G.blur += ex * 16;

  place('lab6', { x: 570, y: 70 });
  place('plat', { x: 960, y: 150 });
  [17.15, 17.5, 17.85].forEach((t0, i) => styleSlam(document.getElementById('pw' + i), t, t0));
  if (t >= 18.2) { place('plat2', { x: 960, y: 235 }); charsIn('plat2', t, 18.2, { st: 0.015, dy: 40 }); }

  const cO = { x: 620, y: 610, z: lerp(-700, 0, ent), rx: 4, ry: 14 + Math.sin(t * 0.8) * 1.5, s: 0.56 };
  place('cPlat', cO); sheen('cPlat', P(t, 17.4, 18.3));

  // OS badges orbit the screenshot, then dive into the packages they produce
  const targets = [520, 820, 1120];
  ['osW', 'osM', 'osL'].forEach((id, i) => {
    const pop = oBack(P(t, 17.3 + i * 0.15, 17.65 + i * 0.15), 2);
    const ang = (-90 + i * 120) * Math.PI / 180 + (t - 17) * 1.1;
    const ox = 620 + Math.cos(ang) * 430, oy = 610 + Math.sin(ang) * 300;
    const fly = ioCubic(P(t, 19.0 + i * 0.15, 19.32 + i * 0.15));
    if (t < 17.3 + i * 0.15 || fly >= 1) return;
    place(id, { x: lerp(ox, targets[i], fly), y: lerp(oy, 985, fly), z: 80, s: Math.max(0.001, pop * lerp(1, 0.35, fly)), o: 1 - P(fly, 0.85, 1) });
  });
  for (let i = 0; i < 4; i++) {
    const t0 = 19.28 + i * 0.15;
    if (t < t0) continue;
    place('fc' + i, { x: 520 + i * 300 + (i === 3 ? 20 : 0), y: 985, s: oBack(P(t, t0, t0 + 0.35), 2.2) });
  }
  if (t >= 19.28) for (let i = 0; i < 4; i++) sparks(t, 19.28 + i * 0.15, gx(520 + i * 300), gy(985), 14, 110, '255,230,150', i * 7);

  const yk = oExpo(P(t, 17.55, 18.1));
  if (t >= 17.55) {
    place('yaml', { x: 1420, y: 610, z: lerp(-700, 0, yk), ry: -12 + Math.sin(t * 0.7) * 1.2, rx: 4, o: P(t, 17.55, 17.7) });
    const n = Math.floor(P(t, 18.0, 20.3) * YTOTAL);
    const caret = Math.floor(t * 4) % 2 === 0 ? '<span style="background:#FFD43B;color:#FFD43B">▍</span>' : '';
    setHTML(document.getElementById('yamlPre'), yamlHTML(n) + caret);
  }
}

// 7 · ship it (21–24)
const STEP_T = i => 21.9 + 0.22 * i;
function s7(t) {
  const ent = oExpo(P(t, 21, 21.4)); G.dy = (1 - ent) * 1300; G.blur = (1 - ent) * 16;
  const ex = iExpo(P(t, 23.72, 24)); G.ds = 1 + ex * 1.6; G.blur += ex * 18; G.o = 1 - ex;

  place('lab7', { x: 570, y: 70 });
  place('ship', { x: 960, y: 150 });
  [21.5, 22.0, 22.5].forEach((t0, i) => styleSlam(document.getElementById('sw' + i), t, t0));
  const cO = { x: 590, y: 610, rx: 4, ry: 12 + Math.sin(t * 0.8) * 1.5, s: 0.62 };
  place('cDist', cO); sheen('cDist', P(t, 21.4, 22.3));

  const prog = clamp((t - STEP_T(0)) / (STEP_T(5) - STEP_T(0)));
  place('plTrack', { x: 1145, y: 485, o: P(t, 21.3, 21.6) });
  document.getElementById('plFill').style.height = (prog * 100).toFixed(1) + '%';
  for (let i = 0; i < 6; i++) {
    const a = oExpo(P(t, 21.3 + i * 0.07, 21.8 + i * 0.07));
    const done = t >= STEP_T(i), active = !done && t >= STEP_T(i) - 0.22;
    const el = place('pl' + i, { x: 1460 + (1 - a) * 220, y: 280 + i * 82, o: a, s: done ? 1 + 0.06 * (1 - oExpo(P(t, STEP_T(i), STEP_T(i) + 0.3))) : 1 });
    const st = el.querySelector('.st');
    setHTML(st, done ? ico('circle-check', '#3ddc97', 30, 2.4) : ico('loader', active ? '#FFD43B' : '#556080', 30));
    st.style.transform = active ? `rotate(${(t * 720) % 360}deg)` : 'none';
    el.style.borderColor = done ? 'rgba(61,220,151,.55)' : 'rgba(255,255,255,.14)';
  }
  if (t >= 22.8) {
    const k = iExpo(P(t, 22.8, 23.0));
    const settle = 1 + 0.08 * Math.sin(P(t, 23.0, 23.35) * Math.PI) * (1 - P(t, 23.0, 23.35));
    place('seal', { x: 860, y: 790, z: 150, rz: -12, s: lerp(3.4, 1, k) * settle, o: k });
  }
  shockwave(t, 23.0, gx(860), gy(790), 600, '61,220,151');
  sparks(t, 23.0, gx(860), gy(790), 30, 300, '170,255,210', 3);
}

// 8 · offline licensing + isolated builds (24–26.5)
const KEY = 'Q7KXM-4RB2P-ZT9WD-H3N6C-8FJ5Y';
const ALPHA = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
function s8(t) {
  const ent = oExpo(P(t, 24, 24.4));
  G.ds = lerp(0.72, 1, ent); G.blur = (1 - ent) * 14; G.o = P(t, 24, 24.1) * (1 - P(t, 26.38, 26.5));

  place('lab8', { x: 570, y: 70 });
  const ck = oExpo(P(t, 24.1, 24.6));
  place('cLic', { x: 960, y: 700 + (1 - ck) * 200, rx: 16, s: 1, o: ck * 0.95 }); sheen('cLic', P(t, 24.6, 25.6));

  let html = '';
  for (let i = 0; i < KEY.length; i++) {
    const c = KEY[i], ts = 24.25 + i * 0.028;
    if (c === '-') { html += '<span style="color:#55607a">-</span>'; continue; }
    if (t < ts) html += `<span style="color:#6b7aa0">${ALPHA[Math.floor(hash(Math.floor(t * 40) * 31 + i) * ALPHA.length)]}</span>`;
    else html += `<span style="color:${t < ts + 0.12 ? '#FFD43B' : '#ffffff'}">${c}</span>`;
  }
  setHTML(document.getElementById('keyText'), html);
  const locked = t >= 25.15;
  const kel = place('key', { x: 960, y: 330, s: oBack(P(t, 24.1, 24.45), 1.8) * (locked ? 1 + 0.05 * (1 - oExpo(P(t, 25.15, 25.45))) : 1) });
  kel.style.borderColor = locked ? 'rgba(255,212,59,.8)' : 'rgba(255,255,255,.14)';
  kel.style.boxShadow = locked ? `0 30px 70px rgba(0,0,0,.55), 0 0 ${lerp(100, 40, P(t, 25.15, 25.8))}px rgba(255,212,59,.45)` : '';
  document.getElementById('keyIco').style.transform = `rotate(${lerp(-90, 0, oBack(P(t, 25.1, 25.4), 2))}deg)`;
  shockwave(t, 25.15, gx(960), gy(330), 700);
  if (t >= 25.2) { place('licCap', { x: 960, y: 455 }); charsIn('licCap', t, 25.2, { st: 0.012, dur: 0.4, dy: 40 }); }
  [520, 960, 1400].forEach((x, i) => { const t0 = 25.6 + i * 0.15; if (t >= t0) place('lc' + i, { x, y: 955, s: oBack(P(t, t0, t0 + 0.35), 2) }); });
}

// 9 · rapid-fire montage + CLI (26.5–28)
const MCAP = ['Themes &amp; settings', 'واجهة عربية كاملة', 'Projects', 'من اليمين لليسار', 'Dark mode', 'Nuitka · عربي'];
const TERM = [
  [27.62, '<span style="color:#7fb8ff">==&gt; [analyzing] 40%</span>'],
  [27.7, '<span style="color:#7fb8ff">==&gt; [pyz] 72%</span>'],
  [27.78, '<span style="color:#7fb8ff">==&gt; [exe] 92%</span>'],
  [27.86, '<span style="color:#3ddc97">✓ dist/notes.exe</span>'],
];
function s9(t) {
  const i = Math.floor((t - 26.5) / 0.125);
  if (i < 6) {
    const lt = (t - 26.5) - i * 0.125;
    const e = E['m' + i];
    place('m' + i, { x: 960 + (i % 2 ? 40 : -40), y: 520, s: e.fit * lerp(0.98, 0.9, lt / 0.125), rz: i % 2 ? 3 : -3, ry: i % 2 ? -12 : 12 });
    setHTML(E.mcap, MCAP[i]);
    place('mcap', { x: 960 + (i % 2 ? -380 : 380), y: 930, rz: i % 2 ? 2 : -2 });
  } else {
    const cmd = '$ py2exe-gui build --strict --yes';
    const n = Math.floor(P(t, 27.27, 27.55) * cmd.length);
    let html = `<span style="color:#FFD43B">${esc(cmd.slice(0, n))}</span>`;
    for (const [t0, l] of TERM) if (t >= t0) html += '\n' + l;
    if (Math.floor(t * 8) % 2 === 0) html += '<span style="color:#FFD43B">▍</span>';
    setHTML(document.getElementById('termPre'), html);
    place('term', { x: 960, y: 540, s: oBack(P(t, 27.25, 27.42), 1.8) * (1 + 0.6 * iExpo(P(t, 27.88, 28))), blur: 14 * iExpo(P(t, 27.88, 28)), o: 1 - iExpo(P(t, 27.9, 28)) });
  }
}

// 10 · end card (28–30)
function s10(t) {
  const out = P(t, 29.8, 30);
  const pop = oBack(P(t, 28.0, 28.45), 2.0);
  glowDot(bg, 960, 380, 420 * pop, '75,139,190', 0.45);
  place('logo', { x: 960, y: 380, s: Math.max(0.001, pop), rz: lerp(-25, 0, oExpo(P(t, 28.0, 28.6))) + Math.sin(t * 1.4) * 1.5, ry: Math.sin(t * 1.1) * 6 });
  document.getElementById('glint').style.left = lerp(-60, 140, ioCubic(P(t, 29.15, 29.6))) + '%';
  shockwave(t, 28.0, 960, 380, 1300);
  sparks(t, 28.0, 960, 380, 48, 800);
  place('endT', { x: 960, y: 600 }); charsIn('endT', t, 28.3, { st: 0.025, dur: 0.5, dy: 90 });
  const tg = oExpo(P(t, 28.75, 29.15)); place('endTag', { x: 960, y: 690 + (1 - tg) * 30, o: tg });
  const u = oExpo(P(t, 29.0, 29.4)); place('endUrl', { x: 960, y: 800 + (1 - u) * 30, o: u });
  blackEl.style.opacity = out;
}

// ================================================================ frame
const SCENES = [[0, 3, s1], [3, 7, s2], [7, 11, s3], [11, 14, s4], [14, 17, s5], [17, 21, s6], [21, 24, s7], [24, 26.5, s8], [26.5, 28, s9], [28, 30.5, s10]];
const FLASHES = [[2.0, 0.55, 0.25], [6.1, 0.12, 0.15], [9.15, 0.12, 0.2], [13.0, 0.25, 0.2], [23.0, 0.3, 0.2], [26.5, 0.4, 0.12], [28.0, 0.75, 0.4]];
const SHAKES = [[2.0, 12], [3, 4], [7, 4], [11, 4], [13.0, 10], [14, 4], [17, 4], [21, 4], [23.0, 16], [24, 4], [25.15, 6], [28.0, 16]];

window.renderFrame = function (t) {
  for (const k in E) E[k].style.display = 'none';
  blackEl.style.opacity = 0;
  fx.clearRect(0, 0, W, H);
  drawBG(t);
  for (const [a, b, fn] of SCENES) if (t >= a && t < b) { resetG(); fn(t); }

  let fl = 0;
  for (const [t0, a, d] of FLASHES) if (t >= t0) fl += a * (1 - P(t, t0, t0 + d));
  flashEl.style.opacity = clamp(fl);

  let sx = 0, sy = 0, zs = 1;
  for (const [t0, a] of SHAKES) if (t >= t0) { const e = Math.exp(-(t - t0) * 9) * a; sx += e * Math.sin((t - t0) * 73 + t0); sy += e * Math.cos((t - t0) * 61 + t0 * 2); }
  if (t > 2 && t < 26.5) { const ph = ((t - 2) % 0.5); zs += 0.007 * Math.exp(-ph * 14); }
  camEl.style.transform = `translate(${sx.toFixed(2)}px,${sy.toFixed(2)}px) scale(${zs.toFixed(4)})`;
  drawGrain(t);
};

window.ready = (async function () {
  await loadIcons();
  buildDOM();
  makeGrain();
  await document.fonts.ready;
  await Promise.all([...document.images].map(img => (img.complete ? Promise.resolve() : img.decode().catch(() => {}))));
  await Promise.all([...document.images].map(img => img.decode().catch(() => {})));
  window.renderFrame(0);
  return true;
})();
