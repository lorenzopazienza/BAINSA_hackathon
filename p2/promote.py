"""Promote a new best: re-verify best/Q{d}.json with evaluator.py (DP and brute force),
export it to submissions/, verify the exported file, and git-commit just those two files.

Usage: python promote.py --d 9              # once
       python promote.py --d 9 --watch 60   # poll every 60 s
"""
import argparse
import subprocess
import time
from pathlib import Path

from evaluator import count_uphill, count_uphill_bruteforce, score_file
from export import OUT, export
from store import load_best

ROOT = Path(__file__).parent


def promote(d):
    best = load_best(d)
    sub = OUT / f"Q{d}_best.txt"
    current = score_file(sub)[1] if sub.exists() else None
    if best is None or (current is not None and best["score"] >= current):
        return False
    order = best["order"]
    dp, bf = count_uphill(order, d), count_uphill_bruteforce(order, d)
    if not dp == bf == best["score"]:
        raise SystemExit(f"Q{d} VERIFICATION FAILED: stored {best['score']} dp {dp} brute {bf}")
    export(d)  # re-verifies the written file
    paths = [str(ROOT / "best" / f"Q{d}.json"), str(sub)]
    msg = (f"Q{d}: new best U = {dp} (was {current}), source: {best['source']}\n\n"
           f"Verified by evaluator.py DP and brute-force enumeration.\n\n"
           f"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    subprocess.run(["git", "add", *paths], check=True, cwd=ROOT)
    subprocess.run(["git", "commit", "-q", "-m", msg, "--", *paths], check=True, cwd=ROOT)
    print(f"{time.strftime('%H:%M:%S')} committed Q{d} = {dp} (was {current})", flush=True)
    return True


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--d", type=int, default=9)
    p.add_argument("--watch", type=float, default=0, help="poll interval in seconds; 0 = once")
    a = p.parse_args()
    promote(a.d)
    while a.watch:
        time.sleep(a.watch)
        promote(a.d)
