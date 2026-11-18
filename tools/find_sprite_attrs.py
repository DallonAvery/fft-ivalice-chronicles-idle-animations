"""Search a binary for FFT's per-sprite attribute table.

In the original game each sprite has 4 bytes: frame layout type, animation set type,
flying flag, height. Types: 0 TYPE1, 1 TYPE2, 2 CYOKO, 3 MON, 4 OTHER, 5 RUKA,
6 ARUTE, 7 KANZEN. This looks for long runs of records that fit that shape and
contain all the expected kinds.

Usage: python find_sprite_attrs.py <file> [min_records]
"""
import sys


def plausible(rec):
    shp, seq, fly, h = rec
    return shp <= 7 and seq <= 7 and fly <= 1 and h <= 0x40


def main():
    data = open(sys.argv[1], "rb").read()
    min_len = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    found = []
    for align in range(4):
        run_start, i = None, align
        while i + 4 <= len(data):
            ok = plausible(data[i:i + 4])
            if ok and run_start is None:
                run_start = i
            if not ok and run_start is not None:
                n = (i - run_start) // 4
                if n >= min_len:
                    recs = [tuple(data[run_start + 4 * k:run_start + 4 * k + 4]) for k in range(n)]
                    kinds = {(a, b) for a, b, _, _ in recs}
                    if {(0, 0), (1, 1), (2, 2), (3, 3)} <= kinds:
                        found.append((run_start, n, recs))
                run_start = None
            i += 4
    for start, n, recs in found:
        print(f"offset 0x{start:X}: {n} records")
        print("  " + " ".join(f"{i}:{a}{b}{'F' if f else ''}h{h}" for i, (a, b, f, h) in enumerate(recs)))


if __name__ == "__main__":
    main()
