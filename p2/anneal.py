"""Local search over labellings of Q_d.

Modes: swap (original swap-only annealing), new (insertion + swap moves, moves
targeted at costly vertices, optional tabu), ils (iterated local search from the
stored best: perturb a window or subcube, re-polish, accept if <= current).

A swap of the labels at positions a < b can only change N(v) for vertices
at positions >= a, so each move recomputes just that suffix (O((n-a)*d)).
Scores inside numba are int64 saturating at CAP; anything stored is
re-verified exactly by evaluator.py (via store.py).

Usage: python anneal.py --d 3 4 5 6 7 8 9 --restarts 8 --jobs 4
       python anneal.py --mode new --d 8 --restarts 4 --tabu 20
       python anneal.py --mode ils --d 9 --jobs 4 --minutes 120
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
RESULTS = Path(__file__).parent / "results" / "results.jsonl"


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


# ---------------------------------------------------------------------------
# Improved local search: insertion + swap moves, moves targeted at costly
# vertices, optional tabu, and iterated local search (perturb + re-polish).
# ---------------------------------------------------------------------------

@njit(cache=True)
def _vertex_costs(pos, d, N, cost):
    """Excess decomposition per vertex: (N(u)-1)*updeg(u), plus 1 for each valley."""
    total = 0
    for u in range(cost.shape[0]):
        up = 0
        for j in range(d):
            if pos[u ^ (1 << j)] > pos[u]:
                up += 1
        c = min(N[u] - 1, 1 << 40) * up
        if up == d:
            c += 1
        cost[u] = c
        total += c
    return total


@njit(cache=True)
def _insert(order, pos, i, j):
    """Move the vertex at position i to position j, shifting the ones in between."""
    v = order[i]
    if i < j:
        for k in range(i, j):
            order[k] = order[k + 1]
            pos[order[k]] = k
    else:
        for k in range(i, j, -1):
            order[k] = order[k - 1]
            pos[order[k]] = k
    order[j] = v
    pos[v] = j


@njit(cache=True)
def search(order, d, iters, T0, T1, window, seed, p_insert, p_target, tabu):
    """Annealing with insertion/swap moves; a fraction p_target of moves picks a vertex
    with probability proportional to its excess cost (or a neighbour of it). Vertices
    moved in the last `tabu` iterations are not moved again (tabu=0 disables)."""
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
    bufO = np.empty(n, np.int64)
    cost = np.zeros(n, np.int64)
    cum = np.zeros(n, np.float64)
    last = np.full(n, -(tabu + 1), np.int64)
    ratio = T1 / T0
    refresh = 0
    for it in range(iters):
        T = T0 * ratio ** (it / iters)
        if it >= refresh:
            _vertex_costs(pos, d, N, cost)
            cum = np.cumsum(cost.astype(np.float64))
            refresh = it + 256
        is_insert = np.random.random() < p_insert
        if cum[-1] > 0 and np.random.random() < p_target:
            u = min(n - 1, np.searchsorted(cum, np.random.random() * cum[-1], side="right"))
            if np.random.random() < 0.3:
                u = u ^ (1 << np.random.randint(d))
            i = pos[u]
            j = min(n - 1, max(0, i + np.random.randint(-window, window + 1)))
        else:
            i = np.random.randint(n)
            if np.random.random() < 0.5:
                j = np.random.randint(n)
            else:
                j = min(n - 1, max(0, i + np.random.randint(-window, window + 1)))
        if i == j:
            continue
        vi, vj = order[i], order[j]
        if tabu > 0 and (it - last[vi] <= tabu or (not is_insert and it - last[vj] <= tabu)):
            continue
        a, b = min(i, j), max(i, j)
        for k in range(a, n):
            bufN[k] = N[order[k]]
            bufP[k + 1] = prefix[k + 1]
        for k in range(a, b + 1):
            bufO[k] = order[k]
        if is_insert:
            _insert(order, pos, i, j)
        else:
            order[i], order[j] = vj, vi
            pos[vi], pos[vj] = j, i
        new = _recompute(order, pos, d, a, N, prefix)
        delta = new - cur
        if delta <= 0 or np.random.random() < np.exp(-delta / T):
            cur = new
            last[vi] = it
            if not is_insert:
                last[vj] = it
            if cur < best:
                best = cur
                best_order[:] = order
        else:  # revert
            for k in range(a, b + 1):
                order[k] = bufO[k]
                pos[order[k]] = k
            for k in range(a, n):
                N[order[k]] = bufN[k]
                prefix[k + 1] = bufP[k + 1]
    return best_order, best


@njit(cache=True)
def _perturb(order, d, kind, strength):
    """kind 0: shuffle a random window of <= strength+1 positions;
    kind 1: shuffle the labels of a random 2..4-dim subcube among themselves;
    kind 2: apply a random automorphism (flip + coordinate permutation) of such a subcube."""
    n = order.shape[0]
    if kind == 0:
        L = 2 + np.random.randint(strength)
        a = np.random.randint(n - L + 1)
        seg = order[a:a + L].copy()
        np.random.shuffle(seg)
        order[a:a + L] = seg
        return
    pos = np.empty(n, np.int64)
    for k in range(n):
        pos[order[k]] = k
    k = 2 + np.random.randint(3)
    coords = np.random.permutation(d)[:k]
    free = 0
    for c in coords:
        free |= 1 << c
    base = np.random.randint(n) & ~free
    members = np.empty(1 << k, np.int64)
    for m in range(1 << k):
        v = base
        for t in range(k):
            if (m >> t) & 1:
                v |= 1 << coords[t]
        members[m] = v
    slots = np.array([pos[v] for v in members])
    if kind == 1:
        img = members.copy()
        np.random.shuffle(img)
    else:
        flip = np.random.randint(1 << k)
        perm = np.random.permutation(k)
        img = np.empty(1 << k, np.int64)
        for m in range(1 << k):
            mm = m ^ flip
            out = 0
            for t in range(k):
                if (mm >> t) & 1:
                    out |= 1 << perm[t]
            img[m] = members[out]
    for m in range(1 << k):
        order[slots[m]] = img[m]


@njit(cache=True)
def ils(order, d, rounds, polish_iters, T0, T1, window, seed, p_insert, p_target, tabu, strength):
    """Iterated local search: perturb the current labelling, re-polish, accept if <= current
    (equal moves allowed, so it drifts on plateaus). Returns (best, best_s, cur, cur_s, n_accepted)."""
    np.random.seed(seed)
    cur = order.copy()
    cur_s = score(cur, d)
    best, best_s = cur.copy(), cur_s
    accepted = 0
    for r in range(rounds):
        cand = cur.copy()
        _perturb(cand, d, np.random.randint(3), strength)
        cand, s = search(cand, d, polish_iters, T0, T1, window, np.random.randint(1 << 30),
                         p_insert, p_target, tabu)
        if s <= cur_s:
            cur, cur_s = cand, s
            accepted += 1
        if s < best_s:
            best, best_s = cand.copy(), s
    return best, best_s, cur, cur_s, accepted


def default_iters(d):
    return {3: 20_000, 4: 100_000, 5: 300_000, 6: 1_000_000, 7: 2_000_000,
            8: 4_000_000, 9: 8_000_000}.get(d, 8_000_000)


def polish(order, d, iters=None, seed=0, T0=1.0, T1=0.05):
    """Improved local search from a given labelling (used by loop.py)."""
    iters = iters or default_iters(d) // 4
    best_order, best = search(np.asarray(order, np.int64), d, iters, T0, T1, 16, seed, 0.5, 0.3, 0)
    return best_order.tolist(), int(best)


def _one_restart(d, iters, seed, T0, T1, init, mode, tabu):
    rng = np.random.default_rng(seed)
    order = np.asarray(init, np.int64) if init is not None else rng.permutation(1 << d).astype(np.int64)
    t = time.time()
    if mode == "swap":  # original swap-only annealing, kept for comparison
        best_order, best = anneal(order, d, iters, T0, T1, 16, seed)
    else:
        best_order, best = search(order, d, iters, T0, T1, 16, seed, 0.5, 0.3, tabu)
    return best_order.tolist(), int(best), time.time() - t


def run(d, restarts, iters, jobs, seed, T0, T1, from_best=False, mode="swap", tabu=0):
    init = load_best(d)["order"] if from_best and load_best(d) else None
    t0 = time.time()
    results = Parallel(n_jobs=jobs)(
        delayed(_one_restart)(d, iters, seed + r, T0, T1, init, mode, tabu) for r in range(restarts))
    LOG.parent.mkdir(exist_ok=True)
    scores = []
    with open(LOG, "a") as log:
        for r, (order, s, secs) in enumerate(results):
            verified = save_if_better(d, order, f"anneal mode={mode} seed={seed + r}")
            assert verified == s, f"numba score {s} != evaluator {verified}"
            scores.append(verified)
            log.write(json.dumps({"time": time.time(), "d": d, "seed": seed + r, "iters": iters,
                                  "T0": T0, "T1": T1, "score": verified, "secs": secs,
                                  "from_best": from_best, "mode": mode, "tabu": tabu}) + "\n")
    print(f"Q{d} [{mode}]: restarts={sorted(scores)}  best-ever={load_best(d)['score']}  "
          f"({time.time() - t0:.1f}s)", flush=True)


def _ils_worker(d, seed, minutes, chunk, polish_iters, T0, T1, tabu, strength):
    """Runs ILS in chunks; adopts the global best when another worker beats it."""
    rng = np.random.default_rng(seed)
    cur = np.asarray(load_best(d)["order"], np.int64)
    cur_s = int(score(cur, d))
    deadline = time.time() + 60 * minutes
    while time.time() < deadline:
        g = load_best(d)
        if g["score"] < cur_s:
            cur, cur_s = np.asarray(g["order"], np.int64), g["score"]
        t = time.time()
        best, best_s, cur, cur_s, acc = ils(cur, d, chunk, polish_iters, T0, T1, 16,
                                            int(rng.integers(1 << 30)), 0.5, 0.3, tabu, strength)
        verified = save_if_better(d, best, f"ils worker={seed}")
        assert verified == best_s
        with open(RESULTS, "a") as f:
            f.write(json.dumps({"source": "ils", "worker": seed, "d": d, "score": int(best_s),
                                "current": int(cur_s), "accepted": acc, "rounds": chunk,
                                "polish_iters": polish_iters, "tabu": tabu, "secs": time.time() - t,
                                "timestamp": time.time()}) + "\n")


def run_ils(d, workers, minutes, chunk, polish_iters, T0, T1, tabu, strength, seed):
    Parallel(n_jobs=workers)(
        delayed(_ils_worker)(d, seed + w, minutes, chunk, polish_iters, T0, T1, tabu, strength)
        for w in range(workers))
    print(f"Q{d} ILS done: best={load_best(d)['score']}", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["swap", "new", "ils"], default="swap",
                   help="swap: original swap-only annealing; new: insertion+swap+targeted+tabu; "
                        "ils: iterated local search from best/Q{d}.json")
    p.add_argument("--d", type=int, nargs="+", default=[3, 4, 5, 6, 7, 8, 9])
    p.add_argument("--restarts", type=int, default=8)
    p.add_argument("--iters", type=float, default=None, help="per restart; default depends on d")
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--T0", type=float, default=None, help="default 3.0 (swap/new), 0.6 (ils)")
    p.add_argument("--T1", type=float, default=0.05)
    p.add_argument("--tabu", type=int, default=0)
    p.add_argument("--from-best", action="store_true", help="start every restart from best/Q{d}.json")
    p.add_argument("--minutes", type=float, default=60, help="ils: wall time per worker")
    p.add_argument("--chunk", type=int, default=50, help="ils: rounds between log/save")
    p.add_argument("--polish-iters", type=int, default=100_000, help="ils: search iters per round")
    p.add_argument("--strength", type=int, default=24, help="ils: max window length for kick")
    a = p.parse_args()
    x = np.arange(8, dtype=np.int64)  # compile once; workers load the numba cache
    anneal(x, 3, 10, 1.0, 0.1, 2, 0)
    ils(x, 3, 2, 10, 1.0, 0.1, 2, 0, 0.5, 0.3, 1, 4)
    for d in a.d:
        if a.mode == "ils":
            run_ils(d, a.jobs, a.minutes, a.chunk, a.polish_iters, a.T0 or 0.6, a.T1, a.tabu,
                    a.strength, a.seed)
        else:
            run(d, a.restarts, int(a.iters or default_iters(d)), a.jobs, a.seed, a.T0 or 3.0, a.T1,
                a.from_best, a.mode, a.tabu)
