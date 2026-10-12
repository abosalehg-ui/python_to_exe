"""Soundtrack for the promo: a 120 BPM electronic track plus sound effects
cued to the animation in promo.js. Pure numpy, deterministic.

    python3 music.py out/audio.wav
"""
import sys
import wave

import numpy as np

SR = 48000
DUR = 30.0
N = int(SR * DUR)
BEAT = 0.5  # 120 BPM
rng = np.random.default_rng(7)

L, R = np.zeros(N), np.zeros(N)          # dry bus
SL, SRv = np.zeros(N), np.zeros(N)       # reverb send


def ts(n):
    return np.arange(n) / SR


def add(sig, t, g=1.0, pan=0.0, send=0.0):
    """Mix a mono signal (or an (l, r) pair) in at second t."""
    if isinstance(sig, tuple):
        sl, sr = sig
    else:
        sl = sr = sig
    i = int(round(t * SR))
    if i >= N:
        return
    if i < 0:
        sl, sr, i = sl[-i:], sr[-i:], 0
    n = min(len(sl), N - i)
    lg = np.cos((pan + 1) * np.pi / 4) * 1.4142
    rg = np.sin((pan + 1) * np.pi / 4) * 1.4142
    L[i:i + n] += sl[:n] * g * lg
    R[i:i + n] += sr[:n] * g * rg
    if send:
        SL[i:i + n] += sl[:n] * g * lg * send
        SRv[i:i + n] += sr[:n] * g * rg * send


def mask(f, lo, hi):
    m = np.ones_like(f)
    if lo:
        m *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** 4)
    if hi:
        m *= 1 / (1 + (f / hi) ** 4)
    return m


def filt(x, lo=0, hi=None):
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(np.fft.rfft(x) * mask(f, lo, hi), len(x))


def tv_filter(x, fn, win=1024, hop=256):
    """Time-varying band filter; fn(seconds) -> (lo, hi)."""
    n = len(x)
    out, wsum = np.zeros(n + win), np.zeros(n + win)
    w = np.hanning(win)
    f = np.fft.rfftfreq(win, 1 / SR)
    for s in range(0, n, hop):
        seg = np.zeros(win)
        chunk = x[s:s + win]
        seg[:len(chunk)] = chunk
        lo, hi = fn(s / SR)
        out[s:s + win] += np.fft.irfft(np.fft.rfft(seg * w) * mask(f, lo, hi), win) * w
        wsum[s:s + win] += w * w
    return out[:n] / np.maximum(wsum[:n], 1e-3)


def noise(d):
    return rng.standard_normal(int(d * SR))


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def saw(freq, n, cutoff=3000):
    t = ts(n)
    s = np.zeros(n)
    k = 1
    while k * freq < cutoff and k < 80:
        s += np.sin(2 * np.pi * k * freq * t + k * 0.7) / k
        k += 1
    return s


# ------------------------------------------------------------------ instruments
def kick(d=0.45):
    n = int(d * SR)
    t = ts(n)
    f = 44 + 115 * np.exp(-t * 30)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    s += rng.standard_normal(n) * np.exp(-t * 400) * 0.25
    return np.tanh(s * 1.6)


def clap():
    n = int(0.35 * SR)
    t = ts(n)
    nz = filt(rng.standard_normal(n), 900, 6000)
    env = np.zeros(n)
    for o in (0.0, 0.010, 0.021):
        i = int(o * SR)
        env[i:] += np.exp(-t[:n - i] * 95)
    i = int(0.021 * SR)
    env[i:] += 0.45 * np.exp(-t[:n - i] * 16)
    return nz * env * 0.6


def hat(d=0.06, open_=False):
    n = int((0.25 if open_ else d) * SR)
    t = ts(n)
    return filt(rng.standard_normal(n), 7000, None) * np.exp(-t * (14 if open_ else 70))


def snare():
    n = int(0.2 * SR)
    t = ts(n)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return (filt(rng.standard_normal(n), 1500, 9000) * np.exp(-t * 24) + 0.5 * body) * 0.7


def pluck(f, d=0.22):
    n = int(d * SR)
    t = ts(n)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return s * np.exp(-t * 17) * np.minimum(1, t * 500)


def bass_note(f, d=0.22):
    n = int(d * SR)
    t = ts(n)
    s = filt(saw(f, n, 1800), 0, 900) * 0.6 + np.sin(2 * np.pi * f * t)
    env = np.minimum(1, t * 300) * np.minimum(1, (d - t) * 60) * (0.75 + 0.25 * np.exp(-t * 12))
    return np.tanh(s * env * 1.4)


def boom(d=1.4, f0=62, f1=30):
    n = int(d * SR)
    t = ts(n)
    f = f1 + (f0 - f1) * np.exp(-t * 6)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    s += filt(rng.standard_normal(n), 0, 400) * np.exp(-t * 9) * 0.6
    return np.tanh(s * 1.8)


def crash(d=1.6):
    n = int(d * SR)
    t = ts(n)
    return filt(rng.standard_normal(n), 3500, None) * np.exp(-t * 3.2) * 0.5


def blip(f0, f1, d=0.07):
    n = int(d * SR)
    t = ts(n)
    f = f0 * (f1 / f0) ** (t / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 40) * np.minimum(1, t * 2000)


def bell(freqs, d=0.9, decay=5.0):
    n = int(d * SR)
    t = ts(n)
    s = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * decay * (1 + i * 0.6)) / (1 + i) for i, f in enumerate(freqs))
    return s * np.minimum(1, t * 800)


def click():
    n = int(0.03 * SR)
    t = ts(n)
    return (np.sin(2 * np.pi * 2400 * t) * 0.6 + filt(rng.standard_normal(n), 2000, None)) * np.exp(-t * 260)


def whoosh(d=0.45):
    x = noise(d)
    peak = 0.72

    def band(s):
        k = s / d
        c = 300 + 5200 * (np.sin(np.pi * min(k / peak, 1) / 2) if k < peak else 1 - (k - peak) / (1 - peak) * 0.6)
        return c / 2.2, c * 1.6
    y = tv_filter(x, band)
    t = ts(len(x))
    env = np.where(t < d * peak, (t / (d * peak)) ** 2, np.exp(-(t - d * peak) * 18))
    return y * env * 0.9


def riser(d, lo=250, hi=9000):
    x = noise(d)
    y = tv_filter(x, lambda s: (lo * 0.5, lo * (hi / lo) ** (s / d)))
    t = ts(len(x))
    sweep = np.sin(2 * np.pi * np.cumsum(220 * (6 ** (t / d))) / SR) * 0.25
    return (y * 0.8 + sweep) * (t / d) ** 2


# ------------------------------------------------------------------ music
CHORDS = {  # pad voicing, bass root
    'Am': ([57, 60, 64], 33), 'F': ([53, 57, 60], 29), 'C': ([52, 55, 60], 36), 'G': ([50, 55, 59], 31)}
PROG = ['Am', 'F', 'C', 'G']


def chord_at(t):
    if t < 2.0:
        return 'Am'
    return PROG[int((t - 2.0) // 2.0) % 4]


kicks = [2.0 + i * BEAT for i in range(int((27.0 - 2.0) / BEAT))] + [28.0]
for k in kicks:
    add(kick(), k, 0.95)

# sidechain envelope from the kicks
sc = np.ones(N)
for k in kicks:
    i = int(k * SR)
    m = min(int(0.42 * SR), N - i)
    sc[i:i + m] = np.minimum(sc[i:i + m], 1 - 0.7 * np.exp(-ts(m) * 9))

for i in range(int((26.5 - 2.0) / BEAT)):
    t = 2.0 + i * BEAT
    if i % 2 == 1:
        add(clap(), t, 0.55, send=0.35)
    add(hat(), t + 0.25, 0.22, pan=0.25)
    if t >= 7.0:
        add(hat(0.03), t + 0.125, 0.09, pan=-0.3)
        add(hat(0.03), t + 0.375, 0.09, pan=-0.3)
    if i % 8 == 7:
        add(hat(open_=True), t + 0.25, 0.12, pan=0.3)
    add(bass_note(midi(CHORDS[chord_at(t)][1])), t + 0.25, 0.42)
    if t >= 14.0:
        add(bass_note(midi(CHORDS[chord_at(t)][1] + 12), 0.1), t + 0.375, 0.16)

# arpeggio with ping-pong delay
arpL, arpR = np.zeros(N), np.zeros(N)
PAT = [0, 2, 1, 3, 2, 1, 3, 2]
for i in range(int((26.5 - 3.0) / 0.125)):
    t = 3.0 + i * 0.125
    notes, _ = CHORDS[chord_at(t)]
    tones = [notes[0] + 12, notes[1] + 12, notes[2] + 12, notes[0] + 24]
    s = pluck(midi(tones[PAT[i % 8]]))
    j = int(t * SR)
    n = min(len(s), N - j)
    acc = 1.0 if i % 4 == 0 else 0.7
    arpL[j:j + n] += s[:n] * acc
    arpR[j:j + n] += s[:n] * acc
d = int(0.375 * SR)
eL, eR = arpL.copy(), arpR.copy()
for k in range(1, 5):
    g = 0.38 ** k
    src = arpL if k % 2 else arpR
    if k % 2:
        eR[d * k:] += src[:N - d * k] * g
    else:
        eL[d * k:] += src[:N - d * k] * g
eL *= 0.6 + 0.4 * sc
eR *= 0.6 + 0.4 * sc
add((eL, eR), 0, 0.12, send=0.5)

# pad: detuned saws per chord, filter opens through the intro, ducked by the kick
padL, padR = np.zeros(N), np.zeros(N)
segs = [(0.0, 2.0, 'Am')] + [(2.0 + i * 2.0, 2.0, PROG[i % 4]) for i in range(13)]
for start, dur, name in segs:
    notes, _ = CHORDS[name]
    n = int((dur + 0.4) * SR)
    t = ts(n)
    env = np.minimum(1, t / 0.08) * np.minimum(1, np.maximum(0, (dur + 0.4 - t) / 0.4))
    vl = sum(saw(midi(m) * 2 ** (-8 / 1200), n, 2600) for m in notes)
    vr = sum(saw(midi(m) * 2 ** (8 / 1200), n, 2600) for m in notes)
    j = int(start * SR)
    n = min(n, N - j)
    padL[j:j + n] += (vl * env)[:n]
    padR[j:j + n] += (vr * env)[:n]
# the end chord: a long Am that rings out
n = int(2.0 * SR)
t = ts(n)
env = np.minimum(1, t / 0.02) * np.exp(-t * 1.1)
padL[int(28 * SR):] += (sum(saw(midi(m) * 2 ** (-8 / 1200), n, 3200) for m in [45, 57, 60, 64, 69]) * env)[:N - int(28 * SR)]
padR[int(28 * SR):] += (sum(saw(midi(m) * 2 ** (8 / 1200), n, 3200) for m in [45, 57, 60, 64, 69]) * env)[:N - int(28 * SR)]


def pad_cut(s):
    if s < 2.0:
        return 0, 300 * (12 ** (s / 2.0))
    if 26.5 <= s < 28.0:
        return 0, 3600 * (0.25 ** ((s - 26.5) / 1.5))
    return 0, 3600


padL = tv_filter(padL, pad_cut) * (0.55 + 0.45 * sc)
padR = tv_filter(padR, pad_cut) * (0.55 + 0.45 * sc)
add((padL, padR), 0, 0.07, send=0.3)

# build-up into the end card: snare roll and riser
roll = [26.5 + i * 0.25 for i in range(2)] + [27.0 + i * 0.125 for i in range(4)] + [27.5 + i * 0.0625 for i in range(8)]
for i, t in enumerate(roll):
    add(snare(), t, 0.25 + 0.5 * i / len(roll), send=0.2)
add(riser(1.5, 400, 10000), 26.5, 0.35, send=0.2)
add(crash(0.9)[::-1], 27.1, 0.5)

# ------------------------------------------------------------------ sound design cues
add(riser(1.75), 0.25, 0.4, send=0.3)
for t, g in [(2.0, 1.0), (28.0, 1.1)]:
    add(boom(), t, g, send=0.4)
    add(crash(), t, 0.7, send=0.5)
for T in [3, 7, 11, 14, 17, 21, 24]:
    add(whoosh(), T - 0.33, 0.55, pan=0.4 if T % 2 else -0.4, send=0.2)
    add(boom(0.6, 80, 40), T, 0.35)
add(whoosh(0.3), 26.2, 0.4, send=0.2)

add(click(), 4.45, 0.7)                                               # cursor clicks Start Build
for i in range(14):                                                   # progress ticks
    add(blip(900 + i * 60, 1000 + i * 60, 0.03), 4.95 + i * 0.08, 0.06, pan=0.3)
add(bell([1760, 2637, 3520], 1.2), 6.1, 0.3, send=0.5)                # build done
add(boom(0.5, 90, 45), 6.15, 0.4)                                     # "Done."

for i in range(3):
    add(blip(500, 900), 7.45 + i * 0.1, 0.18, pan=0.5)                # issues slide in
for t, f in [(8.3, 1320), (8.7, 1568)]:
    add(bell([f, f * 1.5], 0.5, 8), t, 0.18, send=0.4)                # each fix
for i, f in enumerate([1047, 1319, 1568, 2093]):
    add(bell([f], 0.8, 6), 9.15 + i * 0.05, 0.16, send=0.5)           # readiness 100
for i in range(16):
    add(blip(1200, 1400, 0.025), 7.35 + i * 0.037, 0.04, pan=0.4)     # score counting up

for i in range(4):
    add(blip(300 + i * 120, 600 + i * 150, 0.09), 11.05 + i * 0.12, 0.16)  # donut segments
for t in (12.0, 12.25):
    add(filt(noise(0.25), 800, 6000) * np.exp(-ts(int(0.25 * SR)) * 18), t, 0.35, send=0.3)
    add(blip(900, 200, 0.18), t, 0.2)
for i in range(18):
    add(blip(1500, 1300, 0.02), 12.0 + i * 0.05, 0.035, pan=-0.3)    # counter going down
add(boom(0.8, 100, 45), 13.0, 0.55)
add(crash(0.6), 13.0, 0.3, send=0.3)

for i in range(3):
    add(blip(700, 1100, 0.04), 14.6 + i * 0.08, 0.12, pan=-0.4)
    add(blip(700, 1100, 0.04), 14.64 + i * 0.08, 0.12, pan=0.4)
add(bell([1568, 2349], 0.6, 7), 15.15, 0.18, send=0.4)
add(whoosh(0.4), 15.3, 0.3, send=0.2)

for t in (17.15, 17.5, 17.85):                                        # Windows. macOS. Linux.
    add(boom(0.35, 110, 55), t, 0.45)
    add(filt(noise(0.08), 2000, None) * np.exp(-ts(int(0.08 * SR)) * 50), t, 0.25)
for i in range(3):
    add(blip(600, 1200), 17.3 + i * 0.15, 0.14, pan=-0.5 + i * 0.5)
for i in range(40):                                                   # YAML typing
    add(click(), 18.0 + i * 0.0575 + (i * 37 % 7) * 0.004, 0.07, pan=0.5)
for i in range(4):
    add(blip(800 + i * 200, 1600 + i * 300, 0.08), 19.28 + i * 0.15, 0.2, pan=-0.45 + i * 0.3)

for t in (21.5, 22.0, 22.5):                                          # Sign. Package. Release.
    add(boom(0.35, 110, 55), t, 0.45)
    add(filt(noise(0.08), 2000, None) * np.exp(-ts(int(0.08 * SR)) * 50), t, 0.25)
for i in range(6):
    add(blip(1000 + i * 150, 1300 + i * 180, 0.05), 21.9 + 0.22 * i, 0.14, pan=0.4)
add(boom(1.0, 70, 35), 23.0, 0.9, send=0.3)                           # the SIGNED stamp
add(crash(0.9), 23.0, 0.45, send=0.4)

for i in range(27):                                                   # licence key scramble
    add(blip(2000 + (i * 397 % 900), 2200 + (i * 211 % 700), 0.02), 24.25 + i * 0.03, 0.05, pan=(i % 3 - 1) * 0.4)
add(bell([2637, 3729, 4699], 0.7, 7), 25.15, 0.22, send=0.5)          # key locks
add(boom(0.5, 90, 45), 25.15, 0.35)
for i in range(3):
    add(blip(600, 1000), 25.6 + i * 0.15, 0.15, pan=-0.5 + i * 0.5)

for i in range(6):                                                    # montage cuts
    add(filt(noise(0.05), 1500, None) * np.exp(-ts(int(0.05 * SR)) * 90), 26.5 + i * 0.125, 0.3, pan=(-1) ** i * 0.4)
for i in range(12):
    add(click(), 27.27 + i * 0.024, 0.08)
for t in (27.62, 27.7, 27.78):
    add(blip(1200, 1500, 0.03), t, 0.1)
add(bell([1760, 2637], 0.4, 9), 27.86, 0.15)

for i in range(10):                                                   # logo glint shimmer
    add(bell([3000 + i * 400], 0.4, 10), 29.15 + i * 0.04, 0.05, pan=-0.6 + i * 0.13, send=0.6)

# ------------------------------------------------------------------ reverb + master
def reverb(x, seed):
    r = np.random.default_rng(seed)
    n = int(1.8 * SR)
    t = ts(n)
    ir = filt(r.standard_normal(n), 200, 7000) * np.exp(-t / 0.42)
    ir /= np.sqrt(np.sum(ir ** 2))
    m = 1 << int(np.ceil(np.log2(len(x) + n)))
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)]


outL = L + reverb(SL, 1) * 0.5
outR = R + reverb(SRv, 2) * 0.5
peak = max(np.abs(outL).max(), np.abs(outR).max())
outL, outR = outL / peak * 1.3, outR / peak * 1.3
outL, outR = np.tanh(outL) / np.tanh(1.3), np.tanh(outR) / np.tanh(1.3)
fade = np.ones(N)
fade[:int(0.01 * SR)] = np.linspace(0, 1, int(0.01 * SR))
fade[-int(0.25 * SR):] = np.linspace(1, 0, int(0.25 * SR))
outL, outR = outL * fade * 0.89, outR * fade * 0.89

data = (np.stack([outL, outR], axis=1) * 32767).astype('<i2')
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'audio.wav', 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(data.tobytes())
print('wrote', len(data) / SR, 's')
