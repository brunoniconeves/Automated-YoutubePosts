"""What changed in your project since the last episode, to write the next script from.

The last episode is the newest episodes/<YYYY-MM-DD>/ folder (or --since). Lists every commit since that date on
all branches of the project repository (channel.json "project_repo", or --repo), with the branch it was reached
from and the top-level areas it touched.
    python tools/gather_changes.py
    python tools/gather_changes.py --repo ../my-project --since 2026-01-31 --json > changes.json
"""
import argparse, json, os, re, subprocess, sys
from common import ROOT, load_channel


def last_episode():
    days = [d for d in os.listdir(os.path.join(ROOT, "episodes")) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)]
    return max(days) if days else None


def gather(repo, since):
    sep = "\x1f"
    log = subprocess.run(["git", "-C", repo, "log", "--all", "--source", f"--since={since} 00:00", "--date=iso",
                          f"--format=%x1e%h{sep}%S{sep}%ad{sep}%s", "--name-only"],
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    commits = []
    for rec in log.split("\x1e")[1:]:
        head, _, files = rec.partition("\n")
        h, ref, date, subject = (head.split(sep) + [""] * 4)[:4]
        paths = [f for f in files.strip().splitlines() if f]
        areas = sorted({"/".join(p.split("/")[:2]) for p in paths})
        commits.append({"hash": h, "branch": re.sub(r"^refs/(heads|remotes)/", "", ref), "date": date,
                        "subject": subject, "areas": areas})
    return commits


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", help="project repository (default: channel.json project_repo)")
    ap.add_argument("--since", help="YYYY-MM-DD (default: the newest episodes/<date>/ folder)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    repo = os.path.abspath(os.path.join(ROOT, a.repo or load_channel()["project_repo"]))
    since = a.since or last_episode()
    if not since:
        sys.exit("no episodes/<date>/ folder yet: pass --since")
    commits = gather(repo, since)
    if a.json:
        json.dump({"repo": repo, "since": since, "commits": commits}, sys.stdout, ensure_ascii=False, indent=1)
        return
    print(f"{repo}: {len(commits)} commits since {since}")
    for c in commits:
        print(f"- {c['hash']} {c['date'][:16]} [{c['branch']}] {c['subject'][:140]}")
        if c["areas"]:
            print(f"    areas: {', '.join(c['areas'][:8])}")


if __name__ == "__main__":
    main()
