"""Self-review for k = 44: (i) the SAT encoding is not vacuous: on residual placements it
finds multisets of size 40 = k-4 (so UNSAT at 41 is a real bound); (ii) on random Case II
placements the SAT optimum never exceeds the hand bound min(B1,B2)."""
import random
import sat_residual as sr
p, k = 43, 44
Q = sr.primes_below(p); others = [q for q in Q if q >= 5]
random.seed(3)
# (i)
P = ([2, 11, 13], [3, 19, 17], [5, 7, 41, 37, 31, 29, 23])
assert sr.hand(*P, p) >= 41
print("residual example: SAT at 40?", sr.code_sat(*P, p, 40), " SAT at 41?", sr.code_sat(*P, p, 41))
# (ii)
n = 0; worst = None
while n < 300:
    d = [random.randrange(4) for _ in others]
    B = {1: [2], 2: [3], 3: []}
    for q, j in zip(others, d):
        if j: B[j].append(q)
    if not B[3]: continue
    n += 1
    h = sr.hand(B[1], B[2], B[3], p)
    assert not sr.code_sat(B[1], B[2], B[3], p, h + 1), B   # optimum <= hand bound
    t = 1
    lo = 0
    # optimum by linear search downward from h
    opt = h
    while opt > 0 and not sr.code_sat(B[1], B[2], B[3], p, opt): opt -= 1
    if worst is None or h - opt < worst[0]: worst = (h - opt, B, opt, h)
print(f"{n} random placements: SAT optimum <= min(B1,B2) everywhere; tightest {worst}")
