"""Subtitles from the takes' word timings, on each video's own clock:
  final/<prefix>_<episode>_long.<lang>.srt for the main language and every language in translations.json (for
  YouTube: the long video has no burned subtitles), and work/cues_short.json for the Short's captions.
Cues: <= 2 lines of 42 characters, 1-6 s, breaking at sentence ends and pauses; transcription fixes from
episode.json subtitles.fixes. Translations: translations.json = [{"<main>": "cue text", "en": "..."}], matched to
the cues by text (fuzzy); missing ones are written to translations.todo.json for you to fill in.
    python tools/make_subs.py episodes/2026-01-31
"""
import argparse, difflib, json, os, re, textwrap
from common import Episode, words_of, duration

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("episode")
a = ap.parse_args()
ep = Episode(a.episode)
cfg, ch = ep.cfg, ep.channel
main = ch["languages"]["main"]
fixes = cfg.get("subtitles", {}).get("fixes", [])


def long_words():
    out = []
    if cfg["takes"].get("intro"):
        for w in words_of(ep, "intro"):
            out.append((w["s"], w["e"], w["w"].strip()))
        out.append(None)
        shift = duration(ep.path("work", "intro.mp4"))
    else:
        shift = 0.0
    for w in words_of(ep, "main"):
        s, e = ep.cut_time(w["s"]), ep.cut_time(w["e"])
        if s is not None and e is not None:
            out.append((shift + s, shift + e, w["w"].strip()))
    return out


def short_words():
    out = []
    for take, a_, b_, t0 in ep.short_lines():
        start = a_ - ep.PAD
        for w in words_of(ep, take):
            if w["e"] > a_ + 0.05 and w["s"] <= b_:
                out.append((t0 + w["s"] - start, t0 + w["e"] - start, w["w"].strip()))
        out.append(None)
    return out


def cues(words):
    res, cur = [], []
    def flush():
        if cur:
            res.append([cur[0][0], cur[-1][1], " ".join(w[2] for w in cur)]); cur.clear()
    for w in words:
        if w is None:
            flush(); continue
        if cur:
            text = " ".join(x[2] for x in cur)
            if (w[0] - cur[-1][1] > 0.8 or len(text) + len(w[2]) > 76 or w[1] - cur[0][0] > 5.5
                    or (text[-1] in ".?!" and len(text) > 25)):
                flush()
        cur.append(w)
    flush()
    for c in res:
        for wrong, right in fixes:
            c[2] = re.sub(re.escape(wrong), right, c[2])
        c[1] = max(c[1] + 0.3, c[0] + 1.0)
    for i in range(len(res) - 1):
        res[i][1] = min(res[i][1], res[i + 1][0] - 0.05)
    return res


def stamp(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int(round((s % 1) * 1000)) % 1000:03}"


def write_srt(path, items):
    with open(path, "w", encoding="utf-8") as f:
        for i, (a_, b_, text) in enumerate(items, 1):
            f.write(f"{i}\n{stamp(a_)} --> {stamp(b_)}\n" + "\n".join(textwrap.wrap(text, 42)[:2]) + "\n\n")


long_cues, short_cues = cues(long_words()), cues(short_words())
json.dump(long_cues, open(ep.path("work", "cues_long.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
json.dump(short_cues, open(ep.path("work", "cues_short.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
write_srt(ep.path("final", ep.out("long", ext=f"{main}.srt")), long_cues)

tr_path = ep.path(cfg.get("translations", "translations.json"))
table = json.load(open(tr_path, encoding="utf-8")) if os.path.exists(tr_path) else []
langs = ch["languages"].get("extra", [])
def plain(x):
    return " ".join("".join(c for c in w if c.isalnum()) for w in x.lower().split())
def translate(text, lang):
    """The translation whose original matches the cue best (ignoring case and punctuation), if close enough."""
    score = lambda r: difflib.SequenceMatcher(None, plain(r.get(main, "")), plain(text)).ratio()
    best = max(table, key=score, default=None)
    return best[lang] if best and score(best) > 0.8 and best.get(lang) else None
todo = []
for lang in langs:
    for name, cs in (("long", long_cues), ("short", short_cues)):
        out = []
        for a_, b_, text in cs:
            t = translate(text, lang)
            if t is None:
                todo.append(text)
            out.append((a_, b_, t or text))
        if name == "long":
            write_srt(ep.path("final", ep.out("long", ext=f"{lang}.srt")), out)
        else:
            json.dump(out, open(ep.path("work", f"cues_short_{lang}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
if todo:
    rows = [{main: t, **{l: "" for l in langs}} for t in dict.fromkeys(todo)]
    json.dump(rows, open(ep.path("translations.todo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(rows)} cues without a translation -> translations.todo.json (fill it, rename to translations.json, run again)")
print(f"long: {len(long_cues)} cues, short: {len(short_cues)} cues")
