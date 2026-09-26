"""Problem 1, Cell 6: unconstrained local minimisation of A for 7 lines in R^4 (numerical evidence only)."""
import numpy as np
from scipy.optimize import minimize
rng=np.random.default_rng(0)
N,d=7,4
iu=np.triu_indices(N,1)
def A_of(X,eps):
    X=X.reshape(N,d); X=X/np.linalg.norm(X,axis=1,keepdims=True)
    g=(X@X.T)[iu]; a=np.sqrt(g*g+eps*eps)-eps
    return np.arcsin(np.clip(a,0,1)).sum()
res=[]
for t in range(150):
    x=rng.normal(size=N*d)
    for eps in [1e-2,1e-3,1e-4,1e-6]:
        x=minimize(A_of,x,args=(eps,),method='L-BFGS-B').x
    X=x.reshape(N,d); X/=np.linalg.norm(X,axis=1,keepdims=True)
    g=X@X.T; val=np.arcsin(np.clip(np.abs(g[iu]),0,1)).sum()/np.pi
    J=(np.abs(g)>1e-4)&~np.eye(N,dtype=bool)
    import networkx as nx
    G=nx.from_numpy_array(J.astype(int))
    comps=[len(c) for c in nx.connected_components(G)]
    res.append((round(val,4),tuple(sorted(comps)),int(J.sum()//2),int(max(J.sum(1)))))
from collections import Counter
for k,v in sorted(Counter(res).items()): print(k,v)
