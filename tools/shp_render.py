"""Render FFT battle SHP frames and SEQ animations from the toolkit's HD sprite sheets.

SHP layout follows ShishiSpriteEditor (Glain/FFTPatcher: Shape.cs, Frame.cs, Tile.cs).
The toolkit's HD sheets are the original 256x488 sheet at 2x, split in two PNGs
(top 256 rows, then the rest), so every coordinate is doubled.

Usage:
  python shp_render.py <shp> <seq> <sheet_top.png> <sheet_bottom.png> <outdir> <anim> [anim ...]
Writes frames.png (a numbered contact sheet of the frames those animations use)
and anim_<n>.gif for each animation.
"""
import os
import struct
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seq_decode  # noqa: E402

SCALE = 2
SIZES = [(8, 8), (16, 8), (16, 16), (16, 24), (24, 8), (24, 16), (24, 24), (32, 8),
         (32, 16), (32, 24), (32, 32), (32, 40), (48, 16), (40, 32), (48, 48), (56, 56)]
CANVAS = (185, 250)


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def parse_tiles(b, off, yoff):
    n = b[off] | b[off + 1] << 8
    tiles = []
    for i in range(n + 1):
        x, y, lo, hi = struct.unpack_from("<bbBB", b, off + 2 + i * 4)
        flags = lo | hi << 8
        w, h = SIZES[(flags >> 10) & 0x0F]
        tiles.append(dict(dst=(x + 53, y + 118), src=((flags & 0x1F) * 8, ((flags >> 5) & 0x1F) * 8 + yoff),
                          size=(w, h), fx=bool(flags & 0x4000), fy=bool(flags & 0x8000)))
    tiles.reverse()
    return tiles


def parse_shp(b):
    jump = u32(b, 0)
    second_half = b[4] | b[5] << 8
    offs, i = [0], 0
    while True:
        a = u32(b, 0x0C + 4 * i)
        i += 1
        if not a:
            break
        offs.append(a)
    frames = [parse_tiles(b, o + 0x40A, 256 if k >= second_half else 0) for k, o in enumerate(offs)]
    if jump > 8:
        offs, i = [0], 0
        while True:
            a = u32(b, jump + 4 * i + 4)
            i += 1
            if not a:
                break
            offs.append(a)
        frames += [parse_tiles(b, o + jump + 0x402, 256 if k >= second_half else 0) for k, o in enumerate(offs)]
    return frames


def load_sheet(top, bottom):
    t, btm = Image.open(top).convert("RGBA"), Image.open(bottom).convert("RGBA")
    sheet = Image.new("RGBA", (t.width, t.height + btm.height))
    sheet.paste(t, (0, 0))
    sheet.paste(btm, (0, t.height))
    # palette index 0 is transparent; the toolkit's PNGs show it as black
    px = sheet.load()
    for yy in range(sheet.height):
        for xx in range(sheet.width):
            r, g, b_, a = px[xx, yy]
            if r == 0 and g == 0 and b_ == 0:
                px[xx, yy] = (0, 0, 0, 0)
    return sheet


def render(frame, sheet):
    img = Image.new("RGBA", (CANVAS[0] * SCALE, CANVAS[1] * SCALE), (0, 0, 0, 0))
    for t in frame:
        sx, sy = t["src"]
        w, h = t["size"]
        piece = sheet.crop((sx * SCALE, sy * SCALE, (sx + w) * SCALE, (sy + h) * SCALE))
        if t["fx"]:
            piece = piece.transpose(Image.FLIP_LEFT_RIGHT)
        if t["fy"]:
            piece = piece.transpose(Image.FLIP_TOP_BOTTOM)
        img.alpha_composite(piece, (t["dst"][0] * SCALE, t["dst"][1] * SCALE))
    # crop to the area a standing unit occupies (tiles are placed around x 53, y 118)
    return img.crop((13 * SCALE, 58 * SCALE, 93 * SCALE, 138 * SCALE))


def main():
    shp, seq, top, bottom, outdir, *anims = sys.argv[1:]
    anims = [int(a, 0) for a in anims]
    os.makedirs(outdir, exist_ok=True)
    frames = parse_shp(open(shp, "rb").read())
    sheet = load_sheet(top, bottom)
    seqdata = open(seq, "rb").read()
    steps_by_anim = {i: seq_decode.decode(raw) for i, _, raw in seq_decode.animations(seqdata) if i in anims}

    used = sorted({s[1] for st in steps_by_anim.values() for s in st if s[0] == "frame"})
    cells = [render(frames[f], sheet) for f in used]
    cw, ch = cells[0].size
    cols = min(len(cells), 8)
    rows = (len(cells) + cols - 1) // cols
    contact = Image.new("RGBA", (cw * cols, (ch + 24) * rows), (40, 44, 52, 255))
    d = ImageDraw.Draw(contact)
    for k, (f, c) in enumerate(zip(used, cells)):
        x, y = (k % cols) * cw, (k // cols) * (ch + 24)
        contact.alpha_composite(c, (x, y + 24))
        d.text((x + 6, y + 6), f"frame {f}", fill=(255, 255, 255, 255))
    contact.save(os.path.join(outdir, "frames.png"))

    for a, st in steps_by_anim.items():
        imgs, durs = [], []
        for s in st:
            if s[0] != "frame":
                continue
            bg = Image.new("RGBA", (cw, ch), (40, 44, 52, 255))
            bg.alpha_composite(render(frames[s[1]], sheet))
            imgs.append(bg.convert("P", palette=Image.ADAPTIVE))
            durs.append(max(20, round(s[2] * 1000 / 60)))
        if imgs:
            imgs[0].save(os.path.join(outdir, f"anim_{a}.gif"), save_all=True,
                         append_images=imgs[1:], duration=durs, loop=0, disposal=2)
    print(f"{len(frames)} SHP frames; rendered frames {used} -> {outdir}")


if __name__ == "__main__":
    main()
