# Promo video

A 30-second, 60 fps motion-graphics promo for Python to EXE Converter, built
from the app's real screenshots in `docs/screenshots/` and the Lucide icons in
`py2exe_gui/icons/`.

| File | What it does |
|---|---|
| `index.html`, `promo.js` | The animation. Every frame is a pure function of time: `window.renderFrame(t)` |
| `render.mjs` | Serves the repo locally, drives headless Chromium (Playwright) and pipes frames into ffmpeg |
| `music.py` | The 120 BPM soundtrack and the sound effects cued to the animation (numpy only) |

## Build

Requires Node with Playwright, Chromium, ffmpeg and Python 3 with numpy.

```bash
cd promo
node render.mjs --workers 3              # out/seg*.mp4 + out/segments.txt
python3 music.py out/audio.wav
ffmpeg -f concat -safe 0 -i out/segments.txt -i out/audio.wav \
       -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart out/promo.mp4
```

Stills for checking a moment: `node render.mjs --preview 2.3,9.6,23.1`.

## Storyboard

| Time | Scene |
|---|---|
| 0–3 s | A snake of light collapses into a `.py` file that flips into `.exe` on the drop |
| 3–7 s | 01 One-click build: the cursor presses Start Build, the progress bar pops out and fills |
| 7–11 s | 02 Project doctor: three issues get fixed, readiness climbs to 100/100 |
| 11–14 s | 03 Size lab: 30.1 MB → 14.2 MB (−53%), the README's Pillow example |
| 14–17 s | 04 Two engines: PyInstaller vs Nuitka, figures from the compare screenshot |
| 17–21 s | 05 Every platform: `.exe`, `.dmg`, `.AppImage`, `.deb` and the generated CI workflow |
| 21–24 s | 06 Ship it: the release pipeline and the signed installer |
| 24–26.5 s | 07 Offline licensing, isolated builds, lock file, bilingual UI |
| 26.5–28 s | Rapid montage (English and Arabic screens) and the headless CLI |
| 28–30 s | End card with the repository link |
