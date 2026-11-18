"""Build the idle-animation mod variants for FFT: The Ivalice Chronicles (Reloaded-II).

Variants (enable only one at a time in Reloaded-II):
  still_humans  human units stand still; creatures and bosses keep the game's own idle
                (their files are left out of the mod)
  still         every unit stands still while idle (Altima bosses too)
  breathing_all humans, monsters and chocobos breathe; Altima bosses keep their
                original hovering idle (their files are left out of the mod)

How it works (see the other tools for the file formats):
  * SEQ files: idle animations 6-11 (front/back x normal/Haste/Slow) are rewritten.
    Each keeps its 8 steps and total length, so SEQ files never change size.
  * Breathing poses are new SHP frames built from the standing pose's own tiles:
    everything above a body line is drawn 1 pixel lower (breath.py). For humans the
    line is row 32 of the 40-row pose, the first 8-pixel grid line below the hands,
    so only the lower legs and feet stay planted.
  * SHP files have a second frame list with the in-water version of every frame (same
    numbers, upper body only). Breathing slots get in-water breathing frames there too,
    built from the in-water standing pose; otherwise units in water would show
    whatever that slot's in-water copy held (TYPE1: a raised hand; TYPE2: a lone head).
      TYPE1 SHP (type1, type4)  slots 60, 63   copies of 49/53 in both lists; every
                                               reference is moved to the twin first
      TYPE2 SHP (type2, type3)  slots 62, 63   dry copies of 11/16, same remap; in-water
                                               data goes into freed space
      CYOKO SHP (cyoko)         slots 59, 60   unused -> rewritten in place
      MON SHP   (mon, ruka)     slots 13, 19   unused but too small -> data goes into
                                               space freed from duplicate frames
  * No file may change size (the game loads them into fixed-size space).

Usage: python build_mods.py <unpacked unit dir> <output mods dir>
"""
import json
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import breath  # noqa: E402
import nxd_idle  # noqa: E402
import seq_decode  # noqa: E402
import shp_render  # noqa: E402

IDLE = {6: ("normal", "front"), 7: ("normal", "back"), 8: ("haste", "front"),
        9: ("haste", "back"), 10: ("slow", "front"), 11: ("slow", "back")}
# (pose, delay) x 8 steps; "s" = standing, "b" = breathing. Totals 64 / 32 / 96.
BREATH_LOOP = {
    "normal": [("s", 16), ("s", 16), ("s", 4), ("b", 8), ("b", 8), ("b", 8), ("b", 2), ("s", 2)],
    "haste": [("s", 8), ("s", 8), ("s", 2), ("b", 4), ("b", 4), ("b", 4), ("b", 1), ("s", 1)],
    "slow": [("s", 24), ("s", 24), ("s", 6), ("b", 12), ("b", 12), ("b", 12), ("b", 3), ("s", 3)],
}

# human standing pose is a 32x40 block whose top sits at canvas row 83; cut at its row 32
HUMAN_LINE = 83 + 32

# per SHP: SEQs using it, standing frames, breathing slots, body line, and per-SEQ
# remaps that move every use of a breathing slot to its twin frame first.
#
# Pairing (verified 2026-11-15): layout TYPE1 <- type1 + type4 animations,
# layout TYPE2 <- type2 + type3 animations. (type3 uses frames up to 198, which only
# exist as dry frames in TYPE2's 199-frame list; a type3 unit drawn with TYPE2 showed
# TYPE2's both-hands-up frame 32 when breathing used the TYPE1 slot numbers.)
#
# Files must never grow: the game reads them into fixed-size space, so anything past
# the original end is never loaded (monsters blinked). When a slot has too little room,
# its data goes into space freed by pointing exact-duplicate frames of the same list at
# their identical earlier copy (see relocate()).
FAMILIES = {
    # 60 / 63 are exact twins of 49 / 53 in both the dry and the in-water list
    "type1": dict(seqs=["type1", "type4"], stand={"front": 2, "back": 8},
                  slots={"front": 60, "back": 63}, line=HUMAN_LINE,
                  remap={"type1": {60: 49, 63: 53}, "type4": {60: 49, 63: 53}}),
    # TYPE2 has no twins in both lists. 62 / 63 equal 11 / 16 in the dry list; in water they
    # are head-only deep-water poses (type3 deep-water idle 18-23; type2 85/89/233). After the
    # remap those show the in-water 11 / 16 (upper body), as type2's own deep-water idle does.
    "type2": dict(seqs=["type2", "type3"], stand={"front": 2, "back": 8},
                  slots={"front": 62, "back": 63}, line=HUMAN_LINE,
                  remap={"type2": {62: 11, 63: 16}, "type3": {62: 11, 63: 16}}),
    "cyoko": dict(seqs=["cyoko"], stand={"front": 2, "back": 4},
                  slots={"front": 59, "back": 60}, line=105, remap={}),
    "mon": dict(seqs=["mon", "ruka"], stand={"front": 2, "back": 4},
                slots={"front": 13, "back": 19}, line=111, remap={}),
}
# SEQ files whose idle becomes still when they don't breathe (standing frame per facing
# is read from the SEQ's own still animations 2 and 4)
ALL_SEQS = ["type1", "type2", "type3", "type4", "mon", "ruka", "cyoko", "arute", "kanzen"]
BOSSES = ["arute", "kanzen"]
# copied from docs/ into every mod folder when present
MANUALS = ["IdleAnimations_Manual_en.html", "IdleAnimations_Manual_ru.html"]
# manual files from earlier versions, removed from the mod folders
OLD_MANUALS = ["IdleAnimations_Manual.html", "IdleAnimations_Manual.pdf"]

CREATURES = ["mon", "ruka", "cyoko"]

VARIANTS = {
    "still_humans": dict(
        mod_id="fftivc.animation.stillhumans", name="Idle Animations: Still (Humans)",
        desc="Human units stand still while idle instead of walking in place; monsters, "
             "chocobos and bosses keep the game's own idle. Enable only one Idle Animations mod.",
        breathe=[], keep_original=CREATURES + BOSSES),
    "still": dict(
        mod_id="fftivc.animation.standstillidle", name="Idle Animations: Still (Everyone)",
        desc="Every unit, humans and creatures alike, stands still while idle instead of "
             "walking in place. Enable only one Idle Animations mod.",
        # nxd_still=True also patches nxd/charanimseqN; tested 2026-11-15 and it caused an
        # "Access is denied (0xA1000005)" error at the start of every player turn, so it is off
        breathe=[], keep_original=[], nxd_still=False),
    "breathing_all": dict(
        mod_id="fftivc.animation.breathingidleall", name="Idle Animations: Breathing",
        desc="Humans, monsters and chocobos breathe gently while idle, in and out of water; "
             "the Altima bosses keep their original hovering idle. Enable only one Idle "
             "Animations mod.",
        breathe=["type1", "type2", "cyoko", "mon"], keep_original=BOSSES),
}
# mod folders from earlier versions that this build replaces (removed from the output)
RETIRED = ["fftivc.animation.breathingidle"]


# ---------- SHP helpers ----------

def frame_offsets(shp):
    offs, i = [0], 0
    while True:
        (a,) = struct.unpack_from("<I", shp, 0x0C + 4 * i)
        i += 1
        if not a:
            return offs
        offs.append(a)


def frame_bytes(shp, offs, k):
    s = offs[k] + 0x40A
    return shp[s:s + 2 + 4 * ((shp[s] | shp[s + 1] << 8) + 1)]


def water_offsets(shp):
    """Second frame list: the in-water versions of the first list's frames (same numbers),
    showing only the upper body. Pointers start at jump + 4, data at jump + 0x402."""
    jump = struct.unpack_from("<I", shp, 0)[0]
    offs, i = [0], 0
    while True:
        (a,) = struct.unpack_from("<I", shp, jump + 4 + 4 * i)
        i += 1
        if not a:
            return jump, offs
        offs.append(a)


class FrameList:
    """One frame list of an SHP file (dry or in-water) that can be edited in place."""

    def __init__(self, buf, offs, base, ptr_base):
        self.buf, self.offs, self.base, self.ptr_base = buf, list(offs), base, ptr_base

    def span(self, k):
        s = self.offs[k] + self.base
        return s, 2 + 4 * ((self.buf[s] | self.buf[s + 1] << 8) + 1)

    def data(self, k):
        s, n = self.span(k)
        return bytes(self.buf[s:s + n])

    def set_pointer(self, k, off):
        assert k >= 1  # frame 0's pointer is implicit
        struct.pack_into("<I", self.buf, self.ptr_base + 4 * (k - 1), off)
        self.offs[k] = off

    def relocate(self, need, protect):
        """Free `need` contiguous bytes by pointing exact-duplicate frames at their identical
        earlier copy (same bytes, so nothing changes on screen). Returns the freed offset."""
        first = {}
        dups = []
        for k in range(len(self.offs)):
            d = self.data(k)
            if d in first and k not in protect:
                dups.append((self.offs[k], len(d), k, first[d]))
            else:
                first.setdefault(d, k)
        dups.sort()
        users = {}
        for k, o in enumerate(self.offs):
            users.setdefault(o, set()).add(k)
        run = []
        for item in dups:
            off, n, k, orig = item
            if run and run[-1][0] + run[-1][1] != off:
                run = []
            if len(users[off]) != 1:  # data already shared with another frame
                run = []
                continue
            run.append(item)
            if sum(r[1] for r in run) >= need:
                for off_k, _, k_dup, k_orig in run:
                    self.set_pointer(k_dup, self.offs[k_orig])
                return run[0][0]
        raise RuntimeError(f"no {need}-byte run of duplicate frames to reuse")

    def put(self, slot, data, protect):
        start, room = self.span(slot)
        if len(data) <= room:
            self.buf[start:start + room] = data + bytes(room - len(data))
            return "in place"
        off = self.relocate(len(data), protect)
        s = off + self.base
        self.buf[s:s + len(data)] = data
        self.set_pointer(slot, off)
        return f"moved to freed space at +0x{off:X}"


def add_breath_frames(shp, fam):
    """Write dry (and, if the layout has one, in-water) breathing frames into the slots.
    The file never grows."""
    out = bytearray(shp)
    second_half = shp[4] | shp[5] << 8
    frames = shp_render.parse_shp(shp)
    offs = frame_offsets(shp)
    jump = struct.unpack_from("<I", shp, 0)[0]
    lists = [("dry", FrameList(out, offs, 0x40A, 0x0C), 0)]
    if jump > 8:
        _, woffs = water_offsets(shp)
        lists.append(("water", FrameList(out, woffs, jump + 0x402, jump + 4), len(offs)))
    protect = set(fam["slots"].values())
    report = []
    for facing, slot in fam["slots"].items():
        assert 0 < slot < second_half, "breathing frame must read from the top of the sheet"
        for name, fl, shift in lists:
            stand = frames[shift + fam["stand"][facing]]
            data = breath.encode_frame(breath.breath_tiles(stand, fam["line"], 1))
            report.append(f"{name} {slot}: {fl.put(slot, data, protect)}")
    assert len(out) == len(shp)
    return bytes(out), report


# ---------- SEQ helpers ----------

def frames_used(seq):
    used = set()
    for _, _, raw in seq_decode.animations(seq):
        used |= {s[1] for s in seq_decode.decode(raw) if s[0] == "frame"}
    return used


def remap_seq(seq, remap):
    out = bytearray(seq)
    for _, off, raw in seq_decode.animations(seq):
        for s in seq_decode.decode(raw):
            if s[0] == "frame" and s[1] in remap:
                out[seq_decode.DATA_START + off + s[3]] = remap[s[1]]
    return bytes(out)


def still_frames(seq):
    anims = {i: raw for i, _, raw in seq_decode.animations(seq)}

    def single(i):
        (step,) = seq_decode.decode(anims[i])
        assert step[0] == "frame"
        return step[1]

    return {"front": single(2), "back": single(4)}


def set_idle(seq, stand, slots=None):
    """Rewrite idle animations 6-11: still (slots=None) or breathing."""
    out = bytearray(seq)
    anims = {i: (off, raw) for i, off, raw in seq_decode.animations(seq)}
    for idx, (speed, facing) in IDLE.items():
        off, raw = anims[idx]
        steps = seq_decode.decode(raw)
        frame_steps = [s for s in steps if s[0] == "frame"]
        assert [s[1] for s in steps if s[0] == "cmd"] == [0xD5] and steps[-1][0] == "cmd", idx
        base = seq_decode.DATA_START + off
        if slots is None:
            for s in frame_steps:
                out[base + s[3]] = stand[facing]
        else:
            assert len(frame_steps) == 8, idx
            for s, (pose, delay) in zip(frame_steps, BREATH_LOOP[speed]):
                out[base + s[3]] = stand[facing] if pose == "s" else slots[facing]
                out[base + s[3] + 1] = delay
    return bytes(out)


# ---------- build ----------

REPORT = []


def build_files(src, variant):
    def read(name):
        return open(os.path.join(src, f"battle_{name}.bin"), "rb").read()

    files = {}
    breathing_seqs = {}
    for fam_name in variant["breathe"]:
        fam = FAMILIES[fam_name]
        shp = read(f"{fam_name}_shp")
        offs = frame_offsets(shp)
        for remap in fam["remap"].values():
            for dup, twin in remap.items():
                # the dry frames must be identical; in-water differences are documented above
                assert frame_bytes(shp, offs, dup) == frame_bytes(shp, offs, twin), (dup, twin)
        files[f"{fam_name}_shp"], report = add_breath_frames(shp, fam)
        REPORT.append(f"{fam_name}_shp: " + "; ".join(report))
        for name in fam["seqs"]:
            seq = remap_seq(read(f"{name}_seq"), fam["remap"].get(name, {}))
            assert not frames_used(seq) & set(fam["slots"].values()), f"{name} uses a breathing slot"
            breathing_seqs[name] = set_idle(seq, fam["stand"], fam["slots"])
    for name in ALL_SEQS:
        if name in variant["keep_original"]:
            continue
        if name in breathing_seqs:
            files[f"{name}_seq"] = breathing_seqs[name]
        else:
            seq = read(f"{name}_seq")
            files[f"{name}_seq"] = set_idle(seq, still_frames(seq))
    return files


def write_mod(out_dir, variant, files):
    mod_dir = os.path.join(out_dir, variant["mod_id"])
    unit_dir = os.path.join(mod_dir, "FFTIVC", "data", "combined", "fftpack", "unit")
    os.makedirs(unit_dir, exist_ok=True)
    for old in os.listdir(unit_dir):
        os.remove(os.path.join(unit_dir, old))
    for name, data in files.items():
        open(os.path.join(unit_dir, f"battle_{name}.bin"), "wb").write(data)
    # the remaster's own copies of the idle (nxd/charanimseqN.nxd), one set per game mode
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for mode in ("enhanced", "classic"):
        nxd_out = os.path.join(mod_dir, "FFTIVC", "data", mode, "nxd")
        if os.path.isdir(nxd_out):
            shutil.rmtree(nxd_out)
        if variant.get("nxd_still"):
            nxd_idle.patch_tables(os.path.join(root, "unpacked", mode, "nxd"), nxd_out)
    docs = os.path.join(root, "docs")
    for old in OLD_MANUALS:
        if os.path.exists(os.path.join(mod_dir, old)):
            os.remove(os.path.join(mod_dir, old))
    for manual in MANUALS:
        if os.path.exists(os.path.join(docs, manual)):
            shutil.copyfile(os.path.join(docs, manual), os.path.join(mod_dir, manual))
    cfg_path = os.path.join(mod_dir, "ModConfig.json")
    cfg = json.load(open(cfg_path, encoding="utf-8-sig")) if os.path.exists(cfg_path) else {
        "ModAuthor": "", "ModDll": "", "ModIcon": "", "Tags": [], "IsLibrary": False,
        "PluginData": {}, "IsUniversalMod": False, "OptionalDependencies": [], "ProjectUrl": ""}
    cfg.update({"ModId": variant["mod_id"], "ModName": variant["name"], "ModVersion": "1.2.0",
                "ModDescription": variant["desc"], "ModDependencies": ["fftivc.utility.modloader"],
                "SupportedAppId": ["fft_classic.exe", "fft_enhanced.exe"]})
    json.dump(cfg, open(cfg_path, "w", encoding="utf-8"), indent=2)
    return mod_dir


def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    for old in RETIRED:
        if os.path.isdir(os.path.join(out_dir, old)):
            shutil.rmtree(os.path.join(out_dir, old))
            print(f"removed retired build {old}")
    for key, variant in VARIANTS.items():
        files = build_files(src, variant)
        mod_dir = write_mod(out_dir, variant, files)
        sizes = []
        for name, data in sorted(files.items()):
            orig = os.path.getsize(os.path.join(src, f"battle_{name}.bin"))
            # the game reads these files into fixed-size space: nothing may grow
            assert len(data) == orig, f"{name} changed size ({orig} -> {len(data)})"
            sizes.append(name)
        print(f"{key:14s} -> {mod_dir}\n    {' '.join(sizes)}")
        for line in REPORT:
            print(f"    {line}")
        REPORT.clear()


if __name__ == "__main__":
    main()
