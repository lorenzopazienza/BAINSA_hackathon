"""Simulated annealing over labellings of Q_d (swap two labels).

A swap of the labels at positions a < b can only change N(v) for vertices
at positions >= a, so each move recomputes just that suffix (O((n-a)*d)).
Scores inside numba are int64 saturating at CAP; anything stored is
re-verified exactly by evaluator.py (via store.py).

Usage: python anneal.py --d 3 4 5 6 7 8 9 --restarts 8 --jobs 8
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMBA_NUM_THREADS", "1")

import argparse
import json
import time
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed
from numba import njit

from store import load_best, save_if_better

CAP = 1 << 60
LOG = Path(__file__).parent / "results" / "anneal_log.jsonl"


@njit(cache=True)
def _recompute(order, pos, d, start, N, prefix):
    """Recompute N for positions >= start in place; prefix[k] = sum of N over positions < k."""
    n = order.shape[0]
    for k in range(start, n):
        v = order[k]
        s = 0
        has_lower = False
        for j in range(d):
            u = v ^ (1 << j)
            if pos[u] < k:
                has_lower = True
                s = min(s + N[u], CAP)
        if not has_lower:
            s = 1
        N[v] = s
        prefix[k + 1] = min(prefix[k] + s, CAP)
    return prefix[n]


@njit(cache=True)
def score(order, d):
    n = order.shape[0]
    pos = np.empty(n, np.int64)
    for k in range(n):
        pos[order[k]] = k
    N = np.zeros(n, np.int64)
    prefix = np.zeros(n + 1, np.int64)
    return _recompute(order, pos, d, 0, N, prefix)


@njit(cache=True)
def anneal(order, d, iters, T0, T1, window, seed):
    """Anneal from `order`; returns (best_order, best_score)."""
    np.random.seed(seed)
    n = order.shape[0]
    order = order.copy()
    pos = np.empty(n, np.int64)
    for k in range(n):
        pos[order[k]] = k
    N = np.zeros(n, np.int64)
    prefix = np.zeros(n + 1, np.int64)
    cur = _recompute(order, pos, d, 0, N, prefix)
    best, best_order = cur, order.copy()
    bufN = np.empty(n, np.int64)
    bufP = np.empty(n + 1, np.int64)
    ratio = T1 / T0
    for it in range(iters):
        T = T0 * ratio ** (it / iters)
        a = np.random.randint(n)
        if np.random.random() < 0.5:
            b = np.random.randint(n)
        else:
            b = min(n - 1, max(0, a + np.random.randint(-window, window + 1)))
        if a == b:
            continue
        if a > b:
            a, b = b, a
        for k in range(a, n):
            bufN[k] = N[order[k]]
            bufP[k + 1] = prefix[k + 1]
        va, vb = order[a], order[b]
        order[a], order[b] = vb, va
        pos[va], pos[vb] = b, a
        new = _recompute(order, pos, d, a, N, prefix)
        delta = new - cur
        if delta <= 0 or np.random.random() < np.exp(-delta / T):
            cur = new
            if cur < best:
                best = cur
                best_order[:] = order
        else:  # revert: same vertex set occupies positions >= a
            order[a], order[b] = va, vb
            pos[va], pos[vb] = a, b
            for k in range(a, n):
                N[order[k]] = bufN[k]
                prefix[k + 1] = bufP[k + 1]
    return best_order, best


def default_iters(d):
    return {3: 20_000, 4: 100_000, 5: 300_000, 6: 1_000_000, 7: 2_000_000,
            8: 4_000_000, 9: 8_000_000}.get(d, 8_000_000)


def polish(order, d, iters=None, seed=0, T0=1.0, T1=0.05):
    """Short low-temperature anneal from a given labelling (used by loop.py)."""
    iters = iters or default_iters(d) // 4
    best_order, best = anneal(np.asarray(order, np.int64), d, iters, T0, T1, 16, seed)
    return best_order.tolist(), int(best)


def _one_restart(d, iters, seed, T0, T1, init):
    rng = np.random.default_rng(seed)
    order = np.asarray(init, np.int64) if init is not None else rng.permutation(1 << d).astype(np.int64)
    t = time.time()
    best_order, best = anneal(order, d, iters, T0, T1, 16, seed)
    return best_order.tolist(), int(best), time.time() - t


def run(d, restarts, iters, jobs, seed, T0, T1, from_best=False):
    init = load_best(d)["order"] if from_best and load_best(d) else None
    t0 = time.time()
    results = Parallel(n_jobs=jobs)(
        delayed(_one_restart)(d, iters, seed + r, T0, T1, init) for r in range(restarts))
    LOG.parent.mkdir(exist_ok=True)
    scores = []
    with open(LOG, "a") as log:
        for r, (order, s, secs) in enumerate(results):
            verified = save_if_better(d, order, f"anneal seed={seed + r}")
            assert verified == s, f"numba score {s} != evaluator {verified}"
            scores.append(verified)
            log.write(json.dumps({"time": time.time(), "d": d, "seed": seed + r, "iters": iters,
                                  "T0": T0, "T1": T1, "score": verified, "secs": secs,
                                  "from_best": from_best}) + "\n")
    print(f"Q{d}: restarts={sorted(scores)}  best-ever={load_best(d)['score']}  "
          f"|E|+2={d * 2 ** (d - 1) + 2}  ({time.time() - t0:.1f}s)", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--d", type=int, nargs="+", default=[3, 4, 5, 6, 7, 8, 9])
    p.add_argument("--restarts", type=int, default=8)
    p.add_argument("--iters", type=float, default=None, help="per restart; default depends on d")
    p.add_argument("--jobs", type=int, default=8)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--T0", type=float, default=3.0)
    p.add_argument("--T1", type=float, default=0.05)
    p.add_argument("--from-best", action="store_true", help="start every restart from best/Q{d}.json")
    a = p.parse_args()
    anneal(np.arange(8, dtype=np.int64), 3, 10, 1.0, 0.1, 2, 0)  # compile once; workers load the numba cache
    for d in a.d:
        run(d, a.restarts, int(a.iters or default_iters(d)), a.jobs, a.seed, a.T0, a.T1, a.from_best)
