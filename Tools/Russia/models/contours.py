# /// script
# dependencies = ["numpy", "opencv-python-headless"]
# ///
"""Силуэты модели с ортогональных картинок -> parts.json (метры) для build.py.

  uv run Tools/Russia/models/contours.py Tools/Russia/models/t72b3m
"""
import json, os, sys
import cv2, numpy as np

D = sys.argv[1]
C = json.load(open(os.path.join(D, 'config.json')))

def mask(name):
    a = cv2.imread(os.path.join(D, 'ref', name)).astype(int)
    bg = np.median(np.concatenate([a[:8].reshape(-1, 3), a[-8:].reshape(-1, 3)]), 0)
    m = (np.abs(a - bg).sum(2) > 40).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    # без дыр: только внешний контур, залитый
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    f = np.zeros_like(m); cv2.drawContours(f, cs, -1, 255, cv2.FILLED)
    return f

def polys(m, eps=C.get("contour_eps", 2.5), minarea=400):
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return [cv2.approxPolyDP(c, eps, True)[:, 0, :].tolist() for c in cs if cv2.contourArea(c) >= minarea]

def bbox(m):
    ys, xs = np.nonzero(m); return int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())

S, T = C['side'], C['top']
side, top = mask(S['img']), mask(T['img'])
sx = lambda x: (x - S['x0']) / S['k']; sz = lambda y: (S['ground'] - y) / S['k']
tx = lambda x: (x - T['x0']) / T['k']; ty = lambda y: (T['y0'] - y) / T['k']

# зоны на виде сбоку
tz, bz = C['turret_zone'], C['barrel_zone']
zt = np.zeros_like(side); zt[:tz['ymax'], tz['x'][0]:tz['x'][1]] = 255
zb = np.zeros_like(side); zb[bz['y'][0]:bz['y'][1], bz['x'][0]:bz['x'][1]] = 255
side_turret = side & zt & ~zb
side_hull = side & ~zt & ~zb
# башня чуть заходит в корпус, чтобы не было щели
ov = np.zeros_like(side); ov[tz['ymax']:tz['ymax'] + 12, tz['x'][0]:tz['x'][1]] = 255
side_turret |= side & ov & ~zb

plan = np.zeros_like(top); cv2.fillPoly(plan, [np.array(C['turret_plan'], np.int32)], 255)
top_turret = top & plan

# ствол: профиль радиуса по X по виду сбоку
barrel = side & zb
cols = []
for x in range(bz['x'][0], bz['x'][1], 6):
    ys = np.nonzero(barrel[:, x])[0]
    if len(ys) > 2: cols.append([sx(x), (sz(ys.max()) + sz(ys.min())) / 2, (ys.max() - ys.min()) / 2 / S['k']])
cols = [c for c in cols if c[0] >= sx(C['trunnion_x']) - 0.05]
zc = float(np.median([c[1] for c in cols]))

# вид спереди/сзади: подгонка по габаритам к виду сбоку (высота) и сверху (ширина)
width = (bbox(top)[3] - bbox(top)[2]) / T['k']; height = (S['ground'] - bbox(side)[2]) / S['k']
views = {}
for v in ('front', 'rear'):
    m = mask(C[v]['img']); x0, x1, y0, y1 = bbox(m)
    views[v] = dict(img=C[v]['img'], kx=(x1 - x0) / width, cx=(x0 + x1) / 2, kz=(y1 - y0) / height, ground=y1, m=m)
F = views['front']
fy = lambda x: (x - F['cx']) / F['kx']; fz = lambda y: (F['ground'] - y) / F['kz']
# внешний край гусеницы: по виду спереди на высоте 0.3 м
row = F['m'][int(F['ground'] - 0.3 * F['kz'])]
xs = np.nonzero(row)[0]; track_out = float(max(abs(fy(xs.min())), abs(fy(xs.max()))))

W = C['wheels']; k = S['k']
out = dict(
    name=C['name'], game_scale=C['game_scale'],
    side_hull=[[[sx(x), sz(y)] for x, y in p] for p in polys(side_hull)],
    side_turret=[[[sx(x), sz(y)] for x, y in p] for p in polys(side_turret)],
    top_hull=[[[tx(x), ty(y)] for x, y in p] for p in polys(top)],
    top_turret=[[[tx(x), ty(y)] for x, y in p] for p in polys(top_turret)],
    front=[[[fy(x), fz(y)] for x, y in p] for p in polys(F['m'])],
    barrel=dict(z=zc, profile=[[c[0], c[2]] for c in cols]),
    turret_z=sz(tz['ymax']), trunnion=[sx(C['trunnion_x']), zc],
    wheels=[[sx(x), sz(W['y']), W['r'] / k] for x in W['x']],
    sprocket=[sx(C['sprocket']['x']), sz(C['sprocket']['y']), C['sprocket']['r'] / k],
    idler=[sx(C['idler']['x']), sz(C['idler']['y']), C['idler']['r'] / k],
    track_out=track_out, track_width=C['track_width'],
    # проекции для UV: пиксель = a*коорд + b
    proj=dict(
        side=dict(img=S['img'], u=[S['k'], S['x0']], v=[-S['k'], S['ground']]),
        top=dict(img=T['img'], u=[T['k'], T['x0']], v=[-T['k'], T['y0']]),
        front=dict(img=F['img'], u=[F['kx'], F['cx']], v=[-F['kz'], F['ground']]),
        rear=dict(img=views['rear']['img'], u=[-views['rear']['kx'], views['rear']['cx']], v=[-views['rear']['kz'], views['rear']['ground']]),
    ),
    size=[width, height],
)
json.dump(out, open(os.path.join(D, 'parts.json'), 'w'), indent=1)
print('width', round(width, 2), 'height', round(height, 2), 'track_out', round(track_out, 2), 'barrel z', round(zc, 2),
      'polys', {k: len(v) for k, v in out.items() if isinstance(v, list) and k.startswith(('side', 'top', 'front'))},
      'verts', {k: sum(len(p) for p in v) for k, v in out.items() if isinstance(v, list) and k.startswith(('side', 'top', 'front'))})
for n, m in (('side_hull', side_hull), ('side_turret', side_turret), ('top_turret', top_turret), ('front', F['m'])):
    cv2.imwrite(os.path.join(os.environ.get('TMPDIR', '/tmp'), f'mask_{n}.png'), cv2.resize(m, None, fx=0.3, fy=0.3))
