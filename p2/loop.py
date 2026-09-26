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

from analyze import summary
from anneal import default_iters, polish
from evaluator import count_uphill
from store import load_best, save_if_better

ROOT = Path(__file__).parent
LOG = ROOT / "results" / "results.jsonl"
PROGRAMS = ROOT / "programs"
SONNET, OPUS = "claude-sonnet-5", "claude-opus-5-5"
EFFORT = {SONNET: "medium", OPUS: "high"}
STUCK_AFTER = 8  # candidates without improving the target fitness -> use Opus

HELPERS = '''from collections import deque


def forest_labelling(I, d):
    """Provided helper. Labels V minus I component by component in BFS order (from the
    smallest vertex of each component), then gives the vertices of I the top labels.
    If I is independent and Q_d - I is a forest with c trees, U = d*2^(d-1) + c exactly."""
    I = set(I)
    order, seen = [], set(I)
    for r in range(2 ** d):
        if r in seen:
            continue
        seen.add(r)
        queue = deque([r])
        while queue:
            v = queue.popleft()
            order.append(v)
            for j in range(d):
                u = v ^ (1 << j)
                if u not in seen:
                    seen.add(u)
                    queue.append(u)
    return order + sorted(I)
'''

SKELETON = HELPERS + '''

# ---- candidate code (written by the model) ----
{code}


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
Main target: d = 9. Best known U(Q_9) = 2400; lower bound 2368. Goal: U(Q_9) <= 2399.

## What we know
- Excess decomposition (exact, any labelling): U - |E| - 1 = (#valleys - 1) + \
sum_u (N(u) - 1) * updeg(u), where updeg(u) = number of higher neighbours. |E(Q_d)| = d*2^(d-1) \
(d=7: 448, d=8: 1024, d=9: 2304).
- Every best labelling we have (d = 3..9) has the *forest form*: I = the peaks (all \
neighbours lower) is independent and gets the top labels, Q_d - I is an induced forest with c \
trees, each labelled outward from its root (its valley). Then U = |E| + c, and counting edges \
gives (d-1)|I| = 2^(d-1)(d-2) + c. Minimising U in this class = finding the smallest \
independent set I whose removal leaves Q_d acyclic (an independent decycling set).
- d=9: |I| = 224 + c/8, so c is a multiple of 8. Current best: c = 96, |I| = 236, U = 2400. \
Next step down: an independent I with |I| = 235 and Q_9 - I acyclic gives c = 88, U = 2392. \
Values 2393..2399 need a non-forest labelling (some vertex with N >= 2 and a higher neighbour).
- Q7 best (U = 464): I = 56 vertices = union of 7 cosets of the [7,3,4] simplex code (dual of \
the [7,4] Hamming code); c = 16. Q8 best (U = 1040): I = 112 odd-weight vertices = union of 7 \
cosets of the extended Hamming code [8,4,4]; I has a 168-element coordinate-permutation \
symmetry group (GL(3,2)); c = 16. The Q9 best (236-set) has no translation symmetry.
- |I| = 235 is odd, so an I for c = 88 cannot be a union of cosets of any nonzero subspace; \
expect a structured set plus a small repair.
- Tested and useless: the plain product/interleaving Q9 = Q8 x K2 of the optimal Q8 \
labelling gives ~4245 and polishes only to ~3100. Do not retry it.

## Ideas to explore
(a) IMO-style split V = T ⊔ I: T induces a tree or near-tree (forest with few trees) grown \
outward from a single valley, I (near-)independent with the top labels. Build I first, then \
call forest_labelling(I, d).
(b) I from codes: the [7,4] Hamming code (perfect code in Q7; note excess(Q7) = 16 = size of \
the Hamming code and excess(Q3) = 2, possibly a coincidence), the extended [8,4,4] code, \
products like Q7 x Q2 (9 = 7 + 2) with coset choices varying over the Q2 factor, cosets of \
length-9 codes, and repairs of such sets (add/remove a few vertices to kill remaining cycles).
(c) Constructions from the Q7/Q8 optimal structures that are NOT the plain product: different \
coset unions in the two halves of Q9 = Q8 x K2, twisted by an automorphism, or Q7 x Q2 \
with the four Q7-layers using different coset unions.
Your program may also run a small search of its own (e.g. over coset choices or greedy \
repairs, checking acyclicity) as long as it is deterministic and finishes in time.

## Code contract
Write one Python function `construct(d)` returning a list of all 2^d vertices in increasing \
label order (element k is the vertex with label k). A vertex is an int in [0, 2^d); bit j is \
coordinate j; u, v are adjacent iff u ^ v is a power of two. A helper \
`forest_labelling(I, d)` is already defined (do not redefine it): given a vertex set I it \
returns the forest-form labelling described above. You may define helpers and use the \
standard library, numpy and networkx. It must be deterministic, work for every d in 7..9 (at \
least), and run in under 30 seconds for d = 9. Do not print anything. Scores are computed by \
us (exact count, then a short local-search polish); do not claim scores.

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
        path.write_text(SKELETON.replace("{code}", code))
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


def evaluate(code, meta, eval_ds, timeout, target, jobs):
    """Score a program on every d, polish the target d, log one row per d. Returns the rows."""
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
    # polish the target d with the improved local search, `jobs` seeds; keep the best
    if target in raw:
        polished = Parallel(n_jobs=jobs)(
            delayed(polish)(raw[target][0], target, default_iters(target) // 8, s)
            for s in range(jobs))
        order, score = min(polished, key=lambda t: t[1])
        verified = save_if_better(target, order, f"loop {h} polished")
        assert verified == score, f"polish score {score} != evaluator {verified}"
    for d in raw:
        row = {**meta, "hash": h, "d": d, "raw": raw[d][1], "runtime": raw[d][2]}
        if d == target:
            row["polished"] = verified
        rows.append(row)
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
        if r.get("hash") == h:
            out[r["d"]] = ("error" if "raw" not in r else f"raw={r['raw']}" +
                           (f" polished={r['polished']}" if "polished" in r else ""))
    return out


def build_prompt(target, errors):
    parts = ["Current best known labellings found in this search (after annealing): " +
             ", ".join(f"d={d}: {b['score']}" for d in range(3, 10) if (b := load_best(d)))]
    if (b := load_best(target)):
        parts.append(f"## Excess decomposition of the current best Q{target} labelling\n"
                     + summary(b["order"], target))
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
    p.add_argument("--eval-ds", type=int, nargs="+", default=[7, 8, 9])
    p.add_argument("--jobs", type=int, default=2, help="polish processes (ILS may be using 4)")
    p.add_argument("--timeout", type=float, default=60)
    p.add_argument("--fake", action="store_true", help="skip the API; use a fixed program")
    a = p.parse_args()
    if a.target not in a.eval_ds:
        a.eval_ds.append(a.target)

    load_dotenv(ROOT.parent / ".env")
    client = None if a.fake else anthropic.Anthropic(max_retries=4)
    if not leaderboard(a.target):
        evaluate(SEED_PROGRAM, {"model": "seed", "parent": None}, a.eval_ds, a.timeout,
                 a.target, a.jobs)

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
            rows = evaluate(code, meta, a.eval_ds, a.timeout, a.target, a.jobs)
            errors += [r["error"] for r in rows if "error" in r]
            line = " ".join(f"d{r['d']}:{r.get('raw', 'ERR')}" +
                            (f"->{r['polished']}" if "polished" in r else "") for r in rows)
            print(f"[round {rnd}] {model} {rows[0]['hash']} {line}", flush=True)

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
