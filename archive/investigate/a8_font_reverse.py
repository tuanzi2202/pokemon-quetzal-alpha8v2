#!/usr/bin/env python3
from pathlib import Path
import struct
from capstone import *

a8 = Path(r"d:\aaaaaaa_bianyi\gba_decomp_gezhaer_alpha8v2\rom.gba").read_bytes()
en = Path(r"d:\aaaaaaa_bianyi\QuetzalCN_084\golden\en_0.8.4.gba").read_bytes()
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)


def ldr_pc_target(rom, addr):
    hw = struct.unpack_from("<H", rom, addr)[0]
    assert (hw & 0xF800) == 0x4800
    rt = (hw >> 8) & 7
    imm = hw & 0xFF
    pc = (addr + 4) & ~2
    tgt = pc + imm * 4
    val = struct.unpack_from("<I", rom, tgt)[0]
    return rt, tgt, val


print("A8 raw", a8[0x47F8:0x4824].hex())
print("EN raw", en[0x4810:0x4840].hex())
print("A8 ldr", ldr_pc_target(a8, 0x47FE))
print("EN ldr", ldr_pc_target(en, 0x4816))

for name, ptr in [
    ("sheet", 0x091D0494),
    ("high", 0x09EB972F),
    ("high_align", 0x09EB9800),
    ("wokann_area", 0x09FEF390),
    ("fontptr", 0x091D0494),
]:
    needle = struct.pack("<I", ptr)
    hits = []
    i = 0
    while len(hits) < 15:
        j = a8.find(needle, i)
        if j < 0:
            break
        hits.append(j)
        i = j + 1
    print(name, hex(ptr), [hex(h) for h in hits])

# Find A8 relocated RenderText glyph path - search same CharRead pattern as EN
# EN CharRead at 21CC68: 6830 7803 3001 6030
pat = bytes.fromhex("6830780330016030")
print("CharRead pat A8", hex(a8.find(pat)), "EN", hex(en.find(pat)))

# Search A8 for EN's GlyphDispatch prologue B530 0400 0CC2 0252
pat2 = bytes.fromhex("b53004000cc20252")
print("GlyphDisp pat A8", hex(a8.find(pat2)), "EN", hex(en.find(pat2)))

# Diff ratio overall
same = sum(1 for a, b in zip(a8, en) if a == b)
print("same bytes ratio", same / len(en))

# Find title screen text differently: search A8 for bytes that look like dual-byte CN
# near FE A8 pointers from title: 08FEA8C0 -> file 0x1FEA8C0
for label, cpu in [("t1", 0x08FEA8C0), ("t2", 0x08FEA8F0), ("t3", 0x08FEA920)]:
    off = cpu - 0x08000000
    print(label, hex(cpu), a8[off : off + 48].hex())

# sheet table at 0x11D0494
print("sheet table head", a8[0x11D0494 : 0x11D0494 + 64].hex())
# follow first ptrs
for i in range(8):
    p = struct.unpack_from("<I", a8, 0x11D0494 + i * 4)[0]
    if 0x08000000 <= p < 0x0A000000:
        o = p - 0x08000000
        print(f"  sheet[{i}] {p:08X} -> {a8[o:o+16].hex()}")
