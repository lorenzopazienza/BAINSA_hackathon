import numpy as np
from scipy.optimize import minimize
from cycle import A_formula
rng = np.random.default_rng(2)
for m in range(5, 12):
    n = m - 3
    # (a) local minimisation from random starts, box (0,pi/2)
    best = np.inf
    for _ in range(60):
        r = minimize(lambda u: A_formula(np.pi/4*(1+np.tanh(u))), rng.standard_normal(n)*2, method='Nelder-Mead',
                     options={'maxiter': 4000, 'fatol': 1e-13, 'xatol': 1e-10})
        best = min(best, r.fun)
    # (b) coordinate-wise concavity: max second difference along each coordinate
    h = 1e-4; worst = np.full(n, -np.inf)
    for _ in range(4000):
        t = rng.uniform(1e-3 + h, np.pi/2 - 1e-3 - h, n)
        for k in range(n):
            e = np.zeros(n); e[k] = h
            d2 = (A_formula(t+e) - 2*A_formula(t) + A_formula(t-e)) / h**2
            worst[k] = max(worst[k], d2)
    print(f"m={m}: min A-pi by optimisation {best-np.pi:.2e}; max d2A/dt_k^2 per k:", np.round(worst, 4))
