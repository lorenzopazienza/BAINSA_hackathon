"""Where does the excess of a labelling come from?

Summing N(v) over non-valleys counts every edge (u -> higher v) with weight N(u), so
    U = #valleys + sum_u N(u) * updeg(u)
    excess := U - |E| - 1 = (#valleys - 1) + sum_u (N(u) - 1) * updeg(u)
where N(u) = number of uphill paths ending at u, updeg(u) = number of higher neighbours.

Usage: python analyze.py 7 8 9          # analyse best/Q{d}.json
"""
import itertools
import sys
from collections import Counter

from evaluator import count_uphill
from store import load_best


def decompose(order, d):
    label = {v: k for k, v in enumerate(order)}
    N, up = {}, {}
    for v in order:
        lower = [v ^ (1 << j) for j in range(d) if label[v ^ (1 << j)] < label[v]]
        N[v] = sum(N[u] for u in lower) if lower else 1
        up[v] = d - len(lower)
    valleys = [v for v in order if up[v] == d]
    contrib = {u: (N[u] - 1) * up[u] for u in order}
    U = sum(N.values())
    excess = U - d * 2 ** (d - 1) - 1
    assert U == count_uphill(order, d)
    assert excess == len(valleys) - 1 + sum(contrib.values()), "decomposition identity failed"
    return {"U": U, "excess": excess, "label": label, "N": N, "up": up,
            "valleys": valleys, "contrib": contrib}


def weight(v):
    return bin(v).count("1")


def translation_stabilizer(S, d):
    """Masks c with S ^ c == S (S is invariant under the translation x -> x ^ c)."""
    return [c for c in range(1, 1 << d) if {s ^ c for s in S} == S]


def permutation_stabilizer_size(S, d):
    """Number of coordinate permutations mapping S to itself (skipped for d > 8)."""
    if d > 8:
        return None
    count = 0
    for perm in itertools.permutations(range(d)):
        if {sum(((s >> j) & 1) << perm[j] for j in range(d)) for s in S} == S:
            count += 1
    return count


def gf2_rank(vectors):
    rows, rank = list(vectors), 0
    for bit in reversed(range(max(rows, default=0).bit_length())):
        pivot = next((r for r in rows if (r >> bit) & 1), None)
        if pivot is None:
            continue
        rows = [r ^ pivot if (r >> bit) & 1 else r for r in rows if r != pivot]
        rank += 1
    return rank


def set_structure(S, d):
    """Invariants of a vertex set: weights, pairwise distances, affine dimension, symmetry."""
    S = set(S)
    s0 = min(S)
    return {
        "size": len(S),
        "weights": dict(sorted(Counter(weight(s) for s in S).items())),
        "distances": dict(sorted(Counter(weight(a ^ b) for a, b in itertools.combinations(S, 2)).items())),
        "affine_dim": gf2_rank(s ^ s0 for s in S),
        "translation_symmetries": len(translation_stabilizer(S, d)),
        "coord_perm_symmetries": permutation_stabilizer_size(S, d),
    }


def summary(order, d, top=12):
    r = decompose(order, d)
    N, up, label, contrib = r["N"], r["up"], r["label"], r["contrib"]
    n = 1 << d
    costly = [u for u in order if contrib[u] > 0]
    peaks = [v for v in order if up[v] == 0]
    lines = [f"=== Q{d}: U = {r['U']}, |E|+1 = {d * 2 ** (d - 1) + 1}, excess = {r['excess']} "
             f"= (valleys-1) {len(r['valleys']) - 1} + sum (N-1)*updeg {sum(contrib.values())}"]
    lines.append(f"valleys: {len(r['valleys'])} at labels {[label[v] for v in r['valleys']]}")
    lines.append(f"N distribution: {dict(sorted(Counter(N.values()).items()))}")
    lines.append(f"lower-degree distribution (#lower nbrs): "
                 f"{dict(sorted(Counter(d - up[v] for v in order).items()))}")
    lines.append(f"peaks (updeg 0): {len(peaks)}, labels {min(label[p] for p in peaks)}..{n - 1}; "
                 f"non-peaks after first peak: {sum(1 for v in order[label[peaks[0]]:] if up[v])}")
    lines.append(f"costly vertices (N>=2 and updeg>=1): {len(costly)}")
    lines.append("  top: vertex(bits) label N updeg weight contrib")
    for u in sorted(costly, key=lambda u: -contrib[u])[:top]:
        lines.append(f"  {format(u, f'0{d}b')} {label[u]:4d} {N[u]:3d} {up[u]:2d} {weight(u):2d} {contrib[u]:4d}")
    by_n = Counter()
    for u in costly:
        by_n[(N[u], up[u])] += contrib[u]
    lines.append(f"  excess by (N, updeg): {dict(sorted(by_n.items()))}")
    if costly:
        lines.append(f"  costly set structure: {set_structure(costly, d)}")
    lines.append(f"  valley set structure: {set_structure(r['valleys'], d)}")
    # Forest form: V = F + I with I = peaks independent, every F-vertex having <= 1 lower
    # neighbour, so G[F] is a forest whose trees are rooted at the valleys. Then
    # U = |E| + c (c = #valleys) and (d-1)|I| = 2^(d-1)(d-2) + c.
    c = len(r["valleys"])
    if all(d - up[v] in (0, 1) or up[v] == 0 for v in order):
        assert (d - 1) * len(peaks) == 2 ** (d - 1) * (d - 2) + c
        lines.append(f"FOREST FORM: I = peaks ({len(peaks)}) independent, G - I = forest with "
                     f"c = {c} trees; U = |E| + c; (d-1)|I| = 2^(d-1)(d-2) + c")
    lines.append(f"  peak set structure: {set_structure(peaks, d)}")
    return "\n".join(lines)


if __name__ == "__main__":
    for d in [int(x) for x in sys.argv[1:]] or [7, 8, 9]:
        best = load_best(d)
        print(summary(best["order"], d))
