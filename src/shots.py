"""Shot library + master timeline (60.000 s @ 30 fps).

Beat grid: 120 BPM -> 1 beat = 0.5 s = 15 frames; 1 bar = 2 s. Cuts land on beats; the same
CUT/EVENT list drives the sound design in audio.py so picture and sound stay locked.
"""
import math
from PIL import Image, ImageDraw
import numpy as np
from engine import *

FPS = 30
DUR = 60.0
BEAT = 0.5

WHITE = (255, 255, 255)

# ---------------------------------------------------------------- shared pieces
def _fit(name, s, maxw, size, tracking=0):
    while size > 12 and text_w(s, font(name, size), tracking) > maxw:
        size -= 1
    return font(name, size)

def cover_c(canvas, name, fx, fy, zoom, region, **kw):
    """cover() with the focus clamped so the region is always filled."""
    x0, y0, x1, y1 = region
    iw, ih = psize(name)
    s = max((x1 - x0) / iw, (y1 - y0) / ih) * zoom
    vw, vh = (x1 - x0) / (iw * s), (y1 - y0) / (ih * s)
    fx = clamp(fx, vw / 2, 1 - vw / 2) if vw < 1 else 0.5
    fy = clamp(fy, vh / 2, 1 - vh / 2) if vh < 1 else 0.5
    cover(canvas, name, fx, fy, zoom, region=region, **kw)

ROW_SET = ["08", "15", "11", "01", "19", "Afterdark_01", "Noir_Nights_001", "18", "28", "Albums_What_We_Build",
           "Protocol_01_Poster_v02", "32", "38", "24", "42", "Warp_Gradients", "45", "43"]

def collage(canvas, t, speed=70, h=340, rows=(190, 540, 890), dim=0.62, rot=0.0, offset=0):
    """Three parallax rows of posters sliding at different speeds/directions."""
    layer = canvas
    gap = 34
    for ri, cy in enumerate(rows):
        names = ROW_SET[(ri * 5 + offset) % len(ROW_SET):] + ROW_SET[:(ri * 5 + offset) % len(ROW_SET)]
        wds = [psize(n)[0] / psize(n)[1] * h for n in names]
        total = sum(wds) + gap * len(names)
        direction = 1 if ri % 2 == 0 else -1
        sp = speed * (0.8 + 0.35 * ri)
        shift = (t * sp * direction) % total
        x = -shift - 200
        k = 0
        while x < W + 400:
            n = names[k % len(names)]
            w = wds[k % len(names)]
            cx, cyy = x + w / 2, cy
            if rot:
                dx, dy = cx - W / 2, cyy - H / 2
                cx = W / 2 + dx * math.cos(rot) - dy * math.sin(rot)
                cyy = H / 2 + dx * math.sin(rot) + dy * math.cos(rot)
            if -w < cx < W + w:
                place(layer, n, cx, cyy, h, rot=rot, radius=16, shadow=0.0, rim=0.3, brightness=dim)
            x += w + gap
            k += 1
            if k > 60:
                break

def fx_flash(img, amt):
    if amt <= 0.01:
        return img
    return Image.blend(img, Image.new("RGB", img.size, WHITE), clamp(amt))

# ---------------------------------------------------------------- shots
def S_hook(name, p0, p1, z0, z1, dur, slit=False, rot=0.0):
    def f(t, T):
        u = clamp(t / dur)
        e = e_out(u, 2.6)
        fx, fy = lerp(p0[0], p1[0], e), lerp(p0[1], p1[1], e)
        z = lerp(z0, z1, e_out(u, 3.4))
        c = new_canvas((5, 5, 7))
        if slit:
            o = e_expo(t / 0.62)
            wd = lerp(0.045, 1.0, o) * W
            reg = (W / 2 - wd / 2, 0, W / 2 + wd / 2, H)
            c = bg(name, t, dim=0.35)
            cover_c(c, name, fx, fy, z, reg, radius=0 if o > 0.995 else 26, shadow=0.0, rim=0.0)
            if o < 0.995:
                m = round_mask(int(wd), H, 26)
                add_rim(c, m, (int(W / 2 - wd / 2), 0, int(W / 2 + wd / 2), H), strength=0.9, width=3)
        else:
            cover_c(c, name, fx, fy, z, (0, 0, W, H), radius=0)
        return c
    f.mb = 0.5 / FPS
    return f

def S_identity():
    def f(t, T):
        c = new_canvas((6, 6, 8))
        collage(c, t + 2.0, speed=85, h=360, dim=0.52)
        dark = Image.new("RGB", (W, H), (4, 4, 6))
        c = Image.blend(c, dark, 0.42)
        p = e_out(t / 0.8, 3)
        box = (190, 120 + (1 - p) * 40, 1730, 940 + (1 - p) * 40)
        glass(c, box, r=64, amt=0.075, blur=10, lens=1.05, shadow=0.6, shine=lerp(-0.3, 1.3, clamp((t - 0.3) / 3.2)), alpha=clamp(p * 1.6))
        fn = font("Inter-ExtraBold", 192)
        x = 285
        for i, line in enumerate(("Jeevan Saiesh", "Paramkusam")):
            r = e_expo((t - 0.55 - i * 0.14) / 0.75)
            draw_text(c, line, fn, x, 175 + i * 206, tracking=-5, rise=r, alpha=clamp(r * 3))
        r = e_expo((t - 1.35) / 0.8)
        fs = font("InstrumentSerif-Italic", 104)
        draw_text(c, "Graphic Designer", fs, x + 4, 618, fill=(236, 226, 212), rise=r, alpha=clamp(r * 3))
        rr = e_expo((t - 1.7) / 0.9)
        d = ImageDraw.Draw(c)
        d.rectangle((x + 4, 782, x + 4 + int(1350 * rr), 783), fill=(255, 255, 255))
        words = ["Brand Identity", "Packaging", "Typography", "Graphic Design"]
        fsm = font("Inter-SemiBold", 31)
        xx = x + 4
        for i, w_ in enumerate(words):
            a = e_out((t - 2.3 - i * 0.28) / 0.5, 2)
            wd, _ = draw_text(c, w_.upper(), fsm, xx, 818, tracking=4, alpha=a, fill=(235, 235, 235))
            xx += wd + 40
            if i < 3:
                draw_text(c, "·", fsm, xx - 26, 818, alpha=a * 0.8, fill=(235, 235, 235))
        return c
    return f

def _win_frame(name, f0, f1, z0, z1, label, box, dur, peek=None, rampy=True, rot=0.0, bgname=None):
    def f(t, T):
        u = clamp(t / dur)
        p = ramp(u) if rampy else e_out(u, 2)
        c = bg(bgname or name, t, dim=0.5)
        if peek:
            pn, pcx, pcy, ph, pr = peek
            pe = e_expo((t - 0.1) / 0.8)
            place(c, pn, pcx, pcy + (1 - pe) * 120, ph, rot=pr, radius=28, brightness=0.62, shadow=0.5, rim=0.35)
        o = e_expo(t / 0.55)
        x0, y0, x1, y1 = box
        cy = (y0 + y1) / 2
        hh = (y1 - y0) * (0.30 + 0.70 * o)
        reg = (x0, cy - hh / 2, x1, cy + hh / 2)
        zoom = lerp(z0, z1, p)
        fx, fy = lerp(f0[0], f1[0], p), lerp(f0[1], f1[1], p)
        cover_c(c, name, fx, fy, zoom, reg, radius=36, shadow=0.65, rim=0.7)
        if label:
            pill(c, label, W / 2, 940, t, appear=0.28)
        return c
    return f

def S_window(*a, **k):
    return _win_frame(*a, **k)

def S_hero(name, label=None, dur=2.0, h0=930, h1=985, rot0=-0.03, rot1=0.0, bgn=None):
    def f(t, T):
        u = clamp(t / dur)
        c = bg(bgn or name, t, dim=0.55)
        o = e_expo(t / 0.7)
        h = lerp(h0, h1, e_out(u, 2)) * lerp(0.88, 1.0, o)
        place(c, name, W / 2, H / 2 - 10 + (1 - o) * 60, h, rot=lerp(rot0, rot1, e_out(u, 2)), radius=26, shadow=0.7, rim=0.6)
        if label:
            pill(c, label, W / 2, 995, t, appear=0.3, size=30)
        return c
    return f

def S_duo(a, b, label, dur=2.0, flip=False):
    def f(t, T):
        c = bg(a, t, dim=0.55)
        ea = e_expo((t - 0.0) / 0.8)
        eb = e_expo((t - 0.14) / 0.8)
        fl = -1 if flip else 1
        yb = math.sin(t * 1.3) * 8
        u = clamp(t / dur)
        place(c, a, W / 2 - (330 + 40 * u) * fl, 560 + (1 - ea) * 700 + yb, 860 + 30 * u, rot=(-0.045 + 0.02 * u) * fl, radius=26, shadow=0.65, rim=0.6)
        place(c, b, W / 2 + (330 + 40 * u) * fl, 515 + (1 - eb) * 700 - yb, 800 + 30 * u, rot=(0.04 - 0.02 * u) * fl, radius=26, shadow=0.65, rim=0.6)
        if label:
            pill(c, label, W / 2, 985, t, appear=0.35, size=30)
        return c
    return f

def S_trio(names, label=None, dur=3.0):
    a, b, cc = names
    def f(t, T):
        c = bg(b, t, dim=0.55)
        e0 = e_expo(t / 0.8); e1 = e_expo((t - 0.12) / 0.8); e2 = e_expo((t - 0.24) / 0.8)
        drift = lerp(-70, 70, clamp(t / dur))
        bob = math.sin(t * 1.6) * 10
        place(c, a, 430 + drift * 0.5, 560 + bob + (1 - e0) * 800, 780, rot=-0.07, radius=24, shadow=0.6, rim=0.5, brightness=0.9)
        place(c, cc, 1490 - drift * 0.5, 540 - bob + (1 - e2) * 800, 780, rot=0.07, radius=24, shadow=0.6, rim=0.5, brightness=0.9)
        place(c, b, W / 2, 515 + (1 - e1) * 800 - drift * 0.4, 880 + drift * 0.15, rot=0.0, radius=26, shadow=0.75, rim=0.65)
        if label:
            pill(c, label, W / 2, 1000, t, appear=0.4, size=30)
        return c
    return f

def S_tagline(name="37", dur=2.0):
    def f(t, T):
        c = bg("03", t, dim=0.5, tint=(120, 140, 170))
        e = e_expo(t / 0.8)
        place(c, name, 1400 + (1 - e) * 500 - 40 * clamp(t / dur), 540 + 12 * math.sin(t * 1.4), 900 + 40 * clamp(t / dur), rot=0.035 - 0.03 * clamp(t / dur), radius=26, shadow=0.65, rim=0.6)
        fs = font("InstrumentSerif-Italic", 120)
        for i, line in enumerate(("Clarity", "through", "simplicity.")):
            r = e_expo((t - 0.2 - i * 0.14) / 0.75)
            draw_text(c, line, fs, 170, 250 + i * 150, fill=(246, 244, 238), rise=r, alpha=clamp(r * 3), shadow=0.5)
        return c
    return f

def S_beatmontage(items, step, start, bgmix=True, cropmode=False):
    """Hard-cut beat montage. items: list of (name, fx, fy, zoom). Cuts every `step` s from global `start`."""
    def f(t, T):
        k = int((T - start + 1e-6) // step)
        k = max(0, k)
        name, fx, fy, z = items[k % len(items)]
        tt = (T - start) - k * step
        pe = e_out(tt / 0.22, 3)
        if cropmode:
            c = new_canvas((6, 6, 8))
            zz = lerp(z * 1.18, z, pe) * lerp(1.0, 1.06, clamp(tt / step))
            cover_c(c, name, fx, fy, zz, (0, 0, W, H), radius=0)
        else:
            c = bg(name, T, dim=0.6)
            h = lerp(1090, 980, pe) * lerp(1.0, 1.035, clamp(tt / step))
            place(c, name, W / 2, H / 2, h, rot=lerp(0.02 * (-1) ** k, 0.0, pe), radius=24, shadow=0.7, rim=0.6)
        return fx_flash(c, 0.22 * (1 - clamp(tt / 0.12)))
    return f

def S_rows(dur, speed0, speed1, rot=-0.14, label=None):
    def f(t, T):
        u = clamp(t / dur)
        # accelerating ramp: integrate speed
        tt = lerp(speed0, speed1, u / 2) * t / 60.0
        c = new_canvas((5, 5, 7))
        c = bg("11", t, dim=0.5)
        collage(c, tt * 4.0 + 8, speed=60, h=420, rows=(150, 540, 930), dim=0.95, rot=rot, offset=3)
        return c
    return f

def S_triptych(sets, step, start):
    def f(t, T):
        k = max(0, int((T - start + 1e-6) // step))
        names = sets[k % len(sets)]
        tt = (T - start) - k * step
        c = new_canvas((4, 4, 6))
        gap = 14
        cw = (W - gap * 2) / 3
        for i, (n, fx, fy, z) in enumerate(names):
            e = e_expo((tt - i * 0.05) / 0.3)
            x0 = i * (cw + gap)
            yoff = (1 - e) * H * (1 if i % 2 == 0 else -1)
            cover_c(c, n, fx, fy, z * lerp(1.12, 1.0, e_out(tt / 0.6, 2)), (x0, yoff, x0 + cw, yoff + H), radius=0)
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
        c = new_canvas((6, 6, 8))
        collage(c, t + 9, speed=70, h=330, dim=0.5, offset=7)
        c = Image.blend(c, Image.new("RGB", (W, H), (4, 4, 6)), 0.45)
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

# ---------------------------------------------------------------- wall (climax)
WALL_GRID = [
    ["08", "15", "11", "38", "01", "29"],
    ["Afterdark_01", "19", "03", "18", "Noir_Nights_001", "42"],
    ["Protocol_01_Poster_v02", "28", "24", "32", "Albums_What_We_Build", "45"],
]
TW, TH, GAP = 390, 520, 40
_wall = {}

def wall_img():
    if "img" in _wall:
        return _wall["img"]
    cols, rows = 6, 3
    ww = cols * TW + (cols + 1) * GAP + 200
    wh = rows * TH + (rows + 1) * GAP + 200
    im = Image.new("RGB", (ww, wh), (6, 6, 8))
    sh = Image.new("L", (ww, wh), 0)
    pos = {}
    for r in range(rows):
        for cc in range(cols):
            x = 100 + GAP + cc * (TW + GAP)
            y = 100 + GAP + r * (TH + GAP)
            pos[(r, cc)] = (x + TW / 2, y + TH / 2)
            ImageDraw.Draw(sh).rounded_rectangle((x, y + 24, x + TW, y + TH + 24), 20, fill=170)
    sh = sh.filter(ImageFilter.GaussianBlur(22))
    im = Image.composite(Image.new("RGB", (ww, wh), (0, 0, 0)), im, sh)
    m = round_mask(TW, TH, 20)
    for r in range(rows):
        for cc in range(cols):
            x, y = pos[(r, cc)]
            n = WALL_GRID[r][cc]
            src = poster_lvl(n, TH * 2).resize((TW, TH), Image.LANCZOS)
            im.paste(src, (int(x - TW / 2), int(y - TH / 2)), m)
            reg = (int(x - TW / 2), int(y - TH / 2), int(x + TW / 2), int(y + TH / 2))
            sub = im.crop(reg)
            rim = ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(5)))
            im.paste(Image.composite(Image.new("RGB", sub.size, WHITE), sub, rim.point(lambda v: int(v * 0.5))), reg[:2])
    _wall["img"] = im
    _wall["pos"] = pos
    return im

WALL_KEYS = [  # (time, row, col, scale, rot, tilt_x, tilt_y, snap)
    (49.0, 0, 1, 1.50, -0.06, 0.03, 0.00, True),
    (49.5, 1, 4, 1.50, 0.05, -0.03, 0.01, True),
    (50.0, 2, 1, 1.55, -0.04, 0.03, -0.01, True),
    (50.5, 0, 3, 1.50, 0.07, -0.02, 0.01, True),
    (51.0, 1, 0, 1.95, 0.00, 0.04, 0.00, True),
    (51.5, 2, 4, 1.50, -0.06, -0.03, -0.01, True),
    (52.0, 0, 5, 1.50, 0.05, 0.03, 0.01, True),
    (52.5, 1, 3, 1.55, -0.03, -0.03, 0.00, True),
    (53.0, 1.0, 2.5, 0.64, 0.0, 0.0, 0.0, True),
    (53.8, 1.0, 2.5, 0.78, 0.0, 0.0, 0.0, False),
    (54.75, 1, 2, 2.04, 0.0, 0.0, 0.0, False),
]

def _wall_state(T):
    T = T + 0.20   # camera moves are timed to ARRIVE on the beat
    ks = WALL_KEYS
    if T <= ks[0][0]:
        return ks[0][1:7]
    for i in range(len(ks) - 1):
        a, b = ks[i], ks[i + 1]
        if a[0] <= T < b[0]:
            u = (T - a[0]) / (b[0] - a[0])
            if b[7]:
                e = e_inout(clamp(u * 3.4), 3) * 0.965 + 0.035 * u   # beat snap: smooth fast move, then slow float
            else:
                e = ramp(u)
            return [lerp(a[j], b[j], e) for j in range(1, 7)]
    return ks[-1][1:7]

def S_wall():
    def f(t, T):
        im = wall_img()
        pos = _wall["pos"]
        r, cc, s, rot, tx, ty = _wall_state(T)
        # interpolated tile position (fractional row/col)
        r0, c0 = int(math.floor(r)), int(math.floor(cc))
        r1, c1 = min(2, r0 + 1), min(5, c0 + 1)
        fr, fc = r - r0, cc - c0
        def P(rr, c_):
            return pos[(rr, c_)]
        x = lerp(lerp(P(r0, c0)[0], P(r0, c1)[0], fc), lerp(P(r1, c0)[0], P(r1, c1)[0], fc), fr)
        y = lerp(lerp(P(r0, c0)[1], P(r0, c1)[1], fc), lerp(P(r1, c0)[1], P(r1, c1)[1], fc), fr)
        ww, wh = im.size
        base = Image.new("RGB", (W, H), (6, 6, 8))
        cs, sn = math.cos(rot), math.sin(rot)
        a, b_, d, e = cs / s, sn / s, -sn / s, cs / s
        c0_ = x - a * W / 2 - b_ * H / 2
        f0 = y - d * W / 2 - e * H / 2
        out = im.transform((W, H), Image.AFFINE, (a, b_, c0_, d, e, f0), Image.BICUBIC)
        out = keystone(out, tx, ty)
        return out
    f.mb = 0.5 / FPS
    f.mb_n = 9
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
def _crop(n, fx, fy, z):
    return (n, fx, fy, z)

M1 = [("08", 0, 0, 0), ("09", 0, 0, 0), ("12", 0, 0, 0), ("02", 0, 0, 0), ("05", 0, 0, 0), ("21", 0, 0, 0),
      ("29", 0, 0, 0), ("26", 0, 0, 0)]
M2 = [("Afterdark_01", .5, .3, 1.3), ("19", .5, .12, 1.7), ("11", .5, .35, 1.3), ("15", .5, .3, 1.9), ("38", .5, .35, 1.9),
      ("01", .3, .85, 1.6), ("32", .5, .3, 1.5), ("Protocol_01_Poster_v02", .5, .4, 1.5), ("42", .55, .45, 1.6),
      ("03", .6, .3, 1.9), ("28", .5, .2, 1.8), ("Noir_Nights_001", .5, .3, 1.5), ("Albums_What_We_Build", .45, .4, 1.6),
      ("24", .5, .25, 1.6), ("45", .5, .3, 1.7), ("18", .5, .65, 1.9)]
TRIP = [
    [("11", .5, .5, 1.0), ("08", .5, .5, 1.0), ("43", .5, .5, 1.0)],
    [("19", .5, .5, 1.0), ("18", .5, .5, 1.0), ("24", .5, .5, 1.0)],
    [("28", .5, .5, 1.0), ("32", .5, .5, 1.0), ("42", .5, .5, 1.0)],
    [("38", .5, .5, 1.0), ("45", .5, .5, 1.0), ("37", .5, .5, 1.0)],
]

# (cut_time: moment the shot is fully revealed, transition, transition_dur, shot_fn)
TIMELINE = [
    (0.0, "cut", 0.0, S_hook("03", (0.66, 0.20), (0.5, 0.26), 1.75, 1.08, 2.4, slit=True)),
    (2.0, "slats", 0.30, S_hook("15", (0.5, 0.32), (0.5, 0.40), 1.7, 1.15, 2.4)),
    (4.0, "iris", 0.50, S_identity()),
    (9.0, "zoom", 0.30, S_window("19", (0.5, 0.12), (0.5, 0.45), 1.6, 1.0, "Typography", (160, 100, 1760, 820), 2.2)),
    (11.0, "push", 0.25, S_window("18", (0.5, 0.62), (0.5, 0.64), 1.35, 1.0, "Hierarchy", (680, 90, 1780, 850), 2.2,
                                  peek=("24", 330, 570, 720, -0.06))),
    (13.0, "wipe", 0.30, S_window("01", (0.30, 0.80), (0.5, 0.52), 1.3, 1.0, "Color", (330, 90, 1590, 850), 2.2)),
    (15.0, "slats", 0.30, S_window("24", (0.5, 0.26), (0.45, 0.58), 1.45, 1.05, "Composition", (130, 130, 1330, 850), 2.2,
                                   peek=("22", 1590, 530, 700, 0.05))),
    (17.0, "iris", 0.40, S_trio(("08", "15", "11"), dur=3.0)),
    (20.0, "zoom", 0.30, S_tagline("37", 2.0)),
    (22.0, "push", 0.25, S_duo("Albums_What_We_Build", "Albums_Digital_Designer", "Brand Identity")),
    (24.0, "wipe", 0.30, S_window("Protocol_01_Poster_v02", (0.5, 0.12), (0.5, 0.82), 1.1, 1.1, "Poster Design",
                                  (140, 100, 1780, 840), 2.0)),
    (26.0, "slats", 0.30, S_window("Afterdark_01", (0.5, 0.18), (0.5, 0.58), 1.5, 1.05, "Typography",
                                   (260, 100, 1660, 840), 2.0, rampy=True)),
    (28.0, "zoom", 0.30, S_duo("Noir_Nights_001", "Warp_Gradients", "Color Systems", flip=True)),
    (30.0, "pushl", 0.25, S_trio(("28", "32", "42"), "Graphic Design", dur=2.0)),
    (32.0, "iris", 0.45, S_services()),
    (36.0, "flash", 0.15, S_beatmontage(M1, 0.5, 36.0)),
    (40.0, "cut", 0.0, S_beatmontage(M2, 0.25, 40.0, cropmode=True)),
    (44.0, "zoom", 0.25, S_rows(3.0, 80, 260)),
    (47.0, "cut", 0.0, S_triptych(TRIP, 0.5, 47.0)),
    (49.0, "flash", 0.20, S_wall()),
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
