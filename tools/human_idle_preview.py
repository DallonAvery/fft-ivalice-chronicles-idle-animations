"""Mock up richer human idle loops built from the standing pose's own pixels.

The 32x40 standing block is cut into horizontal strips (heights the SHP format
allows for 32-wide blocks: 8, 16, 24, 32, 40) and each strip is drawn some pixels
lower. Lower strips are drawn first so upper strips overlap them (no gaps).

Poses (strips from the top: (height, pixels lower)):
  stand  standing pose, untouched
  head   head and shoulders settle 1 px            [(16,1),(24,0)]
  chest  head, shoulders and chest settle 1 px     [(24,1),(16,0)]   <- current mod
  deep   head 2 px, chest 1 px                      [(16,2),(8,1),(16,0)]

Usage: python human_idle_preview.py <out.gif> <zoom> <sheet> [sheet ...]
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_idle as c  # noqa: E402
import shp_render as r  # noqa: E402
from breath_preview_multi import full_render  # noqa: E402

POSES = {
    "head": [(16, 1), (24, 0)],
    "chest": [(24, 1), (16, 0)],
    "deep": [(16, 2), (8, 1), (16, 0)],
}
# 8 steps each, 64 ticks (normal idle speed)
VARIANTS = {
    "current mod": [("stand", 16), ("stand", 16), ("stand", 4), ("chest", 8), ("chest", 8),
                    ("chest", 8), ("chest", 2), ("stand", 2)],
    "smooth (head leads)": [("stand", 16), ("head", 4), ("chest", 8), ("chest", 10), ("chest", 6),
                            ("head", 4), ("stand", 8), ("stand", 8)],
    "deep breath": [("stand", 14), ("head", 4), ("chest", 4), ("deep", 10), ("deep", 6),
                    ("chest", 4), ("head", 4), ("stand", 18)],
}
BOX = (50, 140, 170, 270)


def strips(tile, spec):
    (sx, sy), (dx, dy) = tile["src"], tile["dst"]
    out, y = [], 0
    for h, sink in spec:
        out.append(dict(tile, src=(sx, sy + y), size=(32, h), dst=(dx, dy + y + sink)))
        y += h
    assert y == 40
    return list(reversed(out))  # bottom strips first, upper strips drawn over them


def main():
    out, zoom, *sheets = sys.argv[1:]
    zoom = int(zoom)
    shp = r.parse_shp(open(os.path.join(c.ORIG, "battle_type1_shp.bin"), "rb").read())
    W, H = (BOX[2] - BOX[0]) * zoom // 2, (BOX[3] - BOX[1]) * zoom // 2
    names = list(VARIANTS)
    timelines = {}
    for v, loop in VARIANTS.items():
        t = []
        for pose, d in loop:
            t += [pose] * d
        timelines[v] = t
    chars = []
    for path in sheets:
        name, sheet = c.load_pair(path)
        poses = {}
        for facing, f in (("front", 2), ("back", 8)):
            (tile,) = shp[f]
            poses[(facing, "stand")] = [tile]
            for p, spec in POSES.items():
                poses[(facing, p)] = strips(tile, spec)
        cache = {}

        def img(facing, pose, poses=poses, sheet=sheet, cache=cache):
            k = (facing, pose)
            if k not in cache:
                cache[k] = full_render(poses[k], sheet, BOX).resize((W, H), Image.NEAREST)
            return cache[k]

        chars.append((name.replace("_", " "), img))

    cols = len(names) * 2
    frames, durations, prev = [], [], None
    for t in range(64):
        key = tuple(timelines[v][t] for v in names)
        if key == prev:
            durations[-1] += 1000 / 60
            continue
        prev = key
        canvas = Image.new("RGBA", (W * cols, 26 + (H + 18) * len(chars)), c.BG)
        d = ImageDraw.Draw(canvas)
        for j, v in enumerate(names):
            d.text((W * 2 * j + 8, 6), v, fill=(255, 210, 120, 255))
            d.line((W * 2 * j, 0, W * 2 * j, canvas.height), fill=(70, 76, 90, 255))
        for i, (name, img) in enumerate(chars):
            y = 26 + i * (H + 18)
            d.text((8, y + 2), name, fill="white")
            for j, v in enumerate(names):
                for k, facing in enumerate(("front", "back")):
                    canvas.alpha_composite(img(facing, key[j]), (W * (2 * j + k), y + 16))
        frames.append(canvas.convert("P", palette=Image.ADAPTIVE))
        durations.append(1000 / 60)
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=[max(20, round(x)) for x in durations], loop=0)
    print("wrote", out, len(frames), "frames", os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
