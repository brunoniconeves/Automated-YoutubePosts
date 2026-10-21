"""The subscribe reminder: a transparent overlay that goes over any footage in the long video (the b-roll, a screen
recording, the editor). Three points of light spiral in on round curves and the words appear in a flash with a burst
of crystals; the lights circle twice and fade; the words hold alone; the lights come back and spiral out the way they
came, taking the words with them; the clip ends on a clean screen.
Writes brand/subscribe_<lang>.mov (1920x1080, 30 fps, QuickTime Animation with alpha). Make it once per channel and
language, like the stings; build_long.py overlays it at long.subscribe.
    python tools/subscribe_overlay.py --lang pt
Settings in channel.json "subscribe": text per language, font, size, colour of the lights, the hold.
"""
import argparse
import math
import os
import random
import shutil
import tempfile

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from common import ROOT, ff, load_channel

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--lang", default=None, help="language of the text (default: channel main language)")
ap.add_argument("--out", default=None, help="output .mov (default: brand/subscribe_<lang>.mov)")
a = ap.parse_args()

ch = load_channel()
cfg = ch.get("subscribe", {})
lang = a.lang or ch["languages"]["main"]
TEXT = cfg.get("text", {}).get(lang) or {"pt": "JÁ SE INSCREVEU?", "en": "SUBSCRIBED YET?", "es": "¿YA TE SUSCRIBISTE?"}.get(lang, "SUBSCRIBED YET?")
FONT = cfg.get("font", "C:/Windows/Fonts/bahnschrift.ttf")
VARIATION = cfg.get("font_variation", "Bold Condensed")
SIZE = cfg.get("size", 190)
HOLD = cfg.get("hold", 4.0)  # seconds the words stay alone between the two light passes


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


RING = hex_rgb(cfg.get("light_color", "#50AFFF"))
CORE = (225, 245, 255)
CRYSTAL = tuple(max(0, c - 30) for c in RING)

W, H, FPS = 1920, 1080, 30
# Timeline (seconds).
SPIRAL_IN = (0.0, 1.3)
T_FLASH_IN = 0.95
LIGHTS_FADE = (2.9, 3.4)
LIGHTS_BACK = (LIGHTS_FADE[1] + HOLD, LIGHTS_FADE[1] + HOLD + 0.3)
SPIRAL_OUT = (LIGHTS_BACK[0] + 1.3, LIGHTS_BACK[0] + 2.4)
T_FLASH_OUT = SPIRAL_OUT[0] + 0.15
SECS = SPIRAL_OUT[1] + 0.9  # a quiet end while the last crystals fade

font = ImageFont.truetype(FONT, SIZE)
if VARIATION:
    try:
        font.set_variation_by_name(VARIATION)
    except Exception:
        pass
box = font.getbbox(TEXT)
tw, th = box[2] - box[0], box[3] - box[1]
CX, CY = W / 2, H * cfg.get("y", 0.45)
tx, ty = CX - tw / 2 - box[0], CY - th / 2 - box[1]

word = Image.new("RGBA", (W, H), (0, 0, 0, 0))
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(shadow).text((tx + 6, ty + 8), TEXT, font=font, fill=(0, 20, 60, 160))
shadow = shadow.filter(ImageFilter.GaussianBlur(10))
ImageDraw.Draw(word).text((tx, ty), TEXT, font=font, fill=(255, 255, 255, 255))
word = Image.alpha_composite(shadow, word)
glyph = Image.new("L", (W, H), 0)
ImageDraw.Draw(glyph).text((tx, ty), TEXT, font=font, fill=255)
halo_a = glyph.filter(ImageFilter.GaussianBlur(22)).point(lambda v: min(255, v * 2))

RX, RY = tw / 2 + 110, th / 2 + 80
STREAKS = [dict(ph=0.0, tilt=-0.12), dict(ph=2 * math.pi / 3, tilt=0.10), dict(ph=4 * math.pi / 3, tilt=0.0)]
TRAIL, SUB = 26, 4  # trail length in frames, samples per frame (fast arcs stay round)


def smooth(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def smoothstep(lo, hi, x):
    return smooth((x - lo) / (hi - lo))


def scale_at(t):
    """Orbit size across and up-down: wide orbits open more up and down, so the lights curve round the screen."""
    w = 1.6 * (1 - smoothstep(*SPIRAL_IN, t)) + 1.6 * smoothstep(*SPIRAL_OUT, t)
    return 1 + 0.45 * w, 1 + 1.5 * w


def speed_at(t):
    """Turns per second, eased: brisk while spiralling, calm while circling."""
    return 0.75 + 0.6 * max(1 - smoothstep(*SPIRAL_IN, t), smoothstep(*SPIRAL_OUT, t))


STEP = 1.0 / (FPS * 8)
ANGLES = [0.0]
for n in range(int(SECS / STEP) + 8):
    ANGLES.append(ANGLES[-1] + 2 * math.pi * speed_at(n * STEP) * STEP)


def point(s, t):
    (sx, sy), ang = scale_at(t), ANGLES[max(0, int(round(t / STEP)))] + s["ph"]
    x, y = math.cos(ang) * RX * sx, math.sin(ang) * RY * sy
    c, sn = math.cos(s["tilt"]), math.sin(s["tilt"])
    return CX + x * c - y * sn, CY + x * sn + y * c, math.sin(ang)  # depth > 0: in front of the words


def lights_alpha(t):
    if t < LIGHTS_BACK[0]:
        return 1.0 - smoothstep(*LIGHTS_FADE, t)
    return smoothstep(*LIGHTS_BACK, t) * (1.0 - smoothstep(SPIRAL_OUT[1] - 0.35, SPIRAL_OUT[1], t))


random.seed(11)
crystals = []


def burst(t, n, spread, maxlife):
    for _ in range(n):
        ang, sp = random.uniform(0, 2 * math.pi), random.uniform(150, 520) * spread
        crystals.append([CX + random.uniform(-tw / 2, tw / 2) * 0.9, CY + random.uniform(-th / 2, th / 2), math.cos(ang) * sp,
                         math.sin(ang) * sp * 0.6, t, random.uniform(0.5, maxlife), random.uniform(6, 14), random.uniform(0, 3.1)])


tmp = tempfile.mkdtemp(prefix="subscribe_")
flashed_in = flashed_out = False
for i in range(int(SECS * FPS)):
    t = i / FPS
    wa_in = smoothstep(T_FLASH_IN - 0.35, T_FLASH_IN + 0.1, t)
    k_out = smoothstep(T_FLASH_OUT - 0.1, SPIRAL_OUT[1] - 0.2, t)
    wa = wa_in * (1 - k_out)
    wscale = 1.12 - 0.12 * wa_in - 0.3 * k_out
    flash = max(0.0, 1 - abs(t - T_FLASH_IN) / 0.25) + 0.7 * max(0.0, 1 - abs(t - T_FLASH_OUT) / 0.25)
    if not flashed_in and t >= T_FLASH_IN:
        burst(t, 40, 1.0, 1.3)
        flashed_in = True
    if not flashed_out and t >= T_FLASH_OUT:
        burst(t, 60, 1.3, 1.2)
        flashed_out = True
    la = lights_alpha(t)

    back, front, glowb, glowf = (Image.new("RGBA", (W, H), (0, 0, 0, 0)) for _ in range(4))
    for s in (STREAKS if la > 0.01 else []):
        pts = [point(s, max(0.0, t - j / (FPS * SUB))) for j in range(TRAIL * SUB)]
        for j in range(TRAIL * SUB - 1):
            (x1, y1, d1), (x2, y2, _) = pts[j], pts[j + 1]
            k = 1 - j / (TRAIL * SUB)
            layer, glow = (front, glowf) if d1 > 0 else (back, glowb)
            dim = (1.0 if d1 > 0 else 0.55) * la
            ImageDraw.Draw(glow).line((x1, y1, x2, y2), fill=RING + (int(230 * k * dim),), width=int(10 + 26 * k))
            ImageDraw.Draw(layer).line((x1, y1, x2, y2), fill=CORE + (int(255 * k * dim),), width=max(3, int(13 * k)))
        x, y, d = pts[0]
        layer, glow = (front, glowf) if d > 0 else (back, glowb)
        ImageDraw.Draw(glow).ellipse((x - 46, y - 46, x + 46, y + 46), fill=RING + (int(230 * la),))
        ImageDraw.Draw(layer).ellipse((x - 11, y - 11, x + 11, y + 11), fill=(255, 255, 255, int(255 * la)))
    frame = Image.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)), glowb.filter(ImageFilter.GaussianBlur(14)))
    frame = Image.alpha_composite(frame, back)
    if wa > 0:
        halo = Image.new("RGBA", (W, H), RING + (0,))
        halo.putalpha(halo_a.point(lambda v: int(v * min(1.0, 0.3 * wa + 1.2 * flash))))
        wl = Image.alpha_composite(halo, word)
        if flash > 0:
            hot = Image.new("RGBA", (W, H), CORE + (0,))
            hot.putalpha(glyph.filter(ImageFilter.GaussianBlur(4)).point(lambda v: int(v * min(1.0, flash))))
            wl = Image.alpha_composite(wl, hot)
        if abs(wscale - 1) > 1e-3:
            big = wl.resize((int(W * wscale), int(H * wscale)), Image.LANCZOS)
            wl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            wl.paste(big, (int(CX - CX * wscale), int(CY - CY * wscale)))
        wl.putalpha(wl.getchannel("A").point(lambda v: int(v * wa)))
        frame = Image.alpha_composite(frame, wl)
    frame = Image.alpha_composite(frame, glowf.filter(ImageFilter.GaussianBlur(14)))
    frame = Image.alpha_composite(frame, front)
    if T_FLASH_IN + 0.4 < t < T_FLASH_OUT - 0.3 and random.random() < 0.3:
        crystals.append([CX + random.uniform(-RX, RX), CY + random.uniform(-RY, RY), random.uniform(-30, 30), random.uniform(-60, -20),
                         t, random.uniform(0.8, 1.6), random.uniform(5, 10), random.uniform(0, 3.1)])
    cg, cs = Image.new("RGBA", (W, H), (0, 0, 0, 0)), Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd, sd = ImageDraw.Draw(cg), ImageDraw.Draw(cs)
    for c in crystals:
        age = t - c[4]
        if 0 <= age <= c[5]:
            al = (1 - age / c[5]) ** 1.5
            x, y, r, rot = c[0] + c[2] * age, c[1] + c[3] * age + 80 * age * age, c[6], c[7] + age * 5
            pts = [(x + math.cos(rot + q) * r * (1.8 if q in (0, math.pi) else 0.8), y + math.sin(rot + q) * r * (1.8 if q in (0, math.pi) else 0.8))
                   for q in (0, math.pi / 2, math.pi, 3 * math.pi / 2)]
            gd.ellipse((x - r * 2.5, y - r * 2.5, x + r * 2.5, y + r * 2.5), fill=RING + (int(150 * al),))
            sd.polygon(pts, fill=CRYSTAL + (int(255 * al),), outline=CORE + (int(255 * al),))
    frame = Image.alpha_composite(frame, cg.filter(ImageFilter.GaussianBlur(8)))
    frame = Image.alpha_composite(frame, cs)
    frame.save(os.path.join(tmp, f"f_{i:04d}.png"))

out = a.out or os.path.join(ROOT, "brand", f"subscribe_{lang}.mov")
os.makedirs(os.path.dirname(out), exist_ok=True)
ff("-framerate", FPS, "-i", os.path.join(tmp, "f_%04d.png"), "-c:v", "qtrle", out)
shutil.rmtree(tmp, ignore_errors=True)
print(f"{out}: {SECS:.1f} s ({TEXT})")
