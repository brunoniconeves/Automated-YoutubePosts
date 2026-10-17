"""Placeholder brand assets for a channel that has none yet: a logo, the 16:9 and 9:16 stings and a music bed.
With Blender (--blender, $BLENDER or on PATH) the stings are 3D (tools/brand_blender.py: a glossy badge popping in,
a light sweep, out-of-focus lights), finished here with bloom, fades and a synthesized whoosh/boom/shimmer;
without it, a 2D version. The music (pad, arpeggio, soft kick and hi-hat) is synthesized by ffmpeg.
Replace any of them with your own; the pipeline only reads the paths in channel.json.
    python tools/make_brand.py [--name "Your Channel"] [--blender "C:/path/to/blender.exe"]
"""
import argparse, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from common import ROOT, ff, V, ENC, AUD, FAST, load_channel

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--name", help="channel name on the logo (default: channel.json name)")
ap.add_argument("--blender", default=os.environ.get("BLENDER", ""), help="blender executable: renders the 3D sting (tools/brand_blender.py); without it, a 2D sting")
ap.add_argument("--rerender", action="store_true", help="render the 3D frames again even if brand/_frames_* exist")
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

# Sound for the stings: a whoosh as the logo pops in, a low boom as it lands, a shimmer as the light sweeps.
sfx = os.path.join(brand, "_sting_sfx.wav")
ff("-f", "lavfi", "-t", "9", "-i", "anoisesrc=c=pink:a=0.6:d=9",
   "-f", "lavfi", "-t", "9", "-i", "aevalsrc='0.9*sin(2*PI*(45+90*exp(-9*t))*t)*exp(-3.5*t)':s=48000",
   "-f", "lavfi", "-t", "9", "-i",
   "aevalsrc='0.10*(sin(2*PI*1568*t)+sin(2*PI*2093*t)+sin(2*PI*2637*t)+sin(2*PI*3136*t))*exp(-1.6*t)*(0.6+0.4*sin(2*PI*7*t))':s=48000",
   "-filter_complex",
   "[0:a]atrim=0:0.75,highpass=f=300,lowpass=f=5000,afade=t=in:d=0.45,afade=t=out:st=0.45:d=0.3,volume=1.6,aformat=channel_layouts=stereo[w];"
   "[1:a]aformat=channel_layouts=stereo,adelay=480|480[b];"
   "[2:a]aformat=channel_layouts=stereo,aecho=0.8:0.7:90|180:0.35|0.2,adelay=1500|1500[s];"
   "[w][b][s]amix=inputs=3:normalize=0:duration=longest,atrim=0:9,apad=whole_dur=9,loudnorm=I=-18:TP=-2,aresample=48000",
   sfx)

# The 3D sting's frames, when Blender is at hand.
import shutil, subprocess
blender = a.blender or shutil.which("blender")
if blender:
    for tag in ("h", "v"):
        frames = os.path.join(brand, f"_frames_{tag}")
        if a.rerender or not (os.path.isdir(frames) and len(os.listdir(frames)) >= 200):
            os.makedirs(frames, exist_ok=True)
            subprocess.run([blender, "-b", "-P", os.path.join(ROOT, "tools", "brand_blender.py"), "--",
                            "--name", name, "--aspect", tag, "--out", frames], check=True)

# Stings: from Blender's frames when they exist (tools/brand_blender.py), with bloom and fades; else 2D.
bloom = ("split[a][b];[b]colorlevels=rimin=0.8:gimin=0.8:bimin=0.8,gblur=sigma=18[g];"
         "[a][g]blend=all_mode=screen:all_opacity=0.22")
for tag, w, h, size in (("h", 1920, 1080, 620), ("v", 1080, 1920, 760)):
    frames = os.path.join(brand, f"_frames_{tag}")
    out = os.path.join(brand, f"sting_{tag}.mp4")
    if os.path.isdir(frames) and len(os.listdir(frames)) >= 200:
        n = len([f for f in os.listdir(frames) if f.startswith("f_")])
        ff("-framerate", "30", "-i", os.path.join(frames, "f_%04d.png"), "-i", sfx, "-filter_complex",
           f"[0:v]{bloom},fade=t=in:d=0.35,fade=t=out:st={n / 30 - 0.8:.2f}:d=0.8,{V}[v]",
           "-map", "[v]", "-map", "1:a", *ENC, *AUD, *FAST, "-shortest", out)
        continue
    ff("-f", "lavfi", "-t", "9", "-i", f"gradients=s={w}x{h}:c0=0x1b1340:c1=0x2a5bd7:c2=0x6a3cf0:n=3:speed=0.02:r=30",
       "-loop", "1", "-t", "9", "-i", logo_path, "-i", sfx,
       "-filter_complex",
       f"[1:v]scale=w='{size}*(0.55+0.45*min(1,t/1.2)*(2-min(1,t/1.2)))':h=-1:eval=frame,format=rgba[l];"
       f"[0:v][l]overlay=x=(W-w)/2:y=(H-h)/2:format=auto,fade=t=in:d=0.6,fade=t=out:st=8.2:d=0.8,{V}[v]",
       "-map", "[v]", "-map", "2:a", *ENC, *AUD, *FAST, "-shortest", out)

# Music: 60 s at 96 bpm over C G Am F: a slow pad, a plucked arpeggio, a soft kick and hi-hat; levelled.
bpm = 96
beat = 60 / bpm
bar = 4 * beat
chords = [(261.6, 329.6, 392.0), (196.0, 246.9, 293.7), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6)]
sel = lambda i, e: f"eq(mod(floor(t/{bar:.4f}),4),{i})*({e})"
pad = "+".join(sel(i, "+".join(f"sin(2*PI*{f / 2}*t)+0.5*sin(2*PI*{f}*t*1.003)" for f in c)) for i, c in enumerate(chords))
arp = "+".join(sel(i, "+".join(f"eq(mod(floor(t/{beat / 2:.4f}),3),{k})*sin(2*PI*{c[k] * 2}*t)" for k in range(3)))
               for i, c in enumerate(chords))
ff("-f", "lavfi", "-t", "60", "-i", f"aevalsrc='0.05*({pad})':s=48000",
   "-f", "lavfi", "-t", "60", "-i", f"aevalsrc='0.10*({arp})*exp(-5*mod(t,{beat / 2:.4f}))':s=48000",
   "-f", "lavfi", "-t", "60", "-i", f"aevalsrc='0.7*sin(2*PI*(50+70*exp(-30*mod(t,{beat:.4f})))*mod(t,{beat:.4f}))*exp(-9*mod(t,{beat:.4f}))':s=48000",
   "-f", "lavfi", "-t", "60", "-i", "anoisesrc=c=white:a=0.5:d=60",
   "-filter_complex",
   "[0:a]aformat=channel_layouts=stereo,lowpass=f=1800,chorus=0.6:0.9:50|60:0.4|0.32:0.25|0.4:2|1.3[p];"
   "[1:a]aformat=channel_layouts=stereo,aecho=0.8:0.6:280|420:0.3|0.2[r];"
   "[2:a]aformat=channel_layouts=stereo,lowpass=f=200[k];"
   f"[3:a]highpass=f=7000,volume='0.18*exp(-40*mod(t+{beat / 2:.4f},{beat:.4f}))':eval=frame,aformat=channel_layouts=stereo[h];"
   "[p][r][k][h]amix=inputs=4:normalize=0,afade=t=in:d=1.5,afade=t=out:st=56:d=4,loudnorm=I=-16:TP=-1.5",
   "-c:a", "aac", "-b:a", "192k", os.path.join(brand, "music.m4a"))
print("brand/: logo.png, sting_h.mp4, sting_v.mp4, music.m4a")
