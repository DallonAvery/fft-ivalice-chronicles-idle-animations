"""Decode FFT battle SEQ animation files (e.g. battle_type1_seq.bin).

Format (from ShishiSpriteEditor's Sequence.cs in Glain/FFTPatcher):
  0x000  4 bytes   header
  0x004  256 x u32 offsets (little endian), relative to 0x406; 0xFFFFFFFF ends the table
  0x404  u16       length of animation data
  0x406  animation data
Each animation is a list of 2-byte steps:
  (frame, delay)      when the first byte is not 0xFF -> show SHP frame `frame` for `delay`/60 s
  FF xx [args...]     a command; xx decides how many extra argument bytes follow

Usage: python seq_decode.py <seq file> [animation index ...]
"""
import struct
import sys

# extra argument bytes after the 2-byte FF xx opcode (others take none)
EXTRA_ARGS = {0xC0: 1, 0xC6: 1, 0xD3: 1, 0xD4: 1, 0xD6: 1, 0xD7: 1, 0xD8: 1,
              0xE2: 1, 0xEE: 1, 0xEF: 1, 0xF0: 1, 0xF6: 1,
              0xC1: 2, 0xD9: 2, 0xF2: 2, 0xFC: 2, 0xFA: 3}

DATA_START = 0x406


def read_offsets(data):
    offsets = []
    for i in range(256):
        (off,) = struct.unpack_from("<I", data, 4 + i * 4)
        if off == 0xFFFFFFFF:
            break
        offsets.append(off)
    return offsets


def decode(raw):
    steps, i = [], 0
    while i < len(raw) - 1:
        if raw[i] != 0xFF:
            steps.append(("frame", raw[i], raw[i + 1], i))
            i += 2
        else:
            op = raw[i + 1]
            n = EXTRA_ARGS.get(op, 0)
            steps.append(("cmd", op, bytes(raw[i + 2:i + 2 + n]), i))
            i += 2 + n
    return steps


def animations(data):
    offsets = read_offsets(data)
    (length,) = struct.unpack_from("<H", data, 0x404)
    end_all = DATA_START + length
    for idx, off in enumerate(offsets):
        nxt = [o for o in offsets if o > off]
        end = DATA_START + min(nxt) if nxt else end_all
        yield idx, off, data[DATA_START + off:end]


def fmt(steps):
    parts = []
    for s in steps:
        if s[0] == "frame":
            parts.append(f"f{s[1]}x{s[2]}")
        else:
            parts.append(f"[FF{s[1]:02X}{(' ' + s[2].hex(' ')) if s[2] else ''}]")
    return " ".join(parts)


def main():
    data = open(sys.argv[1], "rb").read()
    wanted = {int(a, 0) for a in sys.argv[2:]}
    print(f"header={data[:4].hex(' ')}  anims={len(read_offsets(data))}  "
          f"datalen=0x{struct.unpack_from('<H', data, 0x404)[0]:X}  filesize=0x{len(data):X}")
    for idx, off, raw in animations(data):
        if wanted and idx not in wanted:
            continue
        steps = decode(raw)
        total = sum(s[2] for s in steps if s[0] == "frame")
        print(f"#{idx:3d} (0x{idx:02X}) @0x{DATA_START + off:04X} len={len(raw):3d} "
              f"time={total:3d}/60s  {fmt(steps)}")


if __name__ == "__main__":
    main()
