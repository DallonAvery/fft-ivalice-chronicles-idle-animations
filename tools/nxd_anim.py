"""Read the remaster's CharAnimSeq tables (nxd/charanimseq0-7.nxd) from a SQLite export.

Each table is a copy of a subset of one SEQ file's animations:
  Key  = animation number (same numbering as the SEQ file)
  Key2 = step number
  Unknown8 = 1 for "show frame", 144 (0x90) for the end-of-loop marker
  UnknownC = delay << 8 | frame       (e.g. 1547 = 0x060B = frame 11 for 6 ticks)

Usage: python nxd_anim.py <nxd.sqlite> [table] [anim ...]
  With no table: compare every table's animations against every unit SEQ file.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seq_decode  # noqa: E402

UNIT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "unpacked", "fftpack", "unit")
SEQS = ["type1", "type2", "type3", "type4", "mon", "ruka", "cyoko", "arute", "kanzen", "other"]


def table_anims(db, table):
    anims = {}
    for key, key2, kind, val in db.execute(
            f"select Key, Key2, Unknown8, UnknownC from {table} order by Key, Key2"):
        anims.setdefault(key, []).append((kind, val))
    return anims


def as_steps(rows):
    """Frame steps (frame, delay) from table rows; non-frame rows kept as ('cmd', kind, value)."""
    out = []
    for kind, val in rows:
        if kind == 1:
            out.append((val & 0xFF, val >> 8))
        else:
            out.append(("cmd", kind, val))
    return out


def seq_steps(path):
    data = open(path, "rb").read()
    res = {}
    for i, _, raw in seq_decode.animations(data):
        res[i] = [(s[1], s[2]) for s in seq_decode.decode(raw) if s[0] == "frame"]
    return res


def main():
    db = sqlite3.connect(sys.argv[1])
    tables = [r[0] for r in db.execute(
        "select name from sqlite_master where type='table' and name like 'CharAnimSeq%' order by name")]
    if len(sys.argv) > 2:
        anims = table_anims(db, sys.argv[2])
        want = {int(a) for a in sys.argv[3:]}
        for k, rows in anims.items():
            if not want or k in want:
                print(k, " ".join(f"f{f}x{d}" if f != "cmd" else f"[{d}:{v}]" for f, d, *v in
                                  [(s[0], s[1], *s[2:]) if s[0] == "cmd" else (s[0], s[1]) for s in as_steps(rows)]))
        return
    seqs = {n: seq_steps(os.path.join(UNIT_DIR, f"battle_{n}_seq.bin")) for n in SEQS}
    for t in tables:
        anims = table_anims(db, t)
        scores = []
        for n, sq in seqs.items():
            match = sum(1 for k, rows in anims.items()
                        if [s for s in as_steps(rows) if s[0] != "cmd"] == sq.get(k))
            scores.append((match, n))
        scores.sort(reverse=True)
        print(f"{t}: {len(anims)} anims {sorted(anims)}  best match: "
              + ", ".join(f"{n}={m}" for m, n in scores[:3]))


if __name__ == "__main__":
    main()
