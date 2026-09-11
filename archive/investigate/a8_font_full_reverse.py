#!/usr/bin/env python3
"""Reverse A8 Chinese font wiring end-to-end."""
from __future__ import annotations

import struct
from pathlib import Path
from capstone import *

A8 = Path(r"d:\aaaaaaa_bianyi\gba_decomp_gezhaer_alpha8v2\rom.gba").read_bytes()
EN = Path(r"d:\aaaaaaa_bianyi\QuetzalCN_084\golden\en_0.8.4.gba").read_bytes()
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
md.detail = True


def u32(rom: bytes, off: int) -> int:
    return struct.unpack_from("<I", rom, off)[0]


def disasm(rom: bytes, off: int, size: int = 0x80, base: int | None = None):
    base = 0x08000000 + off if base is None else base
    for i in md.disasm(rom[off : off + size], base):
        print(f"  {i.address:08X}: {i.mnemonic}\t{i.op_str}")


print("=== A8 @5858 Chinese divert (mov pc) ===")
print("raw", A8[0x5858:0x5868].hex())
print("pool@5860", hex(u32(A8, 0x5860)))
target = u32(A8, 0x5860)
if 0x08000000 <= target < 0x0A000000:
    toff = target - 0x08000000
    print(f"handler @{target:08X}")
    disasm(A8, toff, 0x120)

print("\n=== A8 CharRead 58C0 + after ===")
disasm(A8, 0x58C0, 0x40)

print("\n=== jump table after CharRead (pool @58DC?) ===")
# after lsl; ldr r1,[pc,#8]; add; ldr; mov pc
# at 58D2: ldr r1,[pc,#8] -> pc=(58D2+4)&~2=58D4, +8=58DC
print("jtable base pool", hex(u32(A8, 0x58DC)))
jt = u32(A8, 0x58DC) - 0x08000000
print("first 8 jump targets:")
for i in range(8):
    t = u32(A8, jt + i * 4)
    print(f"  [{i}] {t:08X}")

print("\n=== Compare A8 vs EN084 low text engine size ===")
# Find where A8 and EN diverge in 0x4000-0x8000
diff_ranges = []
i = 0x4000
while i < 0x8000:
    if A8[i] != EN[i]:
        j = i
        while j < 0x8000 and A8[j] != EN[j]:
            j += 1
        if j - i >= 16:
            diff_ranges.append((i, j - i))
        i = j
    else:
        i += 1
print("diff runs 0x4000-0x8000 (>=16B):", [(hex(a), hex(n)) for a, n in diff_ranges[:20]])

print("\n=== A8 DecompressGlyph family find by BL 4BF0 / 4C08 ===")
# Find functions that BL DecompressGlyphTile
# A8 DecompressGlyphTile may be at 0x4BF0 (from earlier disasm)


def find_bl_to(rom: bytes, dest: int, start: int = 0, end: int = 0x80000):
    hits = []
    for off in range(start, end - 4, 2):
        hw1 = rom[off] | (rom[off + 1] << 8)
        hw2 = rom[off + 2] | (rom[off + 3] << 8)
        if (hw1 & 0xF800) != 0xF000 or (hw2 & 0xF800) != 0xF800:
            continue
        s = (hw1 >> 10) & 1
        imm10 = hw1 & 0x3FF
        j1 = (hw2 >> 13) & 1
        j2 = (hw2 >> 11) & 1
        imm11 = hw2 & 0x7FF
        I1 = ~(j1 ^ s) & 1
        I2 = ~(j2 ^ s) & 1
        imm32 = (s << 24) | (I1 << 23) | (I2 << 22) | (imm10 << 12) | (imm11 << 1)
        if s:
            imm32 |= ~((1 << 25) - 1) & 0xFFFFFFFF
            imm32 = imm32 - (1 << 32) if imm32 >= (1 << 31) else imm32
        # sign extend properly
        if imm32 & (1 << 24):
            imm32 -= 1 << 25
        pc = 0x08000000 + off
        d = (pc + 4 + imm32) & 0xFFFFFFFF
        if d == dest or d == (dest | 1) or (d & ~1) == (dest & ~1):
            hits.append(off)
    return hits


for dest in (0x08004BF0, 0x08004C08, 0x08004C10):
    hits = find_bl_to(A8, dest, 0x6000, 0x8000)
    print(f"A8 BL to {dest:08X} in 6k-8k:", [hex(h) for h in hits[:15]], "count", len(hits))

print("\n=== EN084 BL to 4C08 in 21c000-21d100 ===")
hits = find_bl_to(EN, 0x08004C08, 0x21C000, 0x21D100)
print([hex(h) for h in hits])

print("\n=== A8 gCurGlyph 03003030 xref pools in code ===")
needle = struct.pack("<I", 0x03003030)
idx = 0
pools = []
while True:
    j = A8.find(needle, idx)
    if j < 0:
        break
    if j < 0x100000:  # code-ish
        pools.append(j)
    idx = j + 1
print([hex(p) for p in pools[:30]])

# Who uses font sheet 0x091D0494 - search nearby variants
for ptr in range(0x091D0480, 0x091D04A0, 4):
    pass
# search any ptr into 0x091D0000-0x091E0000
print("\n=== pools pointing into 0x091Dxxxx ===")
count = 0
for off in range(0, 0x400000, 4):
    v = u32(A8, off)
    if 0x091D0000 <= v < 0x091E0000:
        print(hex(off), hex(v))
        count += 1
        if count >= 20:
            break
