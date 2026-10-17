---
name: youtube-episode
description: 'Produce a YouTube episode about a software project end to end with this repository: a script (roteiro.html) from the commits since the last episode, the presenter''s phone takes, transcription, b-roll, a long 16:9 video without burned subtitles plus .srt files per language, and 9:16 Shorts per language with burned word-by-word captions; previews first, finals after approval. Use when asked for a devlog, an episode, a video or Shorts about the project''s progress.'
---

# YouTube episode

You produce everything except the presenter's own talk. Speak to the presenter in their language
(`channel.json` `languages.main`). All tools take the episode folder (`episodes/<YYYY-MM-DD>/`) and answer `--help`.
The demo episode (`python demo/make_demo.py`) shows every input in place.

## 0. Once per channel
- `channel.json`: channel name, `project_repo` (the code the episodes are about), languages, caption style, brand paths.
- Brand assets are fixed: your own logo, `sting_h` (16:9) and `sting_v` (9:16) stings and a music track. Without
  them, `python tools/make_brand.py` makes placeholders. Never regenerate them per episode.

## 1. Script
1. `python tools/new_episode.py [date]`: the folder, `episode.json` from the example, and `changes.json` (every
   commit on every branch since the newest `episodes/<date>/`).
2. Group the commits into 4-8 topics a viewer cares about (what you can see first, internals second). Read the
   interesting commits in full.
3. Write `roteiro.html` from `tools/roteiro_template.html`: an opening to say full screen, per topic a suggested
   line (casual, in the presenter's voice) and the footage you will show, a closing, 4-6 lines for the Short,
   recording tips (phone vertical, face in the lower half, talk freely). Never promise a release frequency.
4. Give the presenter the path (a file sent to your own session view may not reach them).

## 2. Footage, while they record
Start as soon as the script is approved; don't wait for the takes. Everything 1920x1080 30 fps into `broll/`:
screen or window captures (`ffmpeg -f gdigrab` on Windows, `avfoundation` on macOS, `x11grab` on Linux) of the
product, the editor or the terminal; scripted runs of the product if it can render itself; before/after pairs
(the project at the commit before the period, in a separate `git worktree`, never by checking out old commits in
the working folder; same camera or screen, then a wipe); a calm clip for the ending (time-lapse, ambience).
Make a contact sheet of every clip and look at it before using it. If the machine is shared, ask before closing
other people's apps and never save their work.

## 3. Takes and the cut
- The presenter drops the takes in `takes/` (an `intro` take said full screen, a `main` take).
- `python tools/transcribe.py episodes/<date>/takes/<take>.mp4 --lang <main>` -> .txt/.srt/.words.json.
- From the transcript fill `episode.json`: `long.cuts` (keep ranges of the main take: drop private moments,
  false starts), `long.topics` (from which second each topic's b-roll runs), `labels`,
  `short.lines` (the Short's excerpts, ~60 s), `long.ending` only if the script plans a music-only close, `short.top` (b-roll on top, a title per language),
  `subtitles.fixes` (names the transcriber gets wrong), `face` crops. Show the presenter the cut plan.

## 4. Build
1. `python tools/build_long.py <ep>`: intro full screen, presenter framed bottom-right over the topic b-roll,
   then straight from the last word into the 16:9 sting (0.5 s crossfade, music from there), like the Short. A
   music-only close before the sting (a time-lapse, a recap) only when the script declares it (`long.ending`,
   5-10 s of real movement). No burned subtitles.
2. `python tools/build_short.py <ep>`: per language, b-roll square on top with the title, presenter below, cut
   right after the last word, 0.5 s crossfade into the 9:16 sting, music from the crossfade.
3. `python tools/make_subs.py <ep>`: the long video's `.srt` in the main language and the Short's cues. It writes
   `translations.todo.json` with every cue to translate: fill it yourself (natural, casual, same meaning, short
   lines), save as `translations.json`, run again -> the `.srt` of every extra language.
4. `python tools/captions.py <ep> <lang>` for each language: burned word-by-word captions (main language timed
   on the Short's own audio; a sync report prints how many spoken words are boxed on time).

## 5. Previews, approval, finals
- Previews land in `preview/` (long 854x480 < 20 MB, Shorts 540x960). Look at frames around every transition
  and the sting, then send the paths.
- Change, rebuild, re-preview until approved. Then `python tools/finalize.py <ep>` -> `final/`: the long video,
  one Short per language, the long video's `.srt` per language (upload in YouTube Studio > Subtitles).
- Delete old drafts only when the presenter says so.

## Lessons (each one cost a re-render)
- End every video chain with `format=yuv420p` (xfade or 4K inputs otherwise give yuv444p/High 4:4:4, which some
  players cannot open); always run the decode check.
- Never time captions with a list of durations: overlapping captions push everything later. One image per frame
  from absolute times.
- `adelay` takes milliseconds (`adelay=302680|302680`), not "302.68s".
- Transcriber timings on the raw takes can sit ~0.2 s off the final edit: measure on the final audio.
- Don't hold the last frame before the sting; cut after the last word and crossfade.
- The script decides the close: no music-only stretch unless roteiro.html and `long.ending` declare one. When
  there is one, give it real movement and 5-10 s; a static or flat clip there reads as the video being stuck.
- Whisper invents words in silence at the end of a take ("E aí", "Obrigado"): end `long.cuts` on the last
  real word, checked in the transcript, and look at the last cue of every .srt.
- The long video's labels and titles burned into the picture stay in one language; prefer language-neutral
  text (numbers, arrows) or make a version per language.
