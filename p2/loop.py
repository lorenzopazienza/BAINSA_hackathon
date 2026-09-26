"""FunSearch-style loop: Claude writes construct(d), we score it exactly, polish, keep the best.

Each round asks Claude for `--batch` candidates in parallel. A candidate is run
in a subprocess (timeout, no API key in its env) for every d in --eval-ds,
scored by evaluator.py, then polished by a short anneal. Every (candidate, d)
is logged to results/results.jsonl; programs are saved to programs/{hash}.py.
Fitness = polished score at --target d (raw score breaks ties).

Usage: python loop.py --rounds 20 --batch 4
       python loop.py --rounds 1 --batch 2 --fake     # pipeline test, no API calls
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from joblib import Parallel, delayed

from anneal import default_iters, polish
from evaluator import count_uphill
from store import load_best, save_if_better

ROOT = Path(__file__).parent
LOG = ROOT / "results" / "results.jsonl"
PROGRAMS = ROOT / "programs"
SONNET, OPUS = "claude-sonnet-5", "claude-opus-5-5"
EFFORT = {SONNET: "medium", OPUS: "high"}
STUCK_AFTER = 8  # candidates without improving the target fitness -> use Opus

SKELETON = '''{code}


# ---- fixed harness (not written by the model) ----
if __name__ == "__main__":
    import json, sys
    _order = construct(int(sys.argv[1]))
    print(json.dumps([int(v) for v in _order]))
'''

SYSTEM = """You are a research mathematician and expert Python programmer searching for \
labellings of the hypercube Q_d with as few uphill paths as possible.

## Problem
Label the 2^d vertices of Q_d bijectively with 0..2^d-1. A vertex is a *valley* if all its \
neighbours have larger labels. An *uphill path* is a path v1, v2, ..., vk (k >= 1) starting \
at a valley whose labels strictly increase. U = number of uphill paths. Minimise U.
Exact count: process vertices in increasing label; N(v) = 1 if v is a valley, else the sum \
of N(u) over lower-labelled neighbours u; U = sum of N(v).

## Known facts
- For any connected graph U >= |E| + 1, with equality iff V = T ⊔ I where G[T] is a tree and \
I is independent (IMO 2022 P6: the tree is grown outward from the unique valley and the \
independent set gets the top labels). For Q_d (d >= 3) equality is impossible, so \
U(Q_d) >= d*2^(d-1) + 2.
- |E(Q_d)| = d*2^(d-1): d=6: 192, d=7: 448, d=8: 1024, d=9: 2304.
- Main target: d = 9. Best known U(Q_9) = 2400; lower bound 2368. Goal: U(Q_9) <= 2399.

## Ideas worth exploring
- IMO-2022-P6 structure: a spanning-ish tree T grown from a single valley, labelled \
outward (BFS/DFS order), with a near-independent set I receiving the top labels. The excess \
U - |E| - 1 comes from vertices outside T that are not independent, or from extra valleys.
- Recursive constructions Q_d = Q_{d-1} x K2: combine a good labelling of Q_{d-1} with a \
modified copy; interleave or offset the two halves.
- Gray-code orders, Hamming-weight layers, parity classes (Q_d is bipartite: the even and \
odd vertices are each independent), and symmetry (coordinate permutations, bit flips).
- Choose which vertices go in I: large independent sets whose complement induces a tree or \
near-tree; then order T so each vertex of T has exactly one lower neighbour.

## Code contract
Write one Python function `construct(d)` returning a list of all 2^d vertices in increasing \
label order (element k is the vertex with label k). A vertex is an int in [0, 2^d); bit j is \
coordinate j; u, v are adjacent iff u ^ v is a power of two. You may define helpers and use \
the standard library, numpy and networkx. It must be deterministic, work for every d in 3..9, \
and run in under 30 seconds for d = 9. Do not print anything. Scores are computed by us; do \
not claim scores.

Do not over-deliberate: a concrete, runnable program is worth more than an exhaustive \
analysis, since it will be scored and refined in later rounds.
Reply with a short explanation of the idea (at most 5 sentences), then exactly one \
```python code block containing the full program (imports, helpers, construct)."""

SEED_PROGRAM = '''def construct(d):
    """Seed: identity labelling (vertex k gets label k)."""
    return list(range(2 ** d))
'''

FAKE_PROGRAM = '''def construct(d):
    """Fake candidate for --fake: reflected Gray code order."""
    return [k ^ (k >> 1) for k in range(2 ** d)]
'''


def program_hash(code):
    return hashlib.sha256(code.encode()).hexdigest()[:12]


def run_candidate(code, d, timeout):
    """Run construct(d) in a subprocess. Returns (order, error, seconds)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC")}
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "candidate.py"
        path.write_text(SKELETON.format(code=code))
        t = time.time()
        try:
            p = subprocess.run([sys.executable, str(path), str(d)], capture_output=True,
                               text=True, timeout=timeout, cwd=tmp, env=env)
        except subprocess.TimeoutExpired:
            return None, f"d={d}: timeout after {timeout}s", time.time() - t
        secs = time.time() - t
    if p.returncode != 0:
        return None, f"d={d}: exit {p.returncode}\n{p.stderr[-1500:]}", secs
    try:
        order = json.loads(p.stdout.strip().splitlines()[-1])
        count_uphill(order, d)  # validates the bijection
    except Exception as e:
        return None, f"d={d}: invalid output: {e!r}"[:1500], secs
    return order, None, secs


def evaluate(code, meta, eval_ds, timeout):
    """Score a program on every d, polish, log one row per d. Returns the logged rows."""
    h = program_hash(code)
    PROGRAMS.mkdir(exist_ok=True)
    (PROGRAMS / f"{h}.py").write_text(code)
    raw = {}
    rows = []
    for d in eval_ds:
        order, err, secs = run_candidate(code, d, timeout)
        if err:
            rows.append({**meta, "hash": h, "d": d, "error": err, "runtime": secs})
            continue
        raw[d] = (order, count_uphill(order, d), secs)
        save_if_better(d, order, f"loop {h} raw")
    # polish every d with 2 seeds in parallel; keep the better seed
    jobs = [(d, s) for d in raw for s in range(2)]
    polished = Parallel(n_jobs=min(8, len(jobs) or 1))(
        delayed(polish)(raw[d][0], d, default_iters(d) // 8, s) for d, s in jobs)
    best_pol = {}
    for (d, _), (order, score) in zip(jobs, polished):
        if d not in best_pol or score < best_pol[d][1]:
            best_pol[d] = (order, score)
    for d in raw:
        order, score = best_pol[d]
        verified = save_if_better(d, order, f"loop {h} polished")
        assert verified == score, f"polish score {score} != evaluator {verified}"
        rows.append({**meta, "hash": h, "d": d, "raw": raw[d][1], "polished": verified,
                     "runtime": raw[d][2]})
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a") as f:
        for r in rows:
            f.write(json.dumps({**r, "timestamp": time.time()}) + "\n")
    return rows


def leaderboard(target):
    """Programs ranked by (polished, raw) at the target d, from the log."""
    best = {}
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            r = json.loads(line)
            if r["d"] == target and "polished" in r:
                key = (r["polished"], r["raw"])
                if r["hash"] not in best or key < best[r["hash"]]:
                    best[r["hash"]] = key
    return sorted(best.items(), key=lambda kv: kv[1])


def scores_by_d(h):
    out = {}
    for line in LOG.read_text().splitlines():
        r = json.loads(line)
        if r["hash"] == h:
            out[r["d"]] = f"raw={r['raw']} polished={r['polished']}" if "polished" in r else "error"
    return out


def build_prompt(target, errors):
    parts = ["Current best known labellings found in this search (after annealing): " +
             ", ".join(f"d={d}: {b['score']}" for d in range(3, 10) if (b := load_best(d)))]
    top = leaderboard(target)[:2]
    if not top:
        parts.append("No programs scored yet.")
    for rank, (h, _) in enumerate(top, 1):
        s = "; ".join(f"d={d}: {v}" for d, v in sorted(scores_by_d(h).items()))
        parts.append(f"## Program #{rank} (id {h})\nScores: {s}\n"
                     f"```python\n{(PROGRAMS / f'{h}.py').read_text()}\n```")
    if errors:
        parts.append("## Recent failures (avoid these)\n" + "\n---\n".join(errors[-3:]))
    parts.append(f"Write a new, improved construct(d). The fitness is the raw and polished "
                 f"(polished = short local anneal) score at d={target}; lower is better. Aim for "
                 f"a structurally different idea or a real improvement, not a cosmetic tweak.")
    return "\n\n".join(parts)


def ask_claude(client, model, prompt):
    """Returns (code or None, usage dict, error or None)."""
    with client.messages.stream(
        model=model,
        max_tokens=64000,
        thinking={"type": "adaptive"},
        output_config={"effort": EFFORT[model]},
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        msg = stream.get_final_message()
    u = msg.usage
    usage = {"tokens_in": u.input_tokens, "tokens_out": u.output_tokens,
             "cache_read": u.cache_read_input_tokens or 0,
             "cache_write": u.cache_creation_input_tokens or 0}
    if msg.stop_reason == "refusal":
        return None, usage, "refusal"
    text = "".join(b.text for b in msg.content if b.type == "text")
    blocks = re.findall(r"```python\n(.*?)```", text, re.S)
    if not blocks or "def construct" not in blocks[-1]:
        return None, usage, f"no construct() code block (stop_reason={msg.stop_reason})"
    return blocks[-1].strip() + "\n", usage, None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rounds", type=int, default=10)
    p.add_argument("--batch", type=int, default=4, help="parallel Claude calls per round")
    p.add_argument("--target", type=int, default=9)
    p.add_argument("--eval-ds", type=int, nargs="+", default=[6, 7, 8, 9])
    p.add_argument("--timeout", type=float, default=60)
    p.add_argument("--fake", action="store_true", help="skip the API; use a fixed program")
    a = p.parse_args()
    if a.target not in a.eval_ds:
        a.eval_ds.append(a.target)

    load_dotenv(ROOT.parent / ".env")
    client = None if a.fake else anthropic.Anthropic(max_retries=4)
    if not leaderboard(a.target):
        evaluate(SEED_PROGRAM, {"model": "seed", "parent": None}, a.eval_ds, a.timeout)

    calls, since_improvement, errors = 0, 0, []
    for rnd in range(a.rounds):
        board = leaderboard(a.target)
        best_before = board[0][1]
        parent = board[0][0]
        prompt = build_prompt(a.target, errors)
        models = []
        for _ in range(a.batch):
            calls += 1
            models.append("fake" if a.fake else OPUS if calls % 10 == 0 or since_improvement >= STUCK_AFTER else SONNET)

        def call(model):
            if a.fake:
                return FAKE_PROGRAM, {"tokens_in": 0, "tokens_out": 0}, None
            try:
                return ask_claude(client, model, prompt)
            except anthropic.APIError as e:
                return None, {}, f"API error: {e!r}"[:500]

        with ThreadPoolExecutor(a.batch) as pool:
            answers = list(pool.map(call, models))

        for model, (code, usage, err) in zip(models, answers):
            meta = {"model": model, "parent": parent, "round": rnd, **usage}
            if err:
                with open(LOG, "a") as f:
                    f.write(json.dumps({**meta, "hash": None, "d": None, "error": err,
                                        "timestamp": time.time()}) + "\n")
                print(f"[round {rnd}] {model}: {err}", flush=True)
                continue
            if (PROGRAMS / f"{program_hash(code)}.py").exists():
                print(f"[round {rnd}] {model}: duplicate of {program_hash(code)}, skipped", flush=True)
                continue
            rows = evaluate(code, meta, a.eval_ds, a.timeout)
            errors += [r["error"] for r in rows if "error" in r]
            summary = " ".join(f"d{r['d']}:{r.get('raw', 'ERR')}->{r.get('polished', '')}"
                               for r in rows)
            print(f"[round {rnd}] {model} {rows[0]['hash']} {summary}", flush=True)

        board = leaderboard(a.target)
        if board and board[0][1] < best_before:
            since_improvement = 0
            print(f"*** new best program at d={a.target}: polished={board[0][1][0]} ({board[0][0]})",
                  flush=True)
        else:
            since_improvement += a.batch
    best = load_best(a.target)
    print(f"done. best stored Q{a.target} = {best['score']} ({best['source']})")


if __name__ == "__main__":
    main()
