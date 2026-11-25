# /// script
# dependencies = ["numpy", "pillow"]
# ///
"""Здания России из простых фигур (бруски, многогранные столбы) с процедурным атласом 512 -> W3D с анимацией.
Размеры в игровых единицах, X вперёд, Z вверх; площадь застройки берётся у исходного здания (Geometry в INI не меняем).
Варианты: <N> целое, <N>_D повреждённое (та же геометрия, тёмная текстура), <N>_E разбитое (без анимации).

  uv run Tools/Russia/models/bld.py <retail W3D dir: avcrusader.W3D>        # модели и текстуры в Data/Art
  blender -b --factory-startup --python Tools/Russia/models/bld.py -- preview  # bld_out/<N>_preview.png
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'bld_out')
ART = os.path.join(HERE, '../../../GeneralsMD/Code/Data/Art')
A = 512
# области атласа в пикселях (x0, y0, x1, y1)
REG = dict(concrete=(0, 0, 256, 256), cabin=(256, 0, 384, 128), olive=(384, 0, 512, 128),
           array=(256, 128, 512, 256), back=(0, 256, 128, 384), dark=(128, 256, 256, 384),
           grille=(256, 256, 384, 384), roof=(384, 256, 512, 384), mast=(0, 384, 128, 512),
           curb=(128, 384, 256, 512), door=(256, 384, 384, 512), house=(384, 384, 512, 512))

def ruv(reg, s, t):
    # v в W3D снизу вверх, как в Blender (у Т-72 так же): строка y картинки -> v = 1 - y / A
    x0, y0, x1, y1 = REG[reg]; return ((x0 + 1 + s * (x1 - x0 - 2)) / A, 1 - (y0 + 1 + t * (y1 - y0 - 2)) / A)

def quad(p, reg):
    """Четырёхугольник p[0..3] (против часовой снаружи), область reg растянута на грань."""
    a, b, c = p[0], p[1], p[2]
    e1 = [b[i] - a[i] for i in range(3)]; e2 = [c[i] - a[i] for i in range(3)]
    n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
    l = math.sqrt(sum(x * x for x in n)) or 1; n = tuple(x / l for x in n)
    st = [(0, 1), (1, 1), (1, 0), (0, 0)]
    return dict(V=[tuple(v) for v in p], N=[n] * 4, U=[ruv(reg, *x) for x in st], T=[(0, 1, 2), (0, 2, 3)])

def box(c, s, side, top=None, front=None, bottom=False):
    """Брусок: c центр, s размеры; side - боковые грани, top - верх, front - грань +X (дверь, решётка антенны)."""
    x0, y0, z0 = (c[i] - s[i] / 2 for i in range(3)); x1, y1, z1 = (c[i] + s[i] / 2 for i in range(3))
    P = lambda a, b, d: (x1 if a else x0, y1 if b else y0, z1 if d else z0)
    f = [quad([P(0, 1, 0), P(0, 0, 0), P(0, 0, 1), P(0, 1, 1)], side),          # -X
         quad([P(1, 0, 0), P(1, 1, 0), P(1, 1, 1), P(1, 0, 1)], front or side),  # +X
         quad([P(0, 0, 0), P(1, 0, 0), P(1, 0, 1), P(0, 0, 1)], side),          # -Y
         quad([P(1, 1, 0), P(0, 1, 0), P(0, 1, 1), P(1, 1, 1)], side),          # +Y
         quad([P(0, 0, 1), P(1, 0, 1), P(1, 1, 1), P(0, 1, 1)], top or side)]   # верх
    if bottom: f.append(quad([P(0, 1, 0), P(1, 1, 0), P(1, 0, 0), P(0, 0, 0)], side))
    return merge(f)

def post(c, prof, reg, seg=8, cap=True):
    """Многогранный столб вокруг вертикали через c: prof [(z, r)], грани плоские, крышка сверху (cap=False - кольцо)."""
    f = []
    for (z0, r0), (z1, r1) in zip(prof, prof[1:]):
        for k in range(seg):
            a0, a1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
            p = lambda a, z, r: (c[0] + r * math.cos(a), c[1] + r * math.sin(a), z)
            f.append(quad([p(a0, z0, r0), p(a1, z0, r0), p(a1, z1, r1), p(a0, z1, r1)], reg))
    if not cap: return merge(f)
    z, r = prof[-1]
    cap = [(c[0] + r * math.cos(2 * math.pi * k / seg), c[1] + r * math.sin(2 * math.pi * k / seg), z) for k in range(seg)]
    m = merge(f); i0 = len(m['V'])
    m['V'] += cap; m['N'] += [(0, 0, 1)] * seg; m['U'] += [ruv(reg, 0.5 + 0.5 * math.cos(2 * math.pi * k / seg), 0.5 + 0.5 * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
    m['T'] += [(i0, i0 + k, i0 + k + 1) for k in range(1, seg - 1)]
    return m

def twosided(m):
    """Добавляет изнанку (кольцо видно и изнутри)."""
    o = len(m['V'])
    return dict(V=m['V'] * 2, N=m['N'] + [tuple(-x for x in n) for n in m['N']], U=m['U'] * 2,
                T=m['T'] + [(a + o, c + o, b + o) for a, b, c in m['T']])

def merge(parts):
    V, N, U, T = [], [], [], []
    for p in parts:
        o = len(V); V += p['V']; N += p['N']; U += p['U']; T += [(a + o, b + o, c + o) for a, b, c in p['T']]
    return dict(V=V, N=N, U=U, T=T)

def xform(p, rx=0.0, ry=0.0, rz=0.0, d=(0, 0, 0)):
    """Поворот вокруг X, потом Y, потом Z (радианы), затем сдвиг."""
    def r(v):
        x, y, z = v
        y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
        x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
        return (x, y, z)
    return dict(V=[tuple(a + b for a, b in zip(r(v), d)) for v in p['V']], N=[r(n) for n in p['N']], U=p['U'], T=p['T'])

# ---------------------------------------------------------------- РЛС "Зоопарк-1М"
def zoopark(state):
    """Площадка 14x14 (у исходной башни 12x12), кунг с дверью, генератор, мачта, поворотная фазированная решётка.
    Решётка на кости ANTENNA01 (z 12) и крутится вокруг вертикали; в разбитом виде завалена вперёд и стоит."""
    HZ = 12.0
    base = [box((0, 0, 0.3), (14, 14, 0.6), 'curb', 'concrete'),
            box((-3.6, 3.0, 2.85), (5.4, 7.0, 4.5), 'cabin', 'roof', front='door'),
            box((-3.6, 3.0, 5.3), (1.2, 1.2, 0.4), 'dark'),                       # вентилятор на крыше
            box((3.8, -3.9, 1.8), (4.4, 3.2, 2.4), 'grille', 'olive'),            # дизель-генератор
            box((5.6, -3.9, 3.4), (0.5, 0.5, 1.6), 'dark'),                       # выхлоп
            box((0, 0, 1.1), (4.0, 4.0, 1.0), 'olive', 'dark'),                   # основание мачты
            post((0, 0), [(1.6, 1.5), (HZ - 1.0, 0.9)], 'mast'),
            box((-0.8, -5.2, 1.0), (6.0, 0.4, 0.8), 'dark')]                      # кабельный короб
    house = [box((-3.6, 3.0, 4.6), (5.5, 7.1, 0.5), 'house'), box((3.8, -3.9, 2.45), (4.5, 3.3, 0.3), 'house')]
    # решётка: вращающийся стол, вилка, полотно 12x8 с наклоном назад 15 градусов, полоса запросчика сверху
    tilt = math.radians(15)
    panel = xform(box((0, 0, 0), (0.7, 12.0, 8.0), 'back', 'dark', front='array', bottom=True), ry=-tilt, d=(0.9, 0, 4.6))
    ant = [post((0, 0), [(-1.0, 1.9), (0.0, 1.9)], 'dark', 12),
           box((0.0, 2.2, 0.9), (0.8, 0.6, 1.8), 'olive'), box((0.0, -2.2, 0.9), (0.8, 0.6, 1.8), 'olive'),
           box((-0.9, 0, 1.6), (1.8, 4.8, 0.5), 'olive'),
           xform(box((0, 0, 0), (1.6, 0.4, 0.4), 'dark'), ry=-math.radians(55), d=(-0.3, 3.4, 2.6)),
           xform(box((0, 0, 0), (1.6, 0.4, 0.4), 'dark'), ry=-math.radians(55), d=(-0.3, -3.4, 2.6)),
           panel,
           xform(box((0, 0, 0), (0.6, 12.4, 0.7), 'dark'), ry=-tilt, d=(0.9 - 4.35 * math.sin(tilt), 0, 4.6 + 4.35 * math.cos(tilt)))]
    ant = merge(ant)
    if state == 'E':
        # сорвана с мачты и лежит на земле рядом: край у мачты, нижняя точка на земле
        ant = xform(ant, ry=math.radians(80), rx=math.radians(8), rz=math.radians(25))
        mx, mz = min(v[0] for v in ant['V']), min(v[2] for v in ant['V'])
        ant = xform(ant, d=(2.0 - mx, 0, 0.2 - HZ - mz))
    bones = [dict(name='ROOTTRANSFORM', parent=-1, pos=[0, 0, 0]),
             dict(name='ANTENNA01', parent=0, pos=[0, 0, HZ]),
             dict(name='SMOKE01', parent=0, pos=[-3.6, 3.0, 5.5]),
             dict(name='SMOKE02', parent=0, pos=[5.6, -3.9, 4.3]),
             dict(name='FLAME01', parent=0, pos=[3.8, -3.9, 3.2]),
             dict(name='SPARK01', parent=0, pos=[0, 0, HZ - 1])]
    meshes = [('BASE', 'ROOTTRANSFORM', 'solid', merge(base)), ('ANTENNA', 'ANTENNA01', 'solid', ant),
              ('HOUSECOLOR01', 'ROOTTRANSFORM', 'house', merge(house))]
    anim = None
    if state != 'E':
        n = 240 if state == '' else 360   # оборот за 8 с, у повреждённой за 12 с
        anim = (n, 30, {'ANTENNA01': [(0, 0, math.sin(math.pi * f / n), math.cos(math.pi * f / n)) for f in range(n)]})
    return bones, meshes, anim

# ---------------------------------------------------------------- Газотурбинная электростанция
def powerplant(state):
    """Площадка 52x66 (у китайской станции 54x68): машинный зал вдоль Y с воротами на +X, фильтры воздухозабора
    на -X, две выхлопные трубы сзади, трансформаторы и блок воздушного охлаждения (АВО) с тремя вентиляторами.
    Вентиляторы на костях FAN01-03 крутятся вокруг вертикали; в разбитом виде зал просел, труба лежит, лопастей нет."""
    E = state == 'E'
    hh = 7.0 if E else 14.0                                                      # высота зала
    # площадка уходит в грунт на 4: на склоне земля не проступает сквозь бетон
    base = [box((0, 0, -1.5), (52, 66, 5.0), 'curb', 'concrete'),
            box((-6, 4, 0.6 + hh / 2), (26, 40, hh), 'cabin', 'dark' if E else 'roof', front='door'),
            box((-22, 4, 5.6), (6, 30, 10), 'grille', 'olive'),                  # фильтры воздухозабора
            box((-6, -18, 4.6), (4, 4, 8), 'olive', 'dark'), box((-6, -21, 4.6), (12, 3, 3), 'olive', 'dark'),  # газоходы к трубам
            box((17, 10, 2.6), (14, 30, 4.0), 'grille', 'back'),                 # корпус АВО
            box((17, -22, 3.1), (7, 5, 5), 'grille', 'olive'), box((17, -14.5, 3.1), (7, 5, 5), 'grille', 'olive'),  # трансформаторы
            box((-20, -27, 2.6), (8, 8, 4), 'cabin', 'roof', front='door'),      # пункт управления
            box((4, -27, 0.9), (14, 0.6, 0.6), 'dark'), box((10, -18, 0.9), (0.6, 16, 0.6), 'dark')]  # кабельные лотки
    for y in (-22, -14.5):                                                       # изоляторы на трансформаторах
        base += [post((x, y + d), [(5.6, 0.35), (7.4, 0.25)], 'dark', 6) for x in (15.5, 18.5) for d in (-1, 1)]
    for k, x in enumerate((-12, 0)):                                             # выхлопные трубы
        tall = [(0.6, 2.8), (30.0, 2.2), (31.0, 2.4)]
        if E and k == 1: tall = [(0.6, 2.8), (9.0, 2.6)]                         # обломанная
        base.append(post((x, -24), tall, 'array', 10))
    if E:                                                                        # упавшая верхушка второй трубы
        base.append(xform(post((0, 0), [(0, 2.6), (20, 2.2)], 'array', 10), rx=math.radians(84), rz=math.radians(-35), d=(4, -22, 2.4)))
        base.append(box((-6, 4, 1.4), (22, 30, 1.6), 'dark'))                   # завал внутри зала
    # обечайки вентиляторов (кольца без крышки) и ступицы на корпусе АВО
    for y in (0, 10, 20):
        base.append(twosided(post((17, y), [(4.6, 4.6), (6.0, 4.6)], 'olive', 12, cap=False)))
    house = [box((-6, 4, hh - 0.9), (26.3, 40.3, 1.2), 'house'), box((-22, 4, 10.8), (6.1, 30.1, 0.4), 'house')]
    # всё размечено трубами к -Y; разворот на 180 градусов ставит трубы назад (к +Y), АВО налево, чтобы
    # в обычном ракурсе трубы не закрывали зал
    bones = [dict(name='ROOTTRANSFORM', parent=-1, pos=[0, 0, 0])]
    meshes = [('BASE', 'ROOTTRANSFORM', 'solid', xform(merge(base), rz=math.pi)), ('HOUSECOLOR01', 'ROOTTRANSFORM', 'house', xform(merge(house), rz=math.pi))]
    fans = []
    for k, y in enumerate((0, 10, 20)):
        b = f'FAN0{k + 1}'; bones.append(dict(name=b, parent=0, pos=[17, y, 5.2])); fans.append(b)
        if E and k != 1: continue                                                # в руинах осталась одна крыльчатка
        blades = [post((0, 0), [(-0.2, 0.7), (0.5, 0.5)], 'dark', 8)]
        blades += [xform(box((2.3, 0, 0), (3.6, 1.1, 0.12), 'curb'), rx=math.radians(18), rz=math.pi / 2 * j) for j in range(4)]
        fan = merge(blades)
        if E: fan = xform(fan, rx=math.radians(25), d=(0, 0, -0.6))
        meshes.append((f'FAN{k + 1}', b, 'solid', fan))
    bones += [dict(name='SMOKE01', parent=0, pos=[-12, -24, 31.5]), dict(name='SMOKE02', parent=0, pos=[0, -24, 9.5 if E else 31.5]),
              dict(name='SMOKE03', parent=0, pos=[-10, 10, hh + 0.5]), dict(name='SMOKE04', parent=0, pos=[17, 10, 5]),
              dict(name='FIRE01', parent=0, pos=[-2, 0, hh + 0.5]), dict(name='FIRE02', parent=0, pos=[17, -22, 5.8])]
    bones += [dict(name=f'SPARK0{i + 1}', parent=0, pos=[x, y, 7.6]) for i, (x, y) in enumerate(((15.5, -23), (18.5, -21), (15.5, -15.5), (18.5, -13.5)))]
    for b in bones: b['pos'] = [-b['pos'][0], -b['pos'][1], b['pos'][2]]
    anim = None
    if not E:
        n = 45 if state == '' else 90   # оборот за 1.5 с, у повреждённой за 3 с; фазы вентиляторов разные
        anim = (n, 30, {b: [(0, 0, math.sin(math.pi * f / n + 0.4 * k), math.cos(math.pi * f / n + 0.4 * k)) for f in range(n)] for k, b in enumerate(fans)})
    return bones, meshes, anim

MODELS = dict(RUZOOPARK=zoopark, RUPOWER=powerplant)   # RUWARFACT: models/wf3.py

# ---------------------------------------------------------------- текстуры
def textures(name):
    import numpy as np
    from PIL import Image
    rng = np.random.default_rng(7)
    def noise(h, w, sc, amp):
        g = rng.normal(0, 1, (h // sc + 2, w // sc + 2)).astype(np.float32)
        im = np.array(Image.fromarray(g).resize((w + 2 * sc, h + 2 * sc), Image.BICUBIC))[sc:sc + h, sc:sc + w]
        return im * amp
    a = np.zeros((A, A, 3), np.float32)
    def fill(reg, col, grain=6, blot=8):
        x0, y0, x1, y1 = REG[reg]; h, w = y1 - y0, x1 - x0
        t = np.array(col, np.float32)[None, None, :] + rng.normal(0, grain, (h, w, 1)) + noise(h, w, 16, blot)[..., None]
        a[y0:y1, x0:x1] = t; return a[y0:y1, x0:x1]
    olive, dkol = (92, 98, 62), (66, 72, 46)
    c = fill('concrete', (150, 148, 140), 7, 10)            # плиты 2x2 со швами и потёками
    c[::128, :] -= 45; c[:, ::128] -= 45; c[1::128, :] -= 25; c[:, 1::128] -= 25
    c -= np.clip(noise(256, 256, 40, 30), 0, None)[..., None]
    k = fill('cabin', olive)                                # кунг: вертикальные рёбра
    k[:, 4::10] -= 22; k[:, 5::10] += 10
    fill('olive', olive)
    d = fill('door', olive)                                 # дверь кунга по центру торца
    d[:, 4::10] -= 22; d[:, 5::10] += 10
    d[30:118, 40:88] = np.array(dkol) + rng.normal(0, 4, (88, 48, 1)); d[30:118, 40:42] = 40; d[30:118, 86:88] = 40; d[30:32, 40:88] = 40
    d[70:76, 78:84] = 160; d[38:58, 50:78] = (60, 74, 80)   # ручка, окошко
    r = fill('array', (74, 82, 70), 3, 4)                   # решётка: излучатели 8x8 px
    r[::8, :] = (44, 48, 42); r[:, ::8] = (44, 48, 42)
    r[3::8, 3::8] = (126, 132, 120)
    b = fill('back', dkol)                                  # обратная сторона: рёбра жёсткости
    b[::16, :] -= 30; b[1::16, :] += 12; b[:, ::32] -= 25
    fill('dark', (60, 62, 60))
    g = fill('grille', olive)                               # жалюзи генератора
    g[20:108, 12:116] = (50, 54, 40); g[22:108:6, 12:116] = (96, 102, 66)
    f = fill('roof', (104, 110, 74)); f[::32, :] -= 20
    m = fill('mast', olive); m[::24, :] -= 25; m[12::24, 6::16] += 40
    fill('curb', (130, 128, 120), 7, 10)
    fill('house', (200, 200, 200), 2, 0)
    if name == 'RUPOWER':
        t = fill('array', (118, 116, 110), 5, 8); t[::21, :] -= 30; t[1::21, :] += 12   # труба: сталь, кольца швов
        t[:12, :] = (40, 38, 36)                                                          # копоть на срезе
        d = fill('door', olive); d[:, 4::10] -= 22; d[:, 5::10] += 10                   # ворота зала: рулонные
        d[24:128, 20:108] = (84, 88, 80); d[26:128:5, 20:108] -= 22; d[24:26, 18:110] = 40
    clean = np.clip(a, 0, 255)
    soot = np.clip(noise(A, A, 48, 1.0), 0, None)
    dam = np.clip(clean * (1 - 0.55 * np.clip(soot, 0, 1)[..., None]) * 0.85, 0, 255)
    soot2 = np.clip(noise(A, A, 32, 1.4) + 0.6, 0, 1)
    burnt = np.clip(clean * 0.35 * (1 - 0.7 * soot2[..., None]) + np.array([18, 12, 8]) * soot2[..., None], 0, 255)
    return {n: Image.fromarray(x.astype(np.uint8)) for n, x in (('', clean), ('_D', dam), ('_B', burnt))}

def dds(im, path):
    """DDS DXT1 с мипмапами (как в atlas.py)."""
    import io, struct
    from PIL import Image
    levels, w = [], im.copy()
    while True:
        b = io.BytesIO(); w.save(b, 'DDS', pixel_format='DXT1'); d = b.getvalue()
        hdr = bytearray(d[:128]) if not levels else hdr; levels.append(d[128:])
        if min(w.size) <= 4: break
        w = w.resize((max(4, w.width // 2), max(4, w.height // 2)), Image.LANCZOS)
    struct.pack_into('<I', hdr, 8, struct.unpack_from('<I', hdr, 8)[0] | 0x20000)
    struct.pack_into('<I', hdr, 28, len(levels))
    struct.pack_into('<I', hdr, 108, struct.unpack_from('<I', hdr, 108)[0] | 0x400008)
    open(path, 'wb').write(bytes(hdr) + b''.join(levels))

def build(ret):
    sys.path.insert(0, os.path.dirname(HERE)); import w3d
    cru = w3d.parse(open(os.path.join(ret, 'avcrusader.W3D'), 'rb').read())
    retail = dict(solid=(cru, 'CHASSIS'), house=(cru, 'HOUSECOLOR01'))
    os.makedirs(OUT, exist_ok=True)
    for name, fn in MODELS.items():
        if len(sys.argv) > 2 and name not in sys.argv[2:]: continue
        tex = textures(name)
        for suf, im in tex.items():
            im.save(os.path.join(OUT, f'{name}{suf}.png')); dds(im, os.path.join(ART, 'Textures', f'{name}{suf}.dds'))
        for st, tsuf in (('', ''), ('D', '_D'), ('E', '_B')):
            v = name + (f'_{st}' if st else '')
            bones, meshes, anim = fn(st)
            ms = [dict(name=nm, bone=bn, kind=k, verts=[list(x) for x in p['V']], normals=[list(x) for x in p['N']],
                       uvs=[list(x) for x in p['U']], tris=[list(x) for x in p['T']]) for nm, bn, k, p in meshes]
            mj = os.path.join(OUT, f'{v}.json'); json.dump(dict(name=v, bones=bones, meshes=ms), open(mj, 'w'))
            out = os.path.join(ART, 'W3D', f'{v}.W3D')
            w3d.build(mj, out, v, dict(solid=f'{name}{tsuf}.tga', house='Housecolor.tga'), {m['name'] for m in ms}, retail, anim=anim)
            b = open(out, 'rb').read(); assert w3d.ser(w3d.parse(b)) == b
            print(v, 'tris', sum(len(m['tris']) for m in ms), 'anim frames', anim and anim[0], len(b), 'bytes')

def preview():
    """Три состояния рядом и целое здание с антенной, повёрнутой на 90 градусов (проверка кости и анимации)."""
    import bpy
    from mathutils import Vector, Quaternion
    bpy.ops.wm.read_factory_settings(use_empty=True); col = bpy.context.scene.collection
    mats = {}
    def mat(path):
        if path in mats: return mats[path]
        m = bpy.data.materials.new(path); m.use_nodes = True; nt = m.node_tree
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path)
        bs = nt.nodes['Principled BSDF']; nt.links.new(t.outputs[0], bs.inputs['Base Color']); bs.inputs['Roughness'].default_value = 0.8
        mats[path] = m; return m
    name = sys.argv[sys.argv.index('--') + 2] if len(sys.argv) > sys.argv.index('--') + 2 else 'RUZOOPARK'
    M0 = json.load(open(os.path.join(OUT, f'{name}.json')))
    k = max(1.0, max(abs(x[1]) for x in M0['meshes'][0]['verts']) / 7.5)   # масштаб сцены по размеру здания
    for i, (v, tex, turn) in enumerate(((name, '', 0), (name, '', 90), (name + '_D', '_D', 0), (name + '_E', '_B', 0))):
        M = json.load(open(os.path.join(OUT, f'{v}.json'))); bp = {b['name']: b['pos'] for b in M['bones']}
        for m in M['meshes']:
            me = bpy.data.meshes.new(v + m['name']); me.from_pydata(m['verts'], [], m['tris'])
            uv = me.uv_layers.new(name='UVMap')
            for poly in me.polygons:
                for li in poly.loop_indices:
                    u = m['uvs'][me.loops[li].vertex_index]; uv.data[li].uv = (u[0], u[1])
            me.materials.append(mat(os.path.join(OUT, f'{name}{tex}.png') if m['kind'] == 'solid' else os.path.join(OUT, f'{name}.png')))
            o = bpy.data.objects.new(v + m['name'], me); col.objects.link(o)
            p = Vector(bp[m['bone']]); o.location = p + Vector((0, (i * 22 - 33) * k, 0))
            if (m['bone'] == 'ANTENNA01' or m['bone'].startswith('FAN')) and turn: o.rotation_euler = (0, 0, math.radians(turn))
            if m['bone'].startswith('DOOR') and turn: o.rotation_euler = (0, 0, math.radians(-turn if m['bone'] == 'DOOR01' else turn))
    sc = bpy.context.scene; sc.render.resolution_x, sc.render.resolution_y = 1600, 800
    w = bpy.data.worlds.new('w'); sc.world = w; w.color = (0.5, 0.5, 0.5)
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3.5; sun.rotation_euler = (0.7, 0.3, 2.4); col.objects.link(sun)
    cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); col.objects.link(cam); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 100 * k
    cam.location = Vector((60, -20, 50)) * k; cam.rotation_euler = (Vector((0, 0, 6 * k)) - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    sc.render.filepath = os.path.join(OUT, f'{name}_preview.png'); bpy.ops.render.render(write_still=True)

if __name__ == '__main__':
    if 'preview' in sys.argv: preview()
    else: build(sys.argv[1])
