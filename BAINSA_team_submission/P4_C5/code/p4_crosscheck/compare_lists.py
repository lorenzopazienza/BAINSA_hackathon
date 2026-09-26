#!/usr/bin/env python3
"""Independent elementwise comparison of the survivor lists of p4_codex and p4_dfs.

For each k both lists are read from each implementation's own result file (exact, known
formats; anything unexpected is an error):
  p4_codex: p4_codex/results_k{k}.json            -> "survivors": [{"moduli", "decision"}, ...]
  p4_dfs:   p4_dfs/results/k{kk}_sun[_UNFINISHED].json -> "survivors": [{"moduli", "decision"}]
Each survivor is normalised to a tuple of moduli in ascending order and the list is sorted.
Nothing is reconciled silently: survivors that were not already ascending, duplicates, and
every survivor present on only one side are reported explicitly.

Canonical text (same definition as p4_dfs/canonical.py): JSON list of the sorted survivors,
each an ascending list, separators (',', ':'), no whitespace; its SHA-256 is reported for
both sides. Each file's stored hash is checked under its own definition: p4_dfs stores the
canonical-text hash; p4_codex stores SHA-256 of json.dumps(full survivor records incl.
"decision" and "minimal_part", sort_keys=True, separators=(',', ':')) (see
p4_codex/verify_results.py), which is a different text by design.

Decisions: p4_codex's from its file; p4_dfs's from its file, or (for k = 15, 16, whose p4_dfs
files are enumeration-only) from dfs_decisions/kKK_chunk*.json produced by
dfs_decide_chunk.py with p4_dfs's own decider. Every disagreement is listed.

Usage: python compare_lists.py [--ks 3-16] [--json compare_report.json]
"""
import argparse
import glob
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CODEX = os.path.join(HERE, "..", "p4_codex")
DFS = os.path.join(HERE, "..", "review", "Teo ", "hackaton", "p4_dfs")


def canonical(survivors):
    text = json.dumps([list(s) for s in survivors], separators=(",", ":"))
    return text, hashlib.sha256(text.encode()).hexdigest()


def normalise(raw, k, where):
    out, not_sorted = [], 0
    for i, r in enumerate(raw):
        m = r["moduli"]
        if not (isinstance(m, list) and len(m) == k and all(type(x) is int for x in m)):
            raise ValueError(f"{where}[{i}]: bad moduli {m!r}")
        if m != sorted(m):
            not_sorted += 1
        out.append(tuple(sorted(m)))
    return out, not_sorted


def load_codex(k):
    path = os.path.join(CODEX, f"results_k{k}.json")
    d = json.load(open(path))
    assert d["k"] == k and d["gcd_upper_bound"] == k - 1, path
    surv, not_sorted = normalise(d["survivors"], k, path)
    dec = {}
    for s, r in zip(surv, d["survivors"]):
        dec.setdefault(s, []).append(r.get("decision"))
    own = hashlib.sha256(json.dumps(d["survivors"], sort_keys=True, separators=(",", ":"))
                         .encode()).hexdigest()
    return {"file": os.path.relpath(path, HERE), "status": d["status"], "survivors": surv,
            "not_sorted": not_sorted, "decisions": dec, "stored_sha256": d["survivor_sha256"],
            "stored_matches_own_definition": own == d["survivor_sha256"],
            "wall_seconds": d.get("wall_seconds")}


def load_dfs(k):
    files = [f for f in glob.glob(os.path.join(DFS, "results", f"k{k:02d}_sun*.json"))
             if not f.endswith(".canonical.json")]
    if len(files) != 1:
        raise ValueError(f"p4_dfs k={k}: expected one result file, found {files}")
    d = json.load(open(files[0]))
    assert d["k"] == k and d["gcd_bound"] == [2, k - 1], files[0]
    surv, not_sorted = normalise(d["survivors"], k, files[0])
    dec, source = {}, "p4_dfs result file"
    for s, r in zip(surv, d["survivors"]):
        dec.setdefault(s, []).append(r.get("decision"))
    chunks = sorted(glob.glob(os.path.join(HERE, "dfs_decisions", f"k{k:02d}_chunk*.json")))
    if chunks and all(v == ["UNDECIDED"] for v in dec.values()):
        dec, n_chunks = {}, None
        for c in chunks:
            cd = json.load(open(c))
            assert cd["source_survivors_sha256"] == d["survivors_sha256"], c
            n_chunks = cd["n_chunks"]
            for r in cd["records"]:
                dec.setdefault(tuple(r["moduli"]), []).append(r["decision"])
        complete = len(chunks) == n_chunks
        source = f"dfs_decisions/ ({len(chunks)}/{n_chunks} chunks{'' if complete else ', INCOMPLETE'})"
    return {"file": os.path.relpath(files[0], HERE), "status": d["status"],
            "enumeration_finished": d["enumeration_finished"], "survivors": surv,
            "not_sorted": not_sorted, "decisions": dec, "decision_source": source,
            "stored_sha256": d["survivors_sha256"], "wall_clock_s": d["wall_clock_s"]}


def decision_summary(side, surv):
    counts = {}
    for s in surv:
        v = side["decisions"].get(s)
        key = "MISSING" if not v else (v[0] if len(set(v)) == 1 else "INCONSISTENT")
        counts[key] = counts.get(key, 0) + 1
    return counts


def compare(k):
    c, d = load_codex(k), load_dfs(k)
    lc, ld = sorted(c["survivors"]), sorted(d["survivors"])
    text_c, sha_c = canonical(sorted(set(lc)))
    text_d, sha_d = canonical(sorted(set(ld)))
    only_c, only_d = sorted(set(lc) - set(ld)), sorted(set(ld) - set(lc))
    disagreements = []
    for s in sorted(set(lc) & set(ld)):
        a, b = c["decisions"].get(s), d["decisions"].get(s)
        if a and b and "UNDECIDED" not in a + b and set(a) != set(b):
            disagreements.append({"moduli": list(s), "codex": a, "dfs": b})
    row = {
        "k": k,
        "codex": {"file": c["file"], "status": c["status"], "count": len(lc),
                  "duplicates": len(lc) - len(set(lc)), "normalised_unsorted": c["not_sorted"],
                  "canonical_sha256": sha_c, "stored_sha256": c["stored_sha256"],
                  "stored_matches_own_definition": c["stored_matches_own_definition"],
                  "decisions": decision_summary(c, sorted(set(lc))), "wall_seconds": c["wall_seconds"]},
        "dfs": {"file": d["file"], "status": d["status"], "enumeration_finished": d["enumeration_finished"],
                "count": len(ld), "duplicates": len(ld) - len(set(ld)), "normalised_unsorted": d["not_sorted"],
                "canonical_sha256": sha_d, "stored_sha256": d["stored_sha256"],
                "stored_matches_own_definition": d["stored_sha256"] == sha_d,
                "decision_source": d["decision_source"],
                "decisions": decision_summary(d, sorted(set(ld))), "wall_clock_s": d["wall_clock_s"]},
        "lists_identical": lc == ld,
        "only_in_codex": [list(s) for s in only_c],
        "only_in_dfs": [list(s) for s in only_d],
        "decision_disagreements": disagreements,
    }
    return row


def parse_ks(s):
    a, b = map(int, s.split("-"))
    return range(a, b + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ks", default="3-16")
    ap.add_argument("--json", default=os.path.join(HERE, "compare_report.json"))
    args = ap.parse_args()
    rows, all_ok = [], True
    for k in parse_ks(args.ks):
        r = compare(k)
        rows.append(r)
        c, d = r["codex"], r["dfs"]
        ok = (r["lists_identical"] and not r["decision_disagreements"]
              and c["duplicates"] == d["duplicates"] == 0
              and c["stored_matches_own_definition"] and d["stored_matches_own_definition"])
        all_ok &= ok
        print(f"k={k:2d}  {'IDENTICAL' if r['lists_identical'] else 'DIFFERENT'}  "
              f"codex={c['count']:7d}  dfs={d['count']:7d}  sha256 codex={c['canonical_sha256'][:16]} "
              f"dfs={d['canonical_sha256'][:16]}  stored hash reproduces: codex={c['stored_matches_own_definition']} "
              f"dfs={d['stored_matches_own_definition']}")
        print(f"       decisions codex={c['decisions']}  dfs={d['decisions']} ({d['decision_source']})  "
              f"disagreements={len(r['decision_disagreements'])}")
        for side in ("codex", "dfs"):
            if r[side]["duplicates"]:
                print(f"       {r[side]['duplicates']} duplicate survivors in {side}")
            if r[side]["normalised_unsorted"]:
                print(f"       {r[side]['normalised_unsorted']} survivors in {side} were not ascending (sorted)")
        for s in r["only_in_codex"]:
            print(f"       only in codex: {s}")
        for s in r["only_in_dfs"]:
            print(f"       only in dfs:   {s}")
        for x in r["decision_disagreements"]:
            print(f"       decision differs on {x['moduli']}: codex={x['codex']} dfs={x['dfs']}")
    json.dump(rows, open(args.json, "w"), indent=1)
    pending = sum(r["dfs"]["decisions"].get("UNDECIDED", 0) for r in rows)
    print(("ALL LISTS IDENTICAL, NO DECISION DISAGREEMENT" if all_ok else "NOT ALL EQUAL (see above)")
          + (f"; {pending} p4_dfs survivors still UNDECIDED" if pending else ""))


if __name__ == "__main__":
    main()
