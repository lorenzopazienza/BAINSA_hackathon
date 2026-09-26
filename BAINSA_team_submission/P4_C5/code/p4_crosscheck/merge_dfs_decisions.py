#!/usr/bin/env python3
"""Merge dfs_decisions/kKK_chunk*.json into dfs_view/kKK_sun.json (p4_dfs's own result format).

Checks, for each k: all n_chunks chunk files present; every survivor index 0..N-1 decided
exactly once; the moduli at each index equal p4_dfs's enumerated survivor list; the survivor
hash equals p4_dfs's stored survivors_sha256. dfs_view/ also gets symlinks to p4_dfs's own
k = 3..14 result files, so that p4_dfs/compare.py can be run over k = 3..16 unmodified.

Usage: python merge_dfs_decisions.py 15 16
"""
import glob
import hashlib
import json
import os
import sys

from dfs_decide_chunk import DFS, HERE, survivors_of


def merge(k):
    surv, sha, src = survivors_of(k)
    chunks = sorted(glob.glob(os.path.join(HERE, "dfs_decisions", f"k{k:02d}_chunk*.json")))
    parts = [json.load(open(c)) for c in chunks]
    n = parts[0]["n_chunks"]
    assert len(parts) == n and sorted(p["chunk"] for p in parts) == list(range(n)), f"k={k}: chunks missing"
    records = [None] * len(surv)
    for p in parts:
        assert p["source_survivors_sha256"] == sha and p["B"] == k - 1
        for r in p["records"]:
            i = r["index"]
            assert records[i] is None, f"k={k}: index {i} decided twice"
            assert tuple(r["moduli"]) == surv[i], f"k={k}: moduli mismatch at {i}"
            records[i] = r
    assert all(r is not None for r in records), f"k={k}: some survivors not decided"
    text = json.dumps([list(s) for s in sorted(surv)], separators=(",", ":"))
    assert hashlib.sha256(text.encode()).hexdigest() == sha
    orig = json.load(open(src))
    n_sat = sum(r["decision"] == "SAT" for r in records)
    out = {
        "k": k, "status": "COMPLETE", "enumeration_finished": True,
        "gcd_bound": [2, k - 1],
        "note": "survivors and enumeration counts from p4_dfs's own enumeration file "
                f"({os.path.relpath(src, HERE)}); decisions by sun_dfs.decide(ms, B) default mode, "
                f"run in {n} round-robin chunks by p4_crosscheck/dfs_decide_chunk.py",
        "counts": {**orig["counts"], "SAT": n_sat, "UNSAT": len(records) - n_sat, "UNDECIDED": 0,
                   "decision_nodes": sum(r["nodes"] or 0 for r in records)},
        "wall_clock_s": {"enumeration": orig["wall_clock_s"]["enumeration"],
                         "decision_cpu_sum_over_chunks": round(sum(p["wall_seconds"] for p in parts), 3),
                         "decision_max_chunk": round(max(p["wall_seconds"] for p in parts), 3)},
        "survivors_sha256": sha,
        "survivors": [{"moduli": r["moduli"], "decision": r["decision"],
                       **({"residues": r["residues"]} if "residues" in r else {})} for r in records],
    }
    os.makedirs(os.path.join(HERE, "dfs_view"), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "dfs_view", f"k{k:02d}_sun.json"), "w"))
    print(f"k={k}: {len(records)} survivors decided (SAT={n_sat}, UNSAT={len(records) - n_sat}) from "
          f"{n} chunks; decision CPU {out['wall_clock_s']['decision_cpu_sum_over_chunks']}s, "
          f"longest chunk {out['wall_clock_s']['decision_max_chunk']}s; sha256 {sha[:16]} matches")


if __name__ == "__main__":
    view = os.path.join(HERE, "dfs_view")
    os.makedirs(view, exist_ok=True)
    for k in range(3, 15):
        link = os.path.join(view, f"k{k:02d}_sun.json")
        if not os.path.lexists(link):
            os.symlink(os.path.relpath(os.path.join(DFS, "results", f"k{k:02d}_sun.json"), view), link)
    for k in map(int, sys.argv[1:]):
        merge(k)
