"""Side-by-side animated comparison of the original idle and the modded idle.

For each sprite sheet: column 1 = original game files, column 2 = the mod's files,
for the front idle (animation 6) and back idle (animation 7). Also prints how far
each sheet's sprite moves up and down during the ORIGINAL idle, which tells
floating creatures (whole body bobs) apart from standing ones (feet stay put).

Usage:
  python compare_idle.py <family> <out.gif> <sheet> [sheet ...]
    family: mon | cyoko | type1 | type2   (SEQ and SHP names; mod = Breathing (All Units))
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_mods  # noqa: E402
import seq_decode  # noqa: E402
import shp_render as r  # noqa: E402
from breath_preview_multi import full_render  # noqa: E402

ORIG = os.path.join(ROOT, "unpacked", "fftpack", "unit")
MOD = os.path.join(ROOT, "mods", build_mods.VARIANTS["breathing_all"]["mod_id"],
                   "FFTIVC", "data", "combined", "fftpack", "unit")
BG = (32, 36, 44, 255)


def timeline(seq_path, anim):
    data = open(seq_path, "rb").read()
    raw = {i: x for i, _, x in seq_decode.animations(data)}[anim]
    ticks = []
    for s in seq_decode.decode(raw):
        if s[0] == "frame":
            ticks += [s[1]] * s[2]
    return ticks


def load_pair(path):
    base = os.path.basename(path)
    num = base.split("_")[0]
    return base[len(num) + 1:-7], r.load_sheet(path, os.path.join(os.path.dirname(path),
                                                                  str(int(num) + 1) + base[len(num):]))


def main():
    family, out, *sheets = sys.argv[1:]
    seq = {"mon": "mon", "cyoko": "cyoko", "type1": "type1", "type2": "type2"}[family]
    shp_o = r.parse_shp(open(os.path.join(ORIG, f"battle_{family}_shp.bin"), "rb").read())
    shp_m = r.parse_shp(open(os.path.join(MOD, f"battle_{family}_shp.bin"), "rb").read())
    lines = {}
    for anim in (6, 7):
        lines[("orig", anim)] = timeline(os.path.join(ORIG, f"battle_{seq}_seq.bin"), anim)
        lines[("mod", anim)] = timeline(os.path.join(MOD, f"battle_{seq}_seq.bin"), anim)
    total = max(len(v) for v in lines.values())

    box = (40, 120, 200, 280)
    W, H = box[2] - box[0], box[3] - box[1]
    rows = []
    print(f"{'sheet':22s} original idle: bottom edge moves / top edge moves (sprite pixels)")
    for path in sheets:
        name, sheet = load_pair(path)
        cache = {}

        def img(which, f):
            key = (which, f)
            if key not in cache:
                cache[key] = full_render((shp_o if which == "orig" else shp_m)[f], sheet, box)
            return cache[key]

        # float metric on the original front idle
        bottoms, tops = [], []
        for f in set(lines[("orig", 6)]):
            bb = img("orig", f).getbbox()
            if bb:
                tops.append(bb[1])
                bottoms.append(bb[3])
        print(f"{name:22s} {(max(bottoms) - min(bottoms)) / 2:4.1f} / {(max(tops) - min(tops)) / 2:4.1f}")
        rows.append((name, img))

    cols = [("orig", 6, "original front"), ("mod", 6, "mod front"),
            ("orig", 7, "original back"), ("mod", 7, "mod back")]
    frames, durations = [], []
    prev = None
    for t in range(0, total, 2):
        key = tuple(lines[(w, a)][t % len(lines[(w, a)])] for w, a, _ in cols)
        if key == prev:
            durations[-1] += 33
            continue
        prev = key
        canvas = Image.new("RGBA", (W * 4, (H + 18) * len(rows) + 22), BG)
        d = ImageDraw.Draw(canvas)
        for j, (_, _, label) in enumerate(cols):
            d.text((W * j + 6, 4), label, fill=(255, 210, 120, 255))
        for i, (name, img) in enumerate(rows):
            y = 22 + i * (H + 18)
            d.text((6, y + 2), name, fill="white")
            for j, (which, anim, _) in enumerate(cols):
                canvas.alpha_composite(img(which, key[j]), (W * j, y + 18))
        frames.append(canvas.convert("P", palette=Image.ADAPTIVE))
        durations.append(33)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations, loop=0)
    print("wrote", out, len(frames), "frames")


if __name__ == "__main__":
    main()
