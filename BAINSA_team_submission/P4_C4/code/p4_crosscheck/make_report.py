#!/usr/bin/env python3
"""Generate REPORT.md from the result files (no number is typed by hand).

Inputs: compare_report.json (compare_lists.py), dfs_view/k15_sun.json and k16_sun.json
(merge_dfs_decisions.py), dfs_k14_rerun/k14_sun.json (rerun_k14.sh), logs/, machine_info.txt,
p4_codex/results_k*.json, p4_dfs/results/k14_sun.json.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DFS_RESULTS = os.path.join(HERE, "..", "review", "Teo ", "hackaton", "p4_dfs", "results")


def fmt(n):
    return f"{n:,}"


def dec_str(d):
    if not d:
        return "—"
    return ", ".join(f"{v:,} {k}" for k, v in sorted(d.items(), key=lambda kv: kv[0] != "UNSAT"))


def main():
    rows = json.load(open(os.path.join(HERE, "compare_report.json")))
    merged = {k: json.load(open(os.path.join(HERE, "dfs_view", f"k{k:02d}_sun.json"))) for k in (15, 16)}
    rerun = json.load(open(os.path.join(HERE, "dfs_k14_rerun", "k14_sun.json")))
    orig14 = json.load(open(os.path.join(DFS_RESULTS, "k14_sun.json")))
    machine = open(os.path.join(HERE, "machine_info.txt")).read().strip()
    pool = open(os.path.join(HERE, "logs", "total_time.txt")).read()
    pool_real = re.search(r"real\s+([\d.]+)", pool)
    teo_log = open(os.path.join(HERE, "logs", "teo_compare_k3-16.log")).read().strip()

    L = []
    L.append("# Problem 4 cross-check: p4_codex (SAT) vs p4_dfs (DFS), k = 3..16\n")
    all_identical = all(r["lists_identical"] for r in rows)
    all_decided = all(r["dfs"]["decisions"].get("UNDECIDED", 0) == 0 and
                      r["codex"]["decisions"].get("UNDECIDED", 0) == 0 for r in rows)
    n_dis = sum(len(r["decision_disagreements"]) for r in rows)
    n_sat = sum(r["codex"]["decisions"].get("SAT", 0) + r["dfs"]["decisions"].get("SAT", 0) for r in rows)
    L.append("## Result\n")
    L.append(f"- Survivor lists identical for every k = 3..16: **{'yes' if all_identical else 'NO'}** "
             "(elementwise, after normalising each survivor to a sorted tuple and sorting the list).")
    L.append(f"- Every survivor decided by both implementations for k <= 16: **{'yes' if all_decided else 'NO'}**.")
    L.append(f"- Decision disagreements: **{n_dis}**. SAT decisions (counterexamples) on either side: **{n_sat}**.")
    L.append("- Neither implementation's code was modified. p4_dfs's decider was imported read-only "
             "(`PYTHONDONTWRITEBYTECODE=1`).\n")

    L.append("## Per-k table\n")
    L.append("| k | survivors codex | survivors dfs | lists identical? | codex decisions | dfs decisions "
             "| codex wall (s) | dfs wall (s) |")
    L.append("|---:|---:|---:|:---:|:---|:---|---:|---:|")
    for r in rows:
        k, c, d = r["k"], r["codex"], r["dfs"]
        if k in merged:
            w = merged[k]["wall_clock_s"]
            dfs_wall = (f"enum {w['enumeration']:.1f} + decide {w['decision_cpu_sum_over_chunks']:.1f} CPU-s "
                        f"(24 chunks, longest {w['decision_max_chunk']:.1f})")
        else:
            w = d["wall_clock_s"]
            dfs_wall = f"{w['total']:.3f} (enum {w['enumeration']:.3f} + decide {w['decision']:.3f})"
        codex_wall = f"{c['wall_seconds']:.3f}" + (" (parallel)" if k in (15, 16) else "")
        L.append(f"| {k} | {fmt(c['count'])} | {fmt(d['count'])} | {'yes' if r['lists_identical'] else '**NO**'} "
                 f"| {dec_str(c['decisions'])} | {dec_str(d['decisions'])} | {codex_wall} | {dfs_wall} |")
    L.append("")
    L.append("codex wall: `wall_seconds` from p4_codex/results_k*.json (enumeration + SAT decisions; k = 15 "
             "with 6 and k = 16 with 5 worker processes). dfs wall for k <= 14: from p4_dfs/results "
             "(single process). dfs wall for k = 15, 16: enumeration from p4_dfs's own "
             "enumeration-only run (single process); decisions from this cross-check (sum over the 24 "
             "chunks of per-chunk wall time, 6 processes at a time)"
             + (f"; the whole decision pool (k = 15 and 16 together, plus nothing else) took "
                f"{float(pool_real.group(1)):.0f} s elapsed." if pool_real else "."))
    L.append("")

    L.append("## SHA-256 of the canonical survivor text\n")
    L.append("Canonical text (definition of p4_dfs/canonical.py): JSON list of survivors, each an ascending "
             "list of moduli, the list sorted lexicographically, `separators=(',', ':')`, no whitespace. "
             "Computed here independently from each side's list. Stored hashes were also re-checked under "
             "each file's own definition (p4_dfs: the canonical text; p4_codex: "
             "`json.dumps(full survivor records, sort_keys=True, separators=(',', ':'))`, which includes "
             "decisions and minimal_part certificates, so it differs from the canonical text by design).\n")
    L.append("| k | canonical sha256 (codex list) | = dfs list? | codex stored hash reproduces | dfs stored hash reproduces |")
    L.append("|---:|:---|:---:|:---:|:---:|")
    for r in rows:
        c, d = r["codex"], r["dfs"]
        L.append(f"| {r['k']} | `{c['canonical_sha256']}` | {'yes' if c['canonical_sha256'] == d['canonical_sha256'] else '**NO**'} "
                 f"| {'yes' if c['stored_matches_own_definition'] else '**NO**'} "
                 f"| {'yes' if d['stored_matches_own_definition'] else '**NO**'} |")
    L.append("")

    L.append("## Differences\n")
    diffs = []
    for r in rows:
        for s in r["only_in_codex"]:
            diffs.append(f"- k={r['k']}: only in codex: {s}")
        for s in r["only_in_dfs"]:
            diffs.append(f"- k={r['k']}: only in dfs: {s}")
        for x in r["decision_disagreements"]:
            diffs.append(f"- k={r['k']}: decision differs on {x['moduli']}: codex={x['codex']} dfs={x['dfs']}")
        for side in ("codex", "dfs"):
            if r[side]["duplicates"]:
                diffs.append(f"- k={r['k']}: {r[side]['duplicates']} duplicate survivors in {side}")
            if r[side]["normalised_unsorted"]:
                diffs.append(f"- k={r['k']}: {r[side]['normalised_unsorted']} survivors in {side} were not "
                             "in ascending order (normalised)")
    L.extend(diffs or ["None: no survivor on one side only, no duplicates, no unsorted survivors, "
                       "no decision disagreements."])
    L.append("")

    L.append("## p4_dfs k = 14 rerun (reproducibility)\n")
    L.append("| quantity | original p4_dfs run | rerun | equal? |")
    L.append("|:---|---:|---:|:---:|")
    for key in ("enumeration_nodes", "complete_exponent_matrices(leaves)", "gcd_in_range_and_normal_form",
                "survivors(density<=1)", "SAT", "UNSAT", "UNDECIDED", "decision_nodes"):
        a, b = orig14["counts"][key], rerun["counts"][key]
        L.append(f"| {key} | {fmt(a)} | {fmt(b)} | {'yes' if a == b else '**NO**'} |")
    a, b = orig14["survivors_sha256"], rerun["survivors_sha256"]
    L.append(f"| survivors_sha256 | `{a[:16]}…` | `{b[:16]}…` | {'yes' if a == b else '**NO**'} |")
    dec_equal = [x["decision"] for x in orig14["survivors"]] == [x["decision"] for x in rerun["survivors"]]
    L.append(f"| per-survivor decisions | | | {'yes' if dec_equal else '**NO**'} |")
    L.append(f"| wall clock total (s) | {orig14['wall_clock_s']['total']} | {rerun['wall_clock_s']['total']} | (not expected to match) |")
    L.append("")

    L.append("## p4_dfs's own compare.py (unmodified), k = 3..16\n")
    L.append("Run against `codex_view/` (symlinks to p4_codex/results_k3..16.json only: the glob "
             "`results_k*.json` would otherwise also pick up `results_k*_vacuity.json` and stop with "
             "\"two files for k=3\") and `dfs_view/` (symlinks to p4_dfs's k3..14 results plus the merged "
             "k15/k16 files).\n")
    L.append("```\n" + teo_log + "\n```\n")

    L.append("## Reproduce\n")
    L.append("From `p4_crosscheck/`, with the repo's `.venv` (Python 3.12):\n")
    L.append("```bash\n"
             "export OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1\n"
             "./run_dfs_decisions.sh                 # p4_dfs decider on k=15,16 (24 chunks each, xargs -P 6)\n"
             "                                       # + one full p4_dfs rerun of k=14 (rerun_k14.sh)\n"
             "../.venv/bin/python merge_dfs_decisions.py 15 16   # checks and merges chunks -> dfs_view/\n"
             "../.venv/bin/python compare_lists.py --ks 3-16     # independent comparison -> compare_report.json\n"
             "../.venv/bin/python \"../review/Teo /hackaton/p4_dfs/compare.py\" --codex codex_view \\\n"
             "    --ours dfs_view --ks 3-16 --json teo_compare_k3-16.json   # p4_dfs's own comparator\n"
             "../.venv/bin/python make_report.py                 # this file\n"
             "```\n")
    L.append("One chunk by hand: `python dfs_decide_chunk.py K CHUNK N_CHUNKS` (survivor number i goes to "
             "chunk i mod N_CHUNKS; output dfs_decisions/kKK_chunkCCofNN.json with per-survivor decision, "
             "decision nodes and time).\n")

    L.append("## Machine\n")
    L.append("```\n" + machine + "\n```")
    L.append("During the decision runs three unrelated single-process SAT searches (Problem 2) were also "
             "running, so up to 9 of 12 cores were busy; wall clocks are indicative.")
    open(os.path.join(HERE, "REPORT.md"), "w").write("\n".join(L) + "\n")
    print("wrote REPORT.md")


if __name__ == "__main__":
    main()
