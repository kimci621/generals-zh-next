# Hunyuan3D-2mini: форма по картинке на MPS. argv: in.png out_prefix seeds(1,2,..)
import sys, time, torch
from PIL import Image
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline, FloaterRemover, DegenerateFaceRemover

t = time.time()
p = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
    'tencent/Hunyuan3D-2mini', subfolder='hunyuan3d-dit-v2-mini', variant='fp16',
    device='mps', dtype=torch.float16)
print('load', time.time() - t, flush=True)
img = Image.open(sys.argv[1]).convert('RGBA')
for seed in map(int, sys.argv[3].split(',')):
    t = time.time()
    m = p(image=img, num_inference_steps=30, octree_resolution=380, num_chunks=20000,
          generator=torch.manual_seed(seed), output_type='trimesh')[0]
    m = FloaterRemover()(m)
    m = DegenerateFaceRemover()(m)
    m.export(f'{sys.argv[2]}_s{seed}.glb')
    print('seed', seed, 'faces', len(m.faces), 't', time.time() - t, flush=True)
