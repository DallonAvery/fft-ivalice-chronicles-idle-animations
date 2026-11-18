"""Animated, zoomed comparison of idle options for monster sheets (all share one layout).

Columns: original game idle | current mod (cut at the lower line) |
         option: only the top strip moves | option: whole body bobs 1 px
All columns use real timing (1 tick = 1/60 s). Front-facing idle only.

Usage: python idle_options_preview.py <out.gif> <zoom> <sheet> [sheet ...]
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import breath  # noqa: E402
import build_mods  # noqa: E402
import compare_idle as c  # noqa: E402
import shp_render as r  # noqa: E402
from breath_preview_multi import full_render  # noqa: E402

BOX = (40, 120, 200, 280)


def main():
    out, zoom, *sheets = sys.argv[1:]
    zoom = int(zoom)
    shp_o = r.parse_shp(open(os.path.join(c.ORIG, "battle_mon_shp.bin"), "rb").read())
    orig_line = c.timeline(os.path.join(c.ORIG, "battle_mon_seq.bin"), 6)
    mod_loop = []
    for pose, d in build_mods.BREATH_LOOP["normal"]:
        mod_loop += [pose] * d
    stand = shp_o[2]
    variants = {
        "current mod": breath.breath_tiles(stand, build_mods.FAMILIES["mon"]["line"], 1),
        "top strip only": breath.breath_tiles(stand, 79 + 16, 1),
        "whole body bob": breath.breath_tiles(stand, 999, 1),
    }
    cols = ["original game", "current mod", "top strip only", "whole body bob"]
    W, H = (BOX[2] - BOX[0]) * zoom // 2, (BOX[3] - BOX[1]) * zoom // 2
    rows = []
    for path in sheets:
        name, sheet = c.load_pair(path)
        cache = {}

        def img(key, tiles, sheet=sheet, cache=cache):
            if key not in cache:
                x = full_render(tiles, sheet, BOX)
                cache[key] = x.resize((W, H), Image.NEAREST)
            return cache[key]

        rows.append((name, img))

    frames, durations, prev = [], [], None
    for t in range(0, 64, 1):
        of = orig_line[t]
        mp = mod_loop[t]
        key = (of, mp)
        if key == prev:
            durations[-1] += 1000 / 60
            continue
        prev = key
        canvas = Image.new("RGBA", (W * 4, (H + 20) * len(rows) + 24), c.BG)
        d = ImageDraw.Draw(canvas)
        for j, label in enumerate(cols):
            d.text((W * j + 8, 6), label, fill=(255, 210, 120, 255))
        for i, (name, img) in enumerate(rows):
            y = 24 + i * (H + 20)
            d.text((8, y + 3), name, fill="white")
            canvas.alpha_composite(img(("o", of), shp_o[of]), (0, y + 20))
            for j, label in enumerate(cols[1:], start=1):
                tiles = stand if mp == "s" else variants[label]
                canvas.alpha_composite(img((label, mp), tiles), (W * j, y + 20))
        frames.append(canvas.convert("P", palette=Image.ADAPTIVE))
        durations.append(1000 / 60)
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=[max(20, round(x)) for x in durations], loop=0)
    print("wrote", out, len(frames), "frames", os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
