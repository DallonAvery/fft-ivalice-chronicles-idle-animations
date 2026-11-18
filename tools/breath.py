"""Build a 'breathing' version of an SHP frame from its own tiles.

Tiles whose top is above `threshold` (a canvas y coordinate) are drawn `sink` pixels
lower; tiles below it stay where they are, so feet and legs stay planted. A tile that
straddles the threshold is cut into horizontal strips (only sizes the SHP format
supports) so the part above the line can move on its own.
"""
import struct

from shp_render import SIZES

SIZE_INDEX = {size: i for i, size in enumerate(SIZES)}


def strip_heights(width, height, cut):
    """Heights that split a tile at row `cut` using only supported tile sizes, or None."""
    allowed = sorted({h for w, h in SIZES if w == width}, reverse=True)

    def fill(n):
        if n == 0:
            return []
        for h in allowed:
            if h <= n:
                rest = fill(n - h)
                if rest is not None:
                    return [h] + rest
        return None

    top, bottom = fill(cut), fill(height - cut)
    return None if top is None or bottom is None else (top, bottom)


def breath_tiles(tiles, threshold, sink):
    """tiles: draw-order list from shp_render.parse_tiles. Returns a new draw-order list."""
    out = []
    for t in tiles:
        (sx, sy), (w, h), (dx, dy) = t["src"], t["size"], t["dst"]
        if dy >= threshold:
            out.append(t)
            continue
        if dy + h <= threshold or t["fy"]:
            out.append(dict(t, dst=(dx, dy + sink)))
            continue
        split = strip_heights(w, h, threshold - dy)
        if split is None:  # cannot cut here: move the whole tile
            out.append(dict(t, dst=(dx, dy + sink)))
            continue
        top_h, bottom_h = split
        pieces_top, pieces_bottom, y = [], [], 0
        for hh in top_h:
            pieces_top.append(dict(t, src=(sx, sy + y), size=(w, hh), dst=(dx, dy + y + sink)))
            y += hh
        for hh in bottom_h:
            pieces_bottom.append(dict(t, src=(sx, sy + y), size=(w, hh), dst=(dx, dy + y)))
            y += hh
        out += pieces_bottom + pieces_top  # moving part drawn over the planted part
    return out


def encode_frame(tiles, y_offset=0):
    """Encode a draw-order tile list into SHP frame bytes (stored order is reversed)."""
    data = struct.pack("<H", len(tiles) - 1)
    for t in reversed(tiles):
        (sx, sy), size, (dx, dy) = t["src"], t["size"], t["dst"]
        sy -= y_offset
        assert sx % 8 == 0 and sy % 8 == 0 and 0 <= sy < 256, t
        flags = (sx // 8) | (sy // 8) << 5 | SIZE_INDEX[size] << 10
        flags |= 0x4000 if t["fx"] else 0
        flags |= 0x8000 if t["fy"] else 0
        data += struct.pack("<bbH", dx - 53, dy - 118, flags)
    return data
