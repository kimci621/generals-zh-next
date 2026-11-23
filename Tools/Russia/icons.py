# /// script
# dependencies = ["pillow"]
# ///
"""Иконки России для улучшений и способностей: свои глифы (латунь на оливковой стали), без чужого арта.

    uv run Tools/Russia/icons.py [--preview out.png]

Пишет GeneralsMD/Code/Data/Art/Textures/RUIcons.tga (1024x512, клетки 120x96 = 2x ретейловых 60x48)
и Data/INI/MappedImages/HandCreated/RUIcons.ini (RUIcon<Name>). Кнопки ссылаются на RUIcon<Name>.
"""
import argparse
import math
import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "GeneralsMD", "Code", "Data")
CW, CH, K, COLS = 120, 96, 4, 8
TEX_W, TEX_H = 1024, 512
BRASS, BRASS_D, INK = (214, 168, 64), (150, 110, 36), (16, 20, 12)
RED = (196, 52, 36)


def star(cx, cy, r1, r2, n=5, rot=0.0):
    return [(cx + (r1 if i % 2 == 0 else r2) * math.sin(rot + i * math.pi / n),
             cy - (r1 if i % 2 == 0 else r2) * math.cos(rot + i * math.pi / n)) for i in range(2 * n)]


def rot(pts, cx, cy, a):
    c, s = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


class G:
    """Глиф в координатах клетки 120x96; всё масштабируется в K раз."""

    def __init__(self, d):
        self.d = d

    def s(self, pts):
        return [(x * K, y * K) for x, y in pts]

    def poly(self, pts, c=BRASS):
        self.d.polygon(self.s(pts), fill=c)

    def line(self, pts, w, c=BRASS):
        self.d.line(self.s(pts), fill=c, width=int(w * K), joint="curve")

    def ell(self, x0, y0, x1, y1, c=BRASS, outline=None, w=0):
        self.d.ellipse((x0 * K, y0 * K, x1 * K, y1 * K), fill=c, outline=outline, width=int(w * K))

    def rect(self, x0, y0, x1, y1, c=BRASS):
        self.d.rectangle((x0 * K, y0 * K, x1 * K, y1 * K), fill=c)

    def arc(self, box, a0, a1, w, c=BRASS):
        self.d.arc(tuple(v * K for v in box), a0, a1, fill=c, width=int(w * K))

    def text(self, xy, t, size, c=BRASS):
        from PIL import ImageFont
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", size * K)
        self.d.text((xy[0] * K, xy[1] * K), t, font=f, fill=c, anchor="mm")


# ---- глифы -------------------------------------------------------------------------------------

def tax(g):        # мешок с рублём
    g.ell(34, 30, 86, 84)
    g.poly([(48, 32), (72, 32), (78, 20), (42, 20)])
    g.rect(46, 30, 74, 35, BRASS_D)
    g.line([(54, 44), (54, 74)], 5, INK)              # знак рубля: стойка, петля, перекладина
    g.arc((44, 42, 72, 62), 270, 90, 5, INK)
    g.line([(54, 43), (58, 43)], 5, INK)
    g.line([(54, 61), (58, 61)], 5, INK)
    g.line([(46, 67), (64, 67)], 4, INK)


def oilgas(g):     # вышка и капля
    g.poly([(40, 84), (52, 16), (58, 16), (70, 84), (64, 84), (55, 30), (46, 84)])
    for y in (40, 56, 72):
        g.line([(47, y), (63, y)], 3)
    g.poly([(88, 44), (98, 62), (98, 70), (88, 80), (78, 70), (78, 62)])
    g.ell(78, 58, 98, 80)


def ratnik(g):     # шлем
    g.d.chord((26 * K, 18 * K, 94 * K, 98 * K), 180, 360, fill=BRASS)
    g.rect(22, 56, 98, 64)
    g.rect(38, 64, 48, 80)
    g.rect(72, 64, 82, 80)
    g.line([(40, 40), (80, 40)], 3, BRASS_D)


def thermal(g):    # прицел с тепловым пятном
    g.ell(30, 18, 90, 78, None, BRASS, 5)
    g.ell(48, 36, 72, 60, RED)
    g.ell(54, 42, 66, 54, (250, 200, 80))
    for a, b in (((60, 10), (60, 28)), ((60, 68), (60, 86)), ((22, 48), (40, 48)), ((80, 48), (98, 48))):
        g.line([a, b], 4)


def relikt(g):     # блоки ДЗ на броне
    g.poly([(18, 76), (30, 40), (90, 40), (102, 76)], BRASS_D)
    for i in range(4):
        x = 26 + i * 18
        g.rect(x, 24 + (i % 2) * 2, x + 15, 38 + (i % 2) * 2)
        g.rect(x + 2, 46, x + 15, 70)


def cages(g):      # решётка над танком
    g.poly([(20, 80), (28, 64), (92, 64), (100, 80)], BRASS_D)
    g.rect(44, 54, 76, 66, BRASS_D)
    g.line([(76, 58), (104, 54)], 4, BRASS_D)
    g.line([(24, 46), (96, 46), (96, 18), (24, 18), (24, 46)], 3)
    for x in range(36, 96, 12):
        g.line([(x, 18), (x, 46)], 2)
    g.line([(24, 32), (96, 32)], 2)


def person(g, x, y, s, c=BRASS):
    g.ell(x - 6 * s, y - 26 * s, x + 6 * s, y - 14 * s, c)
    g.poly([(x - 10 * s, y + 10 * s), (x - 9 * s, y - 12 * s), (x + 9 * s, y - 12 * s), (x + 10 * s, y + 10 * s)], c)


def mobres(g):     # три силуэта и стрелка
    person(g, 36, 70, 1.0, BRASS_D)
    person(g, 84, 70, 1.0, BRASS_D)
    person(g, 60, 74, 1.3)
    g.poly([(60, 6), (72, 18), (64, 18), (64, 24), (56, 24), (56, 18), (48, 18)])


def pantsirmod(g):  # антенна и шестерня
    g.arc((22, 14, 82, 74), 200, 340, 6)
    g.line([(52, 44), (52, 82)], 6)
    g.rect(40, 80, 64, 86)
    g.line([(52, 44), (70, 22)], 3)
    for i in range(8):
        a = i * math.pi / 4
        g.poly(rot([(84, 50), (92, 50), (92, 58), (84, 58)], 88, 66, a))
    g.ell(78, 56, 98, 76)
    g.ell(84, 62, 92, 70, INK)


def bomb(g, cx, cy, s, a=0.0, wings=False, c=BRASS):
    body = [(cx - 22 * s, cy - 7 * s), (cx + 14 * s, cy - 7 * s), (cx + 24 * s, cy), (cx + 14 * s, cy + 7 * s), (cx - 22 * s, cy + 7 * s)]
    fin = [(cx - 22 * s, cy), (cx - 32 * s, cy - 12 * s), (cx - 28 * s, cy), (cx - 32 * s, cy + 12 * s)]
    g.poly(rot(body, cx, cy, a), c)
    g.poly(rot(fin, cx, cy, a), c)
    if wings:
        g.poly(rot([(cx - 6 * s, cy), (cx + 4 * s, cy - 22 * s), (cx + 10 * s, cy - 22 * s), (cx + 6 * s, cy)], cx, cy, a), BRASS_D)


def guidedfab(g):  # бомба с крыльями и траектория
    g.line([(14, 20), (34, 26), (54, 36)], 2, BRASS_D)
    bomb(g, 66, 52, 1.2, 0.5, wings=True)
    g.ell(88, 74, 104, 90, None, RED, 3)
    g.ell(94, 80, 98, 84, RED)


def cyber(g):      # экран с кодом и молнией
    g.rect(20, 16, 100, 70, BRASS_D)
    g.rect(25, 21, 95, 65, INK)
    for i, t in enumerate(("1011", "0110", "1101")):
        g.text((48, 30 + i * 13), t, 10, (120, 170, 90))
    g.poly([(76, 20), (64, 46), (74, 46), (66, 74), (90, 40), (78, 40), (88, 20)], RED)
    g.rect(52, 70, 68, 78, BRASS_D)
    g.rect(40, 78, 80, 84, BRASS_D)


def fab(g):        # три бомбы
    for x, y in ((40, 30), (70, 50), (52, 72)):
        bomb(g, x, y, 0.8, math.pi / 2.6)


def tornados(g):   # пакет ракет
    for i in range(4):
        x = 22 + i * 16
        g.poly(rot([(x, 70), (x, 30), (x + 5, 20), (x + 10, 30), (x + 10, 70)], 60, 48, -0.45))
        g.poly(rot([(x - 3, 72), (x + 13, 72), (x + 10, 64), (x, 64)], 60, 48, -0.45), BRASS_D)
    g.line([(14, 88), (106, 88)], 4, BRASS_D)


def vdv(g):        # парашют
    g.d.chord((18 * K, 10 * K, 102 * K, 70 * K), 180, 360, fill=BRASS)
    for x in (18, 46, 74, 102):
        g.line([(x, 40), (60, 72)], 2)
    person(g, 60, 92, 0.75)


def reservists(g):  # силуэты с винтовкой
    for x, c in ((32, BRASS_D), (60, BRASS), (88, BRASS_D)):
        person(g, x, 74, 1.1, c)
        g.line([(x + 10, 80), (x + 4, 30)], 3, c)


def ewsuppress(g):  # антенна с волнами, перечёркнуто
    g.line([(60, 40), (60, 86)], 5)
    g.poly([(48, 86), (72, 86), (60, 66)])
    for r in (14, 26, 38):
        g.arc((60 - r, 40 - r, 60 + r, 40 + r), 210, 330, 4)
    g.line([(22, 84), (98, 14)], 7, RED)


def orlan(g):      # беспилотник
    g.poly([(14, 46), (106, 46), (106, 52), (14, 52)])
    g.poly([(52, 32), (68, 32), (72, 50), (66, 76), (54, 76), (48, 50)])
    g.poly([(40, 76), (80, 76), (78, 82), (42, 82)], BRASS_D)
    g.ell(54, 34, 66, 46, INK)


def kinzhal(g):    # ракета, след
    pts = [(14, 58), (78, 58), (106, 48), (78, 38), (14, 38)]
    g.poly(rot(pts, 60, 48, -0.35))
    g.poly(rot([(14, 38), (26, 38), (16, 22), (8, 22)], 60, 48, -0.35), BRASS_D)
    g.poly(rot([(14, 58), (26, 58), (16, 74), (8, 74)], 60, 48, -0.35), BRASS_D)
    g.line(rot([(2, 48), (12, 48)], 60, 48, -0.35), 6, RED)


def oreshnik(g):   # шесть боеголовок веером
    for i in range(6):
        a = -0.9 + i * 0.36
        g.poly(rot([(58, 88), (58, 36), (60, 26), (62, 36), (62, 88)], 60, 92, a))
        tip = rot([(60, 22)], 60, 92, a)[0]
        g.ell(tip[0] - 5, tip[1] - 5, tip[0] + 5, tip[1] + 5, RED)


ICONS = [  # (имя, глиф, способность ли)
    ("Tax", tax, False), ("OilGas", oilgas, False), ("Ratnik", ratnik, False), ("Thermal", thermal, False),
    ("Relikt", relikt, False), ("Cages", cages, False), ("Mobres", mobres, False), ("PantsirMod", pantsirmod, False),
    ("GuidedFAB", guidedfab, False), ("Cyber", cyber, True), ("FAB", fab, True), ("TornadoS", tornados, True),
    ("VDV", vdv, True), ("Reservists", reservists, True), ("EWSuppress", ewsuppress, True), ("Orlan", orlan, True),
    ("Kinzhal", kinzhal, True), ("Oreshnik", oreshnik, True),
]


def cell(draw, power):
    W, H = CW * K, CH * K
    # фон: оливковая сталь с виньеткой; способности темнее и с красной искрой по краю
    bg = Image.new("RGB", (W, H))
    px = bg.load()
    base = (44, 52, 36) if not power else (34, 34, 30)
    for y in range(0, H, K):
        for x in range(0, W, K):
            dx, dy = (x - W / 2) / W, (y - H / 2) / H
            v = 1.25 - 1.4 * (dx * dx + dy * dy)
            c = tuple(max(0, min(255, int(b * v))) for b in base)
            for yy in range(K):
                for xx in range(K):
                    px[x + xx, y + yy] = c
    glyph = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw(G(ImageDraw.Draw(glyph)))
    shadow = Image.new("RGBA", (W, H), INK + (0,))
    shadow.putalpha(glyph.getchannel("A").filter(ImageFilter.GaussianBlur(3 * K)))
    out = bg.convert("RGBA")
    out.alpha_composite(shadow, (2 * K, 2 * K))
    out.alpha_composite(glyph)
    d = ImageDraw.Draw(out)
    d.rectangle((0, 0, W - 1, H - 1), outline=BRASS_D, width=2 * K)
    if power:
        d.line((2 * K, H - 3 * K, W - 2 * K, H - 3 * K), fill=RED, width=K)
    return out.resize((CW, CH), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview")
    args = ap.parse_args()
    atlas = Image.new("RGBA", (TEX_W, TEX_H), (0, 0, 0, 0))
    ini = ["; Russia's upgrade and power buttons, drawn by Tools/Russia/icons.py (own glyphs, no other art).", ""]
    for i, (name, draw, power) in enumerate(ICONS):
        x, y = (i % COLS) * CW, (i // COLS) * CH
        atlas.paste(cell(draw, power), (x, y))
        ini += ["MappedImage RUIcon%s" % name, "  Texture = RUIcons.tga", "  TextureWidth = %d" % TEX_W,
                "  TextureHeight = %d" % TEX_H, "  Coords = Left:%d Top:%d Right:%d Bottom:%d" % (x, y, x + CW, y + CH),
                "  Status = NONE", "End", ""]
    atlas.save(os.path.join(ROOT, "Art", "Textures", "RUIcons.tga"))
    with open(os.path.join(ROOT, "INI", "MappedImages", "HandCreated", "RUIcons.ini"), "w", newline="\n") as f:
        f.write("\n".join(ini))
    if args.preview:
        atlas.crop((0, 0, COLS * CW, 3 * CH)).save(args.preview)
    print("wrote %d icons" % len(ICONS))


if __name__ == "__main__":
    main()
