"""Patch the remaster's CharAnimSeq tables (nxd/charanimseqN.nxd) to match the mod's idle.

The remaster keeps its own copy of about 25 animations per body type in these tables,
including the idle (6-11). Each row of an animation is
  Unknown8 = 1   -> show frame (UnknownC = delay << 8 | frame)
  Unknown8 = 144 -> end of loop
This rewrites the frame of every "show frame" row in animations 6-11. Frames come from
`frames(table_index, anim, step, delay, old_frame)`; delays and row counts are kept.

Conversion uses FF16Tools (nxd -> SQLite -> nxd); a round trip without changes was
verified to give byte-identical files.

Usage (still idle): python nxd_idle.py <nxd dir> <out dir>
"""
import os
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FF16 = os.path.join(os.path.dirname(HERE), "win-x64", "FF16Tools.CLI.exe")
IDLE = {6: "front", 7: "back", 8: "front", 9: "back", 10: "front", 11: "back"}


def run(*args):
    res = subprocess.run([FF16, *args, "-g", "fft"], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stdout + res.stderr)


def still_frame_picker(db, table):
    """Standing frames are the table's own single-frame animations 2 (front) and 4 (back)."""
    rows = dict(db.execute(f"select Key, UnknownC from {table} where Key in (2, 4) and Unknown8 = 1"))
    if 2 not in rows or 4 not in rows:
        return None
    still = {"front": rows[2] & 0xFF, "back": rows[4] & 0xFF}
    return lambda anim, step, delay, old: (still[IDLE[anim]], delay)


def patch_tables(nxd_dir, out_dir, picker_factory=still_frame_picker):
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in")
        os.makedirs(src)
        for f in os.listdir(nxd_dir):
            if f.startswith("charanimseq") and f.endswith(".nxd"):
                with open(os.path.join(nxd_dir, f), "rb") as a, open(os.path.join(src, f), "wb") as b:
                    b.write(a.read())
        dbp = os.path.join(tmp, "t.sqlite")
        run("nxd-to-sqlite", "-i", src, "-o", dbp)
        db = sqlite3.connect(dbp)
        tables = [r[0] for r in db.execute(
            "select name from sqlite_master where type='table' and name like 'CharAnimSeq%'")]
        changed = []
        for t in sorted(tables):
            pick = picker_factory(db, t)
            if pick is None:
                print(f"  {t}: no standing poses (animations 2/4), left unchanged")
                continue
            rows = list(db.execute(
                f"select Key, Key2, UnknownC from {t} where Key between 6 and 11 and Unknown8 = 1 order by Key, Key2"))
            for key, key2, val in rows:
                frame, delay = pick(key, key2, val >> 8, val & 0xFF)
                db.execute(f"update {t} set UnknownC = ? where Key = ? and Key2 = ?",
                           ((delay << 8) | frame, key, key2))
            db.commit()
            changed.append(t)
            print(f"  {t}: {len(rows)} idle rows rewritten")
        db.close()
        if changed:
            run("sqlite-to-nxd", "-i", dbp, "-o", out_dir, "-t", *changed)
    return changed


def main():
    patch_tables(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
