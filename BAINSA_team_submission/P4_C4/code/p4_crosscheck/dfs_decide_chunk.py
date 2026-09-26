#!/usr/bin/env python3
"""Decide one chunk of p4_dfs's survivor list with p4_dfs's own decider, unmodified.

Imports review/Teo /hackaton/p4_dfs/sun_dfs.py read-only and calls
    sun_dfs.decide(ms, B)            # default mode: plain=False, interchange=True
exactly as sun_dfs.run_k does for each survivor (B = k - 1, Sun's conjecture). A SAT answer
is re-checked literally inside decide() (assert verify_solution). Survivors are read from
p4_dfs's own enumeration file (results/kXX_sun*.json, enumeration_finished = true) and
assigned round-robin: survivor number idx goes to chunk idx % n_chunks.

Usage: PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 python dfs_decide_chunk.py K CHUNK N_CHUNKS
Output: p4_crosscheck/dfs_decisions/kKK_chunkCCofNN.json
"""
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DFS = os.path.join(HERE, "..", "review", "Teo ", "hackaton", "p4_dfs")
sys.path.insert(0, DFS)
import sun_dfs  # noqa: E402


def survivors_of(k):
    files = [f for f in glob.glob(os.path.join(DFS, "results", f"k{k:02d}_sun*.json"))
             if not f.endswith(".canonical.json")]
    assert len(files) == 1, files
    d = json.load(open(files[0]))
    assert d["enumeration_finished"] is True and d["k"] == k
    return [tuple(r["moduli"]) for r in d["survivors"]], d["survivors_sha256"], files[0]


def main():
    k, chunk, n = map(int, sys.argv[1:4])
    B = k - 1
    surv, sha, src = survivors_of(k)
    mine = [(i, s) for i, s in enumerate(surv) if i % n == chunk]
    t0, records, nodes_total = time.time(), [], 0
    for j, (i, s) in enumerate(mine):
        t = time.time()
        sol, nodes = sun_dfs.decide(s, B)
        rec = {"index": i, "moduli": list(s), "decision": "SAT" if sol else "UNSAT",
               "nodes": nodes, "seconds": round(time.time() - t, 4)}
        if sol:
            rec["residues"] = sol
        records.append(rec)
        nodes_total += nodes or 0
        if (j + 1) % 2000 == 0:
            print(f"[k={k} chunk {chunk}/{n}] {j + 1}/{len(mine)} decided, {time.time() - t0:.0f}s",
                  flush=True)
    out = {"k": k, "B": B, "chunk": chunk, "n_chunks": n, "source_file": os.path.relpath(src, HERE),
           "source_survivors_sha256": sha, "decider": "sun_dfs.decide(ms, B) default "
           "(plain=False, interchange=True)", "count": len(records),
           "SAT": sum(r["decision"] == "SAT" for r in records),
           "UNSAT": sum(r["decision"] == "UNSAT" for r in records),
           "decision_nodes": nodes_total, "wall_seconds": round(time.time() - t0, 3),
           "records": records}
    os.makedirs(os.path.join(HERE, "dfs_decisions"), exist_ok=True)
    path = os.path.join(HERE, "dfs_decisions", f"k{k:02d}_chunk{chunk:02d}of{n:02d}.json")
    json.dump(out, open(path, "w"))
    print(f"[k={k} chunk {chunk}/{n}] done: {len(records)} decided, SAT={out['SAT']} "
          f"UNSAT={out['UNSAT']}, {out['wall_seconds']}s -> {os.path.basename(path)}", flush=True)


if __name__ == "__main__":
    main()
