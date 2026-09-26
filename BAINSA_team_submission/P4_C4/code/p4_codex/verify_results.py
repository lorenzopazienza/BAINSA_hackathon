#!/usr/bin/env python3
"""Verify exact counts, lists, certificate hashes, and branch merge metadata."""
import hashlib
import json
from pathlib import Path

expected=json.loads(Path('expected_results.json').read_text())
for name,want in expected.items():
    got=json.loads(Path(name).read_text())
    for field,value in want.items():
        if field=='minimal_parts':
            for subfield,subvalue in value.items():
                if got['minimal_parts'].get(subfield)!=subvalue:
                    raise AssertionError(f'{name}: minimal_parts.{subfield} mismatch')
            meta=got['minimal_parts']
            for kind in ('records','witness'):
                path=Path(meta[f'{kind}_file'])
                if hashlib.sha256(path.read_bytes()).hexdigest()!=meta[f'{kind}_sha256']:
                    raise AssertionError(f'{name}: {kind} file hash mismatch')
        elif got.get(field)!=value:
            raise AssertionError(f'{name}: {field} mismatch')
    if name.startswith('results_'):
        canonical=json.dumps(got['survivors'],sort_keys=True,separators=(',',':')).encode()
        if hashlib.sha256(canonical).hexdigest()!=got['survivor_sha256']:
            raise AssertionError(f'{name}: survivor list hash mismatch')
        if 'parallel' in got:
            k=got['k']
            branch_counts={key:0 for key in got['counts']}
            branch_counts['nodes_visited']=1  # global root omitted by branches
            merged=[]
            for branch in got['parallel']['branches']:
                path=Path('work')/f'parallel_k{k}'/f"branch_{branch['first_index']:03d}.json"
                data=json.loads(path.read_text())
                branch_canonical=json.dumps(data['survivors'],sort_keys=True,separators=(',',':')).encode()
                if hashlib.sha256(branch_canonical).hexdigest()!=data['survivor_sha256']:
                    raise AssertionError(f'{name}: branch list hash mismatch')
                if (data['status']!=branch['status'] or
                    data['counts']['nodes_visited']!=branch['nodes_visited'] or
                    data['survivor_sha256']!=branch['survivor_sha256']):
                    raise AssertionError(f'{name}: branch {branch["first_index"]} mismatch')
                for key in branch_counts:
                    branch_counts[key]+=data['counts'][key]
                merged.extend(data['survivors'])
            if branch_counts!=got['counts']:
                raise AssertionError(f'{name}: branch count sum mismatch')
            projected=[{key:value for key,value in item.items() if key!='minimal_part'}
                       for item in got['survivors']]
            if merged!=projected:
                raise AssertionError(f'{name}: branch survivor merge mismatch')
    print(f'{name}: MATCH')
