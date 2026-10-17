"""Burned-in captions for the Short ("queimada" style): a few uppercase words at a time in a heavy face, white
with a dark outline and a soft shadow, the word being said on a coloured rounded box; on the seam between the
b-roll and the speaker, never over the sting.
Main language: word times measured by faster-whisper on the Short's own audio (work/short_base_<main>.mp4), with
the transcript's spelling. Other languages: the translated cue (work/cues_short_<lang>.json, from make_subs.py)
timed inside the original cue, each word's share by its length.
One caption image per video frame (absolute times: overlapping captions cannot drift), then a sync report.
Writes work/short_<lang>.mp4 and preview/<prefix>_<episode>_short_<lang>_preview.mp4 (540x960).
    python tools/captions.py episodes/2026-01-31 pt
"""
import argparse, difflib, json, os, shutil, statistics, subprocess
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from common import Episode, ff, duration, decode_check, words_of, FF, ENC, AUD, FAST

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("episode")
ap.add_argument("lang")
a = ap.parse_args()
ep = Episode(a.episode)
cfg, ch = ep.cfg, ep.channel
cap = ch["captions"]
main = ch["languages"]["main"]
FONT = ImageFont.truetype(cap["font"], cap["size"])
BOX = tuple(int(cap["box_color"][i:i + 2], 16) for i in (1, 3, 5)) + (255,)
WID, HEI, Y = 1080, 420, cap["y"]
END = ep.short_speech_len() - 0.55        # the sting's crossfade starts here (see build_short.py)
base = ep.path("work", f"short_base_{a.lang}.mp4")
OUT = ep.path("work", f"captions_{a.lang}")
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
norm = lambda x: "".join(c for c in x.lower() if c.isalnum())


def transcript_words():
    out = []
    for take, a_, b_, t0 in ep.short_lines():
        start = a_ - ep.PAD
        for w in words_of(ep, take):
            if w["e"] > a_ + 0.05 and w["s"] <= b_:
                out.append((t0 + w["s"] - start, t0 + w["e"] - start, w["w"].strip()))
        out.append(None)
    return out


def measured(lang):
    """faster-whisper word timings on the Short's own audio (cached)."""
    cache = ep.path("work", f"short_audio_{lang}.words.json")
    if not os.path.exists(cache):
        wav = ep.path("work", "short_audio.wav")
        ff("-i", ep.path("work", f"short_base_{lang}.mp4"), "-t", f"{END:.2f}", "-vn", "-ac", "1", "-ar", "16000", wav)
        from faster_whisper import WhisperModel
        seg, _ = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8").transcribe(wav, language=main, word_timestamps=True)
        json.dump([{"w": w.word, "s": round(w.start, 2), "e": round(w.end, 2)} for s in seg for w in s.words],
                  open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return json.load(open(cache, encoding="utf-8"))


def aligned(words, ref):
    """The transcript's words, timed by the measured ones where they match; the median shift elsewhere."""
    flat = [w for w in words if w]
    sm = difflib.SequenceMatcher(None, [norm(w[2]) for w in flat], [norm(r["w"]) for r in ref], autojunk=False)
    fixed = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            fixed[blk.a + k] = (ref[blk.b + k]["s"], ref[blk.b + k]["e"])
    shift = statistics.median([fixed[i][0] - flat[i][0] for i in fixed]) if fixed else 0.0
    out, i = [], 0
    for w in words:
        if w is None:
            out.append(None); continue
        s, e = fixed.get(i, (w[0] + shift, w[1] + shift))
        out.append((s, e, w[2])); i += 1
    return out, shift


def translated(lang, shift):
    out = []
    for a_, b_, text in json.load(open(ep.path("work", f"cues_short_{lang}.json"), encoding="utf-8")):
        ws = text.split()
        span = max(b_ - 0.2, a_ + 0.5) - a_
        total = sum(len(x) + 2 for x in ws)
        t = a_ + shift
        for x in ws:
            d = span * (len(x) + 2) / total
            out.append((t, t + d, x)); t += d
        out.append(None)
    return out


def chunk(words):
    res, cur = [], []
    for w in words:
        if w is None:
            if cur: res.append(cur); cur = []
            continue
        if cur and (len(cur) >= cap["max_words"] or len(" ".join(x[2] for x in cur + [w])) > cap["max_chars"]
                    or w[0] - cur[-1][1] > 0.5):
            res.append(cur); cur = []
        cur.append(w)
        if w[2][-1:] in ".?!,":
            res.append(cur); cur = []
    if cur: res.append(cur)
    return res


def render(words, active, path):
    text = [w.upper() for w in words]
    space = FONT.getlength(" ")
    widths = [FONT.getlength(t) for t in text]
    if sum(widths) + space * (len(text) - 1) <= WID - 120 or len(text) == 1:
        lines = [list(enumerate(text))]
    else:   # two lines as even as can be
        k = min(range(1, len(text)), key=lambda k: max(sum(widths[:k]) + space * (k - 1), sum(widths[k:]) + space * (len(text) - k - 1)))
        lines = [list(enumerate(text))[:k], list(enumerate(text))[k:]]
    asc, desc = FONT.getmetrics()
    lh = asc + desc + 18
    top = (HEI - lh * len(lines)) // 2
    img = Image.new("RGBA", (WID, HEI), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (WID, HEI), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    placed = []
    for li, line in enumerate(lines):
        x = (WID - (sum(FONT.getlength(t) for _, t in line) + space * (len(line) - 1))) / 2
        y = top + li * lh
        for i, t in line:
            placed.append((x, y, t, i)); sd.text((x + 4, y + 7), t, font=FONT, fill=(0, 0, 0, 170))
            x += FONT.getlength(t) + space
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img)
    for x, y, t, i in placed:
        if i == active:
            l, tt, r, bb = d.textbbox((x, y), t, font=FONT)
            d.rounded_rectangle((l - 16, tt - 12, r + 16, bb + 14), radius=16, fill=BOX)
    for x, y, t, i in placed:
        d.text((x, y), t, font=FONT, fill=(255, 255, 255, 255), stroke_width=0 if i == active else 6, stroke_fill=(18, 18, 30, 255))
    img.save(path)


ref = measured(main) if a.lang == main else None
if a.lang == main:
    words, shift = aligned(transcript_words(), ref)
else:
    _, shift = aligned(transcript_words(), measured(main))
    words = translated(a.lang, shift)

states, n = [], 0
Image.new("RGBA", (WID, HEI), (0, 0, 0, 0)).save(os.path.join(OUT, "blank.png"))
for c in chunk(words):
    start, end = c[0][0], min(c[-1][1] + 0.15, END)
    if start >= END:
        continue
    for k, w in enumerate(c):
        ws, we = max(w[0], start), min(c[k + 1][0] if k + 1 < len(c) else end, END)
        if we > ws:
            name = f"s{n:04d}.png"; n += 1
            render([x[2] for x in c], k, os.path.join(OUT, name))
            states.append((ws, we, name, c, k))
seq = os.path.join(OUT, "seq")
os.makedirs(seq)
for frame in range(int(round(duration(base) * 30))):
    t = (frame + 0.5) / 30
    held = [s for s in states if s[0] <= t < s[1]]
    name = max(held, key=lambda s: s[0])[2] if held else "blank.png"
    os.link(os.path.join(OUT, name), os.path.join(seq, f"f_{frame:05d}.png"))

full = ep.path("work", f"short_{a.lang}.mp4")
subprocess.run([FF, "-y", "-v", "error", "-i", base, "-framerate", "30", "-i", os.path.join(seq, "f_%05d.png"), "-filter_complex",
                f"[0:v][1:v]overlay=0:{Y}:eof_action=pass,format=yuv420p[v]", "-map", "[v]", "-map", "0:a", *ENC, *AUD, *FAST, full], check=True)
preview = ep.path("preview", ep.out("short_preview", a.lang))
ff("-i", full, "-vf", "scale=540:960,format=yuv420p", "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "28",
   "-c:a", "aac", "-b:a", "96k", "-ar", "48000", *FAST, preview)
print(f"{a.lang}: {n} caption states, timing shift {shift:+.2f} s")

if a.lang == main:   # sync report: is the spoken word the boxed one 0.1 s after it starts?
    hits, total = 0, 0
    for r in ref:
        if r["s"] >= END:
            continue
        total += 1
        held = [s for s in states if s[0] <= r["s"] + 0.1 < s[1]]
        if held:
            _, _, _, c, k = max(held, key=lambda s: s[0])
            hits += norm(c[k][2]) == norm(r["w"])
    print(f"sync: {hits}/{total} spoken words boxed at +0.1 s")
print(preview, "|", decode_check(preview))
