# Уточнение камеры (перспектива + крен) от ортоподбора. argv: mesh.glb mask.png cam.json out.json
import sys, json, numpy as np, trimesh
from PIL import Image
from scipy.optimize import minimize
from scipy.ndimage import binary_closing
sys.path.insert(0, __import__("os").path.dirname(__file__)); from camlib import proj
m = trimesh.load(sys.argv[1], force='mesh'); P, _ = trimesh.sample.sample_surface(m, 150000, seed=0)
A = np.array(Image.open(sys.argv[2]))[:, :, 3] > 127; H, W = A.shape; k = 3; Am = A[::k, ::k]; h, w = Am.shape
c0 = json.load(open(sys.argv[3])); keys = ['az', 'el', 'roll', 's', 'ox', 'oy', 'dist']
c0.setdefault('roll', 0.0); c0['dist'] = 6.0
def cam(x): return dict(zip(keys, x))
def iou(x):
    if x[6] < 1.5: return 0
    q = np.round(proj(P, cam(x)) / k).astype(int)
    ok = (q[:, 0] >= 0) & (q[:, 0] < w) & (q[:, 1] >= 0) & (q[:, 1] < h)
    M = np.zeros((h, w), bool); M[q[ok, 1], q[ok, 0]] = True; M = binary_closing(M, iterations=2)
    return (M & Am).sum() / (M | Am).sum()
best = None
for dist in (3, 4, 6, 10, 30):
    x0 = np.array([c0[kk] for kk in keys], float); x0[6] = dist
    res = minimize(lambda x: -iou(x), x0, method='Nelder-Mead', options=dict(maxiter=1500, xatol=0.01, fatol=1e-5))
    print('dist0', dist, -res.fun, np.round(res.x, 3).tolist(), flush=True)
    if best is None or res.fun < best.fun: best = res
c = cam(best.x); c['iou'] = -best.fun; c['W'] = W; c['H'] = H
json.dump(c, open(sys.argv[4], 'w')); print('best', c)
