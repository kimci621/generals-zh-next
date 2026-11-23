# /// script
# dependencies = ["pillow"]
# ///
"""Иконки и эмблема России из картинок Tools/Russia/art (сгенерированы Higgsfield Z Image, реалистичная
военная фотография в духе кнопок Generals; промпты в art/PROMPTS.txt).

    uv run Tools/Russia/icons.py [--preview out.png]

Пишет GeneralsMD/Code/Data/Art/Textures/RUIcons.tga (1024x512, клетки 120x96 = 2x ретейловых 60x48),
Data/INI/MappedImages/HandCreated/RUIcons.ini (RUIcon<Name>) и ReforgedFactionRussia.tga 128x128.
Кнопки ссылаются на RUIcon<Name>.

Портреты юнитов и зданий: art/cameo/<id>.jpg (Gemini, промпты в art/cameo/PROMPTS.tsv), id как в gen.py.
Пишет RUCameos.tga (2048x2048: портреты 240x192 сверху, кнопки 120x96 под ними) и RUCameos.ini
(RUCameo<id> - кнопка, RUCameo<id>_L - портрет выбранного, как TRCameos.ini у Турции).
"""
import argparse
import os

from PIL import Image, ImageEnhance, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(HERE, "art")
ROOT = os.path.join(HERE, "..", "..", "GeneralsMD", "Code", "Data")
CW, CH, COLS = 120, 96, 8
TEX_W, TEX_H = 1024, 512

NAMES = ["Tax", "OilGas", "Ratnik", "Thermal", "Relikt", "Cages", "Mobres", "PantsirMod",
         "GuidedFAB", "Cyber", "FAB", "TornadoS", "VDV", "Reservists", "EWSuppress", "Orlan",
         "Kinzhal", "Oreshnik", "TOS", "Veterans"]


def cell(name):
    """фото 480x384 -> 120x96: контраст и резкость, чтобы читалось на панели"""
    im = Image.open(os.path.join(ART, name + ".jpg")).convert("RGB").resize((CW, CH), Image.LANCZOS)
    im = ImageEnhance.Contrast(im).enhance(1.25)
    im = ImageEnhance.Brightness(im).enhance(1.08)
    return im.filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=2)).convert("RGBA")


def cameo(name, w, h):
    """фото ~4:3 -> центр 5:4 -> w x h, контраст и резкость как у иконок"""
    im = Image.open(os.path.join(ART, "cameo", name + ".jpg")).convert("RGB")
    cw = min(im.width, im.height * 5 // 4)
    ch = cw * 4 // 5
    x, y = (im.width - cw) // 2, (im.height - ch) // 2
    im = im.crop((x, y, x + cw, y + ch)).resize((w, h), Image.LANCZOS)
    im = ImageEnhance.Contrast(im).enhance(1.2)
    return im.filter(ImageFilter.UnsharpMask(radius=1, percent=70, threshold=2))


def cameos():
    from gen import BUILDINGS, UNITS
    names = [r[0] for r in BUILDINGS + UNITS]
    size = 2048
    atlas = Image.new("RGB", (size, size))
    ini = ["; Russia's unit and building cameos, built by Tools/Russia/icons.py from Tools/Russia/art/cameo.",
           "; RUCameo<id> is the build button (120x96), RUCameo<id>_L the selection portrait (240x192).", ""]

    def mapped(name, x, y, w, h):
        return ["MappedImage " + name, "  Texture = RUCameos.tga", "  TextureWidth = %d" % size,
                "  TextureHeight = %d" % size, "  Coords = Left:%d Top:%d Right:%d Bottom:%d" % (x, y, x + w, y + h),
                "  Status = NONE", "End", ""]
    by = 6 * 2 * CH  # кнопки под шестью рядами портретов
    for i, name in enumerate(names):
        lx, ly = (i % 8) * 2 * CW, (i // 8) * 2 * CH
        bx, bly = (i % 16) * CW, by + (i // 16) * CH
        atlas.paste(cameo(name, 2 * CW, 2 * CH), (lx, ly))
        atlas.paste(cameo(name, CW, CH), (bx, bly))
        ini += mapped("RUCameo" + name, bx, bly, CW, CH) + mapped("RUCameo" + name + "_L", lx, ly, 2 * CW, 2 * CH)
    atlas.save(os.path.join(ROOT, "Art", "Textures", "RUCameos.tga"))
    with open(os.path.join(ROOT, "INI", "MappedImages", "HandCreated", "RUCameos.ini"), "w", newline="\n") as f:
        f.write("\n".join(ini))
    return atlas, len(names)


def emblem(path):
    """знак на чёрном фоне -> прозрачность по яркости у края, 128x128"""
    im = Image.open(os.path.join(ART, "Emblem.png")).convert("RGB")
    alpha = im.convert("L").point(lambda v: 0 if v < 14 else min(255, (v - 14) * 12))
    out = im.convert("RGBA")
    out.putalpha(alpha.filter(ImageFilter.MinFilter(3)))
    out.resize((128, 128), Image.LANCZOS).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview")
    args = ap.parse_args()
    atlas = Image.new("RGBA", (TEX_W, TEX_H), (0, 0, 0, 0))
    ini = ["; Russia's upgrade and power buttons, built by Tools/Russia/icons.py from Tools/Russia/art.", ""]
    for i, name in enumerate(NAMES):
        x, y = (i % COLS) * CW, (i // COLS) * CH
        atlas.paste(cell(name), (x, y))
        ini += ["MappedImage RUIcon%s" % name, "  Texture = RUIcons.tga", "  TextureWidth = %d" % TEX_W,
                "  TextureHeight = %d" % TEX_H, "  Coords = Left:%d Top:%d Right:%d Bottom:%d" % (x, y, x + CW, y + CH),
                "  Status = NONE", "End", ""]
    atlas.save(os.path.join(ROOT, "Art", "Textures", "RUIcons.tga"))
    emblem(os.path.join(ROOT, "Art", "Textures", "ReforgedFactionRussia.tga"))
    # эмблема на экране загрузки (LoadScreen.cpp ищет LoadCrest<шаблон>)
    ini += ["MappedImage LoadCrestFactionRussia", "  Texture = ReforgedFactionRussia.tga", "  TextureWidth = 128",
            "  TextureHeight = 128", "  Coords = Left:0 Top:0 Right:128 Bottom:128", "  Status = NONE", "End", ""]
    with open(os.path.join(ROOT, "INI", "MappedImages", "HandCreated", "RUIcons.ini"), "w", newline="\n") as f:
        f.write("\n".join(ini))
    cam, n = cameos()
    if args.preview:
        atlas.crop((0, 0, COLS * CW, 3 * CH)).save(args.preview)
        cam.crop((0, 0, 16 * CW, 6 * 2 * CH + 3 * CH)).save(os.path.splitext(args.preview)[0] + "_cameos.png")
    print("wrote %d icons, %d cameos" % (len(NAMES), n))


if __name__ == "__main__":
    main()
