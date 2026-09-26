"""Code-based labellings of Q_d, d = 3..9 (Problem 2, all cells).

Usage:  python uphill_construct.py [OUTDIR]      (default OUTDIR: ../uphill/labellings)

For an even-weight code C of length d with minimum distance >= 4, the labelling
    (codewords of C) < (odd-weight vertices) < (even-weight vertices not in C),
each block in increasing binary order, has exactly
    2^d + (d-1) * (2^(d-1) - |C|)
uphill paths (Proposition "code labelling" in the cells).  The script
checks the code, builds the labelling, counts its uphill paths with the
exact evaluator uphill_eval.py, compares with the formula, and writes the
labelling (one 0/1 string per line, increasing label order) to OUTDIR/Q<d>.txt.
"""
import os
import sys
from itertools import combinations

from uphill_eval import count_uphill


def span(gens):
    words = {0}
    for g in gens:
        words |= {w ^ g for w in words}
    return sorted(words)


def b(s):
    return int(s, 2)


CODES = {
    3: [b("000")],
    4: [b("0000"), b("1111")],
    5: [b("00000"), b("11110")],
    6: span([b("111100"), b("110011")]),
    7: span([b("1111000"), b("1100110"), b("1010101")]),                  # [7,3,4]
    8: span([b("11110000"), b("11001100"), b("10101010"), b("11111111")]),  # ext. Hamming [8,4,4]
    # 20 even words of length 9, pairwise distance >= 4 (A(8,3) = 20; found by a
    # SAT search, the property is re-checked below).
    9: [b(s) for s in """
        000000000 000101011 000110101 001000111 001011100 001110010 010001101
        010111110 011011011 011101000 100011010 100101100 101001001 101111111
        110010111 110100010 110111001 111001110 111010000 111100101""".split()],
}

# Sizes A(d-1,3) of the codes; 2^(d-1) - A(d-1,3) is the decycling number for d <= 8.
EXPECTED_SIZE = {3: 1, 4: 2, 5: 2, 6: 4, 7: 8, 8: 16, 9: 20}
EXPECTED_U = {3: 14, 4: 34, 5: 88, 6: 204, 7: 464, 8: 1040, 9: 2400}


def weight(v):
    return bin(v).count("1")


def check_code(d, C):
    assert len(C) == EXPECTED_SIZE[d] == len(set(C))
    assert all(0 <= c < 1 << d and weight(c) % 2 == 0 for c in C)
    assert all(weight(a ^ c) >= 4 for a, c in combinations(C, 2))


def labelling(d, C):
    Cs = set(C)
    odd = [v for v in range(1 << d) if weight(v) % 2]
    rest = [v for v in range(1 << d) if weight(v) % 2 == 0 and v not in Cs]
    return sorted(C) + odd + rest


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    for d, C in CODES.items():
        check_code(d, C)
        order = labelling(d, C)
        assert sorted(order) == list(range(1 << d))
        P = count_uphill(d, order)
        formula = 2 ** d + (d - 1) * (2 ** (d - 1) - len(C))
        assert P == formula == EXPECTED_U[d], (d, P, formula)
        path = os.path.join(outdir, f"Q{d}.txt")
        with open(path, "w") as fh:
            fh.write("\n".join(format(v, f"0{d}b") for v in order) + "\n")
        print(f"d = {d}: |C| = {len(C):2d}, uphill paths = {P}  -> {path}")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "uphill", "labellings"))
