# /// script
# dependencies = ["numpy", "pillow", "scipy"]
# ///
"""Атлас текстуры из ортогональных видов: чистый, повреждённый, обгоревший + полоса гусеницы.
Пишет в <dir>/out: <NAME>.tga, <NAME>_D.tga, <NAME>_B.tga, <NAME>Trk.tga, <NAME>TrkB.tga, atlas.json.

  uv run Tools/Russia/models/atlas.py Tools/Russia/models/t72b3m [size, по умолчанию 1024]
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

D = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 1024  # 1024: решение пользователя 2026-11-23 (вес репозитория)
C = json.load(open(os.path.join(D, 'config.json'))); P = json.load(open(os.path.join(D, 'parts.json')))
O = os.path.join(D, 'out'); os.makedirs(O, exist_ok=True)
ref = lambda n: Image.open(os.path.join(D, 'ref', n)).convert('RGB')

def bbox(im, pad=10):
    a = np.asarray(im).astype(int); bg = a[5, 5]
    ys, xs = np.nonzero(np.abs(a - bg).sum(2) > 40)
    return [int(xs.min()) - pad, int(ys.min()) - pad, int(xs.max()) + pad, int(ys.max()) + pad]

views = ['side', 'top', 'front', 'rear']
src = {v: P['proj'][v]['img'] for v in views}
crop = {v: bbox(ref(src[v])) for v in views}
cw = {v: crop[v][2] - crop[v][0] for v in views}; ch = {v: crop[v][3] - crop[v][1] for v in views}
a = N / cw['side']; b = N / cw['top']
rest = N - a * ch['side'] - b * ch['top']
c = min(N / (cw['front'] + cw['rear']), rest / max(ch['front'], ch['rear']))
rects = {}
rects['side'] = [0, 0, N, a * ch['side']]
rects['top'] = [0, rects['side'][3], N, b * ch['top']]
y2 = rects['top'][1] + rects['top'][3]
rects['front'] = [0, y2, c * cw['front'], c * ch['front']]
rects['rear'] = [c * cw['front'], y2, c * cw['rear'], c * ch['rear']]

def padfill(im):
    """Фон (почти белый) -> цвет ближайшего пикселя машины: грани у края силуэта не берут белое."""
    a = np.asarray(im).astype(int); bg = a[5, 5]
    m = np.abs(a - bg).sum(2) > 40
    m = ndimage.binary_erosion(m, iterations=3)
    _, (iy, ix) = ndimage.distance_transform_edt(~m, return_indices=True)
    return Image.fromarray(a[iy, ix].astype(np.uint8))

def compose(names):
    at = Image.new('RGB', (N, N), (60, 64, 50))
    for v in views:
        im = padfill(ref(names[v]).crop(crop[v])); x, y, w, h = rects[v]
        at.paste(im.resize((round(w), round(h)), Image.LANCZOS), (round(x), round(y)))
    return at

def burn(im, like, full=False):
    """Перенос цвета (среднее/разброс по каналам) с обгоревшего вида + пятна копоти."""
    x = np.asarray(im).astype(float); r = np.asarray(like).astype(float)
    m = np.abs(r - r[5, 5]).sum(2) > 40; rv = r[m]
    mx = np.ones(x.shape[:2], bool) if full else np.abs(x - x[5, 5]).sum(2) > 40
    y = x.copy(); xv = x[mx]
    y[mx] = (xv - xv.mean(0)) / (xv.std(0) + 1e-3) * rv.std(0) + rv.mean(0)
    rng = np.random.default_rng(7)
    n = Image.fromarray((rng.random((x.shape[0] // 24, x.shape[1] // 24)) * 255).astype(np.uint8)).resize(
        (x.shape[1], x.shape[0]), Image.BICUBIC).filter(ImageFilter.GaussianBlur(6))
    soot = (np.asarray(n).astype(float) / 255.0)[..., None]
    y[mx] = (y * (1 - 0.6 * np.clip(soot * 2 - 0.6, 0, 1)))[mx]
    return Image.fromarray(np.clip(y, 0, 255).astype(np.uint8))

clean = compose(src)
burnt_src = {'side': 'side_burnt.jpg', 'top': 'top_burnt.jpg'}
tmp = {}
for v in ('front', 'rear'):
    p = os.path.join(O, f'_{v}_burnt.png'); burn(ref(src[v]), ref('side_burnt.jpg')).save(p); tmp[v] = p
burnt = Image.new('RGB', (N, N), (40, 30, 25))
for v in views:
    im = padfill((ref(burnt_src[v]) if v in burnt_src else Image.open(tmp[v]).convert('RGB')).crop(crop[v])); x, y, w, h = rects[v]
    burnt.paste(im.resize((round(w), round(h)), Image.LANCZOS), (round(x), round(y)))
for p in tmp.values(): os.remove(p)
# повреждённый: чистый с частичной копотью (обгоревшие виды отличаются формой, их не смешиваем)
damaged = Image.blend(clean, burn(clean, ref('side_burnt.jpg')), 0.4)

# гусеница: вид спереди, левая ветвь снизу (траки идут вертикально) -> полоса вдоль U, целое число звеньев
S = C['side']; fr = np.asarray(ref(src['front'])).astype(float)
x0, x1, y0, y1 = crop['front'][0] + 10, crop['front'][2] - 10, crop['front'][1] + 10, crop['front'][3] - 10
tw = int((x1 - x0) * C['track_width'] / P['size'][0])  # ширина ленты в пикселях
row = fr[y1 - 30]; xl = int(np.nonzero(np.abs(row - fr[5, 5]).sum(1) > 40)[0].min())  # левый край левой гусеницы
band = fr[int(y1 - (y1 - y0) * 0.22):y1 - 12, xl + 6:xl + tw - 6]  # нижние ~22% высоты: передняя дуга
prof = band.mean((1, 2)); prof -= prof.mean()
ac = np.correlate(prof, prof, 'full')[len(prof) - 1:]
period = int(np.argmax(ac[30:len(prof) // 2]) + 30)  # звено не короче 30 px
links = max(1, len(prof) // period)
strip = band[-links * period:]
tile = Image.fromarray(strip.astype(np.uint8)).rotate(90, expand=True)
trk = tile.resize((256, 64), Image.LANCZOS)
# длина плитки в метрах: звено ~0.15 м у Т-72
tile_m = links * 0.15
name = C['name']
def tga(im, n):
    """DDS DXT1 с полной цепочкой мипмапов (Pillow пишет только верхний уровень, склеиваем сами)."""
    import io, struct
    levels, w = [], im.copy()
    while True:
        b = io.BytesIO(); w.save(b, 'DDS', pixel_format='DXT1'); d = b.getvalue()
        hdr = bytearray(d[:128]) if not levels else hdr; levels.append(d[128:])
        if min(w.size) <= 4: break
        w = w.resize((max(4, w.width // 2), max(4, w.height // 2)), Image.LANCZOS)
    struct.pack_into('<I', hdr, 8, struct.unpack_from('<I', hdr, 8)[0] | 0x20000)   # DDSD_MIPMAPCOUNT
    struct.pack_into('<I', hdr, 28, len(levels))
    struct.pack_into('<I', hdr, 108, struct.unpack_from('<I', hdr, 108)[0] | 0x400008)  # COMPLEX|MIPMAP
    open(os.path.join(O, n.replace('.tga', '.dds')), 'wb').write(bytes(hdr) + b''.join(levels))
tga(clean, f'{name}.tga'); tga(damaged, f'{name}_D.tga'); tga(burnt, f'{name}_B.tga')
tga(trk, f'{name}Trk.tga'); tga(burn(trk, ref('side_burnt.jpg'), True), f'{name}TrkB.tga')
json.dump(dict(size=N, rects=rects, crop=crop, track=dict(period_px=period, links=links, tile_m=tile_m)), open(os.path.join(O, 'atlas.json'), 'w'), indent=1)
print('rects', {k: [round(x) for x in v] for k, v in rects.items()}, 'track period', period, 'links', links)
