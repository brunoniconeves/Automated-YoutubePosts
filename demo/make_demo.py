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
from PIL import Image, ImageDraw, ImageFont
from common import ROOT, ff, duration, V, ENC, AUD

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--voice", default="Microsoft Maria Desktop")
a = ap.parse_args()
EP = os.path.join(ROOT, "episodes", "demo")
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


def presenter(wav, mp4):
    """A vertical stand-in for a phone take: gradient, an avatar where a face would be, the voice as a waveform."""
    av = os.path.join(EP, "work", "avatar.png")
    if not os.path.exists(av):
        img = Image.new("RGBA", (520, 520), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((10, 10, 510, 510), fill=(245, 236, 255, 255), outline=(106, 60, 240, 255), width=14)
        d.ellipse((170, 120, 350, 300), fill=(106, 60, 240, 255))
        d.pieslice((90, 300, 430, 640), 180, 360, fill=(106, 60, 240, 255))
        img.save(av)
    d = duration(wav)
    ff("-f", "lavfi", "-t", d, "-i", "gradients=s=1080x1920:c0=0x2b2f4a:c1=0x4b3b8f:n=2:speed=0.01:r=30", "-i", av, "-i", wav,
       "-filter_complex",
       "[2:a]showwaves=s=900x180:mode=cline:colors=0xd9ccff:r=30,format=rgba[w];"
       f"[0:v][1:v]overlay=(W-w)/2:820[b];[b][w]overlay=(W-w)/2:1380,{V}[v]",
       "-map", "[v]", "-map", "2:a", *ENC, *AUD, "-shortest", mp4)


def slide(title, sub, path, n):
    img = Image.new("RGB", (1920, 1080))
    d = ImageDraw.Draw(img)
    for y in range(1080):
        c = y / 1080
        d.line([(0, y), (1920, y)], fill=(int(22 + 30 * c), int(20 + 18 * c), int(48 + 60 * c)))
    d.rounded_rectangle((120, 120, 1800, 960), radius=40, fill=(255, 255, 255), outline=(106, 60, 240), width=8)
    d.text((200, 260), title, font=ImageFont.truetype(HEAVY, 120), fill=(40, 30, 90))
    d.text((205, 470), sub, font=ImageFont.truetype(FONT, 58), fill=(90, 90, 120))
    for i in range(7):
        d.ellipse((205 + i * 90, 800, 255 + i * 90, 850), fill=(106, 60, 240) if i < n else (220, 220, 235))
    img.save(path)


# Narration: the intro take, and the main take (the steps and the closing).
intro_s = INTRO
main_s = [s for _, _, ss in STEPS for s in ss] + CLOSING
intro_t = tts([p for p, _ in intro_s], os.path.join(EP, "work", "intro.wav"))
main_t = tts([p for p, _ in main_s], os.path.join(EP, "work", "main.wav"))
presenter(os.path.join(EP, "work", "intro.wav"), os.path.join(EP, "takes", "intro.mp4"))
presenter(os.path.join(EP, "work", "main.wav"), os.path.join(EP, "takes", "main.mp4"))

# B-roll: a slide per step, slowly zooming; an animated gradient for the ending.
topics, k = [], 0
for i, (title, sub, ss) in enumerate(STEPS):
    png = os.path.join(EP, "work", f"slide_{i}.png")
    slide(title, sub, png, i + 1)
    clip = f"broll/step_{i}.mp4"
    ff("-loop", "1", "-t", 12, "-i", png, "-vf",
       "zoompan=z='1+0.0008*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps=30,format=yuv420p",
       *ENC, os.path.join(EP, clip))
    topics.append({"from": round(main_t[k][0] - 0.3, 2), "to": round(main_t[k + len(ss) - 1][1], 2),
                   "clips": [{"file": clip, "from": 0, "duration": 12}]})
    k += len(ss)
topics[0]["from"] = 0
ff("-f", "lavfi", "-t", 20, "-i", "gradients=s=1920x1080:c0=0x1b1340:c1=0x2a5bd7:c2=0x6a3cf0:n=3:speed=0.03:r=30",
   *ENC, os.path.join(EP, "broll", "ending.mp4"))

main_len = duration(os.path.join(EP, "takes", "main.mp4"))
picks = [1, 6, 8, 9]   # the Short: workflow, burned captions, two languages, previews
episode = {
    "title": "Demo: how this video was made",
    "takes": {"intro": "takes/intro.mp4", "main": "takes/main.mp4"},
    "face": {"full": [0, 560, 1080, 1300], "pip": [0, 660, 1080, 1080], "short": [0, 700, 1080, 840]},
    "long": {"cuts": [[0.0, round(min(main_len, main_t[-1][1] - 0.6), 2)]], "topics": topics,
             "labels": [{"text": "PT · EN", "from": round(main_t[9][0], 2), "to": round(main_t[9][1], 2)}],
             "ending": {"file": "broll/ending.mp4", "from": 0, "duration": 12}},
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
        "{{SHORT}}": "".join(f"<li>{main_s[i][0]}</li>" for i in picks), "{{TIPS_HEADING}}": "Dicas de gravação",
        "{{TIPS}}": "<li>Celular na vertical, rosto na metade de baixo.</li><li>Fale à vontade; os cortes vêm depois.</li>"}
for k_, v_ in fill.items():
    html = html.replace(k_, v_)
open(os.path.join(EP, "roteiro.html"), "w", encoding="utf-8").write(html)
print(f"demo episode ready: {EP} (intro {duration(os.path.join(EP, 'takes', 'intro.mp4')):.1f} s, main {main_len:.1f} s)")
