"""Classify monster sheets as floating / limbless or standing from their ORIGINAL idle.

For every frame of the original front idle (animation 6), find the vertical shift that
best lines it up with the standing pose (frame 2), and how much still differs after
that shift. A floater's idle is mostly the same picture moved up and down (big shift,
small remaining difference). A walker's idle keeps the body in place and moves legs
(no shift, larger difference concentrated at the bottom).

Also writes a zoomed strip per sheet: original idle frames, then the mod's breathing
pose with the cut lines marked.

Usage: python float_check.py <out dir> <sheet> [sheet ...]
"""
import os
import sys

from PIL import Image, ImageChops, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_mods  # noqa: E402
import compare_idle as c  # noqa: E402
import shp_render as r  # noqa: E402
from breath_preview_multi import full_render  # noqa: E402

BOX = (40, 120, 200, 280)


def alpha(img):
    return img.split()[3].point(lambda v: 255 if v else 0)


def diff_ratio(a, b):
    d = ImageChops.difference(a, b)
    on = sum(1 for v in d.getdata() if v)
    total = sum(1 for v in a.getdata() if v) or 1
    return on / total


def best_shift(base, img, max_shift=24):
    """Vertical shift (in HD pixels) of img that best matches base, and leftover difference."""
    a, b = alpha(base), alpha(img)
    best = None
    for dy in range(-max_shift, max_shift + 1, 2):
        shifted = Image.new("L", b.size, 0)
        shifted.paste(b, (0, dy))
        score = diff_ratio(a, shifted)
        if best is None or score < best[1]:
            best = (dy, score)
    return best


def main():
    out_dir, *sheets = sys.argv[1:]
    os.makedirs(out_dir, exist_ok=True)
    shp_o = r.parse_shp(open(os.path.join(c.ORIG, "battle_mon_shp.bin"), "rb").read())
    shp_m = r.parse_shp(open(os.path.join(c.MOD, "battle_mon_shp.bin"), "rb").read())
    idle = c.timeline(os.path.join(c.ORIG, "battle_mon_seq.bin"), 6)
    order = []
    for f in idle:
        if f not in order:
            order.append(f)
    line = build_mods.FAMILIES["mon"]["line"]
    print(f"{'sheet':12s} per-frame (shift in sprite px, leftover diff %) for frames {order}")
    for path in sheets:
        name, sheet = c.load_pair(path)
        base = full_render(shp_o[2], sheet, BOX)
        res = []
        for f in order:
            dy, left = best_shift(base, full_render(shp_o[f], sheet, BOX))
            res.append((f, dy // 2, round(left * 100)))
        shifts = [abs(s) for _, s, _ in res]
        lefts = [x for _, _, x in res]
        kind = "FLOATS (whole body bobs)" if max(shifts) >= 2 and max(lefts) < 35 else (
            "moves in place" if max(shifts) < 2 else "mixed")
        print(f"{name:12s} {' '.join(f'f{f}:{s:+d}/{x}%' for f, s, x in res)}  -> {kind}")

        # zoomed strip: original idle frames | mod breathing pose with cut lines
        scale = 3
        cells = [full_render(shp_o[f], sheet, BOX) for f in order]
        cells.append(full_render(shp_m[13], sheet, BOX))
        cells = [x.resize((x.width * scale // 2, x.height * scale // 2), Image.NEAREST) for x in cells]
        cw, ch = cells[0].size
        strip = Image.new("RGBA", (cw * len(cells), ch + 20), c.BG)
        d = ImageDraw.Draw(strip)
        for i, cell in enumerate(cells):
            strip.alpha_composite(cell, (cw * i, 20))
            label = f"orig f{order[i]}" if i < len(order) else "mod breath"
            d.text((cw * i + 4, 4), label, fill="white")
        # cut lines of the 48x48 block (y = 79 + 16, and the moving/planted line at `line`)
        for y_canvas, col in ((79 + 16, (120, 200, 255)), (line, (255, 96, 160))):
            y = (y_canvas * 2 - BOX[1]) * scale // 2 + 20
            x0 = cw * len(order)
            for x in range(x0, x0 + cw, 10):
                d.line((x, y, x + 5, y), fill=col, width=2)
        strip.save(os.path.join(out_dir, f"strip_{name}.png"))


if __name__ == "__main__":
    main()
