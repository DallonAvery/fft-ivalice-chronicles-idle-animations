"""Check the built idle-animation mods against the original game files.

For every file in each variant: SHP frames that changed, SEQ animations that changed,
and whether any change outside idle animations 6-11 is a pure frame swap between
byte-identical frames. Also compares with earlier builds when they exist.

Usage: python verify_mods.py <unpacked unit dir> <mods dir>
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_mods  # noqa: E402
import seq_decode  # noqa: E402
import shp_render  # noqa: E402


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def check_shp(orig, new):
    a, b = shp_render.parse_shp(orig), shp_render.parse_shp(new)
    assert len(a) == len(b)
    return [k for k in range(len(a)) if a[k] != b[k]]


def check_seq(orig, new, allowed_swaps):
    a = {i: x for i, _, x in seq_decode.animations(orig)}
    b = {i: x for i, _, x in seq_decode.animations(new)}
    changed = [i for i in a if a[i] != b[i]]
    bad = []
    for i in changed:
        if 6 <= i <= 11:
            continue
        for x, y in zip(seq_decode.decode(a[i]), seq_decode.decode(b[i])):
            if x != y and not (x[0] == "frame" and (x[1], y[1]) in allowed_swaps and x[2] == y[2]):
                bad.append((i, x, y))
    return changed, bad


def main():
    src, mods = sys.argv[1], sys.argv[2]
    swaps = {(d, t) for fam in build_mods.FAMILIES.values()
             for remap in fam["remap"].values() for d, t in remap.items()}
    for key, v in build_mods.VARIANTS.items():
        unit = os.path.join(mods, v["mod_id"], "FFTIVC", "data", "combined", "fftpack", "unit")
        print(f"== {key} ({v['mod_id']})")
        for fn in sorted(os.listdir(unit)):
            orig = open(os.path.join(src, fn), "rb").read()
            new = open(os.path.join(unit, fn), "rb").read()
            if fn.endswith("_shp.bin"):
                print(f"   {fn:24s} size {len(orig)}->{len(new)}  frames changed {check_shp(orig, new)}")
            else:
                changed, bad = check_seq(orig, new, swaps)
                extra = [i for i in changed if not 6 <= i <= 11]
                print(f"   {fn:24s} size {'same' if len(orig) == len(new) else 'DIFFERENT'}  "
                      f"idle changed {[i for i in changed if 6 <= i <= 11] == list(range(6, 12))}  "
                      f"other anims (frame swaps only) {extra}  unexpected {bad}")
    # earlier, already-tested builds
    root = os.path.dirname(os.path.abspath(src.rstrip('\\/') + '/../../..'))
    refs = [("still", os.path.join(root, "build", "fftpack", "unit")),
            ("breathing", os.path.join(root, "build_breathing", "fftpack", "unit"))]
    for key, ref in refs:
        if not os.path.isdir(ref) or key not in build_mods.VARIANTS:
            continue
        unit = os.path.join(mods, build_mods.VARIANTS[key]["mod_id"], "FFTIVC", "data", "combined",
                            "fftpack", "unit")
        same = {fn: md5(os.path.join(unit, fn)) == md5(os.path.join(ref, fn))
                for fn in os.listdir(ref) if os.path.exists(os.path.join(unit, fn))}
        print(f"{key} matches earlier build {ref}: {same}")


if __name__ == "__main__":
    main()
