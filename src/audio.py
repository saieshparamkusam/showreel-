"""Original, fully synthesised soundtrack + sound design (no samples, no voiceover).

120 BPM, A minor (Am - F - C - G). Hits/whooshes are generated from the same TIMELINE the
picture uses, so every cut has a matching sound. Output: out/audio.wav (48 kHz stereo, 60.000 s).
"""
import os, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
DUR = 60.0
N = int(SR * DUR)
BEAT = 0.5
rng = np.random.default_rng(7)

dry = np.zeros((2, N), np.float32)     # direct bus
wet = np.zeros((2, N), np.float32)     # reverb send
dly = np.zeros((2, N), np.float32)     # delay send
duck = np.ones(N, np.float32)          # sidechain envelope for pads/bass

def add(bus, x, t, pan=0.0, gain=1.0):
    i = int(round(t * SR))
    if i >= N or i + len(x) <= 0:
        return
    a = max(0, -i)
    j = min(len(x), N - i)
    l = np.cos((pan + 1) * np.pi / 4) * gain
    r = np.sin((pan + 1) * np.pi / 4) * gain
    bus[0, i + a:i + j] += x[a:j] * l
    bus[1, i + a:i + j] += x[a:j] * r

def tt(d):
    return np.arange(int(SR * d)) / SR

def env_exp(d, k):
    return np.exp(-tt(d) * k)

def hp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, "hp", fs=SR, output="sos"), x)

def lp(x, f, o=2):
    return signal.sosfilt(signal.butter(o, f, "lp", fs=SR, output="sos"), x)

def bp(x, f0, f1, o=2):
    return signal.sosfilt(signal.butter(o, [f0, f1], "bp", fs=SR, output="sos"), x)

def noise(d):
    return rng.standard_normal(int(SR * d)).astype(np.float32)

def hz(note):  # MIDI note -> Hz
    return 440.0 * 2 ** ((note - 69) / 12)

# ---------------------------------------------------------------- instruments
def kick(vel=1.0, punch=1.0):
    t = tt(0.5)
    f = 46 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 7.5)
    x += 0.35 * np.sin(2 * np.pi * 900 * t) * np.exp(-t * 400) * punch
    return (np.tanh(x * 1.6) * vel).astype(np.float32)

def sub_hit(d=2.2, f0=58, f1=30):
    t = tt(d)
    f = f1 + (f0 - f1) * np.exp(-t * 4)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 1.9)
    n = lp(noise(d), 600) * np.exp(-t * 6) * 0.5
    return np.tanh((x + n) * 1.4).astype(np.float32)

def hat(open_=False, vel=0.5):
    d = 0.28 if open_ else 0.06
    x = hp(noise(d), 7000, 3) * env_exp(d, 14 if open_ else 70)
    return (x * vel).astype(np.float32)

def clap(vel=0.7):
    d = 0.35
    t = tt(d)
    n = bp(noise(d), 900, 3800)
    e = np.exp(-t * 18) * 0.6
    for off in (0.0, 0.011, 0.022):
        e += np.where(t >= off, np.exp(-(t - off) * 150), 0) * 1.0
    return (n * e * vel).astype(np.float32)

def snare(vel=0.7):
    d = 0.3
    t = tt(d)
    body = np.sin(2 * np.pi * (190 + 60 * np.exp(-t * 40)) * t) * np.exp(-t * 22)
    n = hp(noise(d), 1800) * np.exp(-t * 20)
    return ((body * 0.6 + n * 0.7) * vel).astype(np.float32)

def tick(vel=0.5, f=2400):
    d = 0.05
    t = tt(d)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 120) * vel + hp(noise(d), 3000) * np.exp(-t * 150) * vel * 0.4).astype(np.float32)

def sweep(d, f0, f1, shape=2.0, rev=False, q=0.9, vel=0.6):
    """Filtered noise whoosh: low-pass cutoff glides f0->f1; amplitude swells to the end (rev) or peaks mid."""
    n = int(SR * d)
    x = noise(d)
    out = np.zeros(n, np.float32)
    blk = 512
    zi = None
    for i in range(0, n, blk):
        u = i / n
        fc = f0 * (f1 / f0) ** (u ** (1 / shape))
        sos = signal.butter(2, [max(80, fc * 0.45), min(SR / 2 - 100, fc * 1.35)], "bp", fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        y, zi = signal.sosfilt(sos, x[i:i + blk], zi=zi)
        out[i:i + blk] = y
    u = np.linspace(0, 1, n)
    amp = u ** 2.2 if rev else np.sin(np.pi * u ** 0.7) ** 1.5
    return (out * amp * vel * 3.0).astype(np.float32)

def riser(d, f0=300, f1=9000, vel=0.5):
    x = sweep(d, f0, f1, shape=1.6, rev=True, vel=vel)
    t = tt(d)
    tone = np.sin(2 * np.pi * np.cumsum(120 * 2 ** (t / d * 3)) / SR) * (t / d) ** 3 * 0.12 * vel
    return (x + tone).astype(np.float32)

def pad(chord, d, vel=0.25, bright=0.5):
    t = tt(d)
    out = np.zeros_like(t)
    for m in chord:
        for det in (-0.07, 0.0, 0.07):
            f = hz(m + det)
            for k in range(1, 9):
                if f * k > 7000:
                    break
                out += np.sin(2 * np.pi * f * k * t + k * 1.3 + det * 40) / (k ** (1.3 - bright * 0.6))
    a = np.minimum(1, t / 0.9)
    r = np.minimum(1, (d - t) / 0.9)
    return (out * a * r * vel / (len(chord) * 3)).astype(np.float32)

def pluck(m, vel=0.3, d=0.5):
    t = tt(d)
    f = hz(m)
    x = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) * np.exp(-t * 14) + 0.25 * np.sin(6 * np.pi * f * t) * np.exp(-t * 20))
    return (x * np.exp(-t * 9) * vel).astype(np.float32)

def bass(m, d=0.38, vel=0.55):
    t = tt(d)
    f = hz(m)
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    x = np.tanh(x * 1.8) * np.minimum(1, t / 0.006) * np.exp(-t * 5)
    return (x * vel).astype(np.float32)

def bell(m, vel=0.25, d=1.6):
    t = tt(d)
    f = hz(m)
    x = np.zeros_like(t)
    for ratio, a in ((1, 1.0), (2.01, 0.5), (2.76, 0.35), (5.4, 0.15)):
        x += a * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t * (3 + ratio * 1.2))
    x *= np.minimum(1, t / 0.003)
    return (x * vel).astype(np.float32)

# ---------------------------------------------------------------- score
CHORDS = [[57, 60, 64], [53, 57, 60], [48, 55, 60, 64], [55, 59, 62]]      # Am F C G (pad voicings)
ROOTS = [33, 29, 36, 31]                                                    # A1 F1 C2 G1 (bass)
ARP = [[69, 72, 76, 72], [65, 69, 72, 69], [72, 76, 79, 76], [67, 71, 74, 71]]

def kicks_at(times, vel=0.9, punch=1.0):
    k = kick(vel, punch)
    for t0 in times:
        add(dry, k, t0, 0, 1.0)
        i0 = int(t0 * SR); i1 = min(N, i0 + int(0.28 * SR))
        n = i1 - i0
        if n > 0:
            duck[i0:i1] = np.minimum(duck[i0:i1], 0.35 + 0.65 * (np.arange(n) / n) ** 0.7)

def build():
    from shots import TIMELINE
    # ---- pads (whole piece, per bar), level follows the arc
    def pad_level(t):
        if t < 4: return 0.0
        if t < 9: return 0.55
        if t < 36: return 0.65
        if t < 49: return 0.55
        if t < 55: return 0.5
        return 0.8
    for bar in range(30):
        t0 = bar * 2.0
        lv = pad_level(t0 + 1)
        if lv <= 0:
            continue
        ch = CHORDS[bar % 4]
        p = pad(ch, 2.9, vel=0.9 * lv, bright=0.4 + 0.5 * (t0 > 36))
        pp = np.zeros((2, N), np.float32)
        add(pp, p, t0, 0, 1.0)
        dry_pad[0] += pp[0]; dry_pad[1] += pp[1]
        add(wet, p, t0, 0, 0.35)

    # ---- drums / bass / arp by section
    for beat in range(120):
        t = beat * BEAT
        bar_b = beat % 4
        bar = beat // 4
        # kick
        if 9 <= t < 36:
            if t >= 22 or bar_b in (0, 2) or t >= 13:
                kicks_at([t], 0.62 if t < 22 else 0.8)
        elif 36 <= t < 48.5:
            kicks_at([t], 0.9)
        elif 49 <= t < 55:
            kicks_at([t], 1.0, 1.3)
        elif 6 <= t < 9 and bar_b == 0:
            kicks_at([t], 0.5)
        # clap / snare on 2 & 4
        if bar_b in (1, 3):
            if 13 <= t < 36:
                add(dry, clap(0.5 if t < 22 else 0.65), t, 0.05, 1.0); add(wet, clap(0.5), t, 0, 0.25)
            elif 36 <= t < 47 or 49 <= t < 53:
                add(dry, snare(0.75), t, 0, 1.0); add(dry, clap(0.7), t, 0.1, 0.8); add(wet, clap(0.6), t, 0, 0.3)
        # hats
        if 7 <= t < 55:
            dens = 2 if t < 36 or 47 <= t < 49 else 4
            for k in range(dens):
                tk = t + k * BEAT / dens
                if tk >= 49 and tk < 55 or tk < 55:
                    accent = 1.0 if k % 2 == 0 else 0.6
                    if dens == 2 and k == 1:   # off-beat open hat
                        add(dry, hat(True, 0.30 if t < 36 else 0.4), tk, 0.25, 1.0)
                    else:
                        add(dry, hat(False, 0.32 * accent if t < 36 else 0.42 * accent), tk, (-0.2 if k % 2 else 0.2), 1.0)
        # bass: off-beat 8ths
        if (9 <= t < 36 and t >= 14) or 36 <= t < 49 or 49 <= t < 55:
            root = ROOTS[bar % 4]
            for k, off in enumerate((0.0, 0.75, 1.0, 1.5)):
                pass
        # arp
        if 4.5 <= t < 55:
            notes = ARP[bar % 4]
            sub = 2 if t < 36 else 4
            lvl = 0.16 if t < 22 else (0.22 if t < 36 else 0.26)
            for k in range(sub):
                tk = t + k * BEAT / sub
                if tk >= 55: break
                m = notes[(beat * sub + k) % 4]
                if t < 9 and (beat % 2): continue
                pl = pluck(m, lvl)
                pan = -0.45 + 0.9 * ((k + beat) % 3) / 2
                add(dry, pl, tk, pan, 1.0); add(dly, pl, tk, pan, 0.55); add(wet, pl, tk, 0, 0.3)
    # bass line (8th pattern) in sections
    for bar in range(30):
        t0 = bar * 2.0
        if not ((t0 >= 14 and t0 < 55)):
            continue
        root = ROOTS[bar % 4]
        pat = (0.0, 0.75, 1.0, 1.5, 1.75) if t0 >= 22 else (0.0, 1.0)
        for off in pat:
            m = root + (12 if off in (0.75, 1.75) else 0)
            add(bass_bus, bass(m, 0.36, 0.7 if t0 < 49 else 0.85), t0 + off, 0, 1.0)

    # ---- hook (0-4): impact at 0, riser to 2.0, hit at 2.0, build to 4.0
    add(dry, sub_hit(2.6, 62, 30), 0.0, 0, 1.0)
    add(dry, tick(0.9, 1800), 0.0, 0, 1.0)
    add(wet, sub_hit(1.0, 80, 40), 0.0, 0, 0.5)
    add(dry, riser(1.75, 400, 8000, 0.45), 0.25, 0, 1.0)
    add(dry, sub_hit(1.8, 56, 32), 2.0, 0, 0.9)
    add(dry, clap(0.7), 2.0, 0, 0.8); add(wet, clap(0.7), 2.0, 0, 0.4)
    add(dry, riser(1.4, 500, 9000, 0.4), 2.55, 0, 1.0)

    # ---- transitions: whoosh ending at the cut + hit on the cut
    for i, (cut, tr, d, fn) in enumerate(TIMELINE):
        if i < 2 or d <= 0:
            continue
        if cut >= 36 and cut < 49 and tr == "cut":
            continue
        dd = max(d, 0.28)
        vol = 0.45 if cut < 36 else 0.6
        add(dry, sweep(dd * 1.5, 700, 7500, 1.4, vel=vol), cut - dd * 1.5, 0, 1.0)
        add(wet, sweep(dd * 1.5, 700, 7500, 1.4, vel=vol * 0.5), cut - dd * 1.5, 0, 1.0)
        hit = sub_hit(0.9, 70, 38) * (0.55 if cut < 36 else 0.8)
        add(dry, hit, cut, 0, 1.0)
        add(dry, tick(0.5, 2000), cut, 0, 1.0)

    # identity (4-9): soft impact + sparkles on text reveals
    add(dry, sub_hit(1.8, 52, 32), 4.0, 0, 0.7)
    add(dry, riser(0.7, 500, 6000, 0.3), 3.3, 0, 1.0)
    for ts, m in ((4.05, 76), (4.19, 79), (4.9, 83), (5.3, 88), (6.3, 84), (6.6, 88), (6.9, 91), (7.2, 95)):
        pass
    for ts, m in ((4.6, 81), (4.74, 88), (4.95, 93), (5.85, 84), (6.5, 88), (6.78, 91), (7.06, 93), (7.34, 96)):
        add(dry, bell(m, 0.20), ts, rng.uniform(-0.5, 0.5), 1.0); add(wet, bell(m, 0.2), ts, 0, 0.7)

    # chapter pills (soft ticks) and craft chimes
    for ts in (9.3, 11.3, 13.3, 15.3, 22.35, 24.3, 26.3, 28.35, 30.4):
        add(dry, bell(88, 0.12, 0.9), ts, rng.uniform(-0.4, 0.4), 1.0)
    # tagline / services reveals
    for ts in (20.2, 20.34, 20.48):
        add(dry, bell(91 + int((ts - 20.2) * 20), 0.14, 1.0), ts, 0.0, 1.0)
    for k, ts in enumerate((32.3, 32.45, 32.6, 32.75)):
        add(dry, bell(84 + k * 3, 0.12, 0.9), ts, -0.3 + 0.2 * k, 1.0)

    # build into montage: riser 33.9-36, then hit at 36
    add(dry, riser(2.0, 300, 10000, 0.5), 34.0, 0, 1.0)
    add(dry, sub_hit(1.4, 60, 32), 36.0, 0, 0.9)
    add(dry, clap(0.8), 36.0, 0, 1.0)

    # montage cuts: accents locked to every cut
    for k in range(8):                      # M1: every beat 36-40
        tc = 36.0 + k * 0.5
        add(dry, tick(0.5, 1500 + 150 * (k % 4)), tc, (-1) ** k * 0.3, 1.0)
        add(dry, sweep(0.22, 1200, 6000, 1.2, vel=0.28), tc - 0.14, 0, 1.0)
    for k in range(16):                     # M2: every 0.25 s 40-44
        tc = 40.0 + k * 0.25
        add(dry, tick(0.42, 1800 + 120 * (k % 6)), tc, (-1) ** k * 0.45, 1.0)
    # rows (44-47): sweeping whoosh with pitch ramp
    add(dry, sweep(3.0, 400, 6500, 1.0, vel=0.5), 44.0, 0, 1.0)
    add(dry, sub_hit(1.0, 64, 34), 44.0, 0, 0.7)
    # snare roll into drop (47-49): accelerating
    t = 47.0
    step = 0.25
    while t < 48.75:
        add(dry, snare(0.45 + 0.4 * (t - 47) / 1.75), t, 0, 1.0)
        step = max(0.0625, step * 0.86)
        t += step
    add(dry, riser(2.0, 400, 12000, 0.65), 47.0, 0, 1.0)
    for k in range(4):                      # triptych cuts
        add(dry, sub_hit(0.5, 80, 45), 47.0 + k * 0.5, 0, 0.55)
    # DROP at 49.0
    add(dry, sub_hit(2.8, 64, 28), 49.0, 0, 1.15)
    add(dry, clap(0.9), 49.0, 0, 1.0); add(wet, clap(0.9), 49.0, 0, 0.6)
    add(dry, tick(0.9, 1500), 49.0, 0, 1.0)
    # wall snaps: transient on each camera snap (49.5 .. 52.5)
    for ts in (49.5, 50.0, 50.5, 51.0, 51.5, 52.0, 52.5):
        add(dry, sub_hit(0.6, 90, 48), ts, 0, 0.45)
        add(dry, sweep(0.3, 900, 7000, 1.2, vel=0.35), ts - 0.05, 0, 1.0)
    # 53.0 pull-back, 53-54.75 riser, impact at 55
    add(dry, sweep(1.0, 500, 2500, 1.0, vel=0.45), 52.7, 0, 1.0)
    add(dry, riser(1.75, 350, 12000, 0.7), 53.0, 0, 1.0)
    add(dry, sub_hit(3.5, 66, 26), 55.0, 0, 1.3)
    add(wet, sub_hit(2.0, 70, 40), 55.0, 0, 0.6)
    add(dry, clap(0.8), 55.0, 0, 0.9)
    # end card: airy chimes on reveals
    for ts, m in ((55.85, 81), (56.0, 88), (56.4, 91), (56.75, 93), (57.4, 88), (57.55, 95), (58.1, 100)):
        add(dry, bell(m, 0.20, 2.0), ts, rng.uniform(-0.5, 0.5), 1.0); add(wet, bell(m, 0.2, 2.0), ts, 0, 0.8)

dry_pad = np.zeros((2, N), np.float32)
bass_bus = np.zeros((2, N), np.float32)

def reverb_ir(d=2.6):
    n = int(SR * d)
    t = np.arange(n) / SR
    ir = np.stack([rng.standard_normal(n), rng.standard_normal(n)]) * np.exp(-t * 2.6)
    ir = lp(ir, 5200)
    ir = hp(ir, 140)
    return (ir * 0.012).astype(np.float32)

def main():
    build()
    ir = reverb_ir()
    wet_out = np.stack([signal.fftconvolve(wet[c], ir[c])[:N] for c in range(2)])
    # ping-pong delay (dotted 8th)
    dl = int(0.375 * SR)
    dly_out = np.zeros_like(dly)
    for c in range(2):
        s = dly[c].copy()
        o = np.zeros(N, np.float32)
        for rep in range(1, 5):
            sh = dl * rep
            if sh >= N: break
            tgt = (c + rep) % 2
            dly_out[tgt, sh:] += s[:N - sh] * (0.45 ** rep)
    dly_out = lp(dly_out, 4500)
    mix = dry + dry_pad * duck + bass_bus * duck + wet_out * 0.9 + dly_out * 0.5
    # pre-impact silence dips so the big hits land on contrast (36 s, 49 s, 55 s)
    for hit_t, gap in ((36.0, 0.14), (49.0, 0.18), (55.0, 0.20)):
        i1 = int(hit_t * SR); i0 = i1 - int(gap * SR)
        env = np.ones(N, np.float32)
        r = int(0.02 * SR)
        env[i0:i0 + r] = np.linspace(1, 0.08, r)
        env[i0 + r:i1] = 0.08
        mix *= env
    # master: gentle bus compression-ish (tanh) and limiting
    mix = hp(mix, 28)
    mix = np.tanh(mix * 0.9) / np.tanh(0.9)
    # end: fade last 1.8 s so the file ends cleanly at exactly 60.000 s
    fade = int(1.8 * SR)
    mix[:, -fade:] *= np.linspace(1, 0, fade) ** 1.5
    mix[:, :int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    pk = np.max(np.abs(mix))
    mix = mix / pk * 0.89
    out = (mix.T * 32767).astype(np.int16)
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    wavfile.write(os.path.join(ROOT, "out", "audio_raw.wav"), SR, out)
    print("audio written", out.shape, out.shape[0] / SR, "s")

if __name__ == "__main__":
    main()
