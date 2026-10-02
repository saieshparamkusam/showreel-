"""Compositing engine for the showreel: posters, liquid-glass panels, text, transitions.

Everything is deterministic: frame(t) depends only on t, so any frame can be re-rendered.
"""
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H = 1920, 1080
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTERS = os.path.join(ROOT, "assets", "posters")
FONTS = os.path.join(ROOT, "fonts")

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def e_out(x, p=3):
    x = clamp(x)
    return 1 - (1 - x) ** p

def e_inout(x, p=3):
    x = clamp(x)
    return 0.5 * (2 * x) ** p if x < 0.5 else 1 - 0.5 * (2 * (1 - x)) ** p

def e_expo(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)

def e_back(x, k=1.35):
    x = clamp(x)
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2

def lerp(a, b, u):
    return a + (b - a) * u

def ramp(u, slow=0.5, power=3.2):
    """Speed ramp: fast -> slow around `slow` -> fast. Returns remapped progress 0..1."""
    u = clamp(u)
    # blend of in-out curve and linear gives a long slow middle with energetic ends
    s = e_inout(u, power)
    return lerp(u, s, 0.9)

# ---------------------------------------------------------------- assets
_P = {}
_FONT = {}

def font(name, size):
    k = (name, size)
    if k not in _FONT:
        _FONT[k] = ImageFont.truetype(os.path.join(FONTS, name + ".ttf"), size)
    return _FONT[k]

def poster(name):
    """Poster upscaled 2x (Lanczos) so macro crops stay crisp. Returns RGB PIL image."""
    if name not in _P:
        im = Image.open(os.path.join(POSTERS, name + ".png")).convert("RGB")
        im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=40, threshold=2))
        _P[name] = {"full": im}
    return _P[name]["full"]

def poster_lvl(name, h):
    """Pick a mip level whose height >= h (avoids aliasing when scaling down)."""
    base = poster(name)
    store = _P[name]
    best = base
    for lv in (1536, 1024, 768, 512, 384, 256):
        if lv >= h and lv < best.height:
            if lv not in store:
                store[lv] = base.resize((round(base.width * lv / base.height), lv), Image.LANCZOS)
            best = store[lv]
    return best

def psize(name):
    im = poster(name)
    return im.width, im.height

_MASK = {}
def round_mask(w, h, r, ss=2):
    k = (w, h, int(r))
    if k not in _MASK:
        if len(_MASK) > 120:
            _MASK.clear()
        m = Image.new("L", (w * ss, h * ss), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
        _MASK[k] = m.resize((w, h), Image.LANCZOS)
    return _MASK[k]

# ---------------------------------------------------------------- canvas helpers
def new_canvas(color=(8, 8, 10)):
    return Image.new("RGB", (W, H), color)

def vignette():
    if "vig" not in _P:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
        v = 1 - 0.38 * np.clip(d - 0.15, 0, 1)
        _P["vig"] = v[..., None]
    return _P["vig"]

def bg(name, t, dim=0.42, zoom=1.7, drift=14, tint=None):
    """Colour field derived from a poster: huge soft blur, slowly drifting, dimmed."""
    im = poster_lvl(name, 256)
    iw, ih = im.size
    cw = iw / zoom
    ch = cw * H / W
    if ch > ih:
        ch = ih; cw = ch * W / H
    ox = (iw - cw) / 2 + math.sin(t * 0.35) * drift * 0.5
    oy = (ih - ch) / 2 + math.cos(t * 0.27) * drift
    ox = clamp(ox, 0, iw - cw); oy = clamp(oy, 0, ih - ch)
    small = im.resize((W // 8, H // 8), Image.BICUBIC, box=(ox, oy, ox + cw, oy + ch))
    small = small.filter(ImageFilter.GaussianBlur(9))
    a = np.asarray(small.resize((W, H), Image.BICUBIC), dtype=np.float32)
    a = a * dim + np.array([6, 6, 9], np.float32)
    if tint is not None:
        a = a * 0.85 + np.array(tint, np.float32) * 0.15
    a = a * vignette()
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def _affine(iw, ih, s, cx, cy, rot):
    c, sn = math.cos(rot), math.sin(rot)
    return (c / s, sn / s, iw / 2 - (cx * c + cy * sn) / s,
            -sn / s, c / s, ih / 2 - (-cx * sn + cy * c) / s)

def _shift(a, dx, dy):
    out = np.zeros_like(a)
    h, w = a.shape
    xs0, xs1 = max(0, dx), min(w, w + dx)
    ys0, ys1 = max(0, dy), min(h, h + dy)
    out[ys0:ys1, xs0:xs1] = a[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out

def shadow_rim(canvas, mask, box, shadow=0.55, blur=26, offy=34, rim=0.55, alpha=1.0):
    """Apply drop shadow beneath and specular rim on top of an object whose coverage is `mask` (L, region)."""
    x0, y0, x1, y1 = box
    if shadow > 0:
        pad = blur * 3
        sx0, sy0, sx1, sy1 = max(0, x0 - pad), max(0, y0 - pad + offy), min(W, x1 + pad), min(H, y1 + pad + offy)
        if sx1 > sx0 and sy1 > sy0:
            full = Image.new("L", (sx1 - sx0, sy1 - sy0), 0)
            full.paste(mask, (x0 - sx0, y0 - offy - sy0))
            sw, sh = max(1, full.width // 4), max(1, full.height // 4)
            sm = full.resize((sw, sh), Image.BILINEAR).filter(ImageFilter.GaussianBlur(blur / 4))
            sm = sm.resize(full.size, Image.BILINEAR)
            dark = sm.point(lambda v: int(v * shadow * alpha))
            reg = canvas.crop((sx0, sy0, sx1, sy1))
            reg = Image.composite(Image.new("RGB", reg.size, (0, 0, 0)), reg, dark)
            canvas.paste(reg, (sx0, sy0))
    return

def add_rim(canvas, mask, box, strength=0.6, width=2):
    x0, y0 = box[0], box[1]
    box = (x0, y0, x0 + mask.width, y0 + mask.height)
    m = np.asarray(mask, dtype=np.float32) / 255.0
    tl = np.clip(m - _shift(m, width, width), 0, 1)
    br = np.clip(m - _shift(m, -width, -width), 0, 1)
    r = np.clip(tl * strength + br * strength * 0.3, 0, 1)
    r = Image.fromarray((r * 255).astype(np.uint8))
    reg = canvas.crop(box)
    reg = Image.composite(Image.new("RGB", reg.size, (255, 255, 255)), reg, r)
    canvas.paste(reg, (x0, y0))

def place(canvas, name, cx, cy, h, rot=0.0, radius=26, alpha=1.0, shadow=0.55, rim=0.55,
          clip=None, filt=None, brightness=1.0):
    """Place poster `name` with its centre at (cx,cy), displayed height h (px), rotation (rad).
    clip=(x0,y0,x1,y1,r) restricts to a rounded rect in canvas space."""
    iw0, ih0 = psize(name)
    s = h / ih0
    src = poster_lvl(name, h)
    iw, ih = src.size
    s_l = h / ih  # scale for the chosen level
    w_disp = iw0 * s
    ex = (abs(w_disp * math.cos(rot)) + abs(h * math.sin(rot))) / 2
    ey = (abs(w_disp * math.sin(rot)) + abs(h * math.cos(rot))) / 2
    bx0, by0 = int(max(0, math.floor(cx - ex - 2))), int(max(0, math.floor(cy - ey - 2)))
    bx1, by1 = int(min(W, math.ceil(cx + ex + 2))), int(min(H, math.ceil(cy + ey + 2)))
    if clip is not None:
        bx0, by0 = max(bx0, int(clip[0])), max(by0, int(clip[1]))
        bx1, by1 = min(bx1, int(clip[2])), min(by1, int(clip[3]))
    if bx1 - bx0 < 2 or by1 - by0 < 2:
        return
    bw, bh = bx1 - bx0, by1 - by0
    aff = _affine(iw, ih, s_l, cx - bx0, cy - by0, rot)
    img = src.transform((bw, bh), Image.AFFINE, aff, Image.BICUBIC)
    r_src = max(2, int(round(radius / s_l / 6) * 6))
    pm = round_mask(iw, ih, r_src, ss=1)
    m = pm.transform((bw, bh), Image.AFFINE, aff, Image.BILINEAR)
    if clip is not None:
        cm = round_mask(int(clip[2] - clip[0]), int(clip[3] - clip[1]), clip[4])
        full = Image.new("L", (bw, bh), 0)
        full.paste(cm, (int(clip[0]) - bx0, int(clip[1]) - by0))
        m = ImageChops.multiply(m, full)
    if brightness != 1.0:
        img = img.point(lambda v: min(255, int(v * brightness)))
    if filt is not None:
        img = img.filter(filt)
    box = (bx0, by0, bx1, by1)
    if shadow > 0:
        shadow_rim(canvas, m, box, shadow=shadow, alpha=alpha)
    if alpha < 1.0:
        m = m.point(lambda v: int(v * alpha))
    canvas.paste(img, (bx0, by0), m)
    if rim > 0:
        add_rim(canvas, m, box, strength=rim * alpha)

def cover(canvas, name, fx, fy, zoom, region=None, radius=0, rot=0.0, shadow=0.0, rim=0.0, alpha=1.0, brightness=1.0):
    """Show poster so that normalised point (fx,fy) is at region centre. zoom=1 -> poster just covers region."""
    if region is None:
        region = (0, 0, W, H)
    x0, y0, x1, y1 = region
    rw, rh = x1 - x0, y1 - y0
    iw, ih = psize(name)
    s = max(rw / iw, rh / ih) * zoom
    h = ih * s
    cx = (x0 + x1) / 2 + (0.5 - fx) * iw * s
    cy = (y0 + y1) / 2 + (0.5 - fy) * ih * s
    place(canvas, name, cx, cy, h, rot=rot, radius=1, clip=(x0, y0, x1, y1, radius), shadow=shadow,
          rim=rim, alpha=alpha, brightness=brightness)

# ---------------------------------------------------------------- liquid glass
def glass(canvas, box, r=44, amt=0.10, blur=7, lens=1.035, shadow=0.5, shine=None, tint=(255, 255, 255),
          alpha=1.0, rim=0.8):
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    w, h = x1 - x0, y1 - y0
    if w < 8 or h < 8:
        return
    m = round_mask(w, h, min(r, h // 2, w // 2))
    if alpha < 1:
        m = m.point(lambda v: int(v * alpha))
    reg = canvas.crop((x0, y0, x1, y1))
    # lens: magnify the backdrop slightly (refraction feel) then frost it
    cw, ch = w / lens, h / lens
    reg2 = reg.resize((w, h), Image.BILINEAR, box=((w - cw) / 2, (h - ch) / 2, (w + cw) / 2, (h + ch) / 2))
    sm = reg2.resize((max(1, w // 5), max(1, h // 5)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(blur))
    fr = np.asarray(sm.resize((w, h), Image.BILINEAR), dtype=np.float32)
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    xx = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    fr = fr * (1 - amt) + np.array(tint, np.float32) * amt * (1.15 - 0.55 * yy)
    fr = fr * 0.92
    if shine is not None:
        d = (xx * 0.6 + yy * 0.4) - shine
        fr += np.exp(-(d / 0.07) ** 2) * 34.0
    # soft inner top highlight
    fr += np.clip(1 - yy * 9, 0, 1) * 9
    img = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8))
    box2 = (x0, y0, x1, y1)
    shadow_rim(canvas, m, box2, shadow=shadow, blur=34, offy=26, alpha=alpha)
    canvas.paste(img, (x0, y0), m)
    add_rim(canvas, m, box2, strength=rim * alpha, width=2)
    # fine inner rim (second, softer) for thickness
    inner = ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(5)))
    reg = canvas.crop(box2)
    canvas.paste(Image.composite(Image.new("RGB", reg.size, (255, 255, 255)), reg, inner.point(lambda v: int(v * 0.10))), (x0, y0))

# ---------------------------------------------------------------- text
def text_w(s, fnt, tracking=0):
    return sum(fnt.getlength(c) + tracking for c in s) - tracking if tracking else fnt.getlength(s)

def draw_text(canvas, s, fnt, x, y, fill=(255, 255, 255), anchor="l", tracking=0, alpha=1.0,
              rise=1.0, clip_h=None, shadow=0.0):
    """Draw text with baseline-top at y. rise: 0..1 mask-reveal (text slides up inside a clipping line box)."""
    wd = int(text_w(s, fnt, tracking)) + 8
    asc, desc = fnt.getmetrics()
    hh = asc + desc + 6
    layer = Image.new("L", (wd, hh), 0)
    d = ImageDraw.Draw(layer)
    if tracking:
        cx = 0.0
        for c in s:
            d.text((cx, 0), c, font=fnt, fill=255)
            cx += fnt.getlength(c) + tracking
    else:
        d.text((0, 0), s, font=fnt, fill=255)
    if rise < 1.0:
        off = int((1 - rise) * hh * 0.95)
        shifted = Image.new("L", layer.size, 0)
        shifted.paste(layer, (0, off))
        layer = shifted
    if alpha < 1:
        layer = layer.point(lambda v: int(v * alpha))
    if anchor == "c":
        x = x - wd / 2
    elif anchor == "r":
        x = x - wd
    x, y = int(x), int(y)
    if shadow > 0:
        sh = layer.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * shadow))
        canvas.paste(Image.new("RGB", layer.size, (0, 0, 0)), (x, y + 8), sh)
    canvas.paste(Image.new("RGB", layer.size, fill), (x, y), layer)
    return wd, hh

def pill(canvas, label, cx, cy, t, size=34, appear=0.0):
    """Small glass capsule with label."""
    f = font("Inter-SemiBold", size)
    tr = 3
    tw = text_w(label.upper(), f, tr)
    pw, ph = tw + 76, size + 38
    p = e_expo((t - appear) / 0.55)
    if p <= 0.01:
        return
    y_off = (1 - p) * 26
    box = (cx - pw / 2, cy - ph / 2 + y_off, cx + pw / 2, cy + ph / 2 + y_off)
    glass(canvas, box, r=ph // 2, amt=0.13, blur=6, lens=1.0, shadow=0.35, alpha=p)
    asc, desc = f.getmetrics()
    draw_text(canvas, label.upper(), f, cx, cy - (asc + desc) / 2 + y_off + 1, anchor="c", tracking=tr,
              alpha=p, fill=(255, 255, 255))

# ---------------------------------------------------------------- transitions
def _blend(A, B, mask):
    return Image.composite(B, A, mask)

def tr_slats(A, B, p, n=8):
    """Glass slats rise bottom-to-top, staggered left to right, with a bright leading edge."""
    p = clamp(p)
    mask = np.zeros((H, W), np.float32)
    line = np.zeros((H, W), np.float32)
    cw = W / n
    ys = np.arange(H, dtype=np.float32)[:, None]
    for i in range(n):
        pl = e_inout(clamp(p * 1.6 - (i / n) * 0.6), 3)
        x0, x1 = int(round(i * cw)), int(round((i + 1) * cw))
        front = H * (1 - pl)
        mask[:, x0:x1] = (ys >= front).astype(np.float32)
        if 0.0 < pl < 1.0:
            line[:, x0:x1] = (np.abs(ys - front) < 2.5).astype(np.float32)
        if i:
            line[:, x0:x0 + 2] = np.maximum(line[:, x0:x0 + 2], 0.35 * ((ys >= front) | (pl >= 1.0)))
    out = _blend(A, B, Image.fromarray((mask * 255).astype(np.uint8)))
    arr = np.asarray(out, dtype=np.float32) + line[..., None] * 170
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def tr_iris(A, B, p, aspect=(1.0, 0.62)):
    p = clamp(p)
    e = e_inout(p, 3)
    hw = 40 + e * 1300
    hh = 24 + e * 1300 * aspect[1] / aspect[0] * 0.95
    r = int(lerp(hh, 60, e))
    w, h = int(hw * 2), int(hh * 2)
    box = (W // 2 - w // 2, H // 2 - h // 2)
    m = Image.new("L", (W, H), 0)
    rm = round_mask(w, h, min(r, h // 2, w // 2))
    m.paste(rm, box)
    out = _blend(A, B, m)
    if p < 0.98:
        mm = m.crop((0, 0, W, H))
        add_rim(out, mm, (0, 0, W, H), strength=0.5, width=2)
    return out

def tr_push(A, B, p, direction=1, blur=True):
    p = clamp(p)
    e = e_inout(p, 3)
    off = int(e * W)
    out = Image.new("RGB", (W, H))
    out.paste(A, (-off * direction, 0))
    out.paste(B, (W * direction - off * direction, 0))
    if blur:
        v = abs(math.sin(math.pi * p))
        k = int(v * 46)
        if k > 2:
            a = np.asarray(out, dtype=np.float32)
            acc = np.zeros_like(a)
            taps = 7
            for i in range(taps):
                sh = int((i / (taps - 1) - 0.5) * k)
                acc += np.roll(a, sh, axis=1)
            out = Image.fromarray((acc / taps).astype(np.uint8))
    return out

def tr_zoom(A, B, p):
    p = clamp(p)
    e = e_inout(p, 2.6)
    sa = 1 + 0.45 * e
    sb = 1.18 - 0.18 * e
    def sc(im, s):
        cw, ch = W / s, H / s
        return im.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
    a = sc(A, sa).filter(ImageFilter.GaussianBlur(1 + 8 * e))
    b = sc(B, sb)
    m = Image.new("L", (W, H), int(255 * e_inout(clamp((p - 0.15) / 0.7), 2)))
    return Image.composite(b, a, m)

def tr_flash(A, B, p, hold=0.5):
    p = clamp(p)
    base = _blend(A, B, Image.new("L", (W, H), 255 if p > hold else 0))
    f = max(0.0, 1 - abs(p - hold) / 0.5) ** 1.5
    white = Image.new("RGB", (W, H), (255, 255, 255))
    return Image.blend(base, white, clamp(f * 0.95))

def tr_wipe(A, B, p, angle=0.35):
    p = clamp(p)
    e = e_inout(p, 3)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = (xx / W) + angle * (yy / H)
    thr = e * (1 + angle) * 1.0
    soft = 0.0015
    m = np.clip((thr - d) / (soft * 4) + 0.5, 0, 1)
    out = _blend(A, B, Image.fromarray((m * 255).astype(np.uint8)))
    line = np.exp(-((d - thr) / 0.004) ** 2) * (1 - abs(2 * p - 1) * 0.4)
    arr = np.asarray(out, dtype=np.float32) + line[..., None] * 140
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

TRANS = {"slats": tr_slats, "iris": tr_iris, "push": tr_push, "pushl": lambda A, B, p: tr_push(A, B, p, -1),
         "zoom": tr_zoom, "flash": tr_flash, "wipe": tr_wipe, "cut": lambda A, B, p: B if p > 0 else A}

# ---------------------------------------------------------------- perspective
def persp_coeffs(src_pts, dst_pts):
    """Coefficients for PIL PERSPECTIVE mapping output(dst) -> input(src)."""
    A = []
    b = []
    for (xd, yd), (xs, ys) in zip(dst_pts, src_pts):
        A.append([xd, yd, 1, 0, 0, 0, -xs * xd, -xs * yd]); b.append(xs)
        A.append([0, 0, 0, xd, yd, 1, -ys * xd, -ys * yd]); b.append(ys)
    return np.linalg.solve(np.array(A, np.float64), np.array(b, np.float64)).tolist()

def keystone(im, tilt_x=0.0, tilt_y=0.0):
    """Mild perspective tilt of a full frame (tilt in fraction of size)."""
    if abs(tilt_x) < 1e-4 and abs(tilt_y) < 1e-4:
        return im
    # dst corners = where source corners land
    tl = (0 + tilt_x * W * 0.5 + tilt_y * W * 0.3, 0 + tilt_y * H * 0.5 + tilt_x * H * 0.3)
    tr = (W - tilt_x * W * 0.5 - tilt_y * W * 0.3, 0 - tilt_y * H * 0.5 + tilt_x * H * 0.3)
    bl = (0 + tilt_x * W * 0.5 - tilt_y * W * 0.3, H + tilt_y * H * 0.5 - tilt_x * H * 0.3)
    br = (W - tilt_x * W * 0.5 + tilt_y * W * 0.3, H - tilt_y * H * 0.5 - tilt_x * H * 0.3)
    src = [(0, 0), (W, 0), (0, H), (W, H)]
    dst = [tl, tr, bl, br]
    co = persp_coeffs(src, dst)
    return im.transform((W, H), Image.PERSPECTIVE, co, Image.BICUBIC)

def grain(im, frame, amount=2.2):
    rng = np.random.default_rng(frame * 7919 + 13)
    a = np.asarray(im, dtype=np.float32)
    n = rng.standard_normal((H // 2, W // 2, 1)).astype(np.float32)
    n = np.repeat(np.repeat(n, 2, 0), 2, 1)
    return Image.fromarray(np.clip(a + n * amount, 0, 255).astype(np.uint8))
