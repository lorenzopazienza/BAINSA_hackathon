# Numerical verification of every inequality used in p1_c5.tex.
import numpy as np
rng = np.random.default_rng(11); N = 1_000_000
U = lambda lo, hi, n=N: lo + (hi - lo) * rng.beta(.4, .4, n)
tol = 1e-9; report = []
def chk(name, v): report.append((name, v.min())); print(f"{name:70s} min = {v.min(): .3e}  {'OK' if v.min() > -tol else 'FAIL'}")

# L1 convexity of arccos(r cos s) on cos s>0 (second derivative formula)
r = U(0, 1); s = U(-np.pi/2, np.pi/2)
chk("L1: r cos s (1-r^2)/(1-r^2cos^2 s)^1.5 >= 0", r*np.cos(s)*(1-r**2)/(1-r**2*np.cos(s)**2)**1.5)
# L2 recursion facts: eta' <= Y', X' >= eta', X'-X decreasing in X
Y = U(0, np.pi/2); Yp = U(0, np.pi/2); eta = U(0, np.pi/2); X = U(0, np.pi/2)
etap = np.arctan(np.tan(Yp)*np.sin(eta))
chk("L2a: Y' - eta' >= 0", Yp - etap)
Xp = np.arccos(np.cos(X)*np.cos(etap)); chk("L2b: X' - eta' >= 0", Xp - etap)
chk("L2c: d/dX (X'-X) = sinX cos eta'/sinX' - 1 <= 0", 1 - np.sin(X)*np.cos(etap)/np.maximum(np.sin(Xp), 1e-300))
# L3 sigma(Y,Y') = arcsin(sinY' cosY) + Y - Y' is nondecreasing in Y and >= 0
a = np.arcsin(np.sin(Yp)*np.cos(Y))
chk("L3a: dsigma/dY = 1 - sinY' sinY / cos a >= 0", 1 - np.sin(Yp)*np.sin(Y)/np.cos(a))
chk("L3b: sigma >= 0", a + Y - Yp)
# L4 algebraic core: sqrt(1-s)(t B + s A) <= sqrt(1+s)(t^2+s) for t >= sqrt(s)
s = U(0, 1); t = np.sqrt(s) * np.exp(U(0, 8)); A_ = np.sqrt(1+t**2); B_ = np.sqrt(t**2+s**2)
chk("L4: sqrt(1+s)(t^2+s) - sqrt(1-s)(tB+sA) >= 0, t>=sqrt s", np.sqrt(1+s)*(t**2+s) - np.sqrt(1-s)*(t*B_+s*A_))
# L5 q(t) >= q(s/t) for t >= sqrt(s), q(t) = t/(1+t^2) (cY t/sqrt(t^2+s^2) - 1)
cY = np.sqrt(1-s**2); q = lambda t: t/(1+t**2)*(cY*t/np.sqrt(t**2+s**2) - 1)
chk("L5: q(t) - q(s/t) >= 0 for t >= sqrt s", q(t) - q(s/t))
# L6 K(Y,Y') >= 0  i.e. f(x1)+f(x2) <= Y with tan x1 tan x2 = sin Y
es = np.arctan(np.tan(Yp)*np.sin(Y))
K = a + Y - Yp - np.arccos(np.cos(Y)*np.cos(es)) + es
chk("L6: K(Y,Y') >= 0", K)
# L7 step inequality with the invariants X >= eta, eta <= Y
eta2 = Y*rng.beta(.4, .4, N); X2 = eta2 + (np.pi/2 - eta2)*rng.beta(.4, .4, N)
Yn = Yp; a2 = np.arcsin(np.sin(Yn)*np.cos(Y))
etan = np.arctan(np.tan(Yn)*np.sin(eta2)); Xn = np.arccos(np.cos(X2)*np.cos(etan))
chk("L7: Phi' - Phi = a - (X'-X) - (Y'-Y) + (eta'-eta) >= 0", a2 - (Xn - X2) - (Yn - Y) + (etan - eta2))
# L8 end-to-end: A - pi = Phi_n on explicit cycles, and >= 0
from cycle import vectors, A_direct
from recursion import run_path
worst = np.inf; err = 0
for _ in range(20000):
    n = rng.integers(2, 12); X_ = vectors(np.pi/2*rng.beta(.4, .4, n-1)); m = n + 2
    edges = [np.arcsin(min(1, abs(X_[k] @ X_[k+1]))) for k in range(n-1)]
    Xs, Ys, es_, ss = run_path(edges)[-1]
    phi = ss - Xs - Ys + es_; A = A_direct(X_)
    err = max(err, abs(A - np.pi - phi)); worst = min(worst, A - np.pi)
print(f"{'L8: cycles m=4..13: |A-pi-Phi| max':70s} {err:.1e};  min(A-pi) = {worst:.3e}")
