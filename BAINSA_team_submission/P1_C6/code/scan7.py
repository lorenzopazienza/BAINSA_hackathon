"""Problem 1, Cell 6: for each connected 7-vertex graph J with max degree <= 3 and cyclomatic number >= 2,
minimise A over 7 unit vectors in R^4 with the orthogonality pattern of J imposed (penalty method).
Prints the best value (in units of pi) and the smallest J-entry |g_ij| reached. Numerical evidence only."""
import numpy as np, networkx as nx
from networkx.generators.atlas import graph_atlas_g
from scipy.optimize import minimize
N,d=7,4; rng=np.random.default_rng(1)
iu=np.triu_indices(N,1)
cands=[G for G in graph_atlas_g() if G.number_of_nodes()==7 and nx.is_connected(G)
       and max(dict(G.degree()).values())<=3 and G.number_of_edges()-7+1>=2]
print(len(cands),"graphs")
out=[]
for G in cands:
    Hm=np.ones((N,N),bool); np.fill_diagonal(Hm,False)
    for u,v in G.edges(): Hm[u,v]=Hm[v,u]=False
    H=Hm[iu]
    def f(x,eps,W):
        X=x.reshape(N,d); X=X/np.linalg.norm(X,axis=1,keepdims=True)
        g=(X@X.T)[iu]
        a=np.sqrt(g[~H]**2+eps**2)-eps
        return np.arcsin(np.clip(a,0,1)).sum()+W*(g[H]**2).sum()
    best=None
    for t in range(4):
        x=rng.normal(size=N*d)
        for eps,W in [(1e-2,1e2),(1e-3,1e4),(1e-5,1e6),(1e-7,1e8)]:
            x=minimize(f,x,args=(eps,W),method='L-BFGS-B',options={'maxiter':3000}).x
        X=x.reshape(N,d); X/=np.linalg.norm(X,axis=1,keepdims=True); g=X@X.T
        viol=np.abs(g[iu][H]).max() if H.any() else 0
        Jmin=np.abs(g[iu][~H]).min()
        rank=np.linalg.matrix_rank(X,tol=1e-6)
        val=np.arcsin(np.clip(np.abs(g[iu][~H]),0,1)).sum()/np.pi
        if viol<1e-5 and rank==4 and (best is None or val<best[0]): best=(val,X,Jmin)
    if best: out.append((best[0],sorted(G.edges()),best[1],best[2]))
out.sort(key=lambda t:t[0])
for v,e,_,jm in out[:40]: print(round(v,4),round(jm,4),e)
np.save("best7.npy",out[0][2]); print("best edges",out[0][1])
