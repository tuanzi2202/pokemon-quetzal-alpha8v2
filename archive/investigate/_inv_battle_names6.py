#!/usr/bin/env python3
"""Phase 6: dump alternate move/species name tables used by language switcher."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from gen3_charmap import decode_bytes, encode_plain  # noqa: E402
from chs_encode import load_charmap  # noqa: E402

CN = (ROOT / "out" / "quetzal_084_cn.gba").read_bytes()
GOLD = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()
_, TO_STR = load_charmap()


def u16(rom, off):
    return struct.unpack_from("<H", rom, off)[0]


def u32(rom, off):
    return struct.unpack_from("<I", rom, off)[0]


def find_all(rom, needle, limit=40):
    out, s = [], 0
    while len(out) < limit:
        i = rom.find(needle, s)
        if i < 0:
            break
        out.append(i)
        s = i + 1
    return out


def ptr(off):
    return struct.pack("<I", 0x08000000 + off)


def decode_chs(data, max_len=24):
    parts, i = [], 0
    while i < min(len(data), max_len):
        if data[i] == 0xFF:
            break
        if i + 1 < len(data) and data[i : i + 2] in TO_STR:
            parts.append(TO_STR[data[i : i + 2]])
            i += 2
            continue
        if data[i : i + 1] in TO_STR:
            parts.append(TO_STR[data[i : i + 1]])
            i += 1
            continue
        parts.append(f"[{data[i]:02X}]")
        i += 1
    return "".join(parts)


def dump_table(rom, base, stride, indices, label, chs=False):
    print(f"=== {label} base=0x{base:X} stride={stride} ===")
    for i in indices:
        row = rom[base + i * stride : base + (i + 1) * stride]
        t = decode_chs(row) if chs else decode_bytes(row)
        print(f"  [{i:3d}] {row[:17].hex()} | {t!r}")


# From disasm:
# case/lang == 1: base 0x41BB90, idx*17
# case/lang == 2: base 0x417D68, idx*17
# else?: base 0x41F9B8, idx*17  (uses r3)

ALT_TABLES = [
    (0x417D68, "main_EN_or_CN"),
    (0x41BB90, "alt_lang1"),
    (0x41F9B8, "alt_other"),
]

for base, lab in ALT_TABLES:
    print(f"\n## Table {lab}")
    dump_table(GOLD, base, 17, [0, 1, 2, 33, 165], f"GOLD {lab}")
    dump_table(CN, base, 17, [0, 1, 2, 33, 165], f"CN {lab}", chs=True)
    # ptrs
    print(f"  ptrs: {[hex(h) for h in find_all(GOLD, ptr(base))]}")

# Full disasm of language switcher for moves with correct instruction decode
print("\n=== Full move-name language switcher 0x9F0F4 ===")
# Re-read raw and manually annotate
raw = GOLD[0x9F0F4:0x9F144]
print(raw.hex())
"""
B500          push {lr}  (actually push {r0,lr}? B500 = push {lr} only in some - B500 is push {lr})
0400 0C02     lsls r0,r0,#16; lsrs r2,r0,#16  ; species/move id clear high = uxth to r2?
1C13          adds r3,r2,#0  ; mov r3,r2
4806          ldr r0, =0x03005320
6800          ldr r0,[r0]
4906          ldr r1, =0x2E1
1840          adds r0,r0,r1
7800          ldrb r0,[r0]   ; load language byte?
2107          movs r1,#7
4001          ands r1,r0
2901          cmp r1,#1
D10A          bne +0x0A instructions
0110          lsls r0,r2,#4
1880          adds r0,r0,r2  ; *17
4903          ldr r1, =0x41BB90
E011          b exit_add
...
2902          cmp r1,#2
D005          bne
0110/1880     *17
4900          ldr r1, =0x417D68
E004          b
0118/18C0     *17 with r3
4901          ldr r1, =0x41F9B8
1840          adds r0,r0,r1
BC02          pop {r1}
4708          bx r1
"""

# What is save block offset 0x2E1?
print("\n=== Identify language field @ save+0x2E1 ===")
# Emerald: gSaveBlock2Ptr->options / language
# Check CN vs GOLD code same at switcher
print("CN==GOLD at switcher?", CN[0x9F0F4:0x9F144] == GOLD[0x9F0F4:0x9F144])

# Species switcher similarly - when lang bits match, use secondary
print("\n=== Species switcher tables content compare ===")
# 0x413038 used when lang in {0x20, 0x40}? From disasm:
# and with 0xE0, cmp 0x20 / 0x40 -> use secondary 0x413038 else primary 0x40E308
for base, lab in [(0x40E308, "species_pri"), (0x413038, "species_sec")]:
    dump_table(CN, base, 13, [1, 25, 252], f"CN {lab}", chs=True)

# Check if alt move tables are other languages (Spanish etc) still English letters
print("\n=== Sample alt table strings (may be other EU langs) ===")
for base in [0x41BB90, 0x41F9B8]:
    print(f" base 0x{base:X}:")
    for i in range(1, 8):
        row = GOLD[base + i * 17 : base + (i + 1) * 17]
        print(f"  [{i}] {decode_bytes(row)!r}")

# Is battle using a hardcoded English path?
# Search for other *17 + different bases
print("\n=== Find other gMoveNames-like bases (ptr to '-' then Pound +17) ===")
# row0 pattern AE FF + zeros
row0 = GOLD[0x417D68 : 0x417D68 + 17]
for hit in find_all(GOLD, row0, limit=20):
    nxt = decode_bytes(GOLD[hit + 17 : hit + 34])
    print(f"  row0@{hit:X} next={nxt!r}")

# Also check 0x41BB90 row0
print("alt1 row0", GOLD[0x41BB90 : 0x41BB90 + 17].hex(), decode_bytes(GOLD[0x41BB90 : 0x41BB90 + 17]))
print("alt2 row0", GOLD[0x41F9B8 : 0x41F9B8 + 17].hex(), decode_bytes(GOLD[0x41F9B8 : 0x41F9B8 + 17]))

# Device chk ROMs - what's on device_test?
print("\n=== work/device_*.gba vs out CN at moves ===")
for name in ["device_chk.gba", "device_test.gba", "device_mom.gba", "cn_build.gba"]:
    p = ROOT / "work" / name
    if not p.exists():
        continue
    rom = p.read_bytes()
    off = 0x417D79
    print(f"  {name}: move1={decode_chs(rom[off:off+17])!r} / {decode_bytes(rom[off:off+17])!r}")
    print(f"         sp252={decode_chs(rom[0x40EFD4:0x40EFD4+13])!r}")
    import hashlib
    print(f"         md5={hashlib.md5(rom).hexdigest()} cn_match={rom==CN}")

# Battle string "{FD:0F} used\n{FD:34}!" — FD:34 is move name buffer
# Who fills FD:34? Search BufferMove or similar refs to GetMoveName
print("\n=== Xrefs to move switcher 0x9F0F4 (BL targets) ===")
# Thumb BL: encode offset
# Find BL to 0x9F0F4+1
target = 0x9F0F5  # thumb bit
# scan for BL encoding is heavy; search for pool refs already done
# Alternative: find all sites that load 0x41BB90 / 0x41F9B8
for base in [0x41BB90, 0x41F9B8, 0x417D68]:
    print(f"  ptrs->{base:X}: {[hex(h) for h in find_all(GOLD, ptr(base))]}")

# Check fill_battle_names walk range - did it miss alt tables?
print("\n=== Are alt tables inside MOVES_START..MOVES_END walk? ===")
MOVES_START = 0x417D6A
MOVES_END = 0x41B5C8
for base in [0x417D68, 0x41BB90, 0x41F9B8]:
    print(f"  0x{base:X} in walk range? {MOVES_START <= base < MOVES_END}")
    print(f"  table end ~0x{base+900*17:X} in range end? end_cmp MOVES_END=0x{MOVES_END:X}")

# How far is 0x41BB90 from main?
print(f"  0x41BB90 - 0x417D68 = {0x41BB90-0x417D68} (= { (0x41BB90-0x417D68)/17 } slots)")
print(f"  0x41F9B8 - 0x417D68 = {0x41F9B8-0x417D68}")
print(f"  MOVES_END 0x41B5C8 vs alt1 0x41BB90: alt1 is AFTER MOVES_END by {0x41BB90-0x41B5C8}")

# So fill script ended at Nihil Light 0x41B5C8, MISSING alt tables at 0x41BB90 and 0x41F9B8!

print("\n=== Size of each alt table (until non-text) ===")
for base, lab in ALT_TABLES:
    # count consecutive slots that look like names
    n = 0
    for i in range(2000):
        row = GOLD[base + i * 17 : base + (i + 1) * 17]
        if 0xFF not in row:
            break
        s = decode_bytes(row)
        if i > 0 and not any(c.isalpha() for c in s) and s not in ("-", "-----", ""):
            # allow empty-ish
            if s.strip() == "" or set(s) <= set(" -?"):
                n += 1
                continue
            break
        n += 1
    last = decode_bytes(GOLD[base + (n - 1) * 17 : base + n * 17]) if n else ""
    print(f"  {lab}: ~{n} slots, last~{last!r}, end~0x{base+n*17:X}")

print("\nDone phase6")
