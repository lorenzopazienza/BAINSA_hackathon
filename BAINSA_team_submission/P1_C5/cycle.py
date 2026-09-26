# Cycle family: x_1..x_m in R^{m-2}, x_i ⊥ x_j unless cyclically adjacent.
# Parametrisation: x_1=e_1, x_{k+1}=sin(t_k) e_k + cos(t_k) e_{k+1} (k=1..m-3),
# x_{m-1}=e_{m-2}, x_m = unit vector ⊥ x_2..x_{m-2}.
import numpy as np

def vectors(t):
    t = np.asarray(t, float); m = len(t) + 3; D = m - 2
    X = np.zeros((m, D)); X[0, 0] = 1
    for k in range(m - 3):
        X[k + 1, k] = np.sin(t[k]); X[k + 1, k + 1] = np.cos(t[k])
    X[m - 2, D - 1] = 1
    # x_m: P_k = prod_{j<k} sin t_j * prod_{j>=k} cos t_j (1-based k=1..m-2), alternating signs
    P = np.array([np.prod(np.sin(t[:k])) * np.prod(np.cos(t[k:])) * (-1) ** k for k in range(D)])
    X[m - 1] = P / np.linalg.norm(P)
    return X

def A_formula(t):
    t = np.asarray(t, float); m = len(t) + 3
    P = np.array([np.prod(np.sin(t[:k])) * np.prod(np.cos(t[k:])) for k in range(m - 2)])
    N = np.linalg.norm(P)
    s = t[0] + np.pi / 2 - t[-1]
    s += sum(np.arcsin(np.sin(t[k]) * np.cos(t[k - 1])) for k in range(1, m - 3))
    s += np.arcsin(P[0] / N) + np.arcsin(P[-1] / N)
    return s

def A_direct(X):
    G = np.clip(np.abs(X @ X.T), 0, 1); iu = np.triu_indices(len(X), 1)
    return np.arcsin(G[iu]).sum()

if __name__ == '__main__':
    rng = np.random.default_rng(0)
    for m in range(4, 13):
        worst = np.inf; maxerr = 0; maxoff = 0
        for _ in range(20000):
            t = rng.uniform(0, np.pi / 2, m - 3)
            X = vectors(t); G = X @ X.T
            # check the orthogonality pattern
            for i in range(m):
                for j in range(i + 2, m):
                    if not (i == 0 and j == m - 1):
                        maxoff = max(maxoff, abs(G[i, j]))
            a = A_formula(t); maxerr = max(maxerr, abs(a - A_direct(X)))
            worst = min(worst, a)
        print(f"m={m}: min (A-pi) over 20000 random = {worst-np.pi:.3e}, formula err {maxerr:.1e}, max nonadjacent |g| {maxoff:.1e}")
