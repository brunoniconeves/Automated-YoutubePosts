"""Builds a self-contained demo episode (episodes/demo/) about this very workflow, with no camera and no project:
  - the narration from Windows' offline text-to-speech (System.Speech, a pt-BR voice), standing in for the
    phone takes: a vertical 1080x1920 "presenter" video (an avatar and a live waveform over a gradient);
  - b-roll: one slide per step of the workflow, slowly zooming; an animated gradient for the ending;
  - episode.json (cuts, topics, Short lines, titles) and translations.json (pt -> en), plus a sample roteiro.html.
Then run the pipeline on it (see README).
    python demo/make_demo.py [--voice "Microsoft Maria Desktop"]
"""
import argparse, json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from common import ROOT, FF, ff, duration, V, ENC, AUD

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--voice", default="Microsoft Maria Desktop")
ap.add_argument("--regenerate", action="store_true", help="re-make demo/assets (narration with text-to-speech, slides with a headless browser) instead of using the committed ones")
a = ap.parse_args()
EP = os.path.join(ROOT, "episodes", "demo")
# The narration and the slides are committed here, so the demo rebuilds the same without the Windows voice
# or a browser; --regenerate makes them again (and refreshes this folder).
ASSETS = os.path.join(ROOT, "demo", "assets")
for sub in ("takes", "broll", "work", "preview", "final"):
    os.makedirs(os.path.join(EP, sub), exist_ok=True)
FONT = "C:/Windows/Fonts/arialbd.ttf"
HEAVY = "C:/Windows/Fonts/ariblk.ttf"

INTRO = [("Oi! Este é um vídeo de demonstração.", "Hi! This is a demo video."),
         ("Ele foi montado inteiro por um fluxo automático.", "It was put together entirely by an automated workflow.")]
# (slide title, slide subtitle, [(pt, en), ...])
STEPS = [
    ("1 · Roteiro", "commits desde o último episódio → roteiro.html",
     [("Primeiro, o fluxo olha os commits desde o último vídeo.", "First, the workflow looks at the commits since the last video."),
      ("E monta um roteiro em HTML com os tópicos do episódio.", "And builds an HTML script with the episode's topics.")]),
    ("2 · Takes", "você grava falando livremente, no celular",
     [("Você grava a sua fala no celular, na vertical.", "You record yourself on your phone, vertically."),
      ("Pode falar à vontade, os cortes vêm depois.", "Talk freely, the cuts come later.")]),
    ("3 · Transcrição", "faster-whisper, tempo de cada palavra",
     [("A transcrição marca o tempo de cada palavra.", "The transcription marks the time of every word.")]),
    ("4 · Cenas", "captura de tela, b-roll, antes e depois",
     [("Enquanto isso, as cenas de apoio são gravadas.", "Meanwhile, the supporting footage gets recorded.")]),
    ("5 · Vídeo longo", "sem legenda na imagem · .srt em cada idioma",
     [("O vídeo longo sai sem legenda na imagem.", "The long video comes out with no burned subtitles."),
      ("As legendas vão para o YouTube em arquivos, em cada idioma.", "The subtitles go to YouTube as files, in each language.")]),
    ("6 · Shorts", "legenda queimada, palavra por palavra · PT e EN",
     [("Os Shorts ganham legenda queimada, palavra por palavra.", "The Shorts get burned captions, word by word."),
      ("E saem duas versões, uma em português e outra em inglês.", "And there are two versions, one in Portuguese and one in English.")]),
    ("7 · Prévias e finais", "você aprova as prévias, depois saem os finais",
     [("Primeiro vêm as prévias leves, e só depois os finais.", "First come light previews, and only then the finals.")]),
]
CLOSING = [("É isso. Me segue pra ver os próximos.", "That's it. Follow along for the next ones.")]


def tts(sentences, wav):
    """Each sentence to speech with a pause after it; returns the sentences' (start, end) in the take."""
    parts, times, t = [], [], 0.0
    for i, s in enumerate(sentences):
        p = os.path.join(EP, "work", f"tts_{os.path.basename(wav)}_{i:02d}.wav")
        ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.SelectVoice('{a.voice}'); $s.Rate = 0; $s.SetOutputToWaveFile('{p}'); $s.Speak(@'\n{s}\n'@); $s.Dispose()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
        d = duration(p)
        times.append((t + 0.35, t + 0.35 + d))
        parts.append(p); t += 0.35 + d + 0.45
    inputs, filt = [], ""
    for i, p in enumerate(parts):
        inputs += ["-i", p]
        filt += f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,adelay=350|350,apad=pad_dur=0.45[a{i}];"
    filt += "".join(f"[a{i}]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=0:a=1[a]"
    ff(*inputs, "-filter_complex", filt, "-map", "[a]", wav)
    return times


EDGE = next((p for p in (os.environ.get("BROWSER", ""), r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                          r"C:\Program Files\Google\Chrome\Application\chrome.exe") if p and os.path.exists(p)), None)
CSS = """
* { margin: 0; box-sizing: border-box; }
body { width: %(w)dpx; height: %(h)dpx; overflow: hidden; background: #0b0a1f; font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; color: #fff; }
.blob { position: absolute; border-radius: 50%%; filter: blur(110px); opacity: .75; }
.grid { position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px); background-size: 64px 64px; }
"""
BLOBS = ('<div class="blob" style="width:900px;height:900px;left:-200px;top:-250px;background:#6a3cf0"></div>'
         '<div class="blob" style="width:800px;height:800px;right:-220px;bottom:-260px;background:#1f7aff"></div>'
         '<div class="blob" style="width:520px;height:520px;right:22%;top:12%;background:#c43cf0;opacity:.45"></div><div class="grid"></div>')


def shoot(html, png, w, h):
    """An HTML page to a PNG with a headless browser (Edge or Chrome; $BROWSER to choose)."""
    page = png[:-4] + ".html"
    open(page, "w", encoding="utf-8").write(html)
    profile = os.path.join(EP, "work", "_browser_profile")   # its own profile: never attach to an open browser
    import time
    for attempt in range(4):   # a fresh profile's first run sometimes exits before writing the shot
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                        f"--user-data-dir={profile}", f"--window-size={w},{h}", f"--screenshot={png}",
                        "file:///" + page.replace("\\", "/")], capture_output=True)
        for _ in range(20):
            if os.path.exists(png) and os.path.getsize(png) > 0:
                return
            time.sleep(0.5)
    raise SystemExit(f"the browser did not write {png}")


def presenter_background(path):
    html = ("<html><head><meta charset='utf-8'><style>" + CSS % {"w": 1080, "h": 1920} +
            ".tag { position: absolute; left: 50%; top: 1500px; transform: translateX(-50%); padding: 18px 40px; border-radius: 999px;"
            " background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.25); font-size: 44px; font-weight: 600;"
            " backdrop-filter: blur(20px); white-space: nowrap; } .tag span { color: #b9a6ff; font-weight: 400; }"
            "</style></head><body>" + BLOBS + "<div class='tag'>🎙️ Narrador <span>· demo</span></div></body></html>")
    shoot(html, path, 1080, 1920)


def orb(level, path):
    """The orb at one loudness level (0..15): a lit sphere in the channel colours with a glow that grows with the voice."""
    S = 760
    c = S // 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gr = 230 + level * 9
    ImageDraw.Draw(glow).ellipse((c - gr, c - gr, c + gr, c + gr), fill=(140, 90, 255, 90 + level * 8))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(40 + level * 2)))
    r = 210 + level * 3
    sphere = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(sphere)
    for k in range(r, 0, -2):   # radial gradient, lit from the upper left
        t = k / r
        off = int((1 - t) * r * 0.35)
        d.ellipse((c - k - off, c - k - off, c + k - off, c + k - off),
                  fill=(int(60 + 90 * (1 - t)), int(40 + 120 * (1 - t)), int(230 + 25 * (1 - t)), 255))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((c - r, c - r, c + r, c + r), fill=255)
    img.paste(sphere, (0, 0), mask)
    ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    rr = r + 26 + level * 4
    ImageDraw.Draw(ring).ellipse((c - rr, c - rr, c + rr, c + rr), outline=(200, 180, 255, 120 + level * 7), width=6)
    img = Image.alpha_composite(img, ring.filter(ImageFilter.GaussianBlur(2)))
    img.save(path)


def presenter(wav, mp4):
    """A vertical stand-in for a phone take: the channel background, an orb pulsing with the voice, a name tag."""
    import numpy as np, shutil
    work = os.path.join(EP, "work")
    bg = os.path.join(work, "presenter_bg.png")
    if not os.path.exists(bg):
        kept = os.path.join(ASSETS, "presenter_bg.png")
        if os.path.exists(kept) and not a.regenerate:
            shutil.copy(kept, bg)
        else:
            presenter_background(bg)
            os.makedirs(ASSETS, exist_ok=True); shutil.copy(bg, kept)
    for lv in range(16):
        p = os.path.join(work, f"orb_{lv:02d}.png")
        if not os.path.exists(p):
            orb(lv, p)
    raw = subprocess.run([FF, "-v", "error", "-i", wav, "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    per = 48000 // 30
    rms = np.array([np.sqrt(np.mean(pcm[i:i + per] ** 2)) for i in range(0, len(pcm) - per + 1, per)])
    peak = max(float(rms.max()), 1e-6)
    seq = os.path.join(work, "orb_seq_" + os.path.basename(mp4)[:-4])
    shutil.rmtree(seq, ignore_errors=True)
    os.makedirs(seq)
    level = 0.0
    for i, v in enumerate(rms):
        level = max(min(15.0, 15.0 * (v / peak) ** 0.6), level * 0.82)   # quick attack, smooth release
        os.link(os.path.join(work, f"orb_{int(round(level)):02d}.png"), os.path.join(seq, f"f_{i:05d}.png"))
    ff("-loop", "1", "-framerate", "30", "-i", bg, "-framerate", "30", "-i", os.path.join(seq, "f_%05d.png"), "-i", wav,
       "-filter_complex", f"[0:v][1:v]overlay=(W-w)/2:{1150 - 380}:shortest=1,{V}[v]",
       "-map", "[v]", "-map", "2:a", *ENC, *AUD, "-shortest", mp4)


ICONS = ["📝", "🎙️", "🗣️", "🎬", "🎞️", "📱", "✅"]


def slide(title, sub, path, n):
    """One step of the workflow as a slide: a glass card with the step, its title and points, a big icon."""
    num, name = title.split(" · ", 1)
    items = "".join(f"<li>{x.strip()}</li>" for x in sub.replace("→", "·").split("·"))
    bar = "".join(f"<i class='{'on' if k < n else ''}'></i>" for k in range(7))
    html = ("<html><head><meta charset='utf-8'><style>" + CSS % {"w": 1920, "h": 1080} +
            ".card { position: absolute; left: 140px; top: 150px; width: 1120px; height: 780px; padding: 70px 80px; border-radius: 48px;"
            " background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.22); backdrop-filter: blur(30px);"
            " box-shadow: 0 40px 120px rgba(0,0,0,.45); }"
            ".chip { display: inline-block; padding: 10px 26px; border-radius: 999px; background: rgba(106,60,240,.55);"
            " font-size: 30px; font-weight: 600; letter-spacing: .08em; }"
            "h1 { font-size: 112px; font-weight: 700; margin: 34px 0 30px; line-height: 1.02; }"
            "ul { list-style: none; padding: 0; font-size: 42px; color: #d9d2ff; } li { margin: 14px 0; }"
            "li::before { content: ''; display: inline-block; width: 14px; height: 14px; border-radius: 50%; background: #8f6bff; margin: 0 22px 8px 0; }"
            ".bar { position: absolute; left: 80px; bottom: 64px; display: flex; gap: 14px; }"
            ".bar i { width: 92px; height: 12px; border-radius: 6px; background: rgba(255,255,255,.18); } .bar i.on { background: #8f6bff; }"
            ".icon { position: absolute; right: 190px; top: 300px; width: 420px; height: 420px; border-radius: 96px;"
            " display: flex; align-items: center; justify-content: center; font-size: 230px; font-family: 'Segoe UI Emoji';"
            " background: linear-gradient(145deg, rgba(143,107,255,.55), rgba(31,122,255,.35)); border: 1px solid rgba(255,255,255,.3);"
            " box-shadow: 0 0 120px rgba(143,107,255,.55); }"
            "</style></head><body>" + BLOBS +
            f"<div class='card'><span class='chip'>PASSO {num.strip()} DE 7</span><h1>{name}</h1><ul>{items}</ul>"
            f"<div class='bar'>{bar}</div></div><div class='icon'>{ICONS[n - 1]}</div></body></html>")
    shoot(html, path, 1920, 1080)


# Narration: the intro take, and the main take (the steps and the closing).
intro_s = INTRO
main_s = [s for _, _, ss in STEPS for s in ss] + CLOSING
import shutil
times_file = os.path.join(ASSETS, "narration.json")
if os.path.exists(times_file) and not a.regenerate:
    times = json.load(open(times_file, encoding="utf-8"))
    for take in ("intro", "main"):
        ff("-i", os.path.join(ASSETS, f"{take}.flac"), os.path.join(EP, "work", f"{take}.wav"))
    intro_t, main_t = [tuple(x) for x in times["intro"]], [tuple(x) for x in times["main"]]
else:
    intro_t = tts([p for p, _ in intro_s], os.path.join(EP, "work", "intro.wav"))
    main_t = tts([p for p, _ in main_s], os.path.join(EP, "work", "main.wav"))
    os.makedirs(ASSETS, exist_ok=True)
    for take in ("intro", "main"):
        ff("-i", os.path.join(EP, "work", f"{take}.wav"), "-c:a", "flac", os.path.join(ASSETS, f"{take}.flac"))
    json.dump({"voice": a.voice, "intro": intro_t, "main": main_t}, open(times_file, "w", encoding="utf-8"), indent=1)
presenter(os.path.join(EP, "work", "intro.wav"), os.path.join(EP, "takes", "intro.mp4"))
presenter(os.path.join(EP, "work", "main.wav"), os.path.join(EP, "takes", "main.mp4"))

# B-roll: a slide per step, slowly zooming.
topics, k = [], 0
for i, (title, sub, ss) in enumerate(STEPS):
    png = os.path.join(EP, "work", f"slide_{i}.png")
    kept = os.path.join(ASSETS, f"slide_{i}.png")
    if os.path.exists(kept) and not a.regenerate:
        shutil.copy(kept, png)
    else:
        slide(title, sub, png, i + 1)
        shutil.copy(png, kept)
    clip = f"broll/step_{i}.mp4"
    ff("-loop", "1", "-t", 12, "-i", png, "-vf",
       "scale=3840:-2,zoompan=z='1.0+0.0006*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=30,format=yuv420p",
       *ENC, os.path.join(EP, clip))
    topics.append({"from": round(main_t[k][0] - 0.3, 2), "to": round(main_t[k + len(ss) - 1][1], 2),
                   "clips": [{"file": clip, "from": 0, "duration": 12}]})
    k += len(ss)
topics[0]["from"] = 0
main_len = duration(os.path.join(EP, "takes", "main.mp4"))
picks = [1, 6, 8, 9]   # the Short: workflow, burned captions, two languages, previews
episode = {
    "title": "Demo: how this video was made",
    "takes": {"intro": "takes/intro.mp4", "main": "takes/main.mp4"},
    "face": {"full": [0, 560, 1080, 1300], "pip": [0, 660, 1080, 1080], "short": [0, 640, 1080, 840]},
    "long": {"cuts": [[0.0, round(min(main_len, main_t[-1][1] - 0.6), 2)]], "topics": topics,
             "labels": [{"text": "PT · EN", "from": round(main_t[9][0], 2), "to": round(main_t[9][1], 2)}]},
    "short": {"lines": [["main", round(main_t[i][0], 2), round(main_t[i][1], 2)] for i in picks],
              "top": [{"file": "broll/step_0.mp4", "from": 0, "duration": 9, "crop": 100, "title": {"pt": "Vídeos no automático", "en": "Videos on autopilot"}},
                      {"file": "broll/step_5.mp4", "from": 0, "duration": 12, "crop": 100, "title": {"pt": "Legenda palavra por palavra", "en": "Word-by-word captions"}},
                      {"file": "broll/step_6.mp4", "from": 0, "duration": 12, "crop": 100, "title": {}}]},
    "subtitles": {"fixes": []},
    "translations": "translations.json",
}
json.dump(episode, open(os.path.join(EP, "episode.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
pairs = intro_s + main_s
# The transcriber sometimes splits a sentence in two: the short halves too.
pairs += [("Oi!", "Hi!"), ("Este é um vídeo de demonstração.", "This is a demo video."), ("É isso.", "That's it."),
          ("Me segue pra ver os próximos.", "Follow along for the next ones.")]
json.dump([{"pt": p, "en": e} for p, e in pairs], open(os.path.join(EP, "translations.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# A sample script page, as the workflow would write it.
html = open(os.path.join(ROOT, "tools", "roteiro_template.html"), encoding="utf-8").read()
topics_html = "".join(f'<div class="topic"><h3>{t}</h3><p class="say">{ss[0][0]}</p><p class="shot">{s}</p></div>'
                      for t, s, ss in STEPS)
fill = {"{{LANG}}": "pt-BR", "{{TITLE}}": "Roteiro · demonstração", "{{SUBTITLE}}": "Exemplo gerado por demo/make_demo.py",
        "{{INTRO_HEADING}}": "Abertura", "{{INTRO}}": " ".join(p for p, _ in INTRO), "{{TOPICS_HEADING}}": "Tópicos",
        "{{TOPICS}}": topics_html, "{{CLOSING_HEADING}}": "Fechamento", "{{CLOSING}}": CLOSING[0][0],
        "{{ENDING}}": "Direto para a vinheta, sem trecho só com música.",
        "{{SHORT}}": "".join(f"<li>{main_s[i][0]}</li>" for i in picks), "{{TIPS_HEADING}}": "Dicas de gravação",
        "{{TIPS}}": "<li>Celular na vertical, rosto na metade de baixo.</li><li>Fale à vontade; os cortes vêm depois.</li>"}
for k_, v_ in fill.items():
    html = html.replace(k_, v_)
open(os.path.join(EP, "roteiro.html"), "w", encoding="utf-8").write(html)
print(f"demo episode ready: {EP} (intro {duration(os.path.join(EP, 'takes', 'intro.mp4')):.1f} s, main {main_len:.1f} s)")
