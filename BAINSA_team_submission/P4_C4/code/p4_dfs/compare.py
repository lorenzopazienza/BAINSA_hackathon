#!/usr/bin/env python3
"""Elementwise comparison of survivor lists: p4_dfs (this checker) vs p4_codex (SAT checker).

For every k both lists are normalised to the same canonical form: each survivor becomes
a tuple of moduli in ascending order, and the list is sorted lexicographically. The script
then reports, per k:
  * the survivor count of each side;
  * EQUAL, or the explicit survivors missing on either side;
  * duplicates inside either list (normalisation removes nothing silently: duplicates
    are reported as a difference);
  * decisions (SAT/UNSAT/UNDECIDED) per survivor, where both sides provide them, with
    every disagreement listed;
  * whether each side's run is complete.
Nothing is reconciled.  The exit code is 0 only if every compared k is EQUAL with
matching decisions.

Usage:
    python compare.py --codex ../p4_codex --ours results [--ks 3-14] [--json report.json]

Accepted p4_codex layouts (the first match wins; anything else is an error, not a guess):
  * top-level list of survivors;
  * top-level object with a survivor list under one of SURVIVOR_KEYS.
A survivor is a list of integers, or an object with the moduli under one of MODULI_KEYS
and optionally a decision under one of DECISION_KEYS.  k is taken from a "k" field or
else from the file name (".*k0*(\\d+).*\\.json").
"""
import argparse
import glob
import json
import os
import re
import sys

SURVIVOR_KEYS = ("survivors", "survivor_list", "survivor_multisets", "multisets", "candidates")
MODULI_KEYS = ("moduli", "multiset", "m", "mods")
DECISION_KEYS = ("decision", "status", "result", "sat")


class FormatError(Exception):
    pass


def norm_decision(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return "SAT" if v else "UNSAT"
    s = str(v).strip().upper()
    if s in ("SAT", "SATISFIABLE", "SOLVABLE", "TRUE"):
        return "SAT"
    if s in ("UNSAT", "UNSATISFIABLE", "UNSOLVABLE", "FALSE"):
        return "UNSAT"
    if s in ("UNDECIDED", "UNKNOWN", "TIMEOUT", "UNFINISHED"):
        return "UNDECIDED"
    raise FormatError(f"unrecognised decision value {v!r}")


def parse_survivor(x, where):
    if isinstance(x, list):
        mods, dec = x, None
    elif isinstance(x, dict):
        keys = [k for k in MODULI_KEYS if k in x]
        if len(keys) != 1:
            raise FormatError(f"{where}: survivor object without a unique moduli key: {sorted(x)}")
        mods = x[keys[0]]
        dkeys = [k for k in DECISION_KEYS if k in x]
        dec = norm_decision(x[dkeys[0]]) if dkeys else None
    else:
        raise FormatError(f"{where}: survivor of type {type(x).__name__}")
    if not (isinstance(mods, list) and all(isinstance(m, int) and not isinstance(m, bool) for m in mods)):
        raise FormatError(f"{where}: moduli are not a list of integers: {mods!r}")
    return tuple(sorted(mods)), dec


def load(path):
    with open(path) as f:
        d = json.load(f)
    k = None
    meta = {}
    if isinstance(d, list):
        raw = d
    elif isinstance(d, dict):
        keys = [key for key in SURVIVOR_KEYS if key in d]
        if len(keys) != 1:
            raise FormatError(f"{path}: expected exactly one of {SURVIVOR_KEYS}, found {sorted(d)}")
        raw = d[keys[0]]
        k = d.get("k")
        meta = {key: d[key] for key in ("status", "complete", "counts") if key in d}
    else:
        raise FormatError(f"{path}: top-level JSON is {type(d).__name__}")
    if k is None:
        m = re.search(r"k0*(\d+)", os.path.basename(path))
        if not m:
            raise FormatError(f"{path}: cannot determine k")
        k = int(m.group(1))
    surv = [parse_survivor(x, f"{path}[{i}]") for i, x in enumerate(raw)]
    for s, _ in surv:
        if len(s) != k:
            raise FormatError(f"{path}: survivor {s} has {len(s)} moduli, expected k={k}")
    return int(k), surv, meta


def collect(pattern_list):
    out = {}
    for pat in pattern_list:
        for p in sorted(glob.glob(pat)):
            if p.endswith(".canonical.json"):
                continue
            k, surv, meta = load(p)
            if k in out:
                raise FormatError(f"two files for k={k}: {out[k][2]} and {p}")
            out[k] = (surv, meta, p)
    return out


def parse_ks(s):
    ks = set()
    for part in s.split(","):
        if "-" in part:
            a, b = map(int, part.split("-"))
            ks.update(range(a, b + 1))
        else:
            ks.add(int(part))
    return sorted(ks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codex", required=True, help="directory with p4_codex results_k*.json")
    ap.add_argument("--ours", default="results", help="directory with p4_dfs k*_sun*.json")
    ap.add_argument("--ks", default="3-14")
    ap.add_argument("--json", default=None, help="write a machine-readable report here")
    args = ap.parse_args()

    try:
        theirs = collect([os.path.join(args.codex, "results_k*.json")])
        ours = collect([os.path.join(args.ours, "k*_sun.json"),
                        os.path.join(args.ours, "k*_sun_UNFINISHED.json")])
    except FormatError as e:
        print("FORMAT ERROR:", e)
        sys.exit(2)

    report, all_ok = [], True
    for k in parse_ks(args.ks):
        row = {"k": k}
        if k not in ours or k not in theirs:
            row["verdict"] = "MISSING " + ", ".join(
                n for n, d in (("p4_dfs", ours), ("p4_codex", theirs)) if k not in d)
            print(f"k={k:2d}: {row['verdict']}")
            report.append(row)
            all_ok = False
            continue
        so, mo, po = ours[k]
        st, mt, pt = theirs[k]
        lo = sorted(s for s, _ in so)
        lt = sorted(s for s, _ in st)
        dup_o = len(lo) - len(set(lo))
        dup_t = len(lt) - len(set(lt))
        only_o = sorted(set(lo) - set(lt))
        only_t = sorted(set(lt) - set(lo))
        equal = lo == lt
        row.update(count_p4_dfs=len(lo), count_p4_codex=len(lt), equal=equal,
                   duplicates_p4_dfs=dup_o, duplicates_p4_codex=dup_t,
                   only_in_p4_dfs=[list(s) for s in only_o],
                   only_in_p4_codex=[list(s) for s in only_t],
                   status_p4_dfs=mo.get("status"), status_p4_codex=mt.get("status", mt.get("complete")))
        # decisions
        do = {s: d for s, d in so}
        dt = {s: d for s, d in st}
        dec_diff, dec_missing = [], 0
        for s in set(lo) & set(lt):
            a, b = do.get(s), dt.get(s)
            if a is None or b is None:
                dec_missing += 1
            elif a != b:
                dec_diff.append((list(s), a, b))
        row.update(decision_disagreements=sorted(dec_diff), decisions_not_comparable=dec_missing,
                   decisions_p4_dfs=sorted({d for _, d in so if d}),
                   decisions_p4_codex=sorted({d for _, d in st if d}))
        ok = equal and not dec_diff and dup_o == 0 and dup_t == 0
        all_ok &= ok
        verdict = "EQUAL" if equal else "DIFFERENT"
        print(f"k={k:2d}: {verdict:9s} p4_dfs={len(lo):6d}  p4_codex={len(lt):6d}  "
              f"decisions dfs={row['decisions_p4_dfs']} codex={row['decisions_p4_codex']}  "
              f"decision disagreements={len(dec_diff)}  not comparable={dec_missing}")
        for name, n in (("p4_dfs", dup_o), ("p4_codex", dup_t)):
            if n:
                print(f"        {n} duplicate survivor(s) inside {name}")
        for s in only_o:
            print(f"        only in p4_dfs:   {list(s)}")
        for s in only_t:
            print(f"        only in p4_codex: {list(s)}")
        for s, a, b in dec_diff:
            print(f"        decision differs on {s}: p4_dfs={a}, p4_codex={b}")
        report.append(row)

    if args.json:
        with open(args.json, "w") as f:
            json.dump(report, f, indent=1)
    print("ALL EQUAL" if all_ok else "NOT ALL EQUAL (see above)")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
