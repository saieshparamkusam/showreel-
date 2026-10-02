"""Shot library + master timeline (60.000 s @ 30 fps).

Beat grid: 120 BPM -> 1 beat = 0.5 s = 15 frames; 1 bar = 2 s. Cuts land on beats; the same
TIMELINE drives the sound design in audio.py so picture and sound stay locked.

POSTER RULE: every poster is always shown complete (all four edges, original aspect ratio, no
rounded/shape mask). Masks are used only as brief reveals; shapes sit behind/around posters.
"""
import math
from PIL import Image, ImageDraw
import numpy as np
from engine import *

FPS = 30
DUR = 60.0
BEAT = 0.5
WHITE = (255, 255, 255)

def _fit(name, s, maxw, size, tracking=0):
    while size > 12 and text_w(s, font(name, size), tracking) > maxw:
        size -= 1
    return font(name, size)

def fx_flash(img, amt):
    if amt <= 0.01:
        return img
    return Image.blend(img, Image.new("RGB", img.size, WHITE), clamp(amt))

# ---------------------------------------------------------------- building blocks
def orb(c, cx, cy, r, amt=0.07, shadow=0.3):
    """Liquid-glass disc (refracts the backdrop). Always fully inside the frame."""
    glass(c, (cx - r, cy - r, cx + r, cy + r), r=int(r), amt=amt, blur=16, lens=1.07, shadow=shadow, rim=0.7)

def orbs(c, t, layout, tmul=1.0):
    """layout: list of (x, y, r, phase). Slow float; shapes sit behind posters."""
    for (x, y, r, ph) in layout:
        dx = math.sin(t * 0.7 * tmul + ph) * 22
        dy = math.cos(t * 0.55 * tmul + ph * 1.7) * 18
        orb(c, clamp(x + dx, r + 8, W - r - 8), clamp(y + dy, r + 8, H - r - 8), r)

ORBS_A = [(330, 300, 210, 0.0), (1650, 790, 260, 1.7), (900, 930, 120, 3.1)]
ORBS_B = [(1560, 280, 230, 2.2), (260, 780, 250, 0.6), (980, 130, 100, 4.0)]

def row_layout(names, maxw, maxh, gap):
    ratios = [psize(n)[0] / psize(n)[1] for n in names]
    h = min(maxh, (maxw - gap * (len(names) - 1)) / sum(ratios))
    return h, [r * h for r in ratios]

def draw_row(c, names, cx, cy, maxw, maxh, gap, t, delay=0.0, stagger=0.07, reveal=0.38, stage=True,
             rots=None, grow=0.0, label_clear=0):
    """Complete posters side by side (never overlapping), optional glass stage plate behind them.
    Each poster is revealed by a brief wipe, then shown whole."""
    h, ws = row_layout(names, maxw, maxh, gap)
    h *= 1 + grow
    ws = [w * (1 + grow) for w in ws]
    total = sum(ws) + gap * (len(names) - 1)
    x = cx - total / 2
    if stage:
        pad = 34
        p = e_expo((t - delay) / 0.5)
        plate(c, (x - pad, cy - h / 2 - pad, x + total + pad, cy + h / 2 + pad), r=46, amt=0.06, blur=12, lens=1.0,
              shadow=0.5, alpha=clamp(p * 1.5))
    for i, (n, w) in enumerate(zip(names, ws)):
        pc = x + w / 2
        p = (t - delay - i * stagger) / reveal
        if p > 0:
            e = e_expo(p)
            rot = rots[i] if rots else 0.0
            if e < 0.999:
                x0 = pc - w / 2
                place(c, n, pc, cy, h, rot=rot, radius=0, shadow=0.6, rim=0,
                      clip=(x0, cy - h / 2 - 2, x0 + w * e + 1, cy + h / 2 + 2, 0))
            else:
                place(c, n, pc, cy, h, rot=rot, radius=0, shadow=0.6, rim=0)
        x += w + gap
    return h

def plate(*a, **k):
    """Intentionally empty: posters are never framed or contained by a shape."""
    return None

def shape_bg(name, t, orb_set, dim=0.5):
    c = bg(name, t, dim=dim)
    orbs(c, t, orb_set)
    return c

# ---------------------------------------------------------------- shots
def S_hook(name, dur, slit=False):
    """Hook: complete poster, vertical-slit reveal (brief), then a gentle push that stays inside the frame."""
    def f(t, T):
        u = clamp(t / dur)
        h = lerp(900, 1000, e_out(u, 2.4))
        c = bg(name, t, dim=0.5)
        orbs(c, t, ORBS_A, 1.6)
        iw, ih = psize(name)
        w = iw / ih * h
        e = e_expo(t / 0.5) if slit else 1.0
        if e < 0.999:
            ww = max(10, w * (0.06 + 0.94 * e))
            place(c, name, W / 2, H / 2, h, radius=0, shadow=0.0, rim=0,
                  clip=(W / 2 - ww / 2, H / 2 - h / 2 - 2, W / 2 + ww / 2, H / 2 + h / 2 + 2, 0))
            plate(c, (W / 2 - w / 2 - 40, H / 2 - h / 2 - 40, W / 2 + w / 2 + 40, H / 2 + h / 2 + 40), r=50, amt=0.05,
                  blur=12, lens=1.0, shadow=0.0, alpha=0.0 + 0.0)
        else:
            plate(c, (W / 2 - w / 2 - 38, H / 2 - h / 2 - 38, W / 2 + w / 2 + 38, H / 2 + h / 2 + 38), r=50, amt=0.05,
                  blur=12, lens=1.0, shadow=0.5)
            place(c, name, W / 2, H / 2, h, radius=0, shadow=0.55, rim=0)
        return c
    return f

def S_identity():
    POSTER = "Warp_Gradients"
    def f(t, T):
        c = bg(POSTER, t, dim=0.55)
        orbs(c, t, [(260, 900, 150, 0.5), (1000, 110, 90, 2.5), (1750, 960, 90, 3.3)], 1.2)
        p = e_out(t / 0.8, 3)
        box = (90, 150 + (1 - p) * 40, 1150, 930 + (1 - p) * 40)
        glass(c, box, r=64, amt=0.075, blur=10, lens=1.05, shadow=0.6, shine=lerp(-0.3, 1.3, clamp((t - 0.3) / 3.2)),
              alpha=clamp(p * 1.6))
        fn = font("Inter-ExtraBold", 138)
        x = 150
        for i, line in enumerate(("Jeevan Saiesh", "Paramkusam")):
            r = e_expo((t - 0.55 - i * 0.14) / 0.75)
            draw_text(c, line, fn, x, 235 + i * 150, tracking=-4, rise=r, alpha=clamp(r * 3))
        r = e_expo((t - 1.35) / 0.8)
        draw_text(c, "Graphic Designer", font("InstrumentSerif-Italic", 92), x + 3, 560, fill=(236, 226, 212), rise=r, alpha=clamp(r * 3))
        rr = e_expo((t - 1.7) / 0.9)
        ImageDraw.Draw(c).rectangle((x + 3, 702, x + 3 + int(900 * rr), 703), fill=(255, 255, 255))
        fsm = font("Inter-SemiBold", 29)
        rows = (["Brand Identity", "Packaging"], ["Typography", "Graphic Design"])
        k = 0
        for ri, row in enumerate(rows):
            xx = x + 3
            for wi, w_ in enumerate(row):
                a = e_out((t - 2.3 - k * 0.25) / 0.5, 2)
                wd, _ = draw_text(c, w_.upper(), fsm, xx, 740 + ri * 56, tracking=4, alpha=a, fill=(235, 235, 235))
                xx += wd + 44
                if wi == 0:
                    draw_text(c, "·", fsm, xx - 30, 740 + ri * 56, alpha=a * 0.8, fill=(235, 235, 235))
                k += 1
        # the complete poster, right
        e = e_expo((t - 0.3) / 0.7)
        h = 840
        iw, ih = psize(POSTER)
        w = iw / ih * h
        px = 1530
        plate(c, (px - w / 2 - 30, 540 - h / 2 - 30, px + w / 2 + 30, 540 + h / 2 + 30), r=44, amt=0.05, blur=12, lens=1.0,
              shadow=0.5, alpha=clamp(e * 1.4))
        if e > 0.01:
            place(c, POSTER, px, 540, h, radius=0, shadow=0.6, rim=0,
                  clip=(px - w / 2, 540 - h / 2 - 2, px - w / 2 + w * e + 1, 540 + h / 2 + 2, 0) if e < 0.999 else None)
        return c
    return f

def S_chapter(name, label, side="right", dur=2.0, bgn=None, sub=None):
    """Editorial layout: complete poster on one side, large chapter word on the other."""
    def f(t, T):
        u = clamp(t / dur)
        c = bg(bgn or name, t, dim=0.55)
        orbs(c, t, ORBS_A if side == "right" else ORBS_B)
        iw, ih = psize(name)
        h = lerp(880, 940, e_out(u, 2))
        w = iw / ih * h
        px = 1340 if side == "right" else 580
        sway = math.sin(t * 1.1) * 0.006
        e = e_expo(t / 0.6)
        plate(c, (px - w / 2 - 34, 540 - h / 2 - 34, px + w / 2 + 34, 540 + h / 2 + 34), r=46, amt=0.06, blur=12, lens=1.0,
              shadow=0.5, alpha=clamp(e * 1.4), shine=lerp(-0.3, 1.3, u))
        if e > 0.01:
            x0 = px - w / 2
            place(c, name, px, 540, h, rot=sway, radius=0, shadow=0.65, rim=0,
                  clip=(x0, 540 - h / 2 - 2, x0 + w * e + 1, 540 + h / 2 + 2, 0) if e < 0.999 else None)
        tx = 150 if side == "right" else 1010
        maxw = (px - w / 2 - 80 - tx) if side == "right" else (W - 150 - tx)
        fl = _fit("InstrumentSerif-Italic", label, maxw, 190)
        r = e_expo((t - 0.2) / 0.8)
        draw_text(c, label, fl, tx, 400, fill=(246, 244, 238), rise=r, alpha=clamp(r * 3), shadow=0.5)
        rr = e_expo((t - 0.5) / 0.9)
        ImageDraw.Draw(c).rectangle((tx + 4, 640, tx + 4 + int(min(maxw, 640) * rr), 641), fill=(255, 255, 255))
        return c
    return f

def S_pair(names, label=None, dur=2.0):
    def f(t, T):
        c = bg(names[0], t, dim=0.55)
        orbs(c, t, ORBS_B if len(names) == 2 else ORBS_A)
        draw_row(c, names, W / 2, 490, 1640, 850, 44, t, grow=0.02 * clamp(t / dur))
        if label:
            pill(c, label, W / 2, 1005, t, appear=0.35, size=30)
        return c
    return f

def S_tagline(name="37", dur=2.0):
    def f(t, T):
        u = clamp(t / dur)
        c = bg("03", t, dim=0.5, tint=(120, 140, 170))
        orbs(c, t, ORBS_B)
        iw, ih = psize(name)
        h = lerp(880, 930, e_out(u, 2))
        w = iw / ih * h
        px = 1380
        e = e_expo(t / 0.6)
        plate(c, (px - w / 2 - 34, 540 - h / 2 - 34, px + w / 2 + 34, 540 + h / 2 + 34), r=46, amt=0.06, blur=12, lens=1.0,
              shadow=0.5, alpha=clamp(e * 1.4))
        if e > 0.01:
            x0 = px - w / 2
            place(c, name, px, 540, h, radius=0, shadow=0.65, rim=0,
                  clip=(x0, 540 - h / 2 - 2, x0 + w * e + 1, 540 + h / 2 + 2, 0) if e < 0.999 else None)
        fs = font("InstrumentSerif-Italic", 128)
        for i, line in enumerate(("Clarity", "through", "simplicity.")):
            r = e_expo((t - 0.2 - i * 0.14) / 0.75)
            draw_text(c, line, fs, 150, 250 + i * 160, fill=(246, 244, 238), rise=r, alpha=clamp(r * 3), shadow=0.5)
        return c
    return f

def S_hero_cuts(items, step, start, h0=880, h1=980):
    """Hard-cut beat montage of COMPLETE posters, one per cut, with a scale punch that stays in frame."""
    def f(t, T):
        k = max(0, int((T - start + 1e-6) // step))
        name = items[k % len(items)]
        tt = (T - start) - k * step
        pe = e_out(tt / 0.2, 3)
        c = bg(name, T, dim=0.6)
        orbs(c, T + k * 3.1, ORBS_A if k % 2 == 0 else ORBS_B, 2.0)
        iw, ih = psize(name)
        h = lerp(h0, h1, pe) * lerp(1.0, 1.02, clamp(tt / step))
        w = iw / ih * h
        rot = lerp(0.02 * (-1) ** k, 0.0, pe)
        plate(c, (W / 2 - w / 2 - 30, H / 2 - h / 2 - 30, W / 2 + w / 2 + 30, H / 2 + h / 2 + 30), r=44, amt=0.05, blur=12,
              lens=1.0, shadow=0.45)
        place(c, name, W / 2, H / 2, h, rot=rot, radius=0, shadow=0.7, rim=0)
        return fx_flash(c, 0.22 * (1 - clamp(tt / 0.12)))
    return f

def S_layout_seq(schedule, maxw=1700, maxh=860, gap=36, stage=True, bgn=None):
    """Beat-synced sequence of layouts; schedule = [(global_time, [names...]), ...] (sorted)."""
    def f(t, T):
        k = 0
        for i, (tk, nm) in enumerate(schedule):
            if T >= tk - 1e-6:
                k = i
        tk, names = schedule[k]
        tt = T - tk
        c = bg(names[0], T, dim=0.6)
        orbs(c, T + k * 2.3, ORBS_A if k % 2 == 0 else ORBS_B, 2.0)
        mw = maxw if len(names) > 1 else 900
        draw_row(c, names, W / 2, 520, mw, maxh, gap, tt, stagger=0.045, reveal=0.22, stage=stage,
                 grow=0.03 * clamp(tt / 0.5))
        return fx_flash(c, 0.18 * (1 - clamp(tt / 0.1)))
    return f

# ---------------------------------------------------------------- services
SERVICES = [
    ("Brand", ["Brand strategy", "Identity systems", "Logo architecture", "Brand guidelines"]),
    ("Design", ["Typography & hierarchy", "Color systems", "Poster & editorial", "Print design"]),
    ("Campaigns", ["Social media design", "Advertising creatives", "Campaign design", "Thumbnail design"]),
    ("Digital & packaging", ["Packaging design", "UI & interface", "Brand mockups", "Collateral"]),
]

def S_services():
    def f(t, T):
        c = bg("11", t, dim=0.55)
        orbs(c, t, [(200, 220, 130, 0.3), (1720, 880, 150, 1.9), (1700, 170, 90, 3.0), (210, 900, 80, 4.2)], 1.0)
        p = e_out(t / 0.7, 3)
        glass(c, (110, 110 + (1 - p) * 40, 1810, 970 + (1 - p) * 40), r=60, amt=0.08, blur=10, lens=1.04, shadow=0.6,
              shine=lerp(-0.3, 1.3, clamp((t - 0.2) / 3.6)), alpha=clamp(p * 1.6))
        d = ImageDraw.Draw(c)
        for i, (head, lines) in enumerate(SERVICES):
            x = 200 + (i % 2) * 830
            y0 = 170 + (i // 2) * 400
            r = e_expo((t - 0.3 - i * 0.14) / 0.7)
            draw_text(c, head, font("InstrumentSerif-Italic", 78), x, y0, fill=(255, 255, 255), rise=r, alpha=clamp(r * 3))
            d.rectangle((x, y0 + 108, x + int(720 * e_expo((t - 0.5 - i * 0.14) / 0.8)), y0 + 109), fill=(255, 255, 255))
            fl = font("Inter-SemiBold", 38)
            for j, ln in enumerate(lines):
                rr = e_expo((t - 0.7 - i * 0.14 - j * 0.09) / 0.6)
                draw_text(c, ln, fl, x, y0 + 134 + j * 56, fill=(238, 238, 238), alpha=clamp(rr * 2), rise=rr)
        return c
    return f

# ---------------------------------------------------------------- climax wall (all 18 complete)
WALL = [
    ["08", "15", "11", "38", "01", "29"],
    ["Afterdark_01", "19", "03", "18", "Noir_Nights_001", "42"],
    ["Protocol_01_Poster_v02", "28", "24", "32", "Albums_What_We_Build", "45"],
]
CELL_W, CELL_H, CELL_GAP = 262, 306, 30

def S_wall():
    """Whole portfolio at once: 18 complete posters assemble on a grid (no cropping, no overlap)."""
    order = [(r, c_) for r in range(3) for c_ in range(6)]
    import random
    rnd = random.Random(11)
    rnd.shuffle(order)
    delay = {rc: 0.0 + i * 0.045 for i, rc in enumerate(order)}
    def f(t, T):
        c = bg("03", T, dim=0.55)
        orbs(c, T, ORBS_A, 1.5)
        gw = 6 * CELL_W + 5 * CELL_GAP
        gh = 3 * CELL_H + 2 * CELL_GAP
        u = clamp(t / 2.0)
        sc = lerp(0.96, 1.03, e_out(u, 2))
        # beat pulses on the way out
        for tb in (1.0, 1.5):
            d_ = t - tb
            if 0 <= d_ < 0.18:
                sc *= 1 + 0.02 * (1 - d_ / 0.18)
        x0 = W / 2 - gw * sc / 2
        y0 = H / 2 - gh * sc / 2
        plate(c, (x0 - 34, y0 - 34, x0 + gw * sc + 34, y0 + gh * sc + 34), r=50, amt=0.05, blur=12, lens=1.0, shadow=0.5,
              alpha=clamp(e_expo(t / 0.5) * 1.4))
        for r in range(3):
            for cc in range(6):
                n = WALL[r][cc]
                iw, ih = psize(n)
                ratio = iw / ih
                h = min(CELL_H, CELL_W / ratio) * sc
                w = ratio * h
                cx = x0 + (cc * (CELL_W + CELL_GAP) + CELL_W / 2) * sc
                cy = y0 + (r * (CELL_H + CELL_GAP) + CELL_H / 2) * sc
                p = (t - delay[(r, cc)]) / 0.3
                if p <= 0:
                    continue
                e = e_expo(p)
                if e < 0.999:
                    place(c, n, cx, cy, h, radius=0, shadow=0.45, rim=0,
                          clip=(cx - w / 2, cy - h / 2 - 2, cx - w / 2 + w * e + 1, cy + h / 2 + 2, 0))
                else:
                    place(c, n, cx, cy, h, radius=0, shadow=0.45, rim=0)
        return c
    return f

# ---------------------------------------------------------------- end card
def S_end():
    def f(t, T):
        c = bg("03", t, dim=0.30, zoom=1.5, tint=(60, 80, 120))
        p = e_out(t / 0.9, 3)
        glass(c, (250, 150 + (1 - p) * 30, 1670, 930 + (1 - p) * 30), r=70, amt=0.075, blur=12, lens=1.04,
              shadow=0.6, shine=lerp(-0.3, 1.3, clamp((t - 0.6) / 3.5)), alpha=clamp(p * 1.5))
        cx = W / 2
        r = e_expo((t - 0.5) / 0.8)
        f1 = font("Inter-SemiBold", 25)
        draw_text(c, "JEEVAN SAIESH PARAMKUSAM  ·  GRAPHIC DESIGNER", f1, cx, 236, anchor="c", tracking=5,
                  alpha=clamp(r * 2), fill=(220, 220, 224), rise=r)
        r = e_expo((t - 0.75) / 0.8)
        draw_text(c, "Have a project in mind?", font("Inter-ExtraBold", 96), cx, 318, anchor="c", tracking=-2, rise=r, alpha=clamp(r * 3))
        r = e_expo((t - 1.05) / 0.9)
        draw_text(c, "Let’s talk.", font("InstrumentSerif-Italic", 150), cx, 444, anchor="c", fill=(240, 232, 218), rise=r, alpha=clamp(r * 3))
        r = e_expo((t - 1.6) / 0.8)
        em = "paramkusamjeevansaiesh@gmail.com"
        fe = font("Inter-SemiBold", 48)
        ew = text_w(em, fe)
        if r > 0.02:
            yo = (1 - r) * 24
            glass(c, (cx - ew / 2 - 56, 662 + yo, cx + ew / 2 + 56, 662 + 100 + yo), r=50, amt=0.16, blur=6, lens=1.0,
                  shadow=0.35, alpha=clamp(r * 1.4))
            draw_text(c, em, fe, cx, 685 + yo, anchor="c", alpha=clamp(r * 2))
        r = e_out((t - 2.1) / 0.8, 2)
        fa = font("Inter-SemiBold", 30)
        draw_text(c, "AVAILABLE REMOTELY WORLDWIDE", fa, cx, 812, anchor="c", tracking=5, alpha=r, fill=(214, 214, 220))
        return c
    return f

# ---------------------------------------------------------------- timeline
M1 = ["08", "09", "12", "02", "05", "21", "29", "26"]
M2 = ["Afterdark_01", "19", "11", "15", "38", "01", "32", "Protocol_01_Poster_v02", "42", "03", "28",
      "Noir_Nights_001", "Albums_What_We_Build", "24", "45", "18"]

ROWSEQ = [(44.0, ["43", "39"]), (44.5, ["38", "12", "05"]), (45.0, ["21", "26", "14"]), (45.5, ["09", "02"]),
          (46.0, ["29", "16", "36"]), (46.5, ["Albums_Digital_Designer", "Noir_Nights_001"])]
TRIPSEQ = [(47.0, ["11", "08", "43"]), (47.5, ["19", "18", "24"]), (48.0, ["28", "32", "42"]), (48.5, ["38", "45", "37"])]
CLIMAX = [(49.0, ["08"]), (49.5, ["15", "11"]), (50.0, ["19", "18", "24"]), (50.5, ["01", "28", "32", "38"]),
          (51.0, ["Afterdark_01", "Noir_Nights_001", "Warp_Gradients", "Protocol_01_Poster_v02", "Albums_What_We_Build"]),
          (51.5, ["42"]), (51.75, ["43"]), (52.0, ["39"]), (52.25, ["12"]), (52.5, ["09", "02"]), (52.75, ["05", "21", "29"])]

# (cut_time: moment the shot is fully revealed, transition, transition_dur, shot_fn)
TIMELINE = [
    (0.0, "cut", 0.0, S_hook("03", 2.2, slit=True)),
    (2.0, "slats", 0.30, S_hook("15", 2.4)),
    (4.0, "iris", 0.50, S_identity()),
    (9.0, "zoom", 0.30, S_chapter("19", "Typography", "right", 2.2)),
    (11.0, "push", 0.25, S_chapter("18", "Hierarchy", "left", 2.2)),
    (13.0, "wipe", 0.30, S_chapter("01", "Color", "right", 2.2)),
    (15.0, "slats", 0.30, S_pair(["24", "22"], "Composition", 2.0)),
    (17.0, "iris", 0.40, S_pair(["08", "15", "11"], None, 3.0)),
    (20.0, "zoom", 0.30, S_tagline("37", 2.0)),
    (22.0, "push", 0.25, S_pair(["Albums_What_We_Build", "Albums_Digital_Designer"], "Brand Identity")),
    (24.0, "wipe", 0.30, S_chapter("Protocol_01_Poster_v02", "Poster design", "left", 2.0)),
    (26.0, "slats", 0.30, S_chapter("Afterdark_01", "Typography", "right", 2.0)),
    (28.0, "zoom", 0.30, S_pair(["Noir_Nights_001", "Warp_Gradients"], "Color Systems")),
    (30.0, "pushl", 0.25, S_pair(["28", "32", "42"], "Graphic Design", 2.0)),
    (32.0, "iris", 0.45, S_services()),
    (36.0, "flash", 0.15, S_hero_cuts(M1, 0.5, 36.0)),
    (40.0, "cut", 0.0, S_hero_cuts(M2, 0.25, 40.0, h0=860, h1=960)),
    (44.0, "zoom", 0.25, S_layout_seq(ROWSEQ)),
    (47.0, "cut", 0.0, S_layout_seq(TRIPSEQ, maxh=800)),
    (49.0, "flash", 0.20, S_layout_seq(CLIMAX, maxh=840)),
    (53.0, "flash", 0.15, S_wall()),
    (55.0, "flash", 0.35, S_end()),
]

def shot_range(i):
    cut, tr, d, fn = TIMELINE[i]
    return cut - d

def render_frame(n):
    T = n / FPS
    # active shot index
    idx = 0
    for i, (cut, tr, d, fn) in enumerate(TIMELINE):
        if T >= cut - d - 1e-9:
            idx = i
    cut, tr, d, fn = TIMELINE[idx]
    def draw(i, tt):
        c_, t_, d_, f_ = TIMELINE[i]
        loc = max(0.0, tt - (c_ - d_))
        mb = getattr(f_, "mb", 0)
        if mb:
            acc = None
            ns = getattr(f_, "mb_n", 3)
            offs = [mb * (2.0 * k / (ns - 1) - 1.0) for k in range(ns)]
            for off in offs:
                im = f_(max(0.0, loc + off), tt + off)
                a = np.asarray(im, dtype=np.float32)
                acc = a if acc is None else acc + a
            return Image.fromarray((acc / ns).astype(np.uint8))
        return f_(loc, tt)
    B = draw(idx, T)
    if idx > 0 and T < cut and d > 0:
        A = draw(idx - 1, T)
        p = (T - (cut - d)) / d
        out = TRANS[tr](A, B, p)
    else:
        out = B
    return grain(out, n)
