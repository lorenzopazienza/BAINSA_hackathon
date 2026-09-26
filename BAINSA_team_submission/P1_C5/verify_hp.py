# High-precision re-check of the cases that float64 flagged, plus L8 diagnosis.
import numpy as np, mpmath as mp
mp.mp.dps = 50
rng = np.random.default_rng(12)
def worst(fn, sampler, n=20000):
    w = mp.inf
    for _ in range(n):
        v = fn(*sampler()); w = min(w, v)
    return w
b = lambda lo, hi: mp.mpf(lo + (hi-lo)*rng.beta(.4, .4))
pi2 = mp.pi/2
def L2b(X, Yp, eta):
    ep = mp.atan(mp.tan(Yp)*mp.sin(eta)); return mp.acos(mp.cos(X)*mp.cos(ep)) - ep
def L2c(X, Yp, eta):
    ep = mp.atan(mp.tan(Yp)*mp.sin(eta)); Xp = mp.acos(mp.cos(X)*mp.cos(ep))
    return 1 - mp.sin(X)*mp.cos(ep)/mp.sin(Xp)
def L6(Y, Yp):
    a = mp.asin(mp.sin(Yp)*mp.cos(Y)); es = mp.atan(mp.tan(Yp)*mp.sin(Y))
    return a + Y - Yp - mp.acos(mp.cos(Y)*mp.cos(es)) + es
S3 = lambda: (b(1e-12, 1.5707963), b(1e-12, 1.5707963), b(1e-12, 1.5707963))
print("L2b hp min:", mp.nstr(worst(L2b, S3), 5))
print("L2c hp min:", mp.nstr(worst(L2c, S3), 5))
print("L6  hp min:", mp.nstr(worst(L6, lambda: S3()[:2]), 5))
# L8 diagnosis: explicit cycle vs recursion in high precision
def cycle_A(t):
    t = [mp.mpf(x) for x in t]; n = len(t) + 1
    X = mp.zeros(n + 2, n); X[0, 0] = 1
    for k in range(n - 1): X[k+1, k] = mp.sin(t[k]); X[k+1, k+1] = mp.cos(t[k])
    X[n, n-1] = 1
    P = [(-1)**k * mp.fprod([mp.sin(x) for x in t[:k]]) * mp.fprod([mp.cos(x) for x in t[k:]]) for k in range(n)]
    nr = mp.sqrt(mp.fsum([p**2 for p in P]))
    for k in range(n): X[n+1, k] = P[k]/nr
    m = n + 2; A = 0; edges = []
    for i in range(m):
        for j in range(i+1, m):
            g = abs(mp.fsum([X[i, k]*X[j, k] for k in range(n)])); A += mp.asin(min(g, 1))
    for k in range(n - 1): edges.append(mp.asin(abs(mp.fsum([X[k, c]*X[k+1, c] for c in range(n)]))))
    Xs, Ys, e, s = mp.mpf(0), mp.mpf(0), pi2, mp.mpf(0)
    for a in edges:
        Yn = mp.asin(mp.sin(a)/mp.cos(Ys)); en = mp.atan(mp.tan(Yn)*mp.sin(e)); Xs = mp.acos(mp.cos(Xs)*mp.cos(en))
        Ys, e, s = Yn, en, s + a
    return A, s - Xs - Ys + e
err = 0; wA = mp.inf
for _ in range(1500):
    n = int(rng.integers(2, 10)); t = np.pi/2*rng.beta(.4, .4, n-1)
    A, phi = cycle_A(t); err = max(err, abs(A - mp.pi - phi)); wA = min(wA, A - mp.pi)
print("L8 hp: max |A - pi - Phi| =", mp.nstr(err, 5), "  min A - pi =", mp.nstr(wA, 5))
