"""Best-known labelling per d, stored in best/Q{d}.json.

Every write re-scores the labelling with evaluator.py; callers' scores are
never trusted. A file lock makes concurrent writers (anneal, loop) safe.
"""
import fcntl
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

from evaluator import count_uphill

ROOT = Path(__file__).parent
BEST_DIR = ROOT / "best"


@contextmanager
def _lock():
    BEST_DIR.mkdir(exist_ok=True)
    with open(BEST_DIR / ".lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def load_best(d):
    path = BEST_DIR / f"Q{d}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_if_better(d, order, source):
    """Verify `order`, store it if it beats the current best. Returns the verified score."""
    order = [int(v) for v in order]
    score = count_uphill(order, d)
    with _lock():
        best = load_best(d)
        if best is None or score < best["score"]:
            path = BEST_DIR / f"Q{d}.json"
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"d": d, "score": score, "source": source,
                                       "time": time.time(), "order": order}))
            os.replace(tmp, path)
    return score
