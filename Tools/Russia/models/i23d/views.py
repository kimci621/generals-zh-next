# blender -b --factory-startup --python views.py -- in.glb out_prefix
# Импорт GLB, габариты, 6 ортографических видов в серой глине.
import bpy, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
(bpy.ops.import_scene.gltf(filepath=a[0]) if a[0].endswith('.glb') else bpy.ops.wm.obj_import(filepath=a[0], forward_axis='NEGATIVE_Z', up_axis='Y'))
obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
pts = [o.matrix_world @ v.co for o in obs for v in o.data.vertices]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
print('BBOX', tuple(round(x, 3) for x in lo), tuple(round(x, 3) for x in hi), 'tris', sum(len(o.data.polygons) for o in obs))
c = (lo + hi) / 2; r = (hi - lo).length
sc = bpy.context.scene; sc.render.resolution_x = sc.render.resolution_y = 600
sc.render.engine = 'BLENDER_WORKBENCH'
w = bpy.data.worlds.new('w'); sc.world = w
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = r
views = {'px': (1, 0, 0), 'nx': (-1, 0, 0), 'py': (0, 1, 0), 'ny': (0, -1, 0), 'pz': (0, 0, 1), 'nz': (0, 0, -1),
         'iso': (1, -1, 0.8)}
for n, d in views.items():
    d = Vector(d).normalized()
    cam.location = c + d * r * 2
    up = 'Z' if abs(d.z) < 0.9 else 'Y'
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y' if up == 'Z' else 'Z').to_euler()
    sc.render.filepath = f'{a[1]}_{n}.png'; bpy.ops.render.render(write_still=True)
