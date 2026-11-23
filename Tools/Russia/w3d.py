# W3D: read chunk tree, dump summary, write back.
# Usage: python3 -I w3d.py dump <file.w3d>
#        python3 -I w3d.py check <file.w3d>...   (byte round trip)
import struct, sys

SUB = 0x80000000  # high bit of size: chunk holds sub-chunks

def parse(b, o=0, end=None):
    end = len(b) if end is None else end
    out = []
    while o < end:
        t, s = struct.unpack_from('<II', b, o); o += 8
        n = s & 0x7FFFFFFF
        if s & SUB:
            out.append([t, parse(b, o, o + n)])
        else:
            out.append([t, b[o:o + n]])
        o += n
    return out

def ser(chunks):
    r = bytearray()
    for t, d in chunks:
        if isinstance(d, list):
            body = ser(d); r += struct.pack('<II', t, len(body) | SUB) + body
        else:
            r += struct.pack('<II', t, len(d)) + d
    return bytes(r)

def cstr(b):
    return b.split(b'\0', 1)[0].decode('latin1')

def find(chunks, t):
    return [d for tt, d in chunks if tt == t]

def one(chunks, t):
    r = find(chunks, t); return r[0] if r else None

def mesh_info(m):
    h = one(m, 0x1F)
    name, cont = cstr(h[8:24]), cstr(h[24:40])
    ntri, nv = struct.unpack_from('<II', h, 40)
    attrs = struct.unpack_from('<I', h, 4)[0]
    mn = struct.unpack_from('<3f', h, 76); mx = struct.unpack_from('<3f', h, 88)
    tex = []
    for tx in find(m, 0x30) and one(m, 0x30) or []:
        tex.append(cstr(one(tx[1], 0x32)))
    passes = len(find(m, 0x38))
    vm = []
    for v in (one(m, 0x2A) or []):
        a0 = one(v[1], 0x2E); vm.append(cstr(a0) if a0 else '')
    return dict(name=f'{cont}.{name}', tris=ntri, verts=nv, attrs=hex(attrs), min=mn, max=mx,
                tex=tex, passes=passes, mapper=vm, chunks=[hex(t) for t, _ in m])

def dump(path):
    ch = parse(open(path, 'rb').read())
    for t, d in ch:
        if t == 0x00:
            i = mesh_info(d)
            print('MESH', i['name'], 'tris', i['tris'], 'verts', i['verts'], 'attr', i['attrs'], 'tex', i['tex'],
                  'passes', i['passes'], 'mapper', i['mapper'],
                  'min', tuple(round(x, 2) for x in i['min']), 'max', tuple(round(x, 2) for x in i['max']))
        elif t == 0x100:
            h = one(d, 0x101); print('HIER', cstr(h[4:20]), 'pivots', struct.unpack_from('<I', h, 20)[0])
            pv = one(d, 0x102)
            for k in range(len(pv) // 60):
                nm = cstr(pv[k*60:k*60+16]); par, = struct.unpack_from('<I', pv, k*60+16)
                tr = struct.unpack_from('<3f', pv, k*60+20); q = struct.unpack_from('<4f', pv, k*60+44)
                print(f'  PIV {k:2} {nm:16} parent {par if par != 0xFFFFFFFF else -1:3} t {tuple(round(x,2) for x in tr)} q {tuple(round(x,3) for x in q)}')
        elif t == 0x700:
            h = one(d, 0x701); print('HLOD', cstr(h[8:24]), 'hier', cstr(h[24:40]))
            for tt, arr in d:
                if tt in (0x702, 0x706):
                    for t2, so in arr:
                        if t2 == 0x704:
                            bi, = struct.unpack_from('<I', so); print('  SUB', 'bone', bi, cstr(so[4:36]), '(aggregate)' if tt == 0x706 else '')
        elif t == 0x740:
            print('BOX', cstr(d[8:40]), 'center', struct.unpack_from('<3f', d, 52), 'extent', struct.unpack_from('<3f', d, 64))
        else:
            print('CHUNK', hex(t), len(d) if not isinstance(d, list) else 'sub')

# ---------------------------------------------------------------- запись модели
def name16(s, n=16):
    b = s.encode('latin1')[:n - 1]; return b + b'\0' * (n - len(b))

def mesh_by_name(chunks, name):
    for t, d in chunks:
        if t == 0x00 and cstr(one(d, 0x1F)[8:24]) == name: return d
    raise KeyError(name)

def make_mesh(tpl, container, m, tex):
    """Меш из шаблона retail: материалы, шейдер и флаги шаблона, геометрия и UV из m."""
    import math
    h = bytearray(one(tpl, 0x1F))
    V, Nn, U, T = m['verts'], m['normals'], m['uvs'], m['tris']
    h[8:24] = name16(m['name']); h[24:40] = name16(container)
    struct.pack_into('<II', h, 40, len(T), len(V))
    mn = [min(v[i] for v in V) for i in range(3)]; mx = [max(v[i] for v in V) for i in range(3)]
    c = [(a + b) / 2 for a, b in zip(mn, mx)]; r = max(math.dist(c, v) for v in V)
    struct.pack_into('<3f3f3ff', h, 76, *mn, *mx, *c, r)
    tri_attr = struct.unpack_from('<I', one(tpl, 0x20), 12)[0]
    tris = bytearray()
    for a, b, cc in T:
        pa, pb, pc = V[a], V[b], V[cc]
        e1 = [pb[i] - pa[i] for i in range(3)]; e2 = [pc[i] - pa[i] for i in range(3)]
        n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
        l = math.sqrt(sum(x * x for x in n)) or 1.0; n = [x / l for x in n]
        tris += struct.pack('<4I4f', a, b, cc, tri_attr, *n, sum(n[i] * pa[i] for i in range(3)))
    out = [[0x1F, bytes(h)],
           [0x02, b''.join(struct.pack('<3f', *v) for v in V)],
           [0x03, b''.join(struct.pack('<3f', *n) for n in Nn)],
           [0x20, bytes(tris)],
           [0x22, b''.join(struct.pack('<I', i) for i in range(len(V)))]]
    for t, d in tpl:
        if t in (0x28, 0x29): out.append([t, d])
        elif t == 0x2A:
            vm = [[t2, [list(x) for x in d2]] for t2, d2 in d]
            if m['kind'] == 'treads':  # прокрутка гусеницы: LINEAR_OFFSET, движок двигает U сам
                for _, sub in vm:
                    for x in sub:
                        if x[0] == 0x2D:
                            a = bytearray(x[1]); struct.pack_into('<I', a, 0, (struct.unpack_from('<I', a)[0] & ~0x00FF0000) | 0x00040000); x[1] = bytes(a)
                    sub[:] = [x for x in sub if x[0] not in (0x2E, 0x2F)] + [[0x2E, b'UPerSec=0.0\r\nVPerSec=0.0\r\n\0']]
            out.append([t, vm])
        elif t == 0x30:
            out.append([0x30, [[0x31, [[0x32, tex.encode() + b'\0']]]]])
    out.append([0x38, [[0x39, struct.pack('<I', 0)], [0x3A, struct.pack('<I', 0)],
                       [0x48, [[0x49, struct.pack('<I', 0)], [0x4A, b''.join(struct.pack('<2f', *u) for u in U)]]]]])
    return out

def build(mesh_json, out_path, name, tex, keep, retail, rot=None, origin=None):
    """Пишет <name>.W3D: иерархия из костей mesh.json, меши из keep (имена), текстуры tex[kind].
    retail: dict(solid=, house=, treads=, muzzle=) -> (chunks, mesh name) шаблоны и вспышка выстрела.
    origin: кость, которая встаёт в начало координат (обломок крутится вокруг себя, а не вокруг земли)."""
    import json
    M = json.load(open(mesh_json)); bones = M['bones']; bi = {b['name']: i for i, b in enumerate(bones)}
    rot = rot or {}
    piv = bytearray()
    for b in bones:
        p = bones[b['parent']]['pos'] if b['parent'] >= 0 else (bones[bi[origin]]['pos'] if origin else [0, 0, 0])
        t = [b['pos'][i] - p[i] for i in range(3)]; q = rot.get(b['name'], (0, 0, 0, 1))
        piv += name16(b['name']) + struct.pack('<I3f3f4f', b['parent'] & 0xFFFFFFFF, *t, 0, 0, 0, *q)
    hier = [0x100, [[0x101, struct.pack('<I', 0x00040001) + name16(name) + struct.pack('<I3f', len(bones), 0, 0, 0)], [0x102, bytes(piv)]]]
    chunks, subs = [hier], []
    for m in M['meshes']:
        if m['name'] not in keep: continue
        tch, tname = retail[m['kind']]
        chunks.append([0x00, make_mesh(mesh_by_name(tch, tname), name, m, tex[m['kind']])])
        subs.append((bi[m['bone']], f"{name}.{m['name']}"))
    if 'muzzle' in retail and 'MUZZLEFX01' in keep:
        tch, tname = retail['muzzle']; mm = [list(x) for x in mesh_by_name(tch, tname)]
        h = bytearray(mm[0][1]); h[24:40] = name16(name); mm[0][1] = bytes(h)
        chunks.append([0x00, mm]); subs.append((bi['MUZZLEFX01'], f'{name}.MUZZLEFX01'))
    arr = [[0x703, struct.pack('<If', len(subs), 3.4028235e38)]] + [[0x704, struct.pack('<I', b) + name16(n, 32)] for b, n in subs]
    chunks.append([0x700, [[0x701, struct.pack('<II', 0x00010000, 1) + name16(name) + name16(name)], [0x702, arr]]])
    open(out_path, 'wb').write(ser(chunks))
    return len(subs)

if __name__ == '__main__':
    cmd, *files = sys.argv[1:]
    if cmd == 'dump':
        dump(files[0])
    elif cmd == 'check':
        for f in files:
            b = open(f, 'rb').read(); print(f, 'ok' if ser(parse(b)) == b else 'DIFF')
