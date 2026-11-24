# blender -b --factory-startup --python tview.py -- in.obj out.png
# Текстурированный меш с 4 сторон под углом игровой камеры (наклон ~40), один лист 2x2.
import bpy, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=a[0], forward_axis='NEGATIVE_Z', up_axis='Y')
o = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
for p in o.data.polygons: p.use_smooth = False
pts = [o.matrix_world @ v.co for v in o.data.vertices]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
c = (lo + hi) / 2; r = (hi - lo).length
sc = bpy.context.scene; sc.render.resolution_x = sc.render.resolution_y = 700
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.color_type = 'TEXTURE'; sh.light = 'STUDIO'
sc.world = bpy.data.worlds.new('w')
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = r * 0.95
files = []
for i, az in enumerate((-60, 30, 120, 210)):
    t, e = math.radians(az), math.radians(40)
    d = Vector((math.cos(t) * math.cos(e), math.sin(t) * math.cos(e), math.sin(e)))
    cam.location = c + d * r * 2
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
    f = a[1].replace('.png', f'_{i}.png'); sc.render.filepath = f; bpy.ops.render.render(write_still=True); files.append(f)
im = bpy.data.images.new('s', 1400, 1400); px = [0.0] * (1400 * 1400 * 4)
for i, f in enumerate(files):
    s = bpy.data.images.load(f); sp = list(s.pixels); ox, oy = (i % 2) * 700, (1 - i // 2) * 700
    for y in range(700):
        row = sp[y * 700 * 4:(y + 1) * 700 * 4]; j = ((oy + y) * 1400 + ox) * 4; px[j:j + 700 * 4] = row
im.pixels = px; im.filepath_raw = a[1]; im.file_format = 'PNG'; im.save()
