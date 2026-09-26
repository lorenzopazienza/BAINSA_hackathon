#!/usr/bin/env python3
"""Print concise measured results and survivor hashes from saved JSON."""
import json
from pathlib import Path

for k in range(3, 17):
    path = Path(f'results_k{k}.json')
    if not path.exists():
        print(f'{k}: NOT RUN')
        continue
    r = json.loads(path.read_text())
    c = r['counts']
    print(f"{k}: {r['status']}; gcd={c['multisets_after_gcd']}; "
          f"density={c['multisets_after_density']}; normal={c['multisets_after_normal_form']}; "
          f"SAT calls={c['sat_calls']}; SAT={c['SAT']}; UNSAT={c['UNSAT']}; "
          f"wall={r['wall_seconds']}s; survivor SHA-256={r['survivor_sha256']}")
