# /// script
# dependencies = ["numpy", "pillow"]
# ///
"""Снаряды России из простых фигур (тела вращения, плоские рули, бруски, диски винтов) -> W3D.
Без референсов: снаряд в игре мелкий и быстрый, хватает силуэта и цвета. Единицы игровые, X вперёд, Z вверх.
Текстура RUProj.tga - сетка однотонных образцов цвета; RUProjRotor.tga - размытый винт с прозрачностью.

  uv run Tools/Russia/models/proj.py <retail W3D dir: avcrusader.W3D>      # модели и текстуры в Data/Art
  blender -b --factory-startup --python Tools/Russia/models/proj.py -- preview   # out/proj_preview.png
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'proj_out')
ART = os.path.join(HERE, '../../../GeneralsMD/Code/Data/Art')

# образцы цвета: сетка 4x4 по 32 px
PAL = dict(olive=(86, 96, 58), dkolive=(58, 64, 40), grey=(150, 154, 150), white=(212, 212, 204),
           black=(30, 30, 30), carbon=(56, 58, 60), tan=(150, 128, 88), red=(140, 40, 34),
           blgrey=(118, 128, 132), metal=(120, 120, 116), glass=(20, 34, 44), green=(70, 88, 62))
NAMES = list(PAL)
def swatch_uv(c):
    i = NAMES.index(c); return ((i % 4) * 32 + 16) / 128, ((i // 4) * 32 + 16) / 128

# ---------- геометрия: список (verts, normals, uvs, tris) на часть
def rot_x(p, a):
    x, y, z = p; c, s = math.cos(a), math.sin(a); return (x, y * c - z * s, y * s + z * c)
def rot_y(p, a):
    x, y, z = p; c, s = math.cos(a), math.sin(a); return (x * c + z * s, y, -x * s + z * c)

def lathe(prof, col, seg=8):
    """Тело вращения вокруг X по профилю [(x, r)], нормали сглаженные по кругу, торцы плоские."""
    u = swatch_uv(col); V, N, T = [], [], []
    rings = []
    for x, r in prof:
        ring = []
        for k in range(seg):
            a = 2 * math.pi * (k + 0.5) / seg
            ring.append(len(V)); V.append((x, r * math.cos(a), r * math.sin(a))); N.append((0, math.cos(a), math.sin(a)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(seg):
            k2 = (k + 1) % seg; T += [(a[k], b[k], b[k2]), (a[k], b[k2], a[k2])]
    for (x, r), ring, sgn in ((prof[0], rings[0], -1), (prof[-1], rings[-1], 1)):
        if r <= 1e-4: continue
        c = len(V); V.append((x, 0, 0)); N.append((sgn, 0, 0)); cap = []
        for i in ring: cap.append(len(V)); V.append(V[i]); N.append((sgn, 0, 0))
        for k in range(seg):
            k2 = (k + 1) % seg
            T.append((c, cap[k2], cap[k]) if sgn < 0 else (c, cap[k], cap[k2]))
    return dict(V=V, N=N, U=[u] * len(V), T=T)

def flat(faces, col):
    """Плоские грани (списки точек, обход против часовой снаружи) с плоскими нормалями."""
    u = swatch_uv(col); V, N, T = [], [], []
    for f in faces:
        a, b, c = f[0], f[1], f[2]
        e1 = [b[i] - a[i] for i in range(3)]; e2 = [c[i] - a[i] for i in range(3)]
        n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        l = math.sqrt(sum(x * x for x in n)) or 1; n = tuple(x / l for x in n)
        i0 = len(V)
        for p in f: V.append(tuple(p)); N.append(n)
        for k in range(1, len(f) - 1): T.append((i0, i0 + k, i0 + k + 1))
    return dict(V=V, N=N, U=[u] * len(V), T=T)

def slab(poly, t, col, roll=0.0, r0=0.0):
    """Плоский руль: контур [(x, h)] (h - вылет от оси), толщина t; лежит в плоскости XY, повёрнут на roll вокруг X."""
    top = [(x, r0 + h, t / 2) for x, h in poly]; bot = [(x, r0 + h, -t / 2) for x, h in poly]
    faces = [top, bot[::-1]]
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n; faces.append([bot[i], bot[j], top[j], top[i]])
    p = flat(faces, col)
    # контур задан как (x, вылет); вылет кладём на ось Y до поворота: (x, h, t) -> rot_x
    p['V'] = [rot_x(v, roll) for v in p['V']]; p['N'] = [rot_x(v, roll) for v in p['N']]
    return fix_winding(p)

def box(c, s, col):
    x0, y0, z0 = (c[i] - s[i] / 2 for i in range(3)); x1, y1, z1 = (c[i] + s[i] / 2 for i in range(3))
    P = lambda a, b, d: (x1 if a else x0, y1 if b else y0, z1 if d else z0)
    faces = [[P(0, 0, 0), P(0, 1, 0), P(1, 1, 0), P(1, 0, 0)], [P(0, 0, 1), P(1, 0, 1), P(1, 1, 1), P(0, 1, 1)],
             [P(0, 0, 0), P(1, 0, 0), P(1, 0, 1), P(0, 0, 1)], [P(0, 1, 0), P(0, 1, 1), P(1, 1, 1), P(1, 1, 0)],
             [P(0, 0, 0), P(0, 0, 1), P(0, 1, 1), P(0, 1, 0)], [P(1, 0, 0), P(1, 1, 0), P(1, 1, 1), P(1, 0, 1)]]
    return fix_winding(flat(faces, col))

def fix_winding(p):
    """Разворачивает треугольники, у которых геометрическая нормаль смотрит против заданной."""
    V, N = p['V'], p['N']; T = []
    for a, b, c in p['T']:
        e1 = [V[b][i] - V[a][i] for i in range(3)]; e2 = [V[c][i] - V[a][i] for i in range(3)]
        n = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        T.append((a, c, b) if sum(n[i] * N[a][i] for i in range(3)) < 0 else (a, b, c))
    p['T'] = T; return p

def disc(c, r, axis, seg=12):
    """Диск винта (две стороны), UV на всю текстуру винта. axis 'z' - горизонтальный, 'x' - толкающий."""
    V, N, U, T = [], [], [], []
    for sgn in (1, -1):
        i0 = len(V); n = (0, 0, sgn) if axis == 'z' else (sgn, 0, 0)
        V.append(tuple(c)); N.append(n); U.append((0.5, 0.5))
        for k in range(seg):
            a = 2 * math.pi * k / seg; ca, sa = math.cos(a), math.sin(a)
            V.append((c[0] + r * ca, c[1] + r * sa, c[2]) if axis == 'z' else (c[0], c[1] + r * ca, c[2] + r * sa))
            N.append(n); U.append((0.5 + 0.5 * ca, 0.5 + 0.5 * sa))
        for k in range(seg):
            k2 = (k + 1) % seg; T.append((i0, i0 + 1 + k, i0 + 1 + k2))
    return fix_winding(dict(V=V, N=N, U=U, T=T))

def move(p, d=(0, 0, 0), ry=0.0):
    p['V'] = [tuple(a + b for a, b in zip(rot_y(v, ry), d)) for v in p['V']]; p['N'] = [rot_y(n, ry) for n in p['N']]
    return p

def merge(parts):
    V, N, U, T = [], [], [], []
    for p in parts:
        o = len(V); V += p['V']; N += p['N']; U += p['U']; T += [(a + o, b + o, c + o) for a, b, c in p['T']]
    return dict(V=V, N=N, U=U, T=T)

X4 = [math.pi / 4 + k * math.pi / 2 for k in range(4)]   # крестообразно (X)
P4 = [k * math.pi / 2 for k in range(4)]                  # прямо (+)

def ogive(x0, x1, r, n=4, tip=0.0):
    """Оживальный нос от x0 (полный радиус) до x1 (острие)."""
    return [(x0 + (x1 - x0) * i / n, max(tip, r * math.cos(math.pi / 2 * i / n) ** 0.7)) for i in range(n + 1)]

# ---------- модели: имя W3D -> (тело, винты или None, хвост для ENGINE01)
def fpv():
    """FPV-квадрокоптер с гранатой ПГ-7 под брюхом, наклонён носом вниз как в полёте."""
    b = [box((0, 0, 0), (2.4, 1.0, 0.45), 'carbon'), box((0.1, 0, 0.42), (1.4, 0.8, 0.4), 'black'),
         box((1.2, 0, 0.1), (0.3, 0.35, 0.3), 'glass')]
    for sx in (1, -1):
        for sy in (1, -1):
            a = math.atan2(sy, sx)
            arm = box((0, 0, 0), (2.3, 0.28, 0.16), 'carbon')
            arm['V'] = [(v[0] * math.cos(a) - v[1] * math.sin(a) + 1.15 * math.cos(a), v[0] * math.sin(a) + v[1] * math.cos(a) + 1.15 * math.sin(a), v[2]) for v in arm['V']]
            arm['N'] = [(n[0] * math.cos(a) - n[1] * math.sin(a), n[0] * math.sin(a) + n[1] * math.cos(a), n[2]) for n in arm['N']]
            b.append(arm)
            m = lathe([(-0.2, 0.26), (0.2, 0.26)], 'metal', 8)
            m['V'] = [(v[2] + 1.6 * sx, v[1] + 1.6 * sy, v[0] + 0.15) for v in m['V']]; m['N'] = [(n[2], n[1], n[0]) for n in m['N']]
            b.append(m)
    g = lathe([(-1.6, 0.0), (-1.6, 0.18), (0.4, 0.18), (0.6, 0.42), (1.6, 0.42), (2.4, 0.12), (2.7, 0.05)], 'olive', 8)
    b.append(move(g, (0.2, 0, -0.5)))
    rot = [disc((1.6 * sx, 1.6 * sy, 0.4), 1.25, 'z') for sx in (1, -1) for sy in (1, -1)]
    tilt = math.radians(30)
    return merge([move(p, ry=tilt) for p in b]), merge([move(p, ry=tilt) for p in rot]), -1.4

def lancet():
    """"Ланцет-3": цилиндр, две крестообразные плоскости (спереди и сзади), толкающий винт."""
    body = lathe([(-5.0, 0.0), (-5.0, 0.3), (-4.2, 0.55)] + ogive(3.2, 5.0, 0.55), 'blgrey', 10)
    nose = lathe([(4.6, 0.3), (5.05, 0.05)], 'black', 8)
    p = [body, nose]
    for a in X4:
        p.append(slab([(1.0, 0.4), (2.8, 0.4), (2.6, 2.4), (1.4, 2.4)], 0.08, 'blgrey', a))
        p.append(slab([(-4.0, 0.4), (-2.4, 0.4), (-2.6, 2.3), (-3.8, 2.3)], 0.08, 'blgrey', a))
    return merge(p), disc((-5.15, 0, 0), 1.0, 'x'), -5.0

def kornet():
    """9М133 "Корнет": цилиндр с тупым носом, два руля спереди, четыре складных крыла сзади."""
    body = lathe([(-3.5, 0.0), (-3.5, 0.3), (-3.2, 0.4), (2.8, 0.4), (3.3, 0.3), (3.5, 0.1)], 'olive', 10)
    p = [body, lathe([(3.3, 0.12), (3.7, 0.12), (3.75, 0.0)], 'dkolive', 6)]
    for a in X4: p.append(slab([(-3.3, 0.35), (-2.5, 0.35), (-2.6, 1.15), (-3.1, 1.15)], 0.06, 'dkolive', a))
    for a in (0, math.pi): p.append(slab([(2.0, 0.35), (2.5, 0.35), (2.4, 0.8), (2.1, 0.8)], 0.06, 'dkolive', a))
    return merge(p), None, -3.5

def grad():
    """Ракета 9М22 (122 мм, "Торнадо-Г"): длинная, оживальный нос, четыре хвостовых пера."""
    p = [lathe([(-8.0, 0.0), (-8.0, 0.32), (-7.6, 0.4), (4.5, 0.4)], 'dkolive', 10),
         lathe(ogive(4.5, 8.0, 0.4), 'olive', 10), lathe([(4.3, 0.41), (4.7, 0.41)], 'white', 10)]
    for a in X4: p.append(slab([(-8.0, 0.3), (-6.6, 0.3), (-6.8, 1.2), (-7.9, 1.2)], 0.06, 'dkolive', a))
    return merge(p), None, -8.0

def buk():
    """9М317 "Бук": светлый корпус, тёмный обтекатель, длинные крылья малого размаха и рули сзади."""
    p = [lathe([(-5.0, 0.0), (-5.0, 0.4), (-4.7, 0.5), (2.6, 0.5)], 'white', 10),
         lathe(ogive(2.6, 5.0, 0.5), 'dkolive', 10)]
    for a in X4:
        p.append(slab([(-2.6, 0.45), (1.6, 0.45), (0.8, 1.2), (-2.2, 1.2)], 0.07, 'white', a))
        p.append(slab([(-5.0, 0.45), (-3.9, 0.45), (-4.1, 1.5), (-4.9, 1.5)], 0.07, 'green', a))
    return merge(p), None, -5.0

def tor():
    """9М338 "Тор": белый корпус, острый нос, малые рули спереди, большие крылья сзади."""
    p = [lathe([(-4.0, 0.0), (-4.0, 0.38), (2.0, 0.45)], 'white', 10), lathe(ogive(2.0, 4.0, 0.45), 'grey', 10)]
    for a in P4:
        p.append(slab([(1.6, 0.4), (2.3, 0.4), (2.2, 0.85), (1.8, 0.85)], 0.06, 'grey', a))
        p.append(slab([(-4.0, 0.36), (-2.9, 0.36), (-3.1, 1.4), (-3.9, 1.4)], 0.06, 'white', a))
    return merge(p), None, -4.0

MODELS = dict(RUFPV=fpv, RULANCET=lancet, RUKORNET=kornet, RUGRAD=grad, RUBUKM=buk, RUTORM=tor)

def textures():
    import numpy as np
    from PIL import Image
    rng = np.random.default_rng(1)
    a = np.zeros((128, 128, 3), np.float32)
    for i, c in enumerate(NAMES):
        y, x = (i // 4) * 32, (i % 4) * 32; a[y:y + 32, x:x + 32] = PAL[c]
    a += rng.normal(0, 4, a.shape)
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(ART, 'Textures', 'RUProj.tga'))
    # винт: тёмный диск, прозрачнее к центру и краю, две смазанные лопасти
    n = 64; yy, xx = np.mgrid[0:n, 0:n] - (n - 1) / 2; r = np.hypot(xx, yy) / (n / 2); ang = np.arctan2(yy, xx)
    al = np.where(r < 1, 0.22 + 0.28 * np.cos(2 * ang) ** 8 * (r > 0.15), 0) * (r < 1)
    img = np.zeros((n, n, 4), np.uint8); img[..., :3] = 40; img[..., 3] = (np.clip(al, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(img, 'RGBA').save(os.path.join(ART, 'Textures', 'RUProjRotor.tga'))

def build(ret):
    sys.path.insert(0, os.path.dirname(HERE)); import w3d
    rd = lambda f: w3d.parse(open(f, 'rb').read())
    cru = rd(os.path.join(ret, 'avcrusader.W3D'))
    rotor_tpl = rd(os.path.join(ART, 'W3D', 'TRKARGU.W3D'))  # только шейдер с прозрачностью (Reforged), текстура своя
    retail = dict(solid=(cru, 'CHASSIS'), rotor=(rotor_tpl, 'ROTORS'))
    os.makedirs(OUT, exist_ok=True); textures()
    for name, fn in MODELS.items():
        body, rotors, tail = fn()
        meshes = []
        for nm, p, kind in (('BODY', body, 'solid'), ('ROTORS', rotors, 'rotor')):
            if p: meshes.append(dict(name=nm, bone='MISSILE01', kind=kind, verts=[list(v) for v in p['V']],
                                     normals=[list(n) for n in p['N']], uvs=[list(u) for u in p['U']], tris=[list(t) for t in p['T']]))
        bones = [dict(name='ROOTTRANSFORM', parent=-1, pos=[0, 0, 0]), dict(name='MISSILE01', parent=0, pos=[0, 0, 0]),
                 dict(name='ENGINE01', parent=1, pos=[tail, 0, 0])]
        mj = os.path.join(OUT, f'{name}.json'); json.dump(dict(name=name, bones=bones, meshes=meshes), open(mj, 'w'))
        out = os.path.join(ART, 'W3D', f'{name}.W3D')
        w3d.build(mj, out, name, dict(solid='RUProj.tga', rotor='RUProjRotor.tga'), {m['name'] for m in meshes}, retail)
        b = open(out, 'rb').read(); assert w3d.ser(w3d.parse(b)) == b
        print(name, 'tris', sum(len(m['tris']) for m in meshes), len(b), 'bytes')

def preview():
    import bpy
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True); col = bpy.context.scene.collection
    def mat(path, nm, alpha=False):
        m = bpy.data.materials.new(nm); m.use_nodes = True; nt = m.node_tree
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(path); t.interpolation = 'Closest'
        bs = nt.nodes['Principled BSDF']; nt.links.new(t.outputs[0], bs.inputs['Base Color']); bs.inputs['Roughness'].default_value = 0.7
        if alpha: nt.links.new(t.outputs[1], bs.inputs['Alpha'])
        return m
    ms = mat(os.path.join(ART, 'Textures', 'RUProj.tga'), 's'); mr = mat(os.path.join(ART, 'Textures', 'RUProjRotor.tga'), 'r', True)
    for i, name in enumerate(MODELS):
        M = json.load(open(os.path.join(OUT, f'{name}.json')))
        for m in M['meshes']:
            me = bpy.data.meshes.new(name + m['name']); me.from_pydata(m['verts'], [], m['tris'])
            uv = me.uv_layers.new(name='UVMap')
            for poly in me.polygons:
                for li in poly.loop_indices:
                    u = m['uvs'][me.loops[li].vertex_index]; uv.data[li].uv = (u[0], 1 - u[1])
            me.materials.append(mr if m['kind'] == 'rotor' else ms)
            o = bpy.data.objects.new(name + m['name'], me); col.objects.link(o)
            o.location = ((i % 3) * 20 - 20, -(i // 3) * 14 + 7, 0)
    sc = bpy.context.scene; sc.render.resolution_x, sc.render.resolution_y = 1500, 900
    w = bpy.data.worlds.new('w'); sc.world = w; w.color = (0.45, 0.45, 0.45)
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3.5; sun.rotation_euler = (0.6, 0.2, 2.0); col.objects.link(sun)
    cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); col.objects.link(cam); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 66
    cam.location = Vector((25, -30, 35)); cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    sc.render.filepath = os.path.join(OUT, 'proj_preview.png'); bpy.ops.render.render(write_still=True)

if __name__ == '__main__':
    if 'preview' in sys.argv: preview()
    else: build(sys.argv[1])
