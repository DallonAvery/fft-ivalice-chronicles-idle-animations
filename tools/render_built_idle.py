"""Render the breathing idle exactly as the built mod defines it, for each animation set
with its layout, dry and in water, by reading the idle animation (6 front / 7 back) from
the built SEQ file and its frames from the built SHP file.

Usage: python render_built_idle.py <mod unit dir> <out.png>
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_mods as bm  # noqa: E402
import compare_idle as c  # noqa: E402
import seq_decode as q  # noqa: E402
import shp_render as r  # noqa: E402
from breath_preview_multi import full_render  # noqa: E402

SHEETS = os.path.join(os.path.dirname(HERE), "extracted_sprites")
CASES = [  # (animation set, layout, sheet)
    ("type1", "type1", "1000_Knight_Male"),
    ("type4", "type1", "1012_White_Mage_Male"),
    ("type2", "type2", "1062_Dancer_Female"),
    ("type3", "type2", "1002_Knight_Female"),
    ("cyoko", "cyoko", "1068_Chocobo"),
    ("mon", "mon", "1072_Bomb"),
    ("mon", "mon", "1094_Behemoth"),
]


def idle_frames(seq, anim):
    raw = {i: x for i, _, x in q.animations(seq)}[anim]
    out = []
    for s in q.decode(raw):
        if s[0] == "frame" and s[1] not in out:
            out.append(s[1])
    return out


def main():
    unit, out = sys.argv[1:]
    rows = []
    for seqname, lay, sheetname in CASES:
        seq = open(os.path.join(unit, f"battle_{seqname}_seq.bin"), "rb").read()
        shp = open(os.path.join(unit, f"battle_{lay}_shp.bin"), "rb").read()
        frames = r.parse_shp(shp)
        first = len(bm.frame_offsets(shp))
        has_water = r.u32(shp, 0) > 8
        _, sheet = c.load_pair(os.path.join(SHEETS, sheetname + "_hd.png"))
        cells = []
        for anim, facing in ((6, "front"), (7, "back")):
            for f in idle_frames(seq, anim):
                cells.append((f"{facing} f{f}", frames[f]))
                if has_water:
                    cells.append((f"{facing} f{f} water", frames[first + f]))
        rows.append((f"{seqname} animations on {lay} layout ({sheetname})", cells, sheet))
    W, H = 170, 170
    cols = max(len(cr[1]) for cr in rows)
    img = Image.new("RGBA", (W * cols, (H + 34) * len(rows)), (32, 36, 44, 255))
    d = ImageDraw.Draw(img)
    for i, (title, cells, sheet) in enumerate(rows):
        y = i * (H + 34)
        d.text((4, y + 2), title, fill=(255, 210, 120))
        for j, (label, tiles) in enumerate(cells):
            pic = full_render(tiles, sheet, (30, 120, 200, 290))
            img.alpha_composite(pic, (W * j, y + 34))
            d.text((W * j + 4, y + 18), label, fill="white")
    img.save(out)
    print("wrote", out, img.size)


if __name__ == "__main__":
    main()
