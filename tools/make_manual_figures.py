"""Render the figures used by docs/IdleAnimations_Manual.html into docs/img.

Usage: python make_manual_figures.py
(paths are relative to the project folder this script lives in)
"""
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build_mods  # noqa: E402
import shp_render as r  # noqa: E402

UNIT = os.path.join(ROOT, "unpacked", "fftpack", "unit")
SHEETS = os.path.join(ROOT, "extracted_sprites")
MOD_ALL = os.path.join(ROOT, "mods", build_mods.VARIANTS["breathing_all"]["mod_id"],
                       "FFTIVC", "data", "combined", "fftpack", "unit")
OUT = os.path.join(ROOT, "docs", "img")
BG = (32, 36, 44, 255)
COLORS = [(255, 196, 0), (64, 200, 255), (255, 96, 160), (120, 230, 120), (255, 140, 60),
          (180, 140, 255), (255, 255, 255), (0, 220, 180)]


def sheet(num, name):
    return r.load_sheet(os.path.join(SHEETS, f"{num}_{name}_hd.png"),
                        os.path.join(SHEETS, f"{num + 1}_{name}_hd.png"))


def shp(path):
    return r.parse_shp(open(path, "rb").read())


def render_full(tiles, sh, scale=2):
    img = Image.new("RGBA", (r.CANVAS[0] * 2, r.CANVAS[1] * 2), (0, 0, 0, 0))
    for t in tiles:
        sx, sy = t["src"]
        w, h = t["size"]
        p = sh.crop((sx * 2, sy * 2, (sx + w) * 2, (sy + h) * 2))
        if t["fx"]:
            p = p.transpose(Image.FLIP_LEFT_RIGHT)
        if t["fy"]:
            p = p.transpose(Image.FLIP_TOP_BOTTOM)
        img.alpha_composite(p, (t["dst"][0] * 2, t["dst"][1] * 2))
    if scale != 2:
        img = img.resize((img.width * scale // 2, img.height * scale // 2), Image.NEAREST)
    return img


def outline(img, tiles, scale):
    d = ImageDraw.Draw(img)
    for i, t in enumerate(t for t in tiles if 0 <= t["dst"][0] < 150 and 0 <= t["dst"][1] < 200):
        (dx, dy), (w, h) = t["dst"], t["size"]
        d.rectangle((dx * scale, dy * scale, (dx + w) * scale - 1, (dy + h) * scale - 1),
                    outline=COLORS[i % len(COLORS)], width=2)
    return img


def bbox_crop(imgs, pad=16):
    boxes = [i.getbbox() for i in imgs if i.getbbox()]
    x0 = min(b[0] for b in boxes) - pad
    y0 = min(b[1] for b in boxes) - pad
    x1 = max(b[2] for b in boxes) + pad
    y1 = max(b[3] for b in boxes) + pad
    return [i.crop((max(0, x0), max(0, y0), x1, y1)) for i in imgs]


def on_bg(img):
    bg = Image.new("RGBA", img.size, BG)
    bg.alpha_composite(img)
    return bg


def body_types():
    """One standing pose per body type, scaled 3x, with each SHP tile outlined."""
    scale = 3
    items = [
        ("Human (TYPE1-4)", shp(os.path.join(UNIT, "battle_type1_shp.bin"))[2], sheet(1000, "Knight_Male")),
        ("Chocobo (CYOKO)", shp(os.path.join(UNIT, "battle_cyoko_shp.bin"))[2], sheet(1068, "Chocobo")),
        ("Monster (MON)", shp(os.path.join(UNIT, "battle_mon_shp.bin"))[2], sheet(1094, "Behemoth")),
        ("Altima, 2nd form (KANZEN)", shp(os.path.join(UNIT, "battle_kanzen_shp.bin"))[1],
         sheet(952, "Altima_Second_Form")),
    ]
    cells = []
    for _, tiles, sh in items:
        img = render_full(tiles, sh, scale)
        cells.append(outline(img, tiles, scale))
    out_cells = []
    for c in cells:
        bb = c.getbbox()
        out_cells.append(c.crop((bb[0] - 12, bb[1] - 12, bb[2] + 12, bb[3] + 12)))
    h = max(c.height for c in out_cells)
    w = sum(c.width for c in out_cells) + 24 * (len(out_cells) - 1)
    out = Image.new("RGBA", (w, h), BG)
    x = 0
    for c in out_cells:
        out.alpha_composite(c, (x, h - c.height))
        x += c.width + 24
    out.save(os.path.join(OUT, "body_types.png"))


def sheet_to_frame():
    """Top-left of the Knight's sprite sheet with the standing-pose block highlighted."""
    sh = sheet(1000, "Knight_Male")
    crop = sh.crop((0, 0, 256 * 2, 96 * 2))
    img = Image.new("RGBA", crop.size, BG)
    img.alpha_composite(crop)
    d = ImageDraw.Draw(img)
    d.rectangle((32 * 2, 0, 64 * 2 - 1, 40 * 2 - 1), outline=COLORS[0], width=3)
    d.rectangle((96 * 2, 0, 128 * 2 - 1, 40 * 2 - 1), outline=COLORS[1], width=3)
    img.save(os.path.join(OUT, "sheet_blocks.png"))


def walk_in_place():
    """The original idle (animation 6) and the frames it uses."""
    frames = shp(os.path.join(UNIT, "battle_type1_shp.bin"))
    sh = sheet(1000, "Knight_Male")
    steps = [(11, 6), (10, 8), (9, 10), (10, 8), (11, 6), (12, 8), (13, 10), (12, 8)]
    imgs = bbox_crop([render_full(frames[f], sh, 4) for f, _ in steps], pad=20)
    seq = [on_bg(i).convert("P", palette=Image.ADAPTIVE) for i in imgs]
    seq[0].save(os.path.join(OUT, "idle_original.gif"), save_all=True, append_images=seq[1:],
                duration=[round(d * 1000 / 60) for _, d in steps], loop=0, disposal=2)
    strip_frames = bbox_crop([render_full(frames[f], sh, 3) for f in (9, 10, 11, 12, 13)], pad=10)
    w = sum(i.width for i in strip_frames)
    strip = Image.new("RGBA", (w, strip_frames[0].height), BG)
    x = 0
    for i in strip_frames:
        strip.alpha_composite(i, (x, 0))
        x += i.width
    strip.save(os.path.join(OUT, "walk_frames.png"))


def breathing_split():
    """Standing pose vs breathing pose, with the cut line marked."""
    frames = shp(os.path.join(MOD_ALL, "battle_type1_shp.bin"))
    sh = sheet(1000, "Knight_Male")
    slot = build_mods.FAMILIES["type1"]["slots"]["front"]
    a, b = bbox_crop([render_full(frames[2], sh, 6), render_full(frames[slot], sh, 6)], pad=24)
    gap = 60
    out = Image.new("RGBA", (a.width * 2 + gap, a.height), BG)
    out.alpha_composite(a, (0, 0))
    out.alpha_composite(b, (a.width + gap, 0))
    full = render_full(frames[2], sh, 6)
    top = full.getbbox()[1] - 24
    cut_y = build_mods.HUMAN_LINE * 6 - max(0, top)
    d = ImageDraw.Draw(out)
    for x0 in (0, a.width + gap):
        for x in range(x0, x0 + a.width, 12):
            d.line((x, cut_y, x + 6, cut_y), fill=COLORS[2], width=2)
    out.save(os.path.join(OUT, "breath_split.png"))


def water_frames():
    """Standing and breathing poses from the dry and the in-water frame lists."""
    data = open(os.path.join(MOD_ALL, "battle_type1_shp.bin"), "rb").read()
    frames = r.parse_shp(data)
    first = len(build_mods.frame_offsets(data))
    slot = build_mods.FAMILIES["type1"]["slots"]["front"]
    sh = sheet(1000, "Knight_Male")
    picks = [frames[2], frames[slot], frames[first + 2], frames[first + slot]]
    imgs = bbox_crop([render_full(t, sh, 4) for t in picks], pad=16)
    gap = 48
    out = Image.new("RGBA", (sum(i.width for i in imgs) + gap, imgs[0].height), BG)
    x = 0
    for n, i in enumerate(imgs):
        out.alpha_composite(i, (x, 0))
        x += i.width + (gap if n == 1 else 0)
    out.save(os.path.join(OUT, "water_frames.png"))


def breathing_showcase():
    """Animated breathing loop (normal speed) from the finished 'All Units' mod files."""
    loop = build_mods.BREATH_LOOP["normal"]
    slot = {k: f["slots"]["front"] for k, f in build_mods.FAMILIES.items()}
    cast = [
        ("type1", 2, slot["type1"], sheet(1000, "Knight_Male")),
        ("type2", 2, slot["type2"], sheet(1062, "Dancer_Female")),
        ("cyoko", 2, slot["cyoko"], sheet(1068, "Chocobo")),
        ("mon", 2, slot["mon"], sheet(1094, "Behemoth")),
        ("mon", 2, slot["mon"], sheet(1072, "Bomb")),
        ("mon", 2, slot["mon"], sheet(1096, "Dragon")),
    ]
    poses = []
    for fam, stand, br, sh in cast:
        frames = shp(os.path.join(MOD_ALL, f"battle_{fam}_shp.bin"))
        s_img, b_img = bbox_crop([render_full(frames[stand], sh, 3), render_full(frames[br], sh, 3)], pad=8)
        poses.append((s_img, b_img))
    h = max(p[0].height for p in poses)
    w = sum(p[0].width for p in poses)

    def composite(which):
        img = Image.new("RGBA", (w, h), BG)
        x = 0
        for s_img, b_img in poses:
            pic = s_img if which == "s" else b_img
            img.alpha_composite(pic, (x, h - pic.height))
            x += pic.width
        return img.convert("P", palette=Image.ADAPTIVE)

    frames_out, durations = [], []
    for pose, delay in loop:
        if frames_out and durations and frames_out[-1][0] == pose:
            durations[-1] += delay
            continue
        frames_out.append((pose, composite(pose)))
        durations.append(delay)
    imgs = [f for _, f in frames_out]
    imgs[0].save(os.path.join(OUT, "breathing_showcase.gif"), save_all=True, append_images=imgs[1:],
                 duration=[round(d * 1000 / 60) for d in durations], loop=0)


def main():
    os.makedirs(OUT, exist_ok=True)
    body_types()
    sheet_to_frame()
    walk_in_place()
    breathing_split()
    water_frames()
    breathing_showcase()
    for f in sorted(os.listdir(OUT)):
        print(f, os.path.getsize(os.path.join(OUT, f)))


if __name__ == "__main__":
    main()
