"""Starts an episode: episodes/<date>/ with takes/, broll/, work/, preview/, final/, an episode.json to fill in,
and changes.json (what changed in the project since the last episode, from gather_changes.py) for writing the
script (roteiro.html, from tools/roteiro_template.html).
    python tools/new_episode.py [2026-01-31]
"""
import argparse, datetime, json, os, shutil
from common import ROOT, load_channel
from gather_changes import gather, last_episode

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("date", nargs="?", default=datetime.date.today().isoformat())
a = ap.parse_args()
ch = load_channel()
previous = last_episode()
ep = os.path.join(ROOT, "episodes", a.date)
for sub in ("takes", "broll", "work", "preview", "final"):
    os.makedirs(os.path.join(ep, sub), exist_ok=True)
template = os.path.join(ROOT, "tools", "episode.example.json")
target = os.path.join(ep, "episode.json")
if not os.path.exists(target):
    shutil.copy(template, target)
if previous and previous != a.date:
    repo = os.path.abspath(os.path.join(ROOT, ch["project_repo"]))
    commits = gather(repo, previous)
    json.dump({"repo": repo, "since": previous, "commits": commits}, open(os.path.join(ep, "changes.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"{len(commits)} commits since {previous} -> changes.json")
else:
    print("first episode: pass the period to gather_changes.py --since yourself")
print(f"episode folder: {ep}\nnext: write roteiro.html from tools/roteiro_template.html, fill episode.json")
