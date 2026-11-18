"""Render a before/after GIF for the mod page: the original idle (walking in place) above
the Still (Everyone) idle, for a few body types, from the original and the built files.

Usage: python make_nexus_images.py   (writes release/before_after_still.gif)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_mods  # noqa: E402
import seq_decode as q  # noqa: E402
from make_manual_figures import BG, bbox_crop, render_full, sheet, shp  # noqa: E402

UNIT = os.path.join(ROOT, "unpacked", "fftpack", "unit")
STILL = os.path.join(ROOT, "mods", build_mods.VARIANTS["still"]["mod_id"],
                     "FFTIVC", "data", "combined", "fftpack", "unit")
OUT = os.path.join(ROOT, "release")
CAST = [  # (animation set, layout, sheet number, sheet name)
    ("type1", "type1", 1000, "Knight_Male"),
    ("type2", "type2", 1062, "Dancer_Female"),
    ("cyoko", "cyoko", 1068, "Chocobo"),
    ("mon", "mon", 1094, "Behemoth"),
]
SCALE = 3


def idle_steps(path):
    seq = open(path, "rb").read()
    raw = {i: x for i, _, x in q.animations(seq)}[6]
    return [(s[1], s[2]) for s in q.decode(raw) if s[0] == "frame"]


def frame_at(steps, tick):
    total = sum(d for _, d in steps)
    t = tick % total
    for f, d in steps:
        if t < d:
            return f
        t -= d
    return steps[-1][0]


def font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", name), size)
        except OSError:
            pass
    return ImageFont.load_default()


def main():
    os.makedirs(OUT, exist_ok=True)
    units = []
    for seqname, lay, num, name in CAST:
        frames = shp(os.path.join(UNIT, f"battle_{lay}_shp.bin"))
        sh = sheet(num, name)
        before = idle_steps(os.path.join(UNIT, f"battle_{seqname}_seq.bin"))
        after = idle_steps(os.path.join(STILL, f"battle_{seqname}_seq.bin"))
        used = sorted({f for f, _ in before + after})
        pics = dict(zip(used, bbox_crop([render_full(frames[f], sh, SCALE) for f in used], pad=10)))
        units.append((before, after, pics))
    cell_w = max(p.width for _, _, pics in units for p in pics.values())
    cell_h = max(p.height for _, _, pics in units for p in pics.values())
    label_w, title_h = 230, 0
    W, H = label_w + cell_w * len(units), cell_h * 2 + 12
    f = font(26)
    total = max(sum(d for _, d in b) for b, _, _ in units)
    # one GIF frame per tick where anything changes
    changes = sorted({0} | {t for b, a, _ in units for steps in (b, a)
                            for t in range(total) if frame_at(steps, t) != frame_at(steps, t - 1)})
    imgs, durations = [], []
    for i, t in enumerate(changes):
        img = Image.new("RGBA", (W, H), BG)
        d = ImageDraw.Draw(img)
        for row, label in enumerate(("Original", "Still")):
            y = row * (cell_h + 12)
            d.text((20, y + cell_h // 2), label, font=f, fill=(255, 210, 120) if row else (200, 200, 200),
                   anchor="lm")
            for j, (before, after, pics) in enumerate(units):
                pic = pics[frame_at(after if row else before, t)]
                img.alpha_composite(pic, (label_w + j * cell_w + (cell_w - pic.width) // 2, y + cell_h - pic.height))
        if row == 1:
            d.line((16, cell_h + 6, W - 16, cell_h + 6), fill=(70, 76, 88), width=2)
        imgs.append(img.convert("P", palette=Image.ADAPTIVE))
        nxt = changes[i + 1] if i + 1 < len(changes) else total
        durations.append(round((nxt - t) * 1000 / 60))
    dst = os.path.join(OUT, "before_after_still.gif")
    imgs[0].save(dst, save_all=True, append_images=imgs[1:], duration=durations, loop=0)
    print(dst, (W, H), len(imgs), "frames")


if __name__ == "__main__":
    main()
