"""Compare two sets of CharAnimSeq tables (original vs patched) via FF16Tools' SQLite export.

Prints, per table: rows, how many changed, in which animations, whether only frames
changed (delays and row kinds kept), and the patched animations 6 and 7.

Usage: python nxd_compare.py <original nxd dir> <patched nxd dir>
"""
import os
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FF16 = os.path.join(os.path.dirname(HERE), "win-x64", "FF16Tools.CLI.exe")


def export(nxd_dir, db):
    subprocess.run([FF16, "nxd-to-sqlite", "-i", nxd_dir, "-o", db, "-g", "fft"], capture_output=True, check=True)
    return sqlite3.connect(db)


def fmt(rows):
    return " ".join(f"f{r[5] & 255}x{r[5] >> 8}" if r[4] == 1 else f"[{r[4]}]" for r in rows)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        o = export(sys.argv[1], os.path.join(tmp, "o.sqlite"))
        p = export(sys.argv[2], os.path.join(tmp, "p.sqlite"))
        for (t,) in p.execute("select name from sqlite_master where name like 'CharAnimSeq%' order by name"):
            a = list(o.execute(f"select * from {t} order by Key, Key2"))
            b = list(p.execute(f"select * from {t} order by Key, Key2"))
            diff = [(x, y) for x, y in zip(a, b) if x != y]
            keys = sorted({x[0] for x, _ in diff})
            only_frames = len(a) == len(b) and all(
                6 <= x[0] <= 11 and x[:5] == y[:5] and (x[5] >> 8) == (y[5] >> 8) for x, y in diff)
            print(f"{t}: rows {len(a)}, changed {len(diff)} in anims {keys}, only frames changed: {only_frames}")
            for anim in (6, 7):
                print(f"    orig {anim}: {fmt([r for r in a if r[0] == anim])}")
                print(f"    new  {anim}: {fmt([r for r in b if r[0] == anim])}")
        o.close()
        p.close()


if __name__ == "__main__":
    main()
