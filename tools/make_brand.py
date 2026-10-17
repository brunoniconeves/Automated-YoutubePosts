"""Placeholder brand assets for a channel that has none yet: a logo, the 16:9 and 9:16 stings (9 s, the logo
popping in over a moving gradient, ending on black) and a music loop synthesized by ffmpeg. Replace them with
your own any time; the pipeline only reads the paths in channel.json.
    python tools/make_brand.py [--name "Your Channel"]
"""
import argparse, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from common import ROOT, ff, V, ENC, AUD, FAST, load_channel

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--name", help="channel name on the logo (default: channel.json name)")
a = ap.parse_args()
ch = load_channel()
name = (a.name or ch["name"]).upper()
brand = os.path.join(ROOT, "brand")
os.makedirs(brand, exist_ok=True)

# Logo: a rounded badge with a play mark and the name in two lines.
S = 1024
logo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
grad = Image.new("RGBA", (S, S))
for y in range(S):
    t = y / S
    grad.paste((int(106 + (40 - 106) * t), int(60 + (170 - 60) * t), int(240 + (255 - 240) * t), 255), (0, y, S, y + 1))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle((40, 40, S - 40, S - 40), radius=200, fill=255)
logo.paste(grad, (0, 0), mask)
d = ImageDraw.Draw(logo)
d.polygon([(400, 230), (400, 470), (610, 350)], fill=(255, 255, 255, 255))
font = ImageFont.truetype(ch["captions"]["font"], 112)
words = name.split()
lines = [" ".join(words[: len(words) // 2 or 1]), " ".join(words[len(words) // 2 or 1:])] if len(words) > 1 else [name]
for i, line in enumerate(l for l in lines if l):
    w = d.textlength(line, font=font)
    d.text(((S - w) / 2, 560 + i * 140), line, font=font, fill=(255, 255, 255, 255), stroke_width=4, stroke_fill=(30, 20, 80, 255))
shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
shadow.paste((0, 0, 0, 110), (0, 0), mask.filter(ImageFilter.GaussianBlur(24)))
final = Image.alpha_composite(shadow, logo)
logo_path = os.path.join(brand, "logo.png")
final.save(logo_path)

# Stings: 9 s, the logo grows in with an ease and settles, the gradient drifts, fade in and out.
for tag, w, h, size in (("h", 1920, 1080, 620), ("v", 1080, 1920, 760)):
    ff("-f", "lavfi", "-t", "9", "-i", f"gradients=s={w}x{h}:c0=0x1b1340:c1=0x2a5bd7:c2=0x6a3cf0:n=3:speed=0.02:r=30",
       "-loop", "1", "-t", "9", "-i", logo_path, "-f", "lavfi", "-t", "9", "-i", "anullsrc=r=48000:cl=stereo",
       "-filter_complex",
       f"[1:v]scale=w='{size}*(0.55+0.45*min(1,t/1.2)*(2-min(1,t/1.2)))':h=-1:eval=frame,format=rgba[l];"
       f"[0:v][l]overlay=x=(W-w)/2:y=(H-h)/2:format=auto,fade=t=in:d=0.6,fade=t=out:st=8.2:d=0.8,{V}[v]",
       "-map", "[v]", "-map", "2:a", *ENC, *AUD, *FAST, "-shortest", os.path.join(brand, f"sting_{tag}.mp4"))

# Music: a soft four-chord loop (C G Am F, 90 bpm) of plucked sines, a little echo, 60 s, levelled.
chords = [(261.6, 329.6, 392.0), (196.0, 246.9, 293.7), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6)]
bar = 4 * 60 / 90
def chord(i):
    return "+".join(f"sin(2*PI*{f}*t)" for f in chords[i])
expr = "+".join(f"eq(mod(floor(t/{bar:.4f}),4),{i})*({chord(i)})" for i in range(4))
pluck = f"exp(-2.2*mod(t,{bar / 4:.4f}))"
ff("-f", "lavfi", "-t", "60", "-i", f"aevalsrc='0.12*({expr})*{pluck}':s=48000",
   "-af", "aformat=channel_layouts=stereo,lowpass=f=3000,aecho=0.8:0.6:120|240:0.25|0.15,afade=t=in:d=1,afade=t=out:st=57:d=3,loudnorm=I=-16:TP=-1.5",
   "-c:a", "aac", "-b:a", "192k", os.path.join(brand, "music.m4a"))
print("brand/: logo.png, sting_h.mp4, sting_v.mp4, music.m4a")
