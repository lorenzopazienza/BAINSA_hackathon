#!/usr/bin/env python3
"""Light, read-only data study for P3 Cell 3 (one CPU, no SAT).

Reads the complete extremal lists supplied by the team.  Enumerates partitions
of T_k-1 for k=4..10 and tests several purely static shape hypotheses.  A short
trajectory is used only to cross-check the proved first-ramp equivalence, never
to classify a partition as extremal.  This script does not edit final/.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "review/seby/bs_extremal.txt"


def read_extremals(path: Path) -> dict[int, set[tuple[int, ...]]]:
    groups: dict[int, set[tuple[int, ...]]] = {}
    n = None
    for line in path.read_text().splitlines():
        if line.startswith("n="):
            n = int(line.split()[0][2:])
            groups[n] = set()
        elif line.startswith("  ") and n is not None:
            groups[n].add(tuple(map(int, line.split())))
    return groups


def partitions(n: int, cap: int | None = None):
    if n == 0:
        yield ()
        return
    for first in range(min(n, n if cap is None else cap), 0, -1):
        for tail in partitions(n - first, first):
            yield (first,) + tail


def conjugate(shape: tuple[int, ...]) -> tuple[int, ...]:
    if not shape:
        return ()
    return tuple(sum(row >= i for row in shape) for i in range(1, shape[0] + 1))


def contains(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    return all((a[i] if i < len(a) else 0) >= row for i, row in enumerate(b))


def diagonal_multiset(shape: tuple[int, ...]) -> tuple[int, ...]:
    """Unindexed multiset of NW-SE diagonal lengths (column minus row fixed)."""
    counts: Counter[int] = Counter()
    for row, width in enumerate(shape):
        for column in range(width):
            counts[column - row] += 1
    return tuple(sorted(counts.values()))


def bulgarian_move(shape: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted([len(shape)] + [v - 1 for v in shape if v > 1], reverse=True))


def has_first_ramp(shape: tuple[int, ...], k: int) -> bool:
    counts = []
    for _ in range(k + 2):
        counts.append(len(shape))
        shape = bulgarian_move(shape)
    return counts[k - 1:k + 2] == [k - 1, k, k + 1]


def shapes(k: int):
    n = k * (k + 1) // 2 - 1
    delta_small = tuple(range(k - 1, 0, -1))
    delta_large = tuple(range(k, 0, -1))
    lo = tuple((k + 3 - j) // 2 for j in range(1, k + 2))
    hi = conjugate(tuple(range(2 * k - 3, 0, -2)))
    return n, delta_small, delta_large, lo, hi


def main() -> None:
    data = read_extremals(SOURCE)
    print("k n ext delta_(k-1)_contains delta_k_contains first_bounds "
          "short_bounds lo_plus_top lo..hi corridor_extra conjugate_closed")
    for k in range(4, 11):
        n, small, large, lo, hi = shapes(k)
        ext = data[n]
        all_parts = list(partitions(n))
        assert all(sum(p) == n for p in ext)
        corridor = {p for p in all_parts if contains(p, lo) and contains(hi, p)}
        assert ext <= corridor, (k, "extremal outside corridor", ext - corridor)
        static_first = {p for p in all_parts if contains(p, lo) and p[0] <= k - 1}
        dynamic_first = {p for p in all_parts if has_first_ramp(p, k)}
        assert static_first == dynamic_first, (k, "first-ramp equivalence failed")
        extra = corridor - ext
        report = [
            k, n, len(ext),
            sum(contains(p, small) for p in ext),
            sum(contains(large, p) for p in ext),
            sum(p[0] <= k + 1 and len(p) >= k + 1 for p in all_parts),
            sum(p[0] <= k - 1 and k + 1 <= len(p) <= 2 * k - 3
                for p in all_parts),
            sum(contains(p, lo) and p[0] <= k - 1 for p in all_parts),
            len(corridor), len(extra),
            sum(conjugate(p) in ext for p in ext),
        ]
        print(*report)
        if extra and k in (6, 8):
            print("  corridor false positives:", sorted(extra, reverse=True))
        # Can an unindexed diagonal multiset alone distinguish extremality?
        by_sig: dict[tuple[int, ...], list[tuple[bool, tuple[int, ...]]]] = {}
        for p in corridor:
            sig = diagonal_multiset(p)
            by_sig.setdefault(sig, []).append((p in ext, p))
        mixed = next((v for v in by_sig.values()
                      if any(flag for flag, _ in v) and any(not flag for flag, _ in v)), None)
        if mixed:
            yes = next(p for flag, p in mixed if flag)
            no = next(p for flag, p in mixed if not flag)
            print("  corridor diagonal-multiset collision:", yes, "EXT /", no, "NONEXT")
        else:
            print("  no diagonal-multiset collision at this k")
    counts = [len(data[k * (k + 1) // 2 - 1]) for k in range(4, 11)]
    print("counts", counts)
    print("first-ramp static/dynamic sets agree for k=4..10")
    print("successive ratios", [round(b / a, 6) for a, b in zip(counts, counts[1:])])


if __name__ == "__main__":
    main()
