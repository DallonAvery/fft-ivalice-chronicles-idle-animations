"""Preview a human breathing cut on many sprite sheets (front and back).

Writes <out>.gif (standing / breathing alternating) and <out>_breath.png (breathing
pose with the cut line marked). The strip spec is a list of (height, pixels lower)
from the top of the 40-row standing block, e.g. "32:1,8:0".

Usage: python cut_preview.py <out base> <strips> <sheet first png> [...]
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_idle as c  # noqa: E402
import human_idle_preview as h  # noqa: E402
import shp_render as r  # noqa: E402
from breath_preview_multi import full_render  # noqa: E402


def main():
    out, spec, *sheets = sys.argv[1:]
    strips = [tuple(int(v) for v in part.split(":")) for part in spec.split(",")]
    cuts, y = [], 0
    for hh, _ in strips[:-1]:
        y += hh
        cuts.append(y)
    shp = r.parse_shp(open(os.path.join(c.ORIG, "battle_type1_shp.bin"), "rb").read())
    cells = []
    for path in sheets:
        name, sheet = c.load_pair(path)
        for f, facing in ((2, "front"), (8, "back")):
            (tile,) = shp[f]
            cells.append((f"{name.replace('_', ' ')} {facing}",
                          full_render([tile], sheet, h.BOX), full_render(h.strips(tile, strips), sheet, h.BOX)))
    W, H = (h.BOX[2] - h.BOX[0]) * 2, (h.BOX[3] - h.BOX[1]) * 2
    cols = 8
    rows = (len(cells) + cols - 1) // cols
    imgs = []
    for which in (1, 2):
        img = Image.new("RGBA", (W * cols, (H + 16) * rows), (32, 36, 44, 255))
        d = ImageDraw.Draw(img)
        for i, cell in enumerate(cells):
            x, y = (i % cols) * W, (i // cols) * (H + 16)
            img.alpha_composite(cell[which].resize((W, H), Image.NEAREST), (x, y + 16))
            d.text((x + 4, y + 2), cell[0], fill="white")
            if which == 2:
                for cut in cuts:
                    yy = y + 16 + ((83 + cut) * 2 - h.BOX[1]) * 2
                    for x0 in range(x, x + W, 10):
                        d.line((x0, yy, x0 + 5, yy), fill=(255, 96, 160), width=1)
        imgs.append(img)
    imgs[1].save(out + "_breath.png")
    # animation without the guide lines
    plain = []
    for which in (1, 2):
        img = Image.new("RGBA", (W * cols, (H + 16) * rows), (32, 36, 44, 255))
        d = ImageDraw.Draw(img)
        for i, cell in enumerate(cells):
            x, y = (i % cols) * W, (i // cols) * (H + 16)
            img.alpha_composite(cell[which].resize((W, H), Image.NEAREST), (x, y + 16))
            d.text((x + 4, y + 2), cell[0], fill="white")
        plain.append(img.convert("P", palette=Image.ADAPTIVE))
    plain[0].save(out + ".gif", save_all=True, append_images=[plain[1]], duration=[600, 430], loop=0)
    print("wrote", out + ".gif", out + "_breath.png", len(cells), "poses")


if __name__ == "__main__":
    main()
