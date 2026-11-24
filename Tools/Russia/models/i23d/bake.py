# Перенос цвета с референса на низкополигональный меш. argv: low.obj ref.png cam.json out_prefix [tex=1024]
# Видимые из камеры точки берут цвет с картинки, скрытые - с зеркальной (по X или Z) видимой точки с той же
# ориентацией нормали, иначе с ближайшей видимой. Пишет <out>.obj (с UV) и <out>.png.
import sys, json, numpy as np, trimesh, xatlas
from PIL import Image
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt

mesh = trimesh.load(sys.argv[1], force='mesh', process=True)
_im = Image.open(sys.argv[2]); ref = np.asarray(_im.convert('RGB'), np.float32)
from scipy.ndimage import binary_erosion
alpha = binary_erosion(np.asarray(_im.convert('RGBA'))[:, :, 3] > 127, iterations=4)
cam = json.load(open(sys.argv[3])); out = sys.argv[4]; T = int(sys.argv[5]) if len(sys.argv) > 5 else 1024
H, W = ref.shape[:2]
sys.path.insert(0, __import__('os').path.dirname(__file__)); import camlib
r, u, d = camlib.basis(cam['az'], cam['el'], cam.get('roll', 0)); Cpos = d * cam.get('dist', 1e6)
def proj(p): return camlib.proj(p, cam)

V, F = mesh.vertices.view(np.ndarray), mesh.faces.view(np.ndarray)
FN = mesh.face_normals.view(np.ndarray)

# z-буфер в кадре референса (глубина = p.d, больше = ближе к камере)
zb = np.full((H, W), -np.inf)
S2 = proj(V); D = V @ d
for f in F:
    a, b, c = S2[f]; x0, y0 = np.floor(np.minimum(np.minimum(a, b), c)).astype(int); x1, y1 = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W - 1), min(y1, H - 1)
    if x1 < x0 or y1 < y0: continue
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(den) < 1e-9: continue
    l0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / den
    l1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / den
    l2 = 1 - l0 - l1; ins = (l0 >= -1e-3) & (l1 >= -1e-3) & (l2 >= -1e-3)
    z = l0 * D[f[0]] + l1 * D[f[1]] + l2 * D[f[2]]
    sub = zb[y0:y1 + 1, x0:x1 + 1]; np.maximum(sub, np.where(ins, z, -np.inf), out=sub)

# UV-развёртка
vmap, idx, uvs = xatlas.parametrize(V, F)
V2 = V[vmap]; FN2 = FN
# растеризация в UV: точка и нормаль на каждый тексель
pos = np.zeros((T, T, 3)); nrm = np.zeros((T, T, 3)); cov = np.zeros((T, T), bool)
U = uvs * T
for fi, f in enumerate(idx):
    a, b, c = U[f]; x0, y0 = np.floor(np.minimum(np.minimum(a, b), c)).astype(int); x1, y1 = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, T - 1), min(y1, T - 1)
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(den) < 1e-12: continue
    l0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / den
    l1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / den
    l2 = 1 - l0 - l1; ins = (l0 >= -0.02) & (l1 >= -0.02) & (l2 >= -0.02)
    p = l0[..., None] * V2[f[0]] + l1[..., None] * V2[f[1]] + l2[..., None] * V2[f[2]]
    ys, xs = np.nonzero(ins)
    pos[ys + y0, xs + x0] = p[ys, xs]; nrm[ys + y0, xs + x0] = FN2[fi]; cov[ys + y0, xs + x0] = True

ty, tx = np.nonzero(cov); P = pos[ty, tx]; N = nrm[ty, tx]
q = proj(P); qi = np.clip(np.round(q - 0.5).astype(int), 0, [W - 1, H - 1])
inimg = (q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)
span = np.ptp(V, 0).max()
vis = inimg & alpha[qi[:, 1], qi[:, 0]] & (np.einsum('ij,ij->i', N, (Cpos - P) / np.linalg.norm(Cpos - P, axis=1, keepdims=True)) > np.where(N[:, 1] > 0.6, 0.03, 0.25)) & (P @ d >= zb[qi[:, 1], qi[:, 0]] - 0.01 * span)
def sample(qq):
    x = np.clip(qq[:, 0] - 0.5, 0, W - 1.001); y = np.clip(qq[:, 1] - 0.5, 0, H - 1.001)
    x0, y0 = x.astype(int), y.astype(int); fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    return (ref[y0, x0] * (1 - fx) * (1 - fy) + ref[y0, x0 + 1] * fx * (1 - fy) + ref[y0 + 1, x0] * (1 - fx) * fy + ref[y0 + 1, x0 + 1] * fx * fy)
col = np.zeros((len(P), 3))
col[vis] = sample(q[vis])
print('texels', len(P), 'visible', vis.mean().round(3))

# скрытые: цвет с видимой точки того же класса (крыша / стена по X / стена по Z) с той же стороной нормали,
# позиция зеркалится через центр габарита по оси нормали стены
c0 = (V.min(0) + V.max(0)) / 2
def cls(n):
    up = n[:, 1] > 0.6; wx = ~up & (np.abs(n[:, 0]) >= np.abs(n[:, 2])); sl = up & (np.abs(n[:, 0]) > 0.12)
    return np.where(sl, 5 + (n[:, 0] > 0), np.where(up, 0, np.where(wx, 1 + (n[:, 0] > 0), 3 + (n[:, 2] > 0))))
cv, ch = cls(N[vis]), None
hid = np.nonzero(~vis)[0]; Ph = P[hid].copy(); Nh = N[hid]
c_h = cls(Nh)
Pm = Ph.copy(); want = c_h.copy()
for a, k1, k2 in ((0, 1, 2), (2, 3, 4), (0, 5, 6)):
    s = (c_h == k1) | (c_h == k2); Pm[s, a] = 2 * c0[a] - Pm[s, a]
    want[c_h == k1], want[c_h == k2] = k2, k1
Pv, Cv = P[vis], col[vis]
for k in range(7):
    src = cv == k
    if not src.any(): src = np.ones(len(cv), bool)
    sel = want == k
    if not sel.any(): continue
    _, nb = cKDTree(Pv[src]).query(Pm[sel]); col[hid[sel]] = Cv[src][nb]

img = np.zeros((T, T, 3)); img[ty, tx] = col
# отступ за края островов
_, (iy, ix) = distance_transform_edt(~cov, return_indices=True)
img = img[iy, ix]
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)[::-1]).save(out + '.png')   # v снизу вверх
# OBJ с UV
with open(out + '.obj', 'w') as fo:
    fo.write(f'mtllib {out.split("/")[-1]}.mtl\nusemtl m\n')
    for p in V2: fo.write('v %.5f %.5f %.5f\n' % tuple(p))
    for t in uvs: fo.write('vt %.5f %.5f\n' % tuple(t))
    for f in idx + 1: fo.write('f %d/%d %d/%d %d/%d\n' % (f[0], f[0], f[1], f[1], f[2], f[2]))
open(out + '.mtl', 'w').write(f'newmtl m\nmap_Kd {out.split("/")[-1]}.png\n')
print('ok', len(V2), 'verts', len(idx), 'tris')
