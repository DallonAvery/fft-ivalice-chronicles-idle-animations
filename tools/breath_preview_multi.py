"""Preview breathing frames for several sprite sheets that share one SHP layout.

Usage: python breath_preview_multi.py <shp> <threshold> <out.png> <front frame> <back frame> <sheet> [sheet ...]
  <sheet> is the first of the toolkit's two PNGs (e.g. 1094_Behemoth_hd.png); the
  second is found automatically. Writes a PNG (standing vs breathing, zoomed) and a GIF.
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import breath  # noqa: E402
import shp_render as r  # noqa: E402


def full_render(tiles, sheet, box):
    img = Image.new("RGBA", (r.CANVAS[0] * 2, r.CANVAS[1] * 2), (0, 0, 0, 0))
    for t in tiles:
        sx, sy = t["src"]
        w, h = t["size"]
        p = sheet.crop((sx * 2, sy * 2, (sx + w) * 2, (sy + h) * 2))
        if t["fx"]:
            p = p.transpose(Image.FLIP_LEFT_RIGHT)
        if t["fy"]:
            p = p.transpose(Image.FLIP_TOP_BOTTOM)
        img.alpha_composite(p, (t["dst"][0] * 2, t["dst"][1] * 2))
    return img.crop(box)


def main():
    shp, threshold, out, front, back, *sheets = sys.argv[1:]
    threshold, front, back = int(threshold), int(front), int(back)
    frames = r.parse_shp(open(shp, "rb").read())
    box = (40, 140, 200, 280)
    rows, gif_frames = [], [[], []]
    for path in sheets:
        base = os.path.basename(path)
        num = base.split("_")[0]
        second = os.path.join(os.path.dirname(path), str(int(num) + 1) + base[len(num):])
        sheet = r.load_sheet(path, second)
        cells = []
        for f in (front, back):
            stand = full_render(frames[f], sheet, box)
            br = full_render(breath.breath_tiles(frames[f], threshold, 1), sheet, box)
            cells += [stand, br]
        rows.append((base[len(num) + 1:-7], cells))
    W, H = 160, 140
    sheet_img = Image.new("RGBA", (W * 4, (H + 16) * len(rows)), (40, 44, 52, 255))
    d = ImageDraw.Draw(sheet_img)
    for i, (name, cells) in enumerate(rows):
        for j, c in enumerate(cells):
            sheet_img.alpha_composite(c, (W * j, (H + 16) * i + 16))
        d.text((3, (H + 16) * i + 2), f"{name}: front stand | front breath | back stand | back breath",
               fill="white")
    sheet_img.save(out)
    # animated: standing 36 ticks, breathing 28 ticks
    for phase in (0, 1):
        frame = Image.new("RGBA", (W * 2, H * len(rows)), (40, 44, 52, 255))
        for i, (_, cells) in enumerate(rows):
            frame.alpha_composite(cells[phase], (0, H * i))
            frame.alpha_composite(cells[2 + phase], (W, H * i))
        gif_frames[phase] = frame.convert("P", palette=Image.ADAPTIVE)
    gif_frames[0].save(out[:-4] + ".gif", save_all=True, append_images=[gif_frames[1]],
                       duration=[600, 470], loop=0)
    print("wrote", out)


if __name__ == "__main__":
    main()
