// Render the promo: node render.mjs [--preview t1,t2,...] [--workers N] [--out DIR]
// Serves the repository root over HTTP, drives index.html in headless Chromium
// and pipes frames into ffmpeg. --preview writes PNG stills instead.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const FPS = 60, DUR = 30, TOTAL = FPS * DUR;
const OUT = path.resolve(opt('--out', path.join(HERE, 'out')));
const WORKERS = Number(opt('--workers', 3));
fs.mkdirSync(OUT, { recursive: true });

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.png': 'image/png', '.svg': 'image/svg+xml', '.css': 'text/css' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const URL_ = `http://127.0.0.1:${server.address().port}/promo/index.html`;

const browsers = [];
async function openPage() {
  // one browser per worker: a shared browser process serialises the screenshots
  const browser = await chromium.launch({ args: ['--font-render-hinting=none'] });
  browsers.push(browser);
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('pageerror:', e.message));
  await page.goto(URL_);
  await page.evaluate(() => window.ready);
  return page;
}
const frameAt = async (page, t, type = 'png') => {
  await page.evaluate(t => window.renderFrame(t), t);
  return page.screenshot(type === 'png' ? { type } : { type, quality: 95 });
};

if (args.includes('--preview')) {
  const page = await openPage();
  for (const t of opt('--preview').split(',').map(Number)) {
    fs.writeFileSync(path.join(OUT, `still_${t.toFixed(2)}.png`), await frameAt(page, t));
    console.log('still', t);
  }
} else {
  const per = Math.ceil(TOTAL / WORKERS);
  const t0 = Date.now();
  await Promise.all([...Array(WORKERS)].map(async (_, w) => {
    const a = w * per, b = Math.min(TOTAL, a + per);
    const page = await openPage();
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-r', String(FPS), path.join(OUT, `seg${w}.mp4`)], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let f = a; f < b; f++) {
      const buf = await frameAt(page, f / FPS, 'jpeg');
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if ((f - a) % 60 === 0) console.log(`worker ${w}: frame ${f}/${b} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }));
  fs.writeFileSync(path.join(OUT, 'segments.txt'), [...Array(WORKERS)].map((_, w) => `file 'seg${w}.mp4'`).join('\n') + '\n');
  console.log('frames done in', ((Date.now() - t0) / 1000).toFixed(0), 's');
}
await Promise.all(browsers.map(b => b.close()));
server.close();
