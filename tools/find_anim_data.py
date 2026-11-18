"""Search game files for anything that holds a copy of unit animation data.

Looks in every file under the given folders (and any extra single files, e.g. the exes) for:
  * the exact bytes of the idle animations 6/7 of each SEQ file (original game data)
  * the start of each SEQ and SHP file (an embedded copy of a whole file)
  * the remaster's table encoding of the human idle (delay<<8|frame as 32-bit values:
    frame 11 for 6 ticks, frame 10 for 8 ticks, frame 9 for 10 ticks)

Usage: python find_anim_data.py <unpacked unit dir> <path> [path ...]
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import seq_decode  # noqa: E402

SEQS = ["type1", "type2", "type3", "type4", "mon", "ruka", "cyoko", "arute", "kanzen", "other"]
SHPS = ["type1", "type2", "mon", "cyoko", "arute", "kanzen", "other"]


def signatures(unit_dir):
    sigs = {}
    for n in SEQS:
        data = open(os.path.join(unit_dir, f"battle_{n}_seq.bin"), "rb").read()
        anims = {i: raw for i, _, raw in seq_decode.animations(data)}
        for a in (6, 7):
            sigs[f"{n} idle {a} (SEQ bytes)"] = bytes(anims[a][:16])
        sigs[f"{n} SEQ file start"] = data[:64]
    for n in SHPS:
        p = os.path.join(unit_dir, f"battle_{n}_shp.bin")
        if os.path.exists(p):
            sigs[f"{n} SHP file start"] = open(p, "rb").read()[:64]
    return sigs


TABLE_IDLE = re.compile(re.escape(struct.pack("<I", 0x060B)) + rb"[\s\S]{0,60}?" +
                        re.escape(struct.pack("<I", 0x080A)) + rb"[\s\S]{0,60}?" +
                        re.escape(struct.pack("<I", 0x0A09)))


def walk(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
        else:
            for root, _, files in os.walk(p):
                for f in files:
                    yield os.path.join(root, f)


def main():
    unit_dir, *paths = sys.argv[1:]
    sigs = signatures(unit_dir)
    hits = {}
    n_files = 0
    for path in walk(paths):
        n_files += 1
        try:
            data = open(path, "rb").read()
        except OSError:
            continue
        for label, sig in sigs.items():
            start = 0
            while True:
                i = data.find(sig, start)
                if i < 0:
                    break
                hits.setdefault(label, []).append((path, i))
                start = i + 1
        for m in TABLE_IDLE.finditer(data):
            hits.setdefault("human idle in table encoding", []).append((path, m.start()))
    print(f"searched {n_files} files")
    for label in list(sigs) + ["human idle in table encoding"]:
        found = hits.get(label, [])
        where = sorted({os.path.relpath(p, os.path.commonpath(paths)) if len(paths) > 1 else p
                        for p, _ in found})
        print(f"{label:34s} {len(found):4d} hit(s) " + ("" if not found else "in: " + "; ".join(where[:8])))


if __name__ == "__main__":
    main()
