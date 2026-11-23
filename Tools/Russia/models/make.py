"""Собирает W3D-модели машины из out/mesh.json и кладёт их с текстурами в GeneralsMD/Code/Data/Art.
Варианты: <N> целый, <N>_D повреждённый, <N>_H подбитый корпус без башни, <N>_T сорванная башня.

  python3 -I Tools/Russia/models/make.py Tools/Russia/models/t72b3m <retail W3D dir>
"""
import json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import w3d

D, RET = os.path.abspath(sys.argv[1]), sys.argv[2]
ART = os.path.join(HERE, '../../../GeneralsMD/Code/Data/Art')
M = json.load(open(os.path.join(D, 'out', 'mesh.json'))); N = M['name']
names = {m['name'] for m in M['meshes']}
rd = lambda f: w3d.parse(open(os.path.join(RET, f), 'rb').read())
cru, bm = rd('avcrusader.W3D'), rd('NVBtMstr.W3D')
retail = dict(solid=(cru, 'CHASSIS'), house=(cru, 'HOUSECOLOR01'), treads=(cru, 'TREADS01'), muzzle=(bm, 'MUZZLEFX01'))
rot = {'MUZZLEFX01': (0.7071068, 0, 0, 0.7071068)}
turret = {'TURRET01', 'BARREL01'}
alive = names - {'RING'} | {'MUZZLEFX01'}
hull = {n for n in names if n not in turret and not n.startswith(('HOUSECOLOR', 'CAGES', 'RELIKT'))}
V = {
    N: (alive, dict(solid=f'{N}.tga', house='Housecolor.tga', treads=f'{N}Trk.tga')),
    f'{N}_D': (alive, dict(solid=f'{N}_D.tga', house='Housecolor.tga', treads=f'{N}Trk.tga')),
    f'{N}_H': (hull, dict(solid=f'{N}_B.tga', house='Housecolor.tga', treads=f'{N}TrkB.tga')),
    f'{N}_T': (turret, dict(solid=f'{N}_B.tga')),
}
ORIGIN = {f'{N}_T': 'TURRET01'}
os.makedirs(os.path.join(ART, 'W3D'), exist_ok=True); os.makedirs(os.path.join(ART, 'Textures'), exist_ok=True)
for v, (keep, tex) in V.items():
    out = os.path.join(ART, 'W3D', f'{v}.W3D')
    n = w3d.build(os.path.join(D, 'out', 'mesh.json'), out, v, tex, keep, retail, rot, ORIGIN.get(v))
    b = open(out, 'rb').read(); assert w3d.ser(w3d.parse(b)) == b
    print(v, n, 'sub-objects', len(b), 'bytes')
for f in os.listdir(os.path.join(D, 'out')):
    if f.endswith('.dds'): shutil.copy(os.path.join(D, 'out', f), os.path.join(ART, 'Textures', f))
