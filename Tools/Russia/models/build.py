"""Модель гусеничной машины из parts.json (contours.py) и atlas.json (atlas.py) -> out/mesh.json для w3d.py.
Корпус и башня: пересечение вытянутых силуэтов (сбоку, сверху, спереди). UV - проекция на атлас
по нормали грани. Отдельно: ствол (тело вращения), катки на костях WHEEL_*, гусеницы TREADSL/R.

  blender -b --factory-startup --python Tools/Russia/models/build.py -- Tools/Russia/models/t72b3m
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Vector
from mathutils.geometry import convex_hull_2d

D = os.path.abspath(sys.argv[sys.argv.index('--') + 1])
P = json.load(open(os.path.join(D, 'parts.json')))
A = json.load(open(os.path.join(D, 'out', 'atlas.json')))
NAME, SC = P['name'], P['game_scale']
N = A['size']

bpy.ops.wm.read_factory_settings(use_empty=True)
col = bpy.context.scene.collection

def obj_from_bm(bm, name):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o); return o

def prism(polys, plane, lo, hi, name):
    """polys в осях плоскости plane ('xz', 'xy', 'yz'), вытянуты по третьей оси от lo до hi."""
    bm = bmesh.new()
    ax = {'xz': (0, 2, 1), 'xy': (0, 1, 2), 'yz': (1, 2, 0)}[plane]
    for poly in polys:
        def v(a, b, c):
            p = [0, 0, 0]; p[ax[0]], p[ax[1]], p[ax[2]] = a, b, c; return bm.verts.new(p)
        bot = [v(a, b, lo) for a, b in poly]; top = [v(a, b, hi) for a, b in poly]
        bm.faces.new(bot); bm.faces.new(top[::-1])
        n = len(poly)
        for i in range(n):
            j = (i + 1) % n; bm.faces.new([bot[i], bot[j], top[j], top[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name)

def intersect(a, others, name):
    for o in others:
        m = a.modifiers.new('b', 'BOOLEAN'); m.operation = 'INTERSECT'; m.solver = 'EXACT'; m.object = o
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(a.evaluated_get(dg)); me.name = name
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    for x in [a] + others: bpy.data.objects.remove(x)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(2), verts=bm.verts, edges=bm.edges)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    return o

front = lambda nm: prism(P['front'], 'yz', -7, 8, nm)
hull = intersect(prism(P['side_hull'], 'xz', -3, 3, 'h1'), [prism(P['top_hull'], 'xy', -1, 6, 'h2'), front('h3')], 'HULL')
tur = intersect(prism(P['side_turret'], 'xz', -3, 3, 't1'), [prism(P['top_turret'], 'xy', -1, 6, 't2'), front('t3')], 'TURRET')

# ствол: тело вращения по профилю (X, r), 10 граней
prof = P['barrel']['profile']; zc = P['barrel']['z']
keep = [prof[0]]
for x, r in prof[1:-1]:
    if abs(r - keep[-1][1]) > 0.012 or x - keep[-1][0] > 0.6: keep.append([x, r])
keep.append(prof[-1])
bm = bmesh.new(); SEG = 10; rings = []
for x, r in keep:
    rings.append([bm.verts.new((x, r * math.cos(2 * math.pi * k / SEG), zc + r * math.sin(2 * math.pi * k / SEG))) for k in range(SEG)])
for a, b in zip(rings, rings[1:]):
    for k in range(SEG):
        bm.faces.new([a[k], a[(k + 1) % SEG], b[(k + 1) % SEG], b[k]])
bm.faces.new(rings[-1]); bm.faces.new(rings[0][::-1])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bmesh.ops.triangulate(bm, faces=bm.faces)
barrel = obj_from_bm(bm, 'BARREL')

# катки: 6 опорных + ленивец + ведущее колесо на сторону
TO, TW = P['track_out'], P['track_width']
wheel_defs = [w for w in P['wheels']] + [P['idler'], P['sprocket']]
wheels = []
def disc(x, z, r, y0, y1, name, seg=16):
    bm = bmesh.new()
    a = [bm.verts.new((x + r * math.cos(2 * math.pi * k / seg), y0, z + r * math.sin(2 * math.pi * k / seg))) for k in range(seg)]
    b = [bm.verts.new((x + r * math.cos(2 * math.pi * k / seg), y1, z + r * math.sin(2 * math.pi * k / seg))) for k in range(seg)]
    bm.faces.new(a); bm.faces.new(b[::-1])
    for k in range(seg): bm.faces.new([a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bmesh.ops.triangulate(bm, faces=bm.faces)
    return obj_from_bm(bm, name)
for side, sgn in (('L', 1), ('R', -1)):
    for i, (x, z, r) in enumerate(wheel_defs):
        y0, y1 = sgn * (TO - 0.16), sgn * (TO + 0.012)
        wheels.append((f'WHEEL_{side}{i + 1:02d}', (x, 0, z), disc(x, z, r, min(y0, y1), max(y0, y1), f'W{side}{i}')))

# гусеница: выпуклая оболочка катков (+толщина), лента с наружным боком; U вдоль ленты
T = 0.07
pts = []
for x, z, r in wheel_defs:
    pts += [(x + (r + T) * math.cos(a), z + (r + T) * math.sin(a)) for a in [2 * math.pi * k / 24 for k in range(24)]]
hidx = convex_hull_2d([Vector(p) for p in pts]); loop = [Vector(pts[i]) for i in hidx]
cen = sum(loop, Vector((0, 0))) / len(loop)
inner = [p + (cen - p).normalized() * T for p in loop]
tile = A['track']['tile_m']
def tread(sgn, name):
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
    yo, yi = sgn * (TO + 0.02), sgn * (TO + 0.02 - TW)
    so = [bm.verts.new((p.x, yo, p.y)) for p in loop]; si = [bm.verts.new((p.x, yo, p.y)) for p in inner]
    sb = [bm.verts.new((p.x, yi, p.y)) for p in loop]
    n = len(loop); s = [0.0]
    for i in range(n): s.append(s[-1] + (loop[(i + 1) % n] - loop[i]).length)
    for i in range(n):
        j = (i + 1) % n; u0, u1 = s[i] / tile, s[i + 1] / tile
        f = bm.faces.new([so[i], so[j], si[j], si[i]])  # бок ленты
        for l, (u, v) in zip(f.loops, [(u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)]): l[uv].uv = (u, v)
        f = bm.faces.new([sb[i], sb[j], so[j], so[i]])  # беговая поверхность
        for l, (u, v) in zip(f.loops, [(u0, 1.0), (u1, 1.0), (u1, 0.0), (u0, 0.0)]): l[uv].uv = (u, v)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bmesh.ops.triangulate(bm, faces=bm.faces)
    return obj_from_bm(bm, name)
treads = [tread(1, 'TREADSL'), tread(-1, 'TREADSR')]

# ---- UV-проекция на атлас
R, Cr, PR = A['rects'], A['crop'], P['proj']
def to_uv(view, a, b):
    p = PR[view]; px = p['u'][0] * a + p['u'][1]; py = p['v'][0] * b + p['v'][1]
    x0, y0, x1, y1 = Cr[view]; rx, ry, rw, rh = R[view]
    ax = rx + (px - x0) * rw / (x1 - x0); ay = ry + (py - y0) * rh / (y1 - y0)
    return (ax / N, ay / N)  # v сверху вниз, как у D3D
HOLE = ((N - 40) / N, (N - 40) / N)  # тёмный угол атласа: погон под башней
plan = P['top_turret'][0]
def in_plan(x, y):
    c = False; n = len(plan)
    for i in range(n):
        (x1, y1), (x2, y2) = plan[i], plan[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c
def project(o, force=None, hole=False):
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name='UVMap')
    uvl = me.uv_layers.active.data
    for f in me.polygons:
        n = f.normal; c = f.center
        if force: view = force
        elif n.z > 0.45 or n.z < -0.6: view = 'top'
        elif abs(n.y) * 1.2 >= abs(n.x): view = 'side'
        else: view = 'front' if n.x > 0 else 'rear'
        if hole and view == 'top' and n.z > 0.9 and abs(c.z - P['turret_z']) < 0.03 and in_plan(c.x, c.y):
            for li in f.loop_indices: uvl[li].uv = HOLE
            continue
        for li in f.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            a, b = {'top': (v.x, v.y), 'side': (v.x, v.z), 'front': (v.y, v.z), 'rear': (v.y, v.z)}[view]
            uvl[li].uv = to_uv(view, a, b)
project(hull); project(tur); project(barrel)
for _, _, w in wheels: project(w, force='side')

# ---- кости (метры, мир), без поворотов
TZ = P['turret_z']; trn = P['trunnion']; mx = keep[-1][0]
B = [('ROOTTRANSFORM', -1, (0, 0, 0)), ('CHASSIS', 0, (0, 0, 0)), ('TURRET01', 1, (0, 0, TZ)),
     ('BARREL01', 2, (trn[0], 0, zc)), ('MUZZLE01', 3, (mx, 0, zc)), ('MUZZLEFX01', 3, (mx - 0.02, 0, zc))]
rear_x = min(p.x for p in loop)
B += [('TREADFX01', 1, (rear_x, -TO + TW / 2, 0.1)), ('TREADFX02', 1, (rear_x, TO - TW / 2, 0.1)),
      ('SMOKE01', 2, (-1.0, 0.6, TZ + 0.5)), ('SMOKE02', 1, (-2.4, 0.5, 1.7)), ('SMOKE03', 1, (2.5, -0.4, 1.5))]
for nm, pos, _ in wheels: B.append((nm, 1, pos))
bi = {b[0]: i for i, b in enumerate(B)}

def export(o, bone, tex, kind='solid'):
    """Треугольники с нормалями по углам (сглаживание до 30°), вершины в осях кости, игровые единицы."""
    me = o.data; me.set_sharp_from_angle(angle=math.radians(30))
    me.calc_loop_triangles(); cn = me.corner_normals; uvl = me.uv_layers.active.data
    bw = Vector(B[bi[bone]][2]); key = {}; V, Nn, U, Tr = [], [], [], []
    for t in me.loop_triangles:
        tri = []
        for li in t.loops:
            p = (me.vertices[me.loops[li].vertex_index].co - bw) * SC; n = cn[li].vector; u = uvl[li].uv
            k = (round(p.x, 4), round(p.y, 4), round(p.z, 4), round(n.x, 3), round(n.y, 3), round(n.z, 3), round(u.x, 5), round(u.y, 5))
            if k not in key:
                key[k] = len(V); V.append(list(p)); Nn.append(list(n)); U.append([u.x, u.y])
            tri.append(key[k])
        Tr.append(tri)
    return dict(name=o.name, bone=bone, tex=tex, kind=kind, verts=V, normals=Nn, uvs=U, tris=Tr)

def housecolor(name, bone, x0, x1, z0, z1, target):
    """Табличка цвета команды на борту target, с двух сторон, на 1 см снаружи."""
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
    for sgn in (1, -1):
        dg = bpy.context.evaluated_depsgraph_get()
        hit = target.ray_cast(Vector(((x0 + x1) / 2, sgn * 4, (z0 + z1) / 2)), Vector((0, -sgn, 0)), depsgraph=dg)
        y = hit[1].y + sgn * 0.01 if hit[0] else sgn * 1.8
        vs = [bm.verts.new((x, y, z)) for x, z in ((x0, z0), (x1, z0), (x1, z1), (x0, z1))]
        f = bm.faces.new(vs if sgn < 0 else vs[::-1])
        for l, c in zip(f.loops, ((0, 1), (1, 1), (1, 0), (0, 0))): l[uv].uv = c
    bmesh.ops.triangulate(bm, faces=bm.faces)
    return export(obj_from_bm(bm, name), bone, 'Housecolor.tga', 'house')

tex, trk = f'{NAME}.tga', f'{NAME}Trk.tga'
meshes = [export(hull, 'CHASSIS', tex), export(tur, 'TURRET01', tex), export(barrel, 'BARREL01', tex)]
meshes += [export(w, nm, tex) for nm, _, w in wheels]
meshes += [export(t, 'CHASSIS', trk, 'treads') for t in treads]
# погон без башни (только у подбитого корпуса): тёмный круг на палубе
bm = bmesh.new(); uvr = bm.loops.layers.uv.new('UVMap')
rv = [bm.verts.new((1.15 * math.cos(2 * math.pi * k / 20), 1.15 * math.sin(2 * math.pi * k / 20), TZ + 0.004)) for k in range(20)]
f = bm.faces.new(rv)
for l in f.loops: l[uvr].uv = HOLE
bmesh.ops.triangulate(bm, faces=bm.faces)
meshes.append(export(obj_from_bm(bm, 'RING'), 'CHASSIS', tex))
meshes += [housecolor('HOUSECOLOR01', 'TURRET01', -1.05, -0.35, TZ + 0.18, TZ + 0.42, tur),
           housecolor('HOUSECOLOR02', 'CHASSIS', -2.6, -1.4, 1.25, 1.55, hull)]
for m in meshes:
    if m['name'] == 'HULL': m['name'] = 'CHASSIS'
    if m['name'] == 'TURRET': m['name'] = 'TURRET01'
    if m['name'] == 'BARREL': m['name'] = 'BARREL01'
    if m['name'].startswith('W') and m['bone'].startswith('WHEEL_'): m['name'] = m['bone']
bones = [dict(name=n, parent=p, pos=[c * SC for c in pos]) for n, p, pos in B]
json.dump(dict(name=NAME, bones=bones, meshes=meshes), open(os.path.join(D, 'out', 'mesh.json'), 'w'))
print('TRIS', {m['name']: len(m['tris']) for m in meshes}, 'total', sum(len(m['tris']) for m in meshes))

# ---- превью: камера как в RTS
img = bpy.data.images.load(os.path.join(D, 'out', tex.replace('.tga', '.dds'))); timg = bpy.data.images.load(os.path.join(D, 'out', trk.replace('.tga', '.dds')))
def mat(im, nm):
    m = bpy.data.materials.new(nm); m.use_nodes = True; nt = m.node_tree
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = im; t.interpolation = 'Linear'
    bsdf = nt.nodes['Principled BSDF']; nt.links.new(t.outputs[0], bsdf.inputs['Base Color']); bsdf.inputs['Roughness'].default_value = 0.8
    return m
ma, mt = mat(img, 'atlas'), mat(timg, 'trk')
for o in col.objects:
    if o.type == 'MESH':
        o.data.materials.clear(); o.data.materials.append(mt if o.name.startswith('TREADS') else ma)
        if o.data.uv_layers:  # Blender: v снизу вверх
            for d in o.data.uv_layers.active.data:
                if not o.name.startswith('TREADS'): d.uv.y = 1 - d.uv.y
sc = bpy.context.scene; sc.render.resolution_x, sc.render.resolution_y = 1200, 800
w = bpy.data.worlds.new('w'); sc.world = w; w.color = (0.5, 0.5, 0.5)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3.5; sun.rotation_euler = (0.7, 0.2, 2.2); col.objects.link(sun)
for ang, el, nm in ((40, 35, 'a'), (220, 35, 'b'), (95, 12, 'c')):
    cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); col.objects.link(cam)
    a, e = math.radians(ang), math.radians(el); r = 13
    cam.location = Vector((r * math.cos(a) * math.cos(e), r * math.sin(a) * math.cos(e), r * math.sin(e) + 1))
    cam.rotation_euler = (Vector((0.5, 0, 1.0)) - cam.location).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    sc.render.filepath = os.path.join(D, 'out', f'preview_{nm}.png'); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(D, 'out', f'{NAME}.blend'))
