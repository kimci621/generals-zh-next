# /// script
# dependencies = ["numpy", "pillow"]
# ///
"""Завод бронетехники России (RUWARFACT) из image-to-3D меша -> W3D с распашными воротами.

Исходник: warfactory3d/ (ref.png референс, wf.obj + wf.png меш 8000 треугольников с текстурой, cam.json камера
референса). Как они получены: i23d/ (Hunyuan3D-2mini форма -> сокращение -> подбор камеры -> перенос цвета).
Кадр меша glTF: Y вверх, ворота на грани +Z. В игре X вперёд, Z вверх, ворота на +X, юнит появляется в (0, -27)
и выезжает к +X (выход китайского завода, INI не меняем). Чтобы цех с воротами встал на Y -27 и всё поместилось
в площадку 114x122, здание отражено по Y (MIRROR).
Состояния: RUWARFACT (ворота DOOR01/02 открываются наружу на 90 градусов за 1 с), _D (та же геометрия, текстура
темнее с копотью), _E (руины: здание осело до четверти высоты, створок нет).

  uv run Tools/Russia/models/wf3d.py <retail W3D dir: avcrusader.W3D>      # Art/W3D + Art/Textures
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'warfactory3d')
OUT = os.path.join(HERE, 'bld_out')
ART = os.path.join(HERE, '../../../GeneralsMD/Code/Data/Art')
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
from bld import dds   # DXT1 с мипмапами
import w3d

# ворота в кадре меша (найдены лучами камеры референса по углам створок на ref.png)
GATE_X, GATE_Y, GATE_Z = (0.03, 0.434), (-0.447, -0.18), 0.668
GATE_PX = [(501, 674), (791, 720), (790, 915), (503, 865)]    # створки на ref.png: TL TR BR BL
S, GX, GY, MIRROR = 55.0, 36.0, -27.0, True                  # масштаб, плоскость ворот X, центр ворот Y

def load_obj(p):
    V, T, F = [], [], []
    for ln in open(p):
        a = ln.split()
        if not a: continue
        if a[0] == 'v': V.append([float(x) for x in a[1:4]])
        elif a[0] == 'vt': T.append([float(x) for x in a[1:3]])
        elif a[0] == 'f': F.append([int(x.split('/')[0]) - 1 for x in a[1:4]])
    return np.array(V), np.array(T), np.array(F)

def to_game(P):
    """glTF -> игра: X = z (ворота вперёд), Y = +-x, Z = y; ворота в (GX, GY), низ ворот на Z 0."""
    xg = sum(GATE_X) / 2
    sy = -1 if MIRROR else 1
    return np.stack([(P[:, 2] - GATE_Z) * S + GX, sy * (P[:, 0] - xg) * S + GY, (P[:, 1] - GATE_Y[0]) * S], 1)

def vnormals(V, F):
    """Сглаженные нормали, общие для вершин в одной точке (швы UV не дают ступенек света)."""
    key = np.round(V, 3); _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel()
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])     # длина = 2 площади
    acc = np.zeros((inv.max() + 1, 3))
    for k in range(3): np.add.at(acc, inv[F[:, k]], fn)
    n = acc[inv]; return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)

def quad(p, uv):
    """Четырёхугольник p[0..3] против часовой снаружи, uv на каждую вершину."""
    p = np.array(p, float); n = np.cross(p[1] - p[0], p[2] - p[0]); n /= np.linalg.norm(n)
    return dict(V=p.tolist(), N=[n.tolist()] * 4, U=[list(x) for x in uv], T=[(0, 1, 2), (0, 2, 3)])

def box(c, s, front_uv=None, uv=(0.99, 0.5), back_uv=None):
    """Брусок: c центр, s размеры; грань +X получает front_uv, -X back_uv (по 4 точки), остальные одну точку uv."""
    x0, y0, z0 = (c[i] - s[i] / 2 for i in range(3)); x1, y1, z1 = (c[i] + s[i] / 2 for i in range(3))
    P = lambda a, b, d: (x1 if a else x0, y1 if b else y0, z1 if d else z0)
    one = [uv] * 4
    f = [quad([P(0, 1, 0), P(0, 0, 0), P(0, 0, 1), P(0, 1, 1)], back_uv or one),
         quad([P(1, 0, 0), P(1, 1, 0), P(1, 1, 1), P(1, 0, 1)], front_uv or one),
         quad([P(0, 0, 0), P(1, 0, 0), P(1, 0, 1), P(0, 0, 1)], one),
         quad([P(1, 1, 0), P(0, 1, 0), P(0, 1, 1), P(1, 1, 1)], one),
         quad([P(0, 0, 1), P(1, 0, 1), P(1, 1, 1), P(0, 1, 1)], one)]
    return merge(f)

def merge(parts):
    V, N, U, T = [], [], [], []
    for p in parts:
        o = len(V); V += p['V']; N += p['N']; U += p['U']; T += [(a + o, b + o, c + o) for a, b, c in p['T']]
    return dict(V=V, N=N, U=U, T=T)

def gate_texture():
    """Створки с референса, выпрямленные в 256x256; правая колонка 8 px чёрная (внутренность цеха)."""
    ref = Image.open(os.path.join(SRC, 'ref.png')).convert('RGB')
    (tlx, tly), (trx, try_), (brx, bry), (blx, bly) = GATE_PX
    g = ref.transform((248, 256), Image.QUAD, (tlx, tly, blx, bly, brx, bry, trx, try_), Image.BICUBIC)
    im = Image.new('RGB', (256, 256), (12, 12, 10)); im.paste(g, (0, 0)); return im

def textures():
    base = Image.open(os.path.join(SRC, 'wf.png')).convert('RGB')
    a = np.asarray(base, np.float32)
    rng = np.random.default_rng(3)
    soot = Image.fromarray((rng.random((64, 64)) * 255).astype(np.uint8)).resize(base.size, Image.BICUBIC).filter(ImageFilter.GaussianBlur(12))
    s = np.asarray(soot, np.float32)[..., None] / 255
    dmg = a * (0.62 - 0.25 * np.clip(s * 2 - 0.6, 0, 1))
    rub = a * 0.42 + np.array([6, 5, 4])
    out = {'': base, '_D': Image.fromarray(np.clip(dmg, 0, 255).astype(np.uint8)), '_B': Image.fromarray(np.clip(rub, 0, 255).astype(np.uint8))}
    g = gate_texture(); out['_G'] = g
    out['_GD'] = Image.fromarray(np.clip(np.asarray(g, np.float32) * 0.6, 0, 255).astype(np.uint8))
    return out

def model(state):
    V0, UV, F = load_obj(os.path.join(SRC, 'wf.obj'))
    # дыра под ворота: грани фасада внутри проёма
    c = V0[F].mean(1); n = np.cross(V0[F[:, 1]] - V0[F[:, 0]], V0[F[:, 2]] - V0[F[:, 0]])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    hole = (c[:, 0] > GATE_X[0] + 0.005) & (c[:, 0] < GATE_X[1] - 0.005) & (c[:, 1] < GATE_Y[1] - 0.005) & \
           (c[:, 1] > GATE_Y[0] + 0.01) & (c[:, 2] > GATE_Z - 0.06) & (n[:, 2] > 0.5)
    F = F[~hole]
    V = to_game(V0)
    if MIRROR: F = F[:, [0, 2, 1]]
    E = state == 'E'
    if E: V[:, 2] = np.minimum(V[:, 2], 0) + np.maximum(V[:, 2], 0) * 0.25
    N = vnormals(V, F)
    used = np.unique(F); remap = -np.ones(len(V), int); remap[used] = np.arange(len(used))
    base = dict(V=V[used].tolist(), N=N[used].tolist(), U=UV[used].tolist(), T=remap[F].tolist())
    GW = (GATE_X[1] - GATE_X[0]) * S; GH = (GATE_Y[1] - GATE_Y[0]) * S
    zs = 0.25 if E else 1.0
    # проём: тёмная коробка внутри цеха (видна, когда створки открыты)
    door = [box((GX - 4.0, GY, GH * zs / 2), (8.0, GW, GH * zs))]
    meshes = [('BASE', 'ROOTTRANSFORM', 'solid', base)]
    house = box((GX + 0.3, GY, GH + 2.6), (0.4, GW * 0.9, 1.6))   # табличка цвета игрока над фрамугой
    if not E: meshes.append(('HOUSECOLOR01', 'ROOTTRANSFORM', 'house', house))
    bones = [dict(name='ROOTTRANSFORM', parent=-1, pos=[0, 0, 0]),
             dict(name='DOOR01', parent=0, pos=[GX + 0.3, GY - GW / 2, 0.0]),
             dict(name='DOOR02', parent=0, pos=[GX + 0.3, GY + GW / 2, 0.0])]
    if not E:
        # створка от петли: DOOR01 на -Y (левая для зрителя у ворот, u 0..0.5), DOOR02 на +Y (u 0.5..1)
        for k, sg, u0, u1 in ((1, 1, 0.0, 0.5), (2, -1, 0.5, 1.0)):
            uv = [(u0 * 0.969, 0.0), (u1 * 0.969, 0.0), (u1 * 0.969, 1.0), (u0 * 0.969, 1.0)]
            back = [uv[1], uv[0], uv[3], uv[2]]   # изнанка: та же половина, зеркально (видна у открытой створки)
            meshes.append((f'DOOR{k}', f'DOOR0{k}', 'door', box((0.25, sg * GW / 4, GH / 2), (0.5, GW / 2, GH),
                                                                front_uv=uv, back_uv=back, uv=(0.01, 0.5))))
    meshes.append(('INSIDE', 'ROOTTRANSFORM', 'door', merge(door)))
    # точки дыма и огня: верх меша над заданными точками плана
    def top(x, y, r=5.0):
        d = np.hypot(V[used, 0] - x, V[used, 1] - y); z = V[used, 2][d < r]
        return [x, y, float(z.max()) if len(z) else 10.0]
    chim = V[used][np.argmax(V[used, 2])]
    bones += [dict(name='SMOKE01', parent=0, pos=[float(chim[0]), float(chim[1]), float(chim[2])]),
              dict(name='SMOKE02', parent=0, pos=top(GX - 35, GY)), dict(name='SMOKE03', parent=0, pos=top(GX - 15, GY + 46)),
              dict(name='SMOKE04', parent=0, pos=top(GX - 70, GY)), dict(name='FIRE01', parent=0, pos=top(GX - 15, GY + 3)),
              dict(name='FIRE02', parent=0, pos=top(GX - 60, GY - 5))]
    anim = None
    if not E:
        nf = 30   # 1 с при 30 кадрах; DOOR01 на -90 (наружу к +X), DOOR02 на +90
        ease = [0.5 - 0.5 * math.cos(math.pi * f / (nf - 1)) for f in range(nf)]
        anim = (nf, 30, {'DOOR01': [(0, 0, -math.sin(math.pi / 4 * e), math.cos(math.pi / 4 * e)) for e in ease],
                         'DOOR02': [(0, 0, math.sin(math.pi / 4 * e), math.cos(math.pi / 4 * e)) for e in ease]})
    return bones, meshes, anim

def build(ret):
    cru = w3d.parse(open(os.path.join(ret, 'avcrusader.W3D'), 'rb').read())
    retail = dict(solid=(cru, 'CHASSIS'), house=(cru, 'HOUSECOLOR01'), door=(cru, 'CHASSIS'))
    os.makedirs(OUT, exist_ok=True); name = 'RUWARFACT'
    for suf, im in textures().items():
        im.save(os.path.join(OUT, f'{name}{suf}.png')); dds(im, os.path.join(ART, 'Textures', f'{name}{suf}.dds'))
    for st, tsuf, gsuf in (('', '', '_G'), ('D', '_D', '_GD'), ('E', '_B', '_GD')):
        v = name + (f'_{st}' if st else '')
        bones, meshes, anim = model(st)
        ms = [dict(name=nm, bone=bn, kind=k, verts=[list(x) for x in p['V']], normals=[list(x) for x in p['N']],
                   uvs=[list(x) for x in p['U']], tris=[list(x) for x in p['T']]) for nm, bn, k, p in meshes]
        mj = os.path.join(OUT, f'{v}.json'); json.dump(dict(name=v, bones=bones, meshes=ms), open(mj, 'w'))
        out = os.path.join(ART, 'W3D', f'{v}.W3D')
        w3d.build(mj, out, v, dict(solid=f'{name}{tsuf}.tga', house='Housecolor.tga', door=f'{name}{gsuf}.tga'),
                  {m['name'] for m in ms}, retail, anim=anim)
        b = open(out, 'rb').read(); assert w3d.ser(w3d.parse(b)) == b
        print(v, 'tris', sum(len(m['tris']) for m in ms), 'anim', anim and anim[0], len(b), 'bytes')

if __name__ == '__main__':
    build(sys.argv[1])
