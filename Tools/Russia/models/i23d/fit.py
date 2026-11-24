# Подбор ортокамеры референса по силуэту. argv: mesh.glb mask.png out.json
# Кадр glTF: Y вверх. Камера: поворот az вокруг Y, наклон el; экран u вправо, v вниз.
import sys, json, numpy as np, trimesh
from PIL import Image
from scipy.optimize import minimize

m = trimesh.load(sys.argv[1], force='mesh')
P, _ = trimesh.sample.sample_surface(m, 150000, seed=0)
A = np.array(Image.open(sys.argv[2]))[:, :, 3] > 127
H, W = A.shape; k = 4
Am = A[::k, ::k]; h, w = Am.shape
ys, xs = np.nonzero(A)
mb = np.array([xs.min(), ys.min(), xs.max(), ys.max()], float)

def basis(az, el):
    az, el = np.radians(az), np.radians(el)
    d = np.array([np.sin(az) * np.cos(el), np.sin(el), np.cos(az) * np.cos(el)])  # к камере
    r = np.cross([0, 1, 0], d); r /= np.linalg.norm(r)
    u = np.cross(d, r)
    return r, u, d

def proj(az, el, s, ox, oy):
    r, u, d = basis(az, el)
    return np.stack([P @ r * s + ox, -(P @ u) * s + oy], 1)

def init(az, el):
    r, u, d = basis(az, el)
    pu, pv = P @ r, -(P @ u)
    s = (mb[2] - mb[0]) / (pu.max() - pu.min())
    return s, mb[0] - pu.min() * s, mb[1] - pv.min() * s

def iou(x):
    q = proj(*x) / k
    q = np.round(q).astype(int)
    ok = (q[:, 0] >= 0) & (q[:, 0] < w) & (q[:, 1] >= 0) & (q[:, 1] < h)
    M = np.zeros((h, w), bool); M[q[ok, 1], q[ok, 0]] = True
    from scipy.ndimage import binary_closing
    M = binary_closing(M, iterations=2)
    return (M & Am).sum() / (M | Am).sum()

best = None
for az in range(0, 360, 10):
    for el in range(10, 70, 5):
        x = (az, el, *init(az, el)); v = iou(x)
        if best is None or v > best[0]: best = (v, x)
print('grid', best)
res = minimize(lambda x: -iou(x), best[1], method='Nelder-Mead', options=dict(maxiter=600, xatol=0.05, fatol=1e-4,
               initial_simplex=None))
x = res.x; print('fit', -res.fun, x.tolist())
json.dump(dict(az=x[0], el=x[1], s=x[2], ox=x[3], oy=x[4], iou=-res.fun, W=W, H=H), open(sys.argv[3], 'w'))
# наложение: точки поверх референса
q = proj(*x).astype(int); ok = (q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)
im = np.array(Image.open(sys.argv[2]).convert('RGB')) // 2
im[q[ok, 1], q[ok, 0]] = [255, 0, 255]
Image.fromarray(im).resize((W // 2, H // 2)).save(sys.argv[3].replace('.json', '.jpg'))
