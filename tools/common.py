"""Shared helpers: the channel and episode configs, ffmpeg, encoding settings, timelines."""
import json, os, shutil, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def find_tool(name):
    """ffmpeg / ffprobe from $FFMPEG / $FFPROBE, PATH, or the Chocolatey shim name."""
    env = os.environ.get(name.upper())
    if env:
        return env
    for candidate in (name, name + "_1"):
        found = shutil.which(candidate)
        if found:
            return found
    raise SystemExit(f"{name} not found: install it or set ${name.upper()}")


FF = find_tool("ffmpeg")
FFPROBE = find_tool("ffprobe")

# Every deliverable: H.264 High yuv420p 30 fps, AAC 48 kHz stereo, fast start. (yuv444p from xfade or 4K inputs
# does not open in the Windows player, so every chain ends in format=yuv420p.)
V = "fps=30,format=yuv420p,setsar=1"
ENC = ["-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p"]
AUD = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
FAST = ["-movflags", "+faststart"]


def ff(*args):
    subprocess.run([FF, "-y", "-hide_banner", "-v", "error", *map(str, args)], check=True)


def duration(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def decode_check(path):
    """Full decode pass and the stream spec, for every deliverable."""
    subprocess.run([FF, "-v", "error", "-i", path, "-f", "null", "-"], check=True)
    spec = subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                           "stream=codec_name,profile,pix_fmt,width,height,r_frame_rate,sample_rate,channels",
                           "-of", "compact=p=0:nk=1", path], capture_output=True, text=True, check=True).stdout
    return " / ".join(l for l in spec.splitlines() if l)


def font_arg(path):
    """A font path as drawtext wants it (the drive colon escaped)."""
    return path.replace("\\", "/").replace(":", "\\:")


def load_channel():
    with open(os.path.join(ROOT, "channel.json"), encoding="utf-8") as f:
        return json.load(f)


class Episode:
    """One episode folder: episode.json, takes/, broll/, work/ (intermediate), preview/, final/."""

    def __init__(self, folder):
        self.dir = os.path.abspath(folder)
        with open(os.path.join(self.dir, "episode.json"), encoding="utf-8") as f:
            self.cfg = json.load(f)
        self.channel = load_channel()
        self.name = os.path.basename(self.dir)
        for sub in ("work", "preview", "final"):
            os.makedirs(self.path(sub), exist_ok=True)

    def path(self, *parts):
        return os.path.join(self.dir, *parts)

    def asset(self, rel):
        """A path from the configs: relative to the episode, else to the repo root."""
        p = self.path(rel)
        return p if os.path.exists(p) else os.path.join(ROOT, rel)

    def out(self, kind, lang=None, ext="mp4"):
        prefix = self.channel["output"]["prefix"]
        return f"{prefix}_{self.name}_{kind}{'_' + lang if lang else ''}.{ext}"

    # --- the long video's clock -------------------------------------------------------------------
    def intro_len(self):
        return duration(self.path("work", "intro.mp4"))

    def cuts(self):
        return [tuple(c) for c in self.cfg["long"]["cuts"]]

    def cut_time(self, t):
        """A time on the main take -> the same moment on the cut main take (None if cut out)."""
        acc = 0.0
        for a, b in self.cuts():
            if a <= t <= b:
                return acc + t - a
            acc += b - a
        return None

    def body_len(self):
        return sum(b - a for a, b in self.cuts())

    # --- the Short's clock ------------------------------------------------------------------------
    PAD = 0.3

    def short_lines(self):
        """[(take, from, to, start_on_short)]: the Short's excerpts and where each begins in the Short."""
        out, t0 = [], 0.0
        for take, a, b in self.cfg["short"]["lines"]:
            out.append((take, a, b, t0))
            t0 += b - a + 2 * self.PAD
        return out

    def short_speech_len(self):
        return sum(b - a + 2 * self.PAD for _, a, b in self.cfg["short"]["lines"])


def words_of(ep, take):
    """A take's word timings (from tools/transcribe.py)."""
    base = os.path.splitext(ep.path(ep.cfg["takes"][take]))[0]
    with open(base + ".words.json", encoding="utf-8") as f:
        return json.load(f)
