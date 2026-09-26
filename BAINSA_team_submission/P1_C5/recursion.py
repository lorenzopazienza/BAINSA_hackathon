# Path basis b_1..b_n (tridiagonal Gram). State after n vectors:
#  X = pi/2 - angle(b_1, span(b_2..b_n)),  Y = pi/2 - angle(b_n, span(b_1..b_{n-1})),
#  eta = pi/2 - angle(u,w), u,w normals of span(b_2..b_n), span(b_1..b_{n-1}); s = sum of edge arcsins.
# Recursion when appending b_{n+1} with edge a = arcsin|<b_n,b_{n+1}>|  (needs a <= pi/2 - Y):
#  sin Y' = sin a / cos Y ; tan eta' = tan Y' sin eta ; cos X' = cos X cos eta' ; s' = s + a
# Cycle lemma for m = n+2  <=>  Phi_n := s - X - Y + eta >= 0.
import numpy as np
from cycle import vectors, A_formula

def step(state, a):
    X, Y, eta, s = state
    Yn = np.arcsin(np.sin(a) / np.cos(Y))
    etan = np.arctan(np.tan(Yn) * np.sin(eta))
    Xn = np.arccos(np.cos(X) * np.cos(etan))
    return (Xn, Yn, etan, s + a)

def run_path(avals):
    st = (0.0, 0.0, np.pi/2, 0.0); out = [st]
    for a in avals:
        st = step(st, a); out.append(st)
    return out

if __name__ == '__main__':
    rng = np.random.default_rng(6)
    # (1) consistency with the explicit cycle parametrisation: edge a_k = arcsin(sin t_k cos t_{k-1}), Y_{k+1} = t_k
    maxerr = 0
    for _ in range(2000):
        n = rng.integers(2, 10); t = rng.uniform(0, np.pi/2, n - 1)
        a = [np.arcsin(np.sin(t[0]))] + [np.arcsin(np.sin(t[k]) * np.cos(t[k-1])) for k in range(1, n-1)]
        X, Y, eta, s = run_path(a)[-1]
        A_rec = s + (np.pi/2 - X) + (np.pi/2 - Y) + (np.pi/2 - (np.pi/2 - eta))  # edges b_n-w, u-b_1, u-w
        # A = s + psi_n + psi_1 + arcsin|<u,w>|, psi = pi/2 - closeness, arcsin|<u,w>| = pi/2 - delta = eta
        maxerr = max(maxerr, abs(A_rec - A_formula(t)))
    print("recursion vs explicit formula, max err:", maxerr)
    # (2) monotonicity of Phi along random paths
    worst_inc = np.inf; worst_phi = np.inf
    for _ in range(100000):
        n = rng.integers(2, 12); st = (0.0, 0.0, np.pi/2, 0.0); prev = None
        for k in range(n):
            Y = st[1]; a = rng.uniform(0, np.pi/2 - Y) if rng.random() < .7 else (np.pi/2 - Y) * rng.beta(.3, .3)
            st = step(st, a); phi = st[3] - st[0] - st[1] + st[2]
            if k >= 1:
                worst_phi = min(worst_phi, phi)
                if prev is not None: worst_inc = min(worst_inc, phi - prev)
                prev = phi
    print("min Phi_n (n>=2):", worst_phi, "  min Phi_{n+1}-Phi_n (n>=2):", worst_inc)
