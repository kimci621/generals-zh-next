# /// script
# dependencies = ["numpy", "pillow"]
# ///
"""Завод бронетехники России (RUWARFACT): ровные блоки, грани раскрашены участками референса.

Референс warfactory3d/ref.png (вид 3/4), камера к нему warfactory3d/cam.json. Здание собрано из блоков в кадре
референса (glTF: Y вверх, ворота на грани +Z): цех с двускатной крышей, пристройка, контора, котельная, труба.
Каждая грань берёт цвет со своего участка картинки: по 4 углам, снятым с ref.png (выпрямление), или через камеру.
Невидимые на референсе грани и куски берут цвет с видимых (зеркально или повтором).
В игре X вперёд, Z вверх, ворота на +X, юнит появляется в (0, -27) и выезжает к +X (выход китайского завода,
INI не меняем). Здание отражено по Y, чтобы цех с воротами встал на Y -27, а контора поместилась в площадку 114x122.
Состояния: RUWARFACT (ворота DOOR01/02 открываются наружу на 90 градусов за 1 с), _D (текстура темнее, копоть),
_E (руины: блоки осели до четверти высоты, створок нет).

  uv run Tools/Russia/models/wf3.py <retail W3D dir: avcrusader.W3D>          # Art/W3D + Art/Textures
  uv run Tools/Russia/models/wf3.py overlay <out.png>                          # рёбра блоков поверх ref.png
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'warfactory3d')
OUT = os.path.join(HERE, 'bld_out')
ART = os.path.join(HERE, '../../../GeneralsMD/Code/Data/Art')
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'i23d'))
import camlib

CAM = json.load(open(os.path.join(SRC, 'cam.json')))
REF = np.asarray(Image.open(os.path.join(SRC, 'ref.png')).convert('RGB'), np.float32)

# ---------------------------------------------------------------- блоки (кадр референса)
G = -0.447                                                     # земля
HX, HZ, EAVE, RIDGE = (-0.115, 0.574), (-1.10, 0.668), -0.018, 0.081   # цех
XC = sum(HX) / 2
GATE_X, GATE_Y = (0.03, 0.434), (G, -0.18)                     # створки
AX, AZ, AHI, ALO = (0.574, 0.764), (-0.72, 0.24), -0.15, -0.25  # пристройка, крыша от цеха наружу
OX, OZ, OTOP = (-0.60, -0.115), (0.40, 0.76), -0.074            # контора
BX, BZ, BTOP = (-0.60, -0.28), (-0.25, 0.05), 0.03              # котельная
LX, LZ, LTOP = (-0.60, -0.115), (0.05, 0.40), -0.10             # низкий блок между ними
CH = dict(x=-0.52, z=0.12, r0=0.048, r1=0.037, top=0.45, n=12)  # труба
GATE_PX = [(501, 674), (791, 720), (790, 915), (503, 865)]    # створки на ref.png: TL TR BR BL
S, GX, GY, MIRROR = 55.0, 44.0, -27.0, True                  # масштаб, плоскость ворот X, центр ворот Y
D = 380                                                      # текселей на единицу кадра (1 единица = 55 в игре)

def homog(src, dst):
    """3x3 H: src (u,v) -> dst (px) по 4 парам."""
    A = []
    for (x, y), (X, Y) in zip(src, dst):
        A += [[x, y, 1, 0, 0, 0, -X * x, -X * y, -X], [0, 0, 0, x, y, 1, -Y * x, -Y * y, -Y]]
    h = np.linalg.svd(np.array(A, float))[2][-1]; return h.reshape(3, 3) / h[-1]

def by_quad(uv, px):
    H = homog(uv, px)
    def f(u, v):
        p = np.stack([u, v, np.ones_like(u)], -1) @ H.T; return p[..., :2] / p[..., 2:3]
    return f

def by_cam(o, eu, ev):
    o, eu, ev = map(np.array, (o, eu, ev))
    def f(u, v):
        P = o + u[..., None] * eu + v[..., None] * ev; sh = P.shape[:-1]
        return camlib.proj(P.reshape(-1, 3), CAM).reshape(*sh, 2)
    return f

def remap(f, g):
    """Сначала g: (u,v) -> (u',v') (зеркало, повтор), потом выборка f."""
    return lambda u, v: f(*g(u, v))

def unit(v): v = np.array(v, float); return v / np.linalg.norm(v)

CYLS, BOXES = [], []   # (текстура, низ, верх, r0, r1, граней, крышка) и (текстура, центр низа, размер) - заполняет faces()

def cyl_tex(cx, yb, yt, rb, rt):
    """Цилиндр на ref.png (ось вертикальна, центр cx, низ yb, верх yt, радиусы в px) -> развёртка; тыл - зеркало лица."""
    def f(u, v, W=None, H=None):
        th = u * 2 * math.pi; th = np.where(th > math.pi, th - 2 * math.pi, th)
        th = np.where(np.abs(th) > math.pi / 2, np.sign(th) * math.pi - th, th)
        t = np.clip(v, 0, 1); r = rb * (1 - t) + rt * t
        return np.stack([cx + r * np.sin(th) * 0.97, yb + (yt - yb) * t], -1)
    return f

class Face:
    """Плоская грань: o + u*eu + v*ev, многоугольники в (u,v), размер W x H, выборка цвета sample(u,v)->px.
    share: брать прямоугольник атласа у другой грани (тогда sample не нужен)."""
    def __init__(s, name, o, eu, ev, W, H, polys=None, sample=None, share=None, n=None, flipu=False, tex_only=False):
        s.name, s.o, s.eu, s.ev, s.W, s.H = name, np.array(o, float), unit(eu), unit(ev), W, H
        s.polys = polys or [[(0, 0), (W, 0), (W, H), (0, H)]]
        s.sample, s.share, s.flipu, s.tex_only = sample, share, flipu, tex_only
        s.n = unit(n) if n is not None else np.cross(s.eu, s.ev)

def faces():
    F = []
    W, Hh = HX[1] - HX[0], RIDGE - G; ue, ur = EAVE - G, XC - HX[0]
    gu0, gu1, gv = GATE_X[0] - HX[0], GATE_X[1] - HX[0], GATE_Y[1] - G
    # торец с воротами: ворота по 4 углам, левая половина зеркалом правой (её закрывает контора)
    gable = by_quad([(gu0, gv), (gu1, gv), (gu1, 0), (gu0, 0)], GATE_PX)
    gable = remap(gable, lambda u, v: (np.where(u < ur, 2 * ur - u, u), v))
    tri = [(0, ue), (W, ue), (ur, Hh)]
    front = [[(0, 0), (gu0, 0), (gu0, ue), (0, ue)], [(gu1, 0), (W, 0), (W, ue), (gu1, ue)],
             [(gu0, gv), (gu1, gv), (gu1, ue), (gu0, ue)], tri]
    F.append(Face('gable', (HX[0], G, HZ[1]), (1, 0, 0), (0, 1, 0), W, Hh, front, gable))
    F.append(Face('gable_b', (HX[1], G, HZ[0]), (-1, 0, 0), (0, 1, 0), W, Hh,
                  [[(0, 0), (W, 0), (W, ue), (0, ue)], tri], share='gable'))
    # длинные стены: правая через камеру; низ за пристройкой - повтором открытого переднего куска
    L = HZ[1] - HZ[0]; seg = HZ[1] - AZ[1]; hid = AHI - G
    wall = by_cam((HX[1], G, HZ[1]), (0, 0, -1), (0, 1, 0))
    wall = remap(wall, lambda u, v: (np.where((u > seg) & (v < hid + 0.02), np.mod(u, seg), u), v))
    F.append(Face('wall_r', (HX[1], G, HZ[1]), (0, 0, -1), (0, 1, 0), L, ue, sample=wall))
    F.append(Face('wall_l', (HX[0], G, HZ[1]), (0, 0, -1), (0, 1, 0), L, ue, share='wall_r', n=(-1, 0, 0)))
    # скаты крыши через камеру
    # левый скат камера видит почти вскользь (подбор по силуэту занизил наклон), поэтому он по 4 углам
    sl = math.hypot(ur, RIDGE - EAVE)
    rlq = by_quad([(0, 0), (0, sl), (L, sl), (L, 0)], [(385, 522), (628, 487), (1172, 180), (925, 208)])
    for nm, x0, dx in (('roof_l', HX[0], ur), ('roof_r', HX[1], -ur)):
        ev = unit((dx, RIDGE - EAVE, 0))
        # у заднего торца левый скат на картинке кончается раньше: последние 0.06 берём с соседнего куска
        smp = remap(rlq, lambda u, v: (np.minimum(u, L - 0.06), v)) if dx > 0 else by_cam((x0, EAVE, HZ[1]), (0, 0, -1), ev)
        F.append(Face(nm, (x0, EAVE, HZ[1]), (0, 0, -1), ev, L, sl, [[(-0.02, -0.025), (L + 0.02, -0.025), (L + 0.02, sl), (-0.02, sl)]],
                      sample=smp,
                      n=np.cross((0, 0, -1), ev) * (-1 if dx > 0 else 1)))
    # пристройка
    aw, ad, ah, al = AX[1] - AX[0], AZ[1] - AZ[0], AHI - G, ALO - G
    af = by_quad([(0, ah), (aw, al), (aw, 0), (0, 0)], [(1040, 668), (1180, 710), (1181, 858), (1040, 830)])
    F.append(Face('annex_f', (AX[0], G, AZ[1]), (1, 0, 0), (0, 1, 0), aw, ah, [[(0, 0), (aw, 0), (aw, al), (0, ah)]], af))
    F.append(Face('annex_b', (AX[1], G, AZ[0]), (-1, 0, 0), (0, 1, 0), aw, ah, [[(0, 0), (aw, 0), (aw, ah), (0, al)]],
                  share='annex_f', flipu=True))
    ao = by_quad([(0, al), (ad, al), (ad, 0), (0, 0)], [(1180, 710), (1415, 455), (1415, 605), (1181, 858)])
    F.append(Face('annex_o', (AX[1], G, AZ[1]), (0, 0, -1), (0, 1, 0), ad, al, sample=ao))
    rl = math.hypot(aw, AHI - ALO); rev = unit((aw, ALO - AHI, 0))
    ar = by_quad([(0, 0), (0, rl), (ad, rl), (ad, 0)], [(1040, 668), (1180, 710), (1415, 455), (1282, 408)])
    F.append(Face('annex_r', (AX[0], AHI, AZ[1]), (0, 0, -1), rev, ad, rl, sample=ar, n=np.cross((0, 0, -1), rev) * -1))
    # контора: фасад по 4 углам; бока - его первые окна; крыша по 4 углам
    ow, od, oh = OX[1] - OX[0], OZ[1] - OZ[0], OTOP - G
    of = by_quad([(0, oh), (ow, oh), (ow, 0), (0, 0)], [(38, 548), (390, 588), (390, 868), (40, 822)])
    F.append(Face('office_f', (OX[0], G, OZ[1]), (1, 0, 0), (0, 1, 0), ow, oh, sample=of))
    F.append(Face('office_b', (OX[1], G, OZ[0]), (-1, 0, 0), (0, 1, 0), ow, oh, share='office_f'))
    side = remap(of, lambda u, v: (u + 0.03, v))
    F.append(Face('office_s', (OX[0], G, OZ[0]), (0, 0, 1), (0, 1, 0), od, oh, sample=side, n=(-1, 0, 0)))
    F.append(Face('office_s2', (OX[1], G, OZ[1]), (0, 0, -1), (0, 1, 0), od, oh, share='office_s'))
    orf = by_quad([(0, 0), (ow, 0), (ow, od), (0, od)], [(32, 530), (398, 580), (568, 503), (200, 450)])
    F.append(Face('office_r', (OX[0], OTOP, OZ[1]), (1, 0, 0), (0, 0, -1), ow, od, sample=orf))
    # котельная: крыша и два видимых бока по углам, низ (закрыт низким блоком) повтором верха
    bw, bd, bh = BX[1] - BX[0], BZ[1] - BZ[0], BTOP - G
    br = by_quad([(0, 0), (bw, 0), (bw, bd), (0, bd)], [(289, 328), (572, 343), (633, 298), (350, 283)])
    F.append(Face('boil_r', (BX[0], BTOP, BZ[1]), (1, 0, 0), (0, 0, -1), bw, bd, sample=br))
    band = BTOP - LTOP
    bf = by_quad([(0, bh), (bw, bh), (bw, bh - band), (0, bh - band)], [(289, 328), (572, 343), (572, 403), (289, 388)])
    tile = lambda u, v: (u, np.where(v < bh - band, bh - band + np.mod(bh - band - v, band), v))
    F.append(Face('boil_f', (BX[0], G, BZ[1]), (1, 0, 0), (0, 1, 0), bw, bh, sample=remap(bf, tile)))
    F.append(Face('boil_b', (BX[1], G, BZ[0]), (-1, 0, 0), (0, 1, 0), bw, bh, share='boil_f'))
    bs = by_quad([(0, bh), (bd, bh), (bd, bh - band), (0, bh - band)], [(572, 343), (633, 298), (633, 360), (572, 403)])
    F.append(Face('boil_s', (BX[1], G, BZ[1]), (0, 0, -1), (0, 1, 0), bd, bh, sample=remap(bs, tile)))
    F.append(Face('boil_s2', (BX[0], G, BZ[0]), (0, 0, 1), (0, 1, 0), bd, bh, share='boil_s'))
    # низкий блок: крыша как у конторы, стены как у котельной
    lw, ld, lh = LX[1] - LX[0], LZ[1] - LZ[0], LTOP - G
    F.append(Face('low_r', (LX[0], LTOP, LZ[1]), (1, 0, 0), (0, 0, -1), lw, ld,
                  sample=remap(orf, lambda u, v: (u * ow / lw, v * od / ld))))
    lws = remap(bf, lambda u, v: (np.mod(u, bw), bh - band + np.mod(v, band)))
    F.append(Face('low_s', (LX[0], G, LZ[0]), (0, 0, 1), (0, 1, 0), ld, lh, sample=lws, n=(-1, 0, 0)))
    F.append(Face('low_b', (LX[1], G, LZ[0]), (-1, 0, 0), (0, 1, 0), lw, lh, sample=lws))
    # объёмные детали: цилиндры (труба, кольца, вентиляторы, трубопроводы) и коробки
    c = CH
    F.append(Face('chimney', (0, 0, 0), (1, 0, 0), (0, 1, 0), math.pi * (c['r0'] + c['r1']), c['top'] - LTOP,
                  sample=cyl_tex(310, 380, 20, 34, 26), tex_only=True))
    F.append(Face('vent', (0, 0, 0), (1, 0, 0), (0, 1, 0), 0.14, 0.06, sample=cyl_tex(1252, 278, 226, 19, 19), tex_only=True))
    F.append(Face('pipe', (0, 0, 0), (1, 0, 0), (0, 1, 0), 0.09, 0.12, sample=cyl_tex(176, 460, 360, 14, 14), tex_only=True))
    for nm, q in (('ac', [(150, 480), (206, 490), (206, 514), (150, 504)]), ('duct', [(452, 306), (516, 313), (516, 336), (452, 329)]),
                  ('hood', [(1156, 600), (1198, 598), (1198, 628), (1157, 631)]), ('canopy', [(148, 742), (266, 752), (266, 772), (148, 762)]),
                  ('parapet', [(40, 548), (390, 588), (390, 598), (40, 558)]), ('steps', [(132, 842), (252, 850), (252, 886), (132, 878)])):
        F.append(Face(nm, (0, 0, 0), (1, 0, 0), (0, 1, 0), 0.08, 0.04,
                      sample=by_quad([(0, 0.04), (0.08, 0.04), (0.08, 0), (0, 0)], q), tex_only=True))
    def on(face_uv, face_px, o, eu, ev, px):
        """Точка ref.png -> точка на грани с известными 4 углами."""
        H = homog(face_px, face_uv); q = H @ np.array([px[0], px[1], 1.0]); u, v = q[:2] / q[2]
        return np.array(o) + u * unit(eu) + v * unit(ev)
    def on_cam(o, n, px):
        r, uu, d = camlib.basis(CAM['az'], CAM['el'], CAM.get('roll', 0)); C = d * CAM['dist']
        a = (px[0] - CAM['ox']) / CAM['s']; b = -(px[1] - CAM['oy']) / CAM['s']; v = a * r + b * uu - C
        t = np.dot(np.array(o) - C, n) / np.dot(v, n); return C + t * v
    cyl = CYLS; box_ = BOXES; cyl.clear(); box_.clear()
    ct = c['top']
    cyl += [('chimney', (c['x'], LTOP, c['z']), (c['x'], ct, c['z']), c['r0'], c['r1'], 12, True)]
    for t, w in ((0.5, 0.022), (0.85, 0.02)):              # площадки обслуживания
        y = LTOP + t * (ct - LTOP); r = c['r0'] + t * (c['r1'] - c['r0'])
        cyl.append(('pipe', (c['x'], y, c['z']), (c['x'], y + 0.008, c['z']), r + w, r + w, 12, True))
    cyl.append(('pipe', (c['x'], ct - 0.01, c['z']), (c['x'], ct + 0.012, c['z']), c['r1'] + 0.006, c['r1'] + 0.006, 12, True))
    # вентиляторы: четыре на левом скате (по его 4 углам), два на правом (лучом камеры)
    luv = [(0, 0), (0, sl), (L, sl), (L, 0)]; lpx = [(385, 522), (628, 487), (1172, 180), (925, 208)]
    evl = unit((ur, RIDGE - EAVE, 0)); evr = unit((-ur, RIDGE - EAVE, 0))
    nr = unit(np.cross((0, 0, -1), evr))
    vents = [on(luv, lpx, (HX[0], EAVE, HZ[1]), (0, 0, -1), evl, p) for p in ((1010, 215), (910, 262), (762, 342), (622, 432))]
    vents += [on_cam((HX[1], EAVE, HZ[1]), nr, p) for p in ((1250, 268), (1068, 400))]
    # нарисованные вентиляторы на скатах: их рамки на ref.png; цвет оттуда берём со сдвигом вдоль конька
    VBOX = [(986, 168, 1036, 226), (886, 218, 936, 274), (736, 300, 790, 356), (594, 376, 650, 446),
            (1224, 224, 1280, 290), (1041, 348, 1097, 414)]
    along = unit((1172 - 628, 180 - 487))
    def clean(f):
        def g(u, v):
            q = f(u, v)
            for _ in range(2):
                m = np.zeros(q.shape[:-1], bool)
                sh = np.zeros(q.shape[:-1])
                for x0, y0, x1, y1 in VBOX:      # с тенью ниже рамки; задние (у торца) сдвигаем к воротам, чтобы не уйти с крыши
                    k = (q[..., 0] > x0 - 4) & (q[..., 0] < x1 + 10) & (q[..., 1] > y0) & (q[..., 1] < y1 + 16)
                    m |= k; sh = np.where(k, -1.0 if x0 > 950 else 1.0, sh)
                q = np.where(m[..., None], q + 75 * sh[..., None] * along, q)
            return q
        return g
    for f in F:
        if f.name in ('roof_l', 'roof_r'): f.sample = clean(f.sample)
    for v in vents:
        cyl.append(('vent', v - (0, 0.01, 0), v + (0, 0.035, 0), 0.016, 0.016, 8, False))
        cyl.append(('vent', v + (0, 0.035, 0), v + (0, 0.07, 0), 0.026, 0.02, 10, True))
    # трубопроводы: вдоль стены цеха справа, стояк и подвод к трубе у котельной, переход на крышу цеха
    cyl += [('pipe', (HX[1] + 0.02, G + 0.05, 0.62), (HX[1] + 0.02, G + 0.05, AZ[1] + 0.01), 0.014, 0.014, 8, False),
            ('pipe', (BX[0] - 0.03, G, 0.12), (BX[0] - 0.03, LTOP + 0.06, 0.12), 0.016, 0.016, 8, True),
            ('pipe', (BX[0] - 0.03, LTOP + 0.05, 0.12), (c['x'] - c['r0'], LTOP + 0.05, 0.12), 0.014, 0.014, 8, False),
            ('pipe', (c['x'] + 0.03, LTOP + 0.03, 0.28), (HX[0] + 0.01, LTOP + 0.03, 0.28), 0.013, 0.013, 8, False),
            ('pipe', (BX[1] - 0.02, BTOP - 0.05, 0.08), (HX[0] + 0.01, BTOP - 0.05, 0.08), 0.012, 0.012, 8, False)]
    # коробки на крышах (по углам крыш на картинке), козырёк, крыльцо, парапет конторы
    ouv = [(0, 0), (ow, 0), (ow, od), (0, od)]; opx = [(32, 530), (398, 580), (568, 503), (200, 450)]
    oo, oeu, oev = (OX[0], OTOP, OZ[1]), (1, 0, 0), (0, 0, -1)
    box_ += [('ac', on(ouv, opx, oo, oeu, oev, (180, 506)), (0.07, 0.035, 0.045)),
             ('duct', on(ouv, opx, oo, oeu, oev, (284, 546)), (0.075, 0.028, 0.04))]
    buv = [(0, 0), (bw, 0), (bw, bd), (0, bd)]; bpx = [(289, 328), (572, 343), (633, 298), (350, 283)]
    bo = (BX[0], BTOP, BZ[1])
    box_ += [('duct', on(buv, bpx, bo, (1, 0, 0), (0, 0, -1), (530, 300)), (0.08, 0.03, 0.04)),
             ('duct', on(buv, bpx, bo, (1, 0, 0), (0, 0, -1), (485, 332)), (0.07, 0.026, 0.035))]
    cyl.append(('vent', on(buv, bpx, bo, (1, 0, 0), (0, 0, -1), (430, 302)), on(buv, bpx, bo, (1, 0, 0), (0, 0, -1), (430, 302)) + (0, 0.035, 0), 0.012, 0.012, 8, True))
    auv = [(0, 0), (0, rl), (ad, rl), (ad, 0)]; apx = [(1040, 668), (1180, 710), (1415, 455), (1282, 408)]
    for p in ((1178, 628), (1290, 498)):
        box_.append(('hood', on(auv, apx, (AX[0], AHI, AZ[1]), (0, 0, -1), rev, p), (0.035, 0.03, 0.035)))
    fuv = [(0, oh), (ow, oh), (ow, 0), (0, 0)]; fpx = [(38, 548), (390, 588), (390, 868), (40, 822)]
    dc = on(fuv, fpx, (OX[0], G, OZ[1]), (1, 0, 0), (0, 1, 0), (207, 770))
    box_ += [('canopy', (dc[0], dc[1], OZ[1] + 0.03), (0.15, 0.01, 0.06)),
             ('steps', (dc[0], G, OZ[1] + 0.035), (0.13, 0.03, 0.07))]
    for cx, cz, sx, sz in ((sum(OX) / 2, OZ[1] - 0.004, ow, 0.008), (sum(OX) / 2, OZ[0] + 0.004, ow, 0.008),
                           (OX[0] + 0.004, sum(OZ) / 2, 0.008, od)):
        box_.append(('parapet', (cx, OTOP, cz), (sx, 0.014, sz)))
    # площадка перед воротами: через камеру по земле
    pz, pw = 0.25, GATE_X[1] - GATE_X[0] + 0.24
    ap = by_quad([(0, 0), (pw, 0), (pw, pz), (0, pz)], [(285, 968), (780, 1030), (858, 945), (418, 872)])
    F.append(Face('apron', (GATE_X[0] - 0.12, G + 0.004, HZ[1] + pz), (1, 0, 0), (0, 0, -1), pw, pz, sample=ap, n=(0, 1, 0)))
    return F

def cyl_mesh(p0, p1, r0, r1, n, rect, A, cap):
    """Цилиндр p0 -> p1 (кадр референса); угол 0 смотрит на камеру референса (как развёртка cyl_tex)."""
    p0, p1 = np.array(p0, float), np.array(p1, float); a = unit(p1 - p0)
    az = math.radians(CAM['az']); cd = np.array([math.sin(az), 0, math.cos(az)])
    b1 = cd - np.dot(cd, a) * a
    b1 = unit(b1) if np.linalg.norm(b1) > 1e-3 else unit(np.cross(a, (0, 1, 0)))
    b2 = np.cross(a, b1)
    x0, y0, w, h = rect; V, N, U, T = [], [], [], []
    for i in range(n + 1):
        t = 2 * math.pi * i / n; d = math.cos(t) * b1 + math.sin(t) * b2
        for k, (p, r) in enumerate(((p0, r0), (p1, r1))):
            V.append(p + r * d); N.append(d); U.append([(x0 + w * i / n) / A, 1 - (y0 + (h if k == 0 else 0)) / A])
    for i in range(n):
        q = 2 * i; T += [(q, q + 2, q + 3), (q, q + 3, q + 1)]
    if cap:
        o = len(V); cu = [(x0 + w * 0.25) / A, 1 - (y0 + h * 0.5) / A]
        V.append(p1); N.append(a); U.append(cu)
        for i in range(n + 1):
            t = 2 * math.pi * i / n; V.append(p1 + r1 * (math.cos(t) * b1 + math.sin(t) * b2)); N.append(a); U.append(cu)
        T += [(o, o + 1 + i, o + 2 + i) for i in range(n)]
    # наружу: проверка по первой грани
    out = []
    for tr in T:
        A_, B_, C_ = (V[k] for k in tr); nn = np.cross(B_ - A_, C_ - A_)
        out.append(tr if np.dot(nn, N[tr[0]] + N[tr[1]] + N[tr[2]]) >= 0 else (tr[0], tr[2], tr[1]))
    return V, N, U, out

def box_mesh(c, s, rect, A):
    """Коробка: c центр низа, s размер (x, y, z); все 5 граней с одной текстурой rect."""
    x0, y0, w, h = rect; c = np.array(c, float); hx, hz = s[0] / 2, s[2] / 2
    P = lambda i, j, k: c + np.array([(2 * i - 1) * hx, j * s[1], (2 * k - 1) * hz])
    faces_ = [((P(0, 0, 1), P(1, 0, 1), P(1, 1, 1), P(0, 1, 1)), (0, 0, 1)), ((P(1, 0, 0), P(0, 0, 0), P(0, 1, 0), P(1, 1, 0)), (0, 0, -1)),
              ((P(1, 0, 1), P(1, 0, 0), P(1, 1, 0), P(1, 1, 1)), (1, 0, 0)), ((P(0, 0, 0), P(0, 0, 1), P(0, 1, 1), P(0, 1, 0)), (-1, 0, 0)),
              ((P(0, 1, 1), P(1, 1, 1), P(1, 1, 0), P(0, 1, 0)), (0, 1, 0))]
    uv = [[x0 / A, 1 - (y0 + h) / A], [(x0 + w) / A, 1 - (y0 + h) / A], [(x0 + w) / A, 1 - y0 / A], [x0 / A, 1 - y0 / A]]
    V, N, U, T = [], [], [], []
    for q, n in faces_:
        o = len(V); V += list(q); N += [np.array(n, float)] * 4; U += uv
        a, b, cc = q[0], q[1], q[2]
        T += [(o, o + 1, o + 2), (o, o + 2, o + 3)] if np.dot(np.cross(b - a, cc - a), n) > 0 else [(o, o + 2, o + 1), (o, o + 3, o + 2)]
    return V, N, U, T

def bake():
    """Атлас: прямоугольник на грань (D текселей на единицу), цвет по sample. -> (картинка, rect по имени)."""
    F = faces(); own = [f for f in F if f.share is None]
    size = {f.name: (max(4, int(f.W * D)), max(4, int(f.H * D))) for f in own}
    A = 1024; x = y = rowh = 0; rect = {}
    for f in sorted(own, key=lambda f: -size[f.name][1]):
        w, h = size[f.name]
        if x + w + 4 > A: x, y, rowh = 0, y + rowh + 4, 0
        rect[f.name] = (x + 2, y + 2, w, h); x += w + 4; rowh = max(rowh, h)
    used = y + rowh + 4; assert used <= A, used
    img = np.zeros((A, A, 3), np.float32)
    for f in own:
        x0, y0, w, h = rect[f.name]
        u = (np.arange(-2, w + 2) + 0.5) / w * f.W; v = (h + 2 - np.arange(h + 4) - 0.5) / h * f.H   # v вверх
        uu, vv = np.meshgrid(u, v)
        p = f.sample(uu / f.W, vv / f.H) if f.name in ('chimney', 'vent', 'pipe') else f.sample(uu, vv)
        px = np.clip(p[..., 0] - 0.5, 0, REF.shape[1] - 1.001); py = np.clip(p[..., 1] - 0.5, 0, REF.shape[0] - 1.001)
        ix, iy = px.astype(int), py.astype(int); fx, fy = (px - ix)[..., None], (py - iy)[..., None]
        col = (REF[iy, ix] * (1 - fx) * (1 - fy) + REF[iy, ix + 1] * fx * (1 - fy) + REF[iy + 1, ix] * (1 - fx) * fy
               + REF[iy + 1, ix + 1] * fx * fy)
        img[y0 - 2:y0 + h + 2, x0 - 2:x0 + w + 2] = col
    print('atlas used', used, 'of', A)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)), rect, F, A

def tri_poly(P):
    """Выпуклый многоугольник веером."""
    return [(0, i, i + 1) for i in range(1, len(P) - 1)]

def to_game(P):
    """Кадр референса -> игра: X = z (ворота вперёд), Y = -+x, Z = y; ворота в (GX, GY), земля на Z 0."""
    P = np.asarray(P, float); xg = sum(GATE_X) / 2; sy = -1 if MIRROR else 1
    return np.stack([(P[:, 2] - HZ[1]) * S + GX, sy * (P[:, 0] - xg) * S + GY, (P[:, 1] - G) * S], 1)

def to_game_n(N):
    N = np.asarray(N, float); sy = -1 if MIRROR else 1
    return np.stack([N[:, 2], sy * N[:, 0], N[:, 1]], 1)

def base_mesh(rect, F, A, squash=1.0):
    V, N, U, T = [], [], [], []
    by = {f.name: f for f in F}
    for f in F:
        if f.tex_only: continue
        src = by[f.share] if f.share else f
        x0, y0, w, h = rect[src.name]
        for poly in f.polys:
            o = len(V)
            for (u, v) in poly:
                p = f.o + u * f.eu + v * f.ev; V.append(p); N.append(f.n)
                uu = min(max((f.W - u) if f.flipu else u, 0), f.W); vv = min(max(v, 0), f.H)   # свес крыши - краевой тексель
                U.append([(x0 + uu / f.W * w) / A, 1 - (y0 + h - vv / f.H * h) / A])
            for t in tri_poly(poly):
                a, b, c = (V[o + k] for k in t)
                if np.dot(np.cross(b - a, c - a), f.n) < 0: t = (t[0], t[2], t[1])
                T.append(tuple(o + k for k in t))
    def add(part):
        o = len(V); V.extend(np.array(p, float) for p in part[0]); N.extend(np.array(n, float) for n in part[1]); U.extend(part[2])
        T.extend((a + o, b + o, c + o) for a, b, c in part[3])
    for tex, p0, p1, r0, r1, n, cap in CYLS: add(cyl_mesh(p0, p1, r0, r1, n, rect[tex], A, cap))
    for tex, c, sz in BOXES: add(box_mesh(c, sz, rect[tex], A))
    V = to_game(V); N = to_game_n(N)
    if MIRROR: T = [(a, c, b) for a, b, c in T]
    if squash != 1.0: V[:, 2] *= squash
    return dict(V=V.tolist(), N=N.tolist(), U=U, T=T)

def overlay(out):
    im = Image.open(os.path.join(SRC, 'ref.png')).convert('RGB'); d = ImageDraw.Draw(im)
    for f in faces():
        if f.tex_only: continue
        for poly in f.polys:
            P = np.array([f.o + u * f.eu + v * f.ev for u, v in poly])
            q = camlib.proj(P, CAM); d.line([tuple(x) for x in q] + [tuple(q[0])], fill=(255, 0, 255), width=2)
    im.save(out)

# ---------------------------------------------------------------- W3D (ворота, кости - как в R8.9)
def quad(p, uv):
    p = np.array(p, float); n = np.cross(p[1] - p[0], p[2] - p[0]); n /= np.linalg.norm(n)
    return dict(V=p.tolist(), N=[n.tolist()] * 4, U=[list(x) for x in uv], T=[(0, 1, 2), (0, 2, 3)])

def merge(parts):
    V, N, U, T = [], [], [], []
    for p in parts:
        o = len(V); V += p['V']; N += p['N']; U += p['U']; T += [(a + o, b + o, c + o) for a, b, c in p['T']]
    return dict(V=V, N=N, U=U, T=T)

def box(c, s, front_uv=None, uv=(0.99, 0.5), back_uv=None):
    x0, y0, z0 = (c[i] - s[i] / 2 for i in range(3)); x1, y1, z1 = (c[i] + s[i] / 2 for i in range(3))
    P = lambda a, b, d: (x1 if a else x0, y1 if b else y0, z1 if d else z0)
    one = [uv] * 4
    return merge([quad([P(0, 1, 0), P(0, 0, 0), P(0, 0, 1), P(0, 1, 1)], back_uv or one),
                  quad([P(1, 0, 0), P(1, 1, 0), P(1, 1, 1), P(1, 0, 1)], front_uv or one),
                  quad([P(0, 0, 0), P(1, 0, 0), P(1, 0, 1), P(0, 0, 1)], one),
                  quad([P(1, 1, 0), P(0, 1, 0), P(0, 1, 1), P(1, 1, 1)], one),
                  quad([P(0, 0, 1), P(1, 0, 1), P(1, 1, 1), P(0, 1, 1)], one)])

def gate_texture():
    """Створки с референса, выпрямленные в 248x256; правая колонка 8 px тёмная (внутренность цеха)."""
    ref = Image.open(os.path.join(SRC, 'ref.png')).convert('RGB')
    (tlx, tly), (trx, try_), (brx, bry), (blx, bly) = GATE_PX
    g = ref.transform((248, 256), Image.QUAD, (tlx, tly, blx, bly, brx, bry, trx, try_), Image.BICUBIC)
    im = Image.new('RGB', (256, 256), (12, 12, 10)); im.paste(g, (0, 0)); return im

def textures(base):
    a = np.asarray(base, np.float32); rng = np.random.default_rng(3)
    from PIL import ImageFilter
    soot = Image.fromarray((rng.random((64, 64)) * 255).astype(np.uint8)).resize(base.size, Image.BICUBIC).filter(ImageFilter.GaussianBlur(24))
    s = np.asarray(soot, np.float32)[..., None] / 255
    dmg = a * (0.62 - 0.25 * np.clip(s * 2 - 0.6, 0, 1))
    rub = a * 0.42 + np.array([6, 5, 4])
    out = {'': base, '_D': Image.fromarray(np.clip(dmg, 0, 255).astype(np.uint8)), '_B': Image.fromarray(np.clip(rub, 0, 255).astype(np.uint8))}
    g = gate_texture(); out['_G'] = g
    out['_GD'] = Image.fromarray(np.clip(np.asarray(g, np.float32) * 0.6, 0, 255).astype(np.uint8))
    return out

def model(state, rect, F, A):
    E = state == 'E'; zs = 0.25 if E else 1.0
    base = base_mesh(rect, F, A, zs)
    V = np.array(base['V'])
    GW = (GATE_X[1] - GATE_X[0]) * S; GH = (GATE_Y[1] - GATE_Y[0]) * S
    meshes = [('BASE', 'ROOTTRANSFORM', 'solid', base)]
    door = [box((GX - 4.0, GY, GH * zs / 2), (8.0, GW - 0.2, GH * zs))]       # тёмный проём внутри цеха
    if not E: meshes.append(('HOUSECOLOR01', 'ROOTTRANSFORM', 'house', box((GX + 0.3, GY, GH + 2.6), (0.4, GW * 0.9, 1.6))))
    bones = [dict(name='ROOTTRANSFORM', parent=-1, pos=[0, 0, 0]),
             dict(name='DOOR01', parent=0, pos=[GX + 0.3, GY - GW / 2, 0.0]),
             dict(name='DOOR02', parent=0, pos=[GX + 0.3, GY + GW / 2, 0.0])]
    if not E:
        for k, sg, u0, u1 in ((1, 1, 0.0, 0.5), (2, -1, 0.5, 1.0)):
            uv = [(u0 * 0.969, 0.0), (u1 * 0.969, 0.0), (u1 * 0.969, 1.0), (u0 * 0.969, 1.0)]
            back = [uv[1], uv[0], uv[3], uv[2]]
            meshes.append((f'DOOR{k}', f'DOOR0{k}', 'door', box((0.25, sg * GW / 4, GH / 2), (0.5, GW / 2, GH),
                                                                front_uv=uv, back_uv=back, uv=(0.01, 0.5))))
    meshes.append(('INSIDE', 'ROOTTRANSFORM', 'door', merge(door)))
    def top(x, y, r=5.0):
        d = np.hypot(V[:, 0] - x, V[:, 1] - y); z = V[:, 2][d < r]
        return [x, y, float(z.max()) if len(z) else 10.0]
    cg = to_game([[CH['x'], CH['top'], CH['z']]])[0]
    bones += [dict(name='SMOKE01', parent=0, pos=[float(cg[0]), float(cg[1]), float(cg[2] * zs)]),
              dict(name='SMOKE02', parent=0, pos=top(GX - 35, GY)), dict(name='SMOKE03', parent=0, pos=top(GX - 15, GY + 40)),
              dict(name='SMOKE04', parent=0, pos=top(GX - 70, GY)), dict(name='FIRE01', parent=0, pos=top(GX - 15, GY + 3)),
              dict(name='FIRE02', parent=0, pos=top(GX - 60, GY - 5))]
    anim = None
    if not E:
        nf = 30
        ease = [0.5 - 0.5 * math.cos(math.pi * f / (nf - 1)) for f in range(nf)]
        anim = (nf, 30, {'DOOR01': [(0, 0, -math.sin(math.pi / 4 * e), math.cos(math.pi / 4 * e)) for e in ease],
                         'DOOR02': [(0, 0, math.sin(math.pi / 4 * e), math.cos(math.pi / 4 * e)) for e in ease]})
    return bones, meshes, anim

def build(ret):
    sys.path.insert(0, os.path.dirname(HERE))
    from bld import dds
    import w3d
    cru = w3d.parse(open(os.path.join(ret, 'avcrusader.W3D'), 'rb').read())
    retail = dict(solid=(cru, 'CHASSIS'), house=(cru, 'HOUSECOLOR01'), door=(cru, 'CHASSIS'))
    os.makedirs(OUT, exist_ok=True); name = 'RUWARFACT'
    atlas, rect, F, A = bake()
    for suf, im in textures(atlas).items():
        im.save(os.path.join(OUT, f'{name}{suf}.png')); dds(im, os.path.join(ART, 'Textures', f'{name}{suf}.dds'))
    for st, tsuf, gsuf in (('', '', '_G'), ('D', '_D', '_GD'), ('E', '_B', '_GD')):
        v = name + (f'_{st}' if st else '')
        bones, meshes, anim = model(st, rect, F, A)
        ms = [dict(name=nm, bone=bn, kind=k, verts=[list(map(float, x)) for x in p['V']], normals=[list(map(float, x)) for x in p['N']],
                   uvs=[list(map(float, x)) for x in p['U']], tris=[list(map(int, x)) for x in p['T']]) for nm, bn, k, p in meshes]
        mj = os.path.join(OUT, f'{v}.json'); json.dump(dict(name=v, bones=bones, meshes=ms), open(mj, 'w'))
        out = os.path.join(ART, 'W3D', f'{v}.W3D')
        w3d.build(mj, out, v, dict(solid=f'{name}{tsuf}.tga', house='Housecolor.tga', door=f'{name}{gsuf}.tga'),
                  {m['name'] for m in ms}, retail, anim=anim)
        b = open(out, 'rb').read(); assert w3d.ser(w3d.parse(b)) == b
        print(v, 'tris', sum(len(m['tris']) for m in ms), 'anim', anim and anim[0], len(b), 'bytes')

if __name__ == '__main__':
    if sys.argv[1] == 'overlay': overlay(sys.argv[2])
    elif sys.argv[1] == 'atlas': bake()[0].save(sys.argv[2])
    else: build(sys.argv[1])
