"""The Short's base for each language (9:16, 1080x1920, before captions): b-roll in a square on top with an
optional title per language, the speaker's excerpts (short.lines) below; cut right after the last word, a 0.5 s
crossfade into the 9:16 sting, the music starting with the crossfade.
Writes work/short_base_<lang>.mp4 for the main language and each extra one.
    python tools/build_short.py episodes/2026-01-31
"""
import argparse
from common import Episode, ff, duration, font_arg, V, ENC, AUD, FAST

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("episode")
a = ap.parse_args()
ep = Episode(a.episode)
cfg, ch = ep.cfg, ep.channel
W = lambda *p: ep.path("work", *p)
XF = 0.5

# The speaker below: each excerpt with 0.3 s either side, one after the other.
x, y, w, h = cfg["face"]["short"]
parts = []
for i, (take, a_, b_, _) in enumerate(ep.short_lines()):
    out = W(f"line_{i:02d}.mp4")
    ff("-ss", f"{a_ - ep.PAD:.3f}", "-t", f"{b_ - a_ + 2 * ep.PAD:.3f}", "-i", ep.path(cfg["takes"][take]),
       "-vf", f"crop={w}:{h}:{x}:{y},scale=1080:840,{V}", "-af", "aresample=48000,aformat=channel_layouts=stereo",
       *ENC, *AUD, out)
    parts.append(out)
with open(W("lines.txt"), "w") as f:
    for p in parts:
        f.write(f"file '{p}'\n")
speech = ep.short_speech_len()
ff("-f", "concat", "-safe", "0", "-i", W("lines.txt"), "-vf", V,
   "-af", f"loudnorm=I={ch['voice_level_lufs']}:TP=-1.5:LRA=11", *ENC, *AUD, W("bottom.mp4"))

def crop_x(c):
    """Where the square is taken from the 16:9 clip: "left", "center" (default), "right" or a pixel x."""
    x = c.get("crop", "center")
    return {"left": "0", "center": "(iw-1080)/2", "right": "iw-1080"}.get(x, str(x))


# The b-roll on top, in order, the last one trimmed to the speech.
tops, t, spans = [], 0.0, []
for i, c in enumerate(cfg["short"]["top"]):
    if t >= speech:
        break
    d = min(c["duration"], speech - t)
    out = W(f"top_{i:02d}.mp4")
    ff("-ss", c.get("from", 0), "-t", f"{d:.3f}", "-i", ep.asset(c["file"]), "-vf",
       f"scale=-2:1080,crop=1080:1080:{crop_x(c)},{V}", "-an", *ENC, out)
    tops.append(out); spans.append((t, t + d, c.get("title", {}))); t += d
with open(W("top.txt"), "w") as f:
    for p in tops:
        f.write(f"file '{p}'\n")
ff("-f", "concat", "-safe", "0", "-i", W("top.txt"), "-vf", V, *ENC, W("top.mp4"))

font = font_arg(ch["labels_font"])
langs = [ch["languages"]["main"]] + ch["languages"].get("extra", [])
off = speech - XF - ep.PAD + 0.25   # the crossfade starts just after the last word (it ends ~PAD before the speech end)
for lang in langs:
    titles = ""
    for s, e, title in spans:
        text = title.get(lang, "")
        if text:
            text = text.replace(":", "\\:").replace("'", "’")
            titles += (f",drawtext=fontfile='{font}':text='{text}':fontsize=48:fontcolor=white:box=1:boxcolor=black@0.55:"
                       f"boxborderw=16:x=(w-tw)/2:y=40:enable='between(t,{s:.2f},{min(e, s + 6) if s > 0 else e:.2f})'")
    ms = int(round(off * 1000))
    ff("-i", W("top.mp4"), "-i", W("bottom.mp4"), "-i", ep.asset(ch["brand"]["sting_v"]), "-i", ep.asset(ch["brand"]["music"]),
       "-filter_complex",
       f"[0:v][1:v]vstack{titles},trim=0:{off + XF:.3f},setpts=PTS-STARTPTS,{V}[sv];"
       f"[2:v]scale=1080:1920:flags=lanczos,{V}[vv];[sv][vv]xfade=transition=fade:duration={XF}:offset={off:.3f},format=yuv420p[v];"
       f"[1:a]atrim=0:{off + XF:.3f},asetpts=N/SR/TB,afade=t=out:st={off + XF - 0.15:.3f}:d=0.15,apad[voice];"
       f"[3:a]atrim=0:9,asetpts=N/SR/TB,loudnorm=I={ch['music_level_lufs']}:TP=-1.5:LRA=11,aresample=48000,"
       f"aformat=channel_layouts=stereo,afade=t=in:d=0.5,afade=t=out:st=7:d=2,adelay={ms}|{ms}[m];"
       f"[voice][m]amix=inputs=2:normalize=0:duration=longest,atrim=0:{off + duration(ep.asset(ch['brand']['sting_v'])):.3f}[a]",
       "-map", "[v]", "-map", "[a]", *ENC, *AUD, *FAST, W(f"short_base_{lang}.mp4"))
    print(f"work/short_base_{lang}.mp4: {duration(W(f'short_base_{lang}.mp4')):.1f} s, sting at {off:.2f} s")
