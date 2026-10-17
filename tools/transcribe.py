"""Transcribes a take with faster-whisper on the CPU: <take>.srt and <take>.txt beside it, and the word timings
in <take>.words.json (the cuts, the subtitles and the captions all come from these).
    python tools/transcribe.py episodes/2026-01-31/takes/main.mp4 [--lang pt] [--model large-v3-turbo]
"""
import argparse, json, os
from faster_whisper import WhisperModel


def stamp(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int((s % 1) * 1000):03}"


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("video")
ap.add_argument("--lang", default="pt")
ap.add_argument("--model", default="large-v3-turbo")
a = ap.parse_args()
model = WhisperModel(a.model, device="cpu", compute_type="int8")
segments, info = model.transcribe(a.video, language=a.lang, word_timestamps=True, vad_filter=True)
base = os.path.splitext(a.video)[0]
srt, txt, words = [], [], []
for i, s in enumerate(segments, 1):
    srt.append(f"{i}\n{stamp(s.start)} --> {stamp(s.end)}\n{s.text.strip()}\n")
    txt.append(f"[{stamp(s.start)[:8]}] {s.text.strip()}")
    words += [{"w": w.word, "s": round(w.start, 2), "e": round(w.end, 2), "p": round(w.probability, 2)} for w in s.words]
    print(txt[-1], flush=True)
open(base + ".srt", "w", encoding="utf-8").write("\n".join(srt))
open(base + ".txt", "w", encoding="utf-8").write("\n".join(txt) + "\n")
json.dump(words, open(base + ".words.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"done: {info.duration:.0f} s of audio")
