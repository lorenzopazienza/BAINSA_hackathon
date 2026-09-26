# Direct minimisation of A = sum_{i<j} arcsin|<x_i,x_j>| over d+2 unit vectors in R^d.
import numpy as np
from scipy.optimize import minimize
rng = np.random.default_rng(1)

def A_of(X):
    X = X / np.linalg.norm(X, axis=1, keepdims=True)
    G = np.clip(np.abs(X @ X.T), 0, 1)
    iu = np.triu_indices(len(X), 1)
    return np.arcsin(G[iu]).sum()

def run(d, trials=300):
    n = d + 2
    best = []
    for _ in range(trials):
        x0 = rng.standard_normal(n * d)
        f = lambda v: A_of(v.reshape(n, d))
        r = minimize(f, x0, method='Nelder-Mead', options={'maxiter': 20000, 'xatol': 1e-10, 'fatol': 1e-12})
        r = minimize(f, r.x, method='Powell', options={'maxiter': 20000, 'xtol': 1e-10, 'ftol': 1e-13})
        best.append((r.fun, r.x.reshape(n, d)))
    best.sort(key=lambda t: t[0])
    vals = np.array([b[0] for b in best])
    print(f"d={d}: min A/pi = {vals[0]/np.pi:.8f}, #within 1e-4 of pi: {(vals < np.pi + 1e-4).sum()}/{trials}, "
          f"any below pi-1e-6: {(vals < np.pi - 1e-6).any()}")
    return best

for d in [2, 3, 4, 5]:
    best = run(d, trials=200 if d < 5 else 120)
    X = best[0][1]; X = X / np.linalg.norm(X, axis=1, keepdims=True)
    G = np.abs(X @ X.T)
    print(np.round(G, 3))
