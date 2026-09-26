"""Writes k16status.tex: the state of the p4_dfs decision run for k = 16 AT COMPILE TIME.
Counts the finished round-robin blocks p4_crosscheck/dfs_decisions/k16_chunkXXof24.json,
checks that each block was run on the survivor list with the same SHA-256 as p4_codex and
p4_dfs (compare_report.json), and that every decision in it is UNSAT (p4_codex decided all
236,333 survivors UNSAT, so UNSAT = agreement).
Usage: python3 k16_status.py <path to p4_crosscheck> <output .tex>"""
import glob, json, os, sys, time
cc, out = sys.argv[1], sys.argv[2]
rep = {e["k"]: e for e in json.load(open(os.path.join(cc, "compare_report.json")))}
sha = rep[16]["codex"]["canonical_sha256"]
assert rep[16]["dfs"]["canonical_sha256"] == sha and rep[16]["lists_identical"]
assert rep[16]["codex"]["decisions"] == {"UNSAT": 236333}
files = sorted(glob.glob(os.path.join(cc, "dfs_decisions", "k16_chunk*of24.json")))
n = agree = 0
seen = set()
for f in files:
    p = json.load(open(f))
    assert p["n_chunks"] == 24 and p["source_survivors_sha256"] == sha
    assert p["chunk"] not in seen; seen.add(p["chunk"])
    for r in p["records"]:
        n += 1
        agree += r["decision"] == "UNSAT"
assert agree == n, "DISAGREEMENT with p4_codex"
stamp = time.strftime("%Y-%m-%d %H:%M")
open(out, "w").write(
    f"\\newcommand{{\\kXVIblocks}}{{{len(files)}}}\n"
    f"\\newcommand{{\\kXVIdecided}}{{{n:,}}}\n".replace(",", "\\,") +
    f"\\newcommand{{\\kXVIstamp}}{{{stamp}}}\n")
print(f"k=16: {len(files)}/24 blocks, {n} survivors decided by p4_dfs, all UNSAT (agree); {stamp}")
