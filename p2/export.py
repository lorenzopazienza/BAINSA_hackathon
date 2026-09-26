"""Write best/Q{d}.json to submissions/Q{d}_best.txt (0/1 strings, increasing label),
then re-read each written file and re-verify it with evaluator.py.

Usage: python export.py            # every d with a stored best
       python export.py 3 4 5      # only these d
"""
import sys
from pathlib import Path

from evaluator import count_uphill, score_file, to_strings
from store import BEST_DIR, load_best

OUT = Path(__file__).parent / "submissions"


def export(d):
    best = load_best(d)
    if best is None:
        print(f"Q{d}: no stored labelling")
        return
    score = count_uphill(best["order"], d)
    assert score == best["score"], f"Q{d}: stored score {best['score']} != evaluator {score}"
    OUT.mkdir(exist_ok=True)
    path = OUT / f"Q{d}_best.txt"
    path.write_text("\n".join(to_strings(best["order"], d)) + "\n")
    d_file, score_file_ = score_file(path)  # verify the file exactly as it will be submitted
    assert (d_file, score_file_) == (d, score)
    print(f"Q{d}: {score} uphill paths -> {path}  (source: {best['source']})")


if __name__ == "__main__":
    ds = [int(x) for x in sys.argv[1:]] or sorted(int(p.stem[1:]) for p in BEST_DIR.glob("Q*.json"))
    for d in ds:
        export(d)
