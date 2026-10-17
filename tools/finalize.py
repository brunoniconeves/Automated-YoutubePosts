"""After the previews are approved: copies the full-quality videos to final/ with their publishing names and
checks each one (full decode, H.264 High yuv420p, AAC 48 kHz). The .srt files are already in final/.
    python tools/finalize.py episodes/2026-01-31
"""
import argparse, os, shutil
from common import Episode, decode_check

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("episode")
a = ap.parse_args()
ep = Episode(a.episode)
langs = [ep.channel["languages"]["main"]] + ep.channel["languages"].get("extra", [])
pairs = [("long.mp4", ep.out("long"))] + [(f"short_{l}.mp4", ep.out("short", l)) for l in langs]
for src, dst in pairs:
    s = ep.path("work", src)
    if not os.path.exists(s):
        print("missing", src); continue
    d = ep.path("final", dst)
    shutil.copy(s, d)
    print(f"{dst}  {os.path.getsize(d) / 1e6:.0f} MB  {decode_check(d)}")
for f in sorted(os.listdir(ep.path("final"))):
    if f.endswith(".srt"):
        print(f)
