# Сокращение меша: in.glb out.obj target_faces
import sys, pymeshlab, trimesh
m = trimesh.load(sys.argv[1], force='mesh')
ms = pymeshlab.MeshSet()
ms.add_mesh(pymeshlab.Mesh(m.vertices, m.faces))
ms.meshing_merge_close_vertices()
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=int(sys.argv[3]), preservenormal=True,
                                            planarquadric=True, qualitythr=0.3, preserveboundary=True)
ms.meshing_remove_unreferenced_vertices()
c = ms.current_mesh()
print('faces', c.face_number(), 'verts', c.vertex_number())
ms.save_current_mesh(sys.argv[2])
