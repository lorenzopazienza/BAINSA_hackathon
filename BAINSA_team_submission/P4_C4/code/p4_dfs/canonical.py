#!/usr/bin/env python3
"""Write results/kXX_sun.canonical.json: exactly the text whose SHA-256 is reported.

The text is a JSON list of survivors. Each survivor is a list of moduli in ascending order,
and the list is sorted lexicographically. It is serialised with separators (',', ':') and
no whitespace or trailing newline. The script also re-verifies the stored hash and prints
one summary line per k.
"""
import glob
import hashlib
import json
import sys

files = sys.argv[1:] or sorted(glob.glob("results/k*_sun.json"))
for f in files:
    d = json.load(open(f))
    surv = sorted(tuple(r["moduli"]) for r in d["survivors"])
    assert all(list(s) == sorted(s) for s in surv)
    text = json.dumps([list(s) for s in surv], separators=(",", ":"))
    h = hashlib.sha256(text.encode()).hexdigest()
    assert h == d["survivors_sha256"], f
    with open(f.replace(".json", ".canonical.json"), "w") as g:
        g.write(text)
    dec = {r["decision"] for r in d["survivors"]}
    print(f"k={d['k']:2d}  survivors={len(surv):6d}  decisions={sorted(dec) or '-'}  "
          f"t={d['wall_clock_s']['total']}s  sha256={h}")
