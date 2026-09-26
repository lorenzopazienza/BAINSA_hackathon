"""Shows that the joint bound M5+M7 <= 19 leaves 8 k=44 placements open (code
relaxation reaches 41 = k-3), while <= 18 closes them."""
import sat_residual as sr
P_list = [
 ([2, 11, 13], [3, 19, 17], [5, 7, 41, 37, 31, 29, 23]),
 ([2, 11, 13, 41], [3, 19, 17, 37], [5, 7, 31, 29, 23]),
 ([2, 11, 41, 37], [3, 13, 19, 17], [5, 7, 31, 29, 23]),
 ([2, 11, 41, 37], [3, 19, 17, 31], [5, 7, 13, 29, 23]),
 ([2, 11, 41, 37], [3, 19, 17, 31, 29], [5, 7, 13, 23]),
 ([2, 13, 41, 37], [3, 11, 19, 17], [5, 7, 31, 29, 23]),
 ([2, 13, 41, 37], [3, 19, 17, 31], [5, 7, 11, 29, 23]),
 ([2, 13, 41, 37], [3, 19, 17, 31, 29], [5, 7, 11, 23])]
orig = sr.eps_of
for J in (19, 18, 17, 16, 15):
    sr.eps_of = lambda P3, p, J=J: (J-2, {5: 12, 7: 15}, J) if (5 in P3 and 7 in P3) else orig(P3, p)
    # find max achievable total for each
    res = []
    for P in P_list:
        t = 41
        while sr.code_sat(*P, 43, t): t += 1
        res.append(t - 1)
    print("joint", J, "max code totals", res)
