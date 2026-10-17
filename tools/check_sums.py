"""Compares the demo you just built with the reference finals in examples/demo/ (SHA-256), or writes the list.
    python tools/check_sums.py                      # compare episodes/demo/final with examples/demo/SHA256SUMS
    python tools/check_sums.py --write              # (maintainers) refresh examples/demo from episodes/demo/final
"""
import argparse, hashlib, os, shutil, sys
from common import ROOT

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--write", action="store_true")
a = ap.parse_args()
final = os.path.join(ROOT, "episodes", "demo", "final")
ref = os.path.join(ROOT, "examples", "demo")
sums = os.path.join(ref, "SHA256SUMS")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


if a.write:
    os.makedirs(ref, exist_ok=True)
    lines = []
    for name in sorted(os.listdir(final)):
        shutil.copy(os.path.join(final, name), os.path.join(ref, name))
        lines.append(f"{sha(os.path.join(ref, name))}  {name}")
    open(sums, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(0)

same = True
for line in open(sums, encoding="utf-8"):
    digest, name = line.split(None, 1)
    name = name.strip()
    mine = os.path.join(final, name)
    ok = os.path.exists(mine) and sha(mine) == digest
    same &= ok
    print(f"{'same' if ok else 'DIFFERENT'}  {name}")
sys.exit(0 if same else 1)
