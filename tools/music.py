"""Original ambient piano/pad beds, composed and rendered in code (GeneralUser GS soundfont, license allows commercial use).
No third-party recordings or compositions: the music is Worship Room's own."""
import json, os, subprocess, sys, zlib
import numpy as np, tinysoundfont
from scipy.signal import fftconvolve, butter, sosfilt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
SF = os.path.join(ROOT, 'assets', 'soundfont', 'GeneralUser-GS.sf2')
rng = np.random.default_rng(7)

NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
def n(s):  # 'F#5' -> midi
    name, octv = (s[:-1], int(s[-1]))
    return 12 * (octv + 1) + NOTE[name]

# chord: (bass, [chord tones for arpeggio, low->high], [pad voicing])
# Presets: a video's "music" field picks one. D = warm, F = slow night (sleep/grief), G = open/hopeful.
PIECES = {
    'D': dict(bpm=64, arp='eighths', pad=89, pad_vel=34, strings=None,
        bars=[('D2', ['A2', 'D3', 'F#3', 'A3'], ['D3', 'A3', 'F#4']), ('C#2', ['A2', 'E3', 'A3', 'C#4'], ['C#3', 'A3', 'E4']),
              ('B1', ['F#2', 'B2', 'D3', 'F#3'], ['B2', 'F#3', 'D4']), ('G1', ['D2', 'G2', 'B2', 'D3'], ['G2', 'D3', 'B3'])],
        melody=[[('F#5', 2), ('A5', 2)], [('E5', 4)], [('D5', 2), ('F#5', 2)], [('D5', 2), ('B4', 2)],
                [('A5', 2), ('F#5', 2)], [('E5', 2), ('C#5', 2)], [('F#5', 4)], [('G5', 2), ('E5', 2)]],
        final=('D2', ['A2', 'D3', 'F#3', 'A3'], ['D3', 'A3', 'F#4'], 'D5')),
    'F': dict(bpm=54, arp='quarters', pad=89, pad_vel=44, strings=49,
        bars=[('F2', ['C3', 'F3', 'A3', 'E4'], ['F3', 'C4', 'E4', 'A4']), ('E2', ['C3', 'G3', 'C4', 'E4'], ['E3', 'C4', 'G4']),
              ('D2', ['A2', 'D3', 'F3', 'C4'], ['D3', 'A3', 'C4', 'F4']), ('Bb1', ['F2', 'Bb2', 'D3', 'A3'], ['Bb2', 'F3', 'A3', 'D4'])],
        melody=[[('A5', 4)], [('G5', 4)], [('F5', 4)], [('D5', 4)], [('C6', 2), ('A5', 2)], [('G5', 4)], [('A5', 4)], [('F5', 4)]],
        final=('F2', ['C3', 'F3', 'A3', 'E4'], ['F3', 'C4', 'E4', 'A4'], 'A5')),
    'G': dict(bpm=66, arp='eighths', pad=89, pad_vel=32, strings=49,
        bars=[('G1', ['D2', 'G2', 'B2', 'D3'], ['G2', 'D3', 'B3']), ('F#1', ['D2', 'A2', 'D3', 'F#3'], ['F#2', 'D3', 'A3']),
              ('E2', ['B2', 'E3', 'G3', 'B3'], ['E3', 'B3', 'G4']), ('C2', ['G2', 'C3', 'E3', 'G3'], ['C3', 'G3', 'E4']),
              ('A1', ['E2', 'A2', 'C3', 'E3'], ['A2', 'E3', 'C4']), ('B1', ['D2', 'G2', 'B2', 'D3'], ['B2', 'D3', 'G3']),
              ('C2', ['G2', 'C3', 'E3', 'G3'], ['C3', 'G3', 'E4']), ('D2', ['A2', 'D3', 'G3', 'A3'], ['D3', 'A3', 'G4'])],
        melody=[[('D5', 2), ('B4', 2)], [('A4', 4)], [('B4', 2), ('G4', 2)], [('E5', 2), ('D5', 2)],
                [('C5', 2), ('E5', 2)], [('D5', 4)], [('E5', 4)], [('F#5', 2), ('A5', 2)]],
        final=('G1', ['D2', 'G2', 'B2', 'D3'], ['G2', 'D3', 'B3'], 'B4')),
}


def events_for(p, total):
    beat = 60 / p['bpm']; bar = 4 * beat
    nbars = int(np.ceil((total - 5.0) / bar))  # leave room for the final chord + tail
    ev = []  # (t, chan, key, vel, dur)
    t = 0.4
    for i in range(nbars):
        bass, arp, pad = p['bars'][i % len(p['bars'])]
        mel = p['melody'][i % len(p['melody'])]
        # pad + strings sustain the whole bar (slight overlap for legato)
        for k in pad: ev.append((t, 1, n(k), p['pad_vel'], bar + 0.3))
        if p['strings']:
            for k in pad[:2]: ev.append((t, 2, n(k), 30, bar + 0.3))
        ev.append((t, 0, n(bass), 46, bar))
        if p['arp'] == 'eighths':
            seq = [arp[0], arp[1], arp[2], arp[3], arp[2], arp[1], arp[2], arp[3]]
            step = beat / 2
        else:
            seq = [arp[0], arp[2], arp[3], arp[1]]
            step = beat
        for j, k in enumerate(seq):
            jitter = rng.normal(0, 0.008)
            ev.append((t + j * step + jitter, 0, n(k), int(np.clip(rng.normal(38, 4), 28, 50)), bar - j * step))
        mt = t
        for k, beats in mel:
            ev.append((mt + rng.normal(0, 0.006), 0, n(k), int(np.clip(rng.normal(52, 3), 44, 60)), beats * beat))
            mt += beats * beat
        t += bar
    bass, arp, pad, top = p['final']
    ring = max(total - t, 4.0)
    for k in pad: ev.append((t, 1, n(k), p['pad_vel'], ring))
    if p['strings']:
        for k in pad[:2]: ev.append((t, 2, n(k), 30, ring))
    ev.append((t, 0, n(bass), 44, ring))
    for j, k in enumerate(arp): ev.append((t + j * 0.11, 0, n(k), 36, ring))
    ev.append((t + 0.5, 0, n(top), 48, ring))
    return sorted(ev)


def render(p, total):
    s = tinysoundfont.Synth(samplerate=SR, gain=-6)
    sf = s.sfload(SF)
    s.program_select(0, sf, 0, 0)            # Grand Piano
    s.program_select(1, sf, 0, p['pad'])     # Warm Pad
    if p['strings']: s.program_select(2, sf, 0, p['strings'])
    ev = events_for(p, total)
    offs = sorted([(t + d, ch, k) for t, ch, k, v, d in ev])
    timeline = sorted([(t, 'on', ch, k, v) for t, ch, k, v, d in ev] + [(t, 'off', ch, k, 0) for t, ch, k in offs], key=lambda x: (x[0], x[1] == 'on'))
    N = int((total + 0.5) * SR); out = np.zeros((N, 2), np.float32); pos = 0
    for t, kind, ch, k, v in timeline:
        tgt = min(int(max(t, 0) * SR), N)
        if tgt > pos:
            out[pos:tgt] = np.frombuffer(s.generate(tgt - pos), dtype=np.float32).reshape(-1, 2); pos = tgt
        if kind == 'on': s.noteon(ch, k, v)
        else: s.noteoff(ch, k)
    if pos < N: out[pos:] = np.frombuffer(s.generate(N - pos), dtype=np.float32).reshape(-1, 2)
    return out[:int(total * SR)]


def reverb(x, secs=3.2, wet=0.32):
    L = int(secs * SR); t = np.arange(L) / SR
    ir = np.stack([rng.standard_normal(L), rng.standard_normal(L)], 1) * np.exp(-t / (secs / 6.5))[:, None]
    ir = sosfilt(butter(2, 5500, 'low', fs=SR, output='sos'), ir, axis=0)
    ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    y = np.stack([fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], 1)
    return (1 - wet) * x + wet * y * 0.9


def master(x, total):
    t = np.arange(len(x)) / SR
    env = np.clip(t / 1.2, 0, 1) * np.clip((total - t) / 3.0, 0, 1)
    x = x * env[:, None]
    return x / (np.abs(x).max() + 1e-9) * 0.7


def make(preset, total, wav, seed_key=''):
    """Render preset to a loudness-normalized WAV of exactly `total` seconds."""
    global rng
    rng = np.random.default_rng(zlib.crc32(seed_key.encode()))
    x = master(reverb(render(PIECES[preset], total)), total)
    raw = wav + '.f32'; x.astype(np.float32).tofile(raw)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', raw,
                    '-af', 'highpass=f=75:poles=2,equalizer=f=160:t=q:w=1.0:g=-3,loudnorm=I=-17:TP=-1.5:LRA=11',
                    '-ar', str(SR), wav], check=True)
    os.remove(raw)
