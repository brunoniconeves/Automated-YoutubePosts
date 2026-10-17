# Automated YouTube Posts

*[Português](README.pt-BR.md)*

Turn your project's progress into YouTube episodes with as little editing as possible: you talk to your phone,
the pipeline (and Claude Code, through the included skill) does the rest.

For each episode it produces:

- a **script** (`roteiro.html`) written from the commits since the last episode;
- a **long 16:9 video**: your intro full screen, then you in a framed corner over footage of each topic, a calm
  ending with music, your channel's sting. **No burned-in subtitles**: it writes `.srt` files for every language
  you publish in, to upload in YouTube Studio;
- one **9:16 Short per language** with burned-in word-by-word captions ("queimada" style: the word being said on a
  coloured box), cut right after your last word and crossfading into your sting with music.

Light previews come first; finals only after you approve them.

![Word-by-word captions](docs/short_captions.gif) ![Short, Portuguese](docs/short_pt.png) ![Short, English](docs/short_en.png)

![Long video frame](docs/long.png)

## How it works

```
commits since the last episode ─► roteiro.html ─► you record (phone, vertical)
                                        │
            b-roll / screen captures ◄──┘          transcribe (faster-whisper, word timings)
                                                         │
     episode.json (cuts, topics, Short lines) ◄──────────┘
                    │
   build_long ─► long video + .srt (main + translations)
   build_short ─► Short base per language ─► captions ─► Short per language
                    │
              previews ─► your OK ─► finalize ─► final/
```

## Requirements

- Python 3.10+, `pip install -r requirements.txt` (faster-whisper, Pillow)
- ffmpeg 6+ with libx264 on PATH (or `$FFMPEG` / `$FFPROBE`)
- Windows for the bundled defaults (fonts in `channel.json`, the demo's offline voice); change the font paths and
  the capture command to run elsewhere.
- Optional: [Claude Code](https://claude.com/claude-code); the skill in `.claude/skills/youtube-episode` drives
  the whole thing.

## Quickstart (the demo)

The demo needs no camera and no project: it narrates the workflow itself with Windows' built-in text-to-speech.

```bash
python tools/make_brand.py                 # placeholder logo, stings and music in brand/
python demo/make_demo.py                   # episodes/demo: takes, b-roll, episode.json, translations.json
python tools/transcribe.py episodes/demo/takes/intro.mp4
python tools/transcribe.py episodes/demo/takes/main.mp4
python tools/build_long.py episodes/demo
python tools/build_short.py episodes/demo
python tools/make_subs.py episodes/demo
python tools/captions.py episodes/demo pt
python tools/captions.py episodes/demo en
python tools/finalize.py episodes/demo     # after looking at preview/
```

## Your own episodes

1. Edit `channel.json`: your channel name, `project_repo` (the code your episodes are about), languages,
   caption style. Replace `brand/` with your own logo, stings and music (keep the file names or change the paths).
2. `python tools/new_episode.py` creates `episodes/<today>/` and `changes.json`. With Claude Code, ask for an
   episode and the skill writes `roteiro.html` from it.
3. Record your takes (`takes/intro.mp4`, `takes/main.mp4`), capture footage into `broll/`.
4. Transcribe, fill `episode.json` (see `tools/episode.example.json`), build, translate (`translations.todo.json`
   -> `translations.json`), preview, finalize.

Episodes (your takes, your voice, all renders) are git-ignored and never leave your machine.

## License

MIT
