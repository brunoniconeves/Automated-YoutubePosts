"""The long video (16:9, 1920x1080), no burned subtitles (they go to YouTube as .srt, see make_subs.py):
  1. the intro take full screen (the vertical take centred over a blurred copy of itself),
  2. the main take cut to long.cuts, the speaker in a framed square bottom-right over b-roll chosen per topic,
     with optional labels,
  3. the ending b-roll with no voice, where the music starts (fade in 1 s), then the 16:9 sting, music fading out.
Writes work/long.mp4 (full quality) and preview/<prefix>_<episode>_long_preview.mp4 (854x480, light).
    python tools/build_long.py episodes/2026-01-31
"""
import argparse, os
from common import Episode, ff, duration, decode_check, font_arg, V, ENC, AUD, FAST

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("episode")
a = ap.parse_args()
ep = Episode(a.episode)
cfg, ch = ep.cfg, ep.channel
W = lambda *p: ep.path("work", *p)
voice = f"loudnorm=I={ch['voice_level_lufs']}:TP=-1.5:LRA=11"

# 1. Intro, full screen.
x, y, w, h = cfg["face"]["full"]
intro_take = ep.path(cfg["takes"]["intro"]) if cfg["takes"].get("intro") else None
if intro_take:
    ff("-i", intro_take, "-filter_complex",
       f"[0:v]fps=30,split[a][b];[a]scale=1920:-2,crop=1920:1080,boxblur=30:2,eq=brightness=-0.12[bg];"
       f"[b]crop={w}:{h}:{x}:{y},scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:0,{V}[v]",
       "-map", "[v]", "-map", "0:a", "-af", voice, *ENC, *AUD, W("intro.mp4"))

# 2. The main take cut, and the b-roll under it, topic by topic.
cuts = ep.cuts()
sel = "+".join(f"between(t,{a_},{b_})" for a_, b_ in cuts)
ff("-i", ep.path(cfg["takes"]["main"]), "-vf", f"select='{sel}',setpts=N/FRAME_RATE/TB,{V}",
   "-af", f"aselect='{sel}',asetpts=N/SR/TB,{voice}", *ENC, *AUD, W("cut.mp4"))
body = duration(W("cut.mp4"))

def clip(i, c):
    out = W(f"clip_{i:03d}.mp4")
    if not os.path.exists(out):
        ff("-ss", c.get("from", 0), "-t", c["duration"], "-i", ep.asset(c["file"]), "-vf",
           f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,{V}", "-an", *ENC, out)
    return out, c["duration"]

topics = sorted(cfg["long"]["topics"], key=lambda t: t["from"])
starts = [max(0.0, ep.cut_time(t["from"]) or 0.0) for t in topics]
starts[0] = 0.0
lst, n = [], 0
for k, t in enumerate(topics):
    left = (starts[k + 1] if k + 1 < len(topics) else body) - starts[k]
    clips = [clip(n + j, c) for j, c in enumerate(t["clips"])]
    n += len(clips)
    j = 0
    while left > 0.05:
        path, d = clips[j % len(clips)]
        use = min(d, left)
        lst.append((path, use)); left -= use; j += 1
with open(W("bg.txt"), "w") as f:
    for path, use in lst:
        f.write(f"file '{path}'\noutpoint {use:.3f}\n")
ff("-f", "concat", "-safe", "0", "-i", W("bg.txt"), "-vf", V, *ENC, W("bg.mp4"))

px, py, pw, ph = cfg["face"]["pip"]
font = font_arg(ch["labels_font"])
labels = ""
for lab in cfg["long"].get("labels", []):
    a_, b_ = ep.cut_time(lab["from"]), ep.cut_time(lab["to"])
    if a_ is None or b_ is None:
        continue
    text = lab["text"].replace(":", "\\:").replace("'", "’")
    labels += (f",drawtext=fontfile='{font}':text='{text}':fontsize=58:fontcolor=white:box=1:boxcolor=0x10233a@0.75:"
               f"boxborderw=24:x=(w-tw)/2:y=90:enable='between(t,{a_:.2f},{b_:.2f})'")
ff("-i", W("bg.mp4"), "-i", W("cut.mp4"), "-filter_complex",
   f"[1:v]crop={pw}:{ph}:{px}:{py},scale=400:400,pad=412:412:6:6:color=white[pip];"
   f"[0:v][pip]overlay=W-w-40:H-h-40{labels},{V}[v]",
   "-map", "[v]", "-map", "1:a", *ENC, *AUD, "-shortest", W("body.mp4"))

# 3. Ending b-roll (no voice), the sting, the music from where the voice ends.
e = cfg["long"]["ending"]
ff("-ss", e.get("from", 0), "-t", e["duration"], "-i", ep.asset(e["file"]), "-f", "lavfi", "-t", e["duration"],
   "-i", "anullsrc=r=48000:cl=stereo", "-vf",
   f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fade=t=out:st={e['duration'] - 1}:d=1,{V}",
   "-map", "0:v", "-map", "1:a", *ENC, *AUD, "-shortest", W("ending.mp4"))
ff("-i", ep.asset(ch["brand"]["sting_h"]), "-vf", f"scale=1920:1080:flags=lanczos,{V}", *ENC, *AUD, W("sting_h.mp4"))
parts = ([W("intro.mp4")] if intro_take else []) + [W("body.mp4"), W("ending.mp4"), W("sting_h.mp4")]
with open(W("long.txt"), "w") as f:
    for p in parts:
        f.write(f"file '{p}'\n")
ff("-f", "concat", "-safe", "0", "-i", W("long.txt"), "-vf", V, *ENC, *AUD, W("long_voice.mp4"))
music_at = (duration(W("intro.mp4")) if intro_take else 0.0) + duration(W("body.mp4"))
total = duration(W("long_voice.mp4"))
span = total - music_at
ms = int(round(music_at * 1000))
ff("-i", W("long_voice.mp4"), "-i", ep.asset(ch["brand"]["music"]), "-filter_complex",
   f"[1:a]atrim=0:{span:.3f},asetpts=N/SR/TB,loudnorm=I={ch['music_level_lufs']}:TP=-1.5:LRA=11,aresample=48000,"
   f"aformat=channel_layouts=stereo,afade=t=in:d=1,afade=t=out:st={max(span - 2.5, 0):.3f}:d=2.5,adelay={ms}|{ms}[m];"
   f"[0:a][m]amix=inputs=2:normalize=0:duration=first[a];[0:v]{V}[v]",
   "-map", "[v]", "-map", "[a]", *ENC, *AUD, *FAST, W("long.mp4"))
preview = ep.path("preview", ep.out("long_preview"))
ff("-i", W("long.mp4"), "-vf", "scale=854:480,format=yuv420p", "-c:v", "libx264", "-profile:v", "high", "-preset", "slow",
   "-b:v", "330k", "-maxrate", "450k", "-bufsize", "900k", "-c:a", "aac", "-b:a", "96k", "-ar", "48000", *FAST, preview)
print(f"music starts at {music_at:.2f} s; long {total:.1f} s")
print(preview, "|", decode_check(preview))
