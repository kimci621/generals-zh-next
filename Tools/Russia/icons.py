# /// script
# dependencies = ["pillow"]
# ///
"""Иконки и эмблема России из картинок Tools/Russia/art (сгенерированы Higgsfield Z Image, реалистичная
военная фотография в духе кнопок Generals; промпты в art/PROMPTS.txt).

    uv run Tools/Russia/icons.py [--preview out.png]

Пишет GeneralsMD/Code/Data/Art/Textures/RUIcons.tga (1024x512, клетки 120x96 = 2x ретейловых 60x48),
Data/INI/MappedImages/HandCreated/RUIcons.ini (RUIcon<Name>) и ReforgedFactionRussia.tga 128x128.
Кнопки ссылаются на RUIcon<Name>.
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
    with open(os.path.join(ROOT, "INI", "MappedImages", "HandCreated", "RUIcons.ini"), "w", newline="\n") as f:
        f.write("\n".join(ini))
    if args.preview:
        atlas.crop((0, 0, COLS * CW, 3 * CH)).save(args.preview)
    print("wrote %d icons" % len(NAMES))


if __name__ == "__main__":
    main()
