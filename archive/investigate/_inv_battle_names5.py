#!/usr/bin/env python3
"""Phase 5: proper GetMoveName disasm; second tables; MyBoy content; nickname theory."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from gen3_charmap import decode_bytes, encode_plain  # noqa: E402
from chs_encode import encode_text, load_charmap  # noqa: E402

CN = (ROOT / "out" / "quetzal_084_cn.gba").read_bytes()
GOLD = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()
MYB = Path(r"d:\aaaaaaa_bianyi\MyBoyQuetzal\vendor\quetzal.gba").read_bytes()
A8 = Path(r"d:\aaaaaaa_bianyi\gba_decomp_gezhaer_alpha8v2\rom.gba").read_bytes()
_, TO_STR = load_charmap()


def u16(rom, off):
    return struct.unpack_from("<H", rom, off)[0]


def u32(rom, off):
    return struct.unpack_from("<I", rom, off)[0]


def find_all(rom, needle, limit=50):
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


def disasm_thumb(rom, start, count=50):
    pc = start & ~1
    for _ in range(count):
        hw = u16(rom, pc)
        op = f"{hw:04X}"
        note = ""
        if (hw & 0xF800) == 0x4800:  # ldr rd,[pc,#imm]
            rd = (hw >> 8) & 7
            imm = (hw & 0xFF) << 2
            pool = ((pc + 4) & ~2) + imm
            val = u32(rom, pool)
            fo = val - 0x08000000 if val >= 0x08000000 else val
            note = f"ldr r{rd}, [pc, #{imm}] ; pool@0x{pool:X}=0x{fo:X}"
        elif (hw & 0xF800) == 0x2000:
            note = f"movs r{(hw>>8)&7}, #{hw&0xFF}"
        elif (hw & 0xFFC0) == 0x4340:
            note = f"muls r{hw&7}, r{(hw>>3)&7}"
        elif (hw & 0xFE00) == 0x1800:
            note = f"adds r{hw&7}, r{(hw>>3)&7}, r{(hw>>6)&7}"
        elif (hw & 0xF800) == 0x3000:
            note = f"adds r{(hw>>8)&7}, #{hw&0xFF}"
        elif (hw & 0xFF00) == 0xB500:
            note = f"push {{{hw&0xFF:02X}, lr}}"
        elif hw == 0x4770:
            note = "bx lr"
        elif (hw & 0xFF00) == 0xBC00:
            note = f"pop {{{hw&0xFF:02X}}}"
        elif (hw & 0xFF00) == 0xBD00:
            note = f"pop {{{hw&0xFF:02X}, pc}}"
        elif (hw & 0xF800) == 0xE000:
            note = f"b +{((hw&0x7FF)<<1)}"
        elif (hw & 0xF000) == 0xD000:
            cond = (hw >> 8) & 0xF
            note = f"bcond({cond}) +{((hw&0xFF)<<1)}"
        elif (hw & 0xFFC0) == 0x4280:
            note = f"cmp r{hw&7}, r{(hw>>3)&7}"
        elif (hw & 0xF800) == 0x2800:
            note = f"cmp r{(hw>>8)&7}, #{hw&0xFF}"
        elif (hw & 0xFE00) == 0x1A00:
            note = f"subs r{hw&7}, r{(hw>>3)&7}, r{(hw>>6)&7}"
        elif (hw & 0xF800) == 0x0000 and (hw & 0xC000) == 0:
            # lsl
            note = f"lsls r{hw&7}, r{(hw>>3)&7}, #{(hw>>6)&0x1F}"
        print(f"  {pc:08X}: {op}  {note}")
        pc += 2
        if note == "bx lr" or "pop {" in note and "pc" in note:
            break


# Locate exact function containing pool 0x9F130
print("=== Disasm around move-name pool 0x9F130 ===")
# Search backward for push {lr}
start = None
for back in range(0, 0x100, 2):
    off = 0x9F130 - back
    hw = u16(GOLD, off)
    if hw in (0xB500, 0xB570, 0xB5F0, 0xB5F8, 0xB4F0, 0xB4FF) or (hw & 0xFF00) == 0xB500:
        # peek if this region references our pool
        start = off
        break
print(f"func start candidate: 0x{start:X}")
# Also try known emerald-style: often small function
# Dump raw from 0x9F100
print("\nRaw window 0x9F100-0x9F150:")
print(GOLD[0x9F100:0x9F150].hex())
disasm_thumb(GOLD, 0x9F100, 45)

print("\n=== Search ALL movs rX,#17 near anything referencing moves ===")
# Find movs #17 (11 20 + rn)
for rn in range(8):
    pat = bytes([17, 0x20 + rn])
    hits = find_all(GOLD, pat, limit=30)
    # filter those near 0x9F000-0xA0000
    near = [h for h in hits if 0x9E000 <= h <= 0xA2000]
    print(f"  movs r{rn},#17 total={len(hits)} near_9F: {[hex(h) for h in near[:15]]}")

print("\n=== Search movs #13 / #17 in 0x9F000-0x9F200 ===")
region = GOLD[0x9F000:0x9F200]
for imm in [11, 12, 13, 16, 17, 18]:
    for rn in range(8):
        pat = bytes([imm, 0x20 + rn])
        for h in find_all(region, pat, limit=10):
            print(f"  0x{0x9F000+h:X}: movs r{rn}, #{imm}")

# Better: find function by scanning for ldr that loads 0x417D68 from pool
print("\n=== Scan 0x9F000-0xA0000 for ldr pc pools pointing at 0x417D68 ===")
for pc in range(0x9F000, 0xA0000, 2):
    hw = u16(GOLD, pc)
    if (hw & 0xF800) != 0x4800:
        continue
    rd = (hw >> 8) & 7
    imm = (hw & 0xFF) << 2
    pool = ((pc + 4) & ~2) + imm
    if pool + 4 > len(GOLD):
        continue
    if u32(GOLD, pool) == 0x08417D68:
        print(f"  ldr r{rd}, [pc,#] @0x{pc:X} pool@0x{pool:X}")
        # disasm from push before
        func = pc
        for back in range(0, 0x40, 2):
            if (u16(GOLD, pc - back) & 0xFF00) == 0xB500:
                func = pc - back
                break
        print(f"  -> func 0x{func:X}")
        disasm_thumb(GOLD, func, 35)

print("\n=== Same for species GetSpeciesName-like ===")
for target in [0x0840E308, 0x08413038]:
    print(f" target {hex(target)}")
    for pc in range(0x99000, 0xA0000, 2):
        hw = u16(GOLD, pc)
        if (hw & 0xF800) != 0x4800:
            continue
        imm = (hw & 0xFF) << 2
        pool = ((pc + 4) & ~2) + imm
        if pool + 4 > len(GOLD):
            continue
        if u32(GOLD, pool) == target:
            rd = (hw >> 8) & 7
            print(f"  ldr r{rd} @0x{pc:X} pool@0x{pool:X}")
            func = pc
            for back in range(0, 0x40, 2):
                if (u16(GOLD, pc - back) & 0xFF00) == 0xB500:
                    func = pc - back
                    break
            disasm_thumb(GOLD, func, 25)
            print("  ---")

# Second Tackle @0x419445
print("\n=== Second Tackle @0x419445 context (17-byte?) ===")
for base in [0x419445, 0x419440, 0x419430, 0x419400, 0x418800]:
    # check if Struggle nearby with stride 17 from main table end
    pass
# Main Struggle @0x41885d = 0x417D68+165*17
# What's at 0x419445?
print("decode around 0x419400:")
p = 0x419400
for i in range(20):
    eos = GOLD.find(b"\xff", p, p + 40)
    if eos < 0:
        break
    print(f"  0x{p:X}: {decode_bytes(GOLD[p:eos+1])!r}")
    p = eos + 1

# Is 0x419445 inside main table?
print(f"0x419445 - 0x417D68 = {0x419445-0x417D68} /17 = {(0x419445-0x417D68)/17}")
# 0x419445 might be a longer-name alternate or description

# Check ability / move description tables?
print("\n=== MyBoy move/species samples (is MyBoy English or partial CN?) ===")
for i in [1, 2, 33]:
    off = 0x417D68 + i * 17
    print(f"  MyBoy move[{i}] @{off:X}: en={decode_bytes(MYB[off:off+17])!r} chs={decode_chs(MYB[off:off+17])!r}")
    print(f"  CN    move[{i}] @{off:X}: en={decode_bytes(CN[off:off+17])!r} chs={decode_chs(CN[off:off+17])!r}")
for idx in [1, 252]:
    off = 0x40E308 + idx * 13
    print(f"  MyBoy sp[{idx}]: {decode_chs(MYB[off:off+13])!r} / {decode_bytes(MYB[off:off+13])!r}")
    print(f"  CN    sp[{idx}]: {decode_chs(CN[off:off+13])!r}")

# Diff MyBoy vs GOLD at tables - is MyBoy closer to golden EN?
print("\n=== MyBoy vs GOLD table diffs ===")
for a, b, lab in [
    (0x40E308, 0x40E308 + 13 * 400, "species_pri"),
    (0x417D68, 0x417D68 + 17 * 800, "moves"),
]:
    d_mg = sum(1 for x, y in zip(MYB[a:b], GOLD[a:b]) if x != y)
    d_cg = sum(1 for x, y in zip(CN[a:b], GOLD[a:b]) if x != y)
    d_mc = sum(1 for x, y in zip(MYB[a:b], CN[a:b]) if x != y)
    print(f"  {lab}: MyBoy-GOLD={d_mg} CN-GOLD={d_cg} MyBoy-CN={d_mc}")

# A8 Chinese species alternate @0x3F48C8
print("\n=== A8 Chinese species-like @0x3F48C8 ===")
print("  ", decode_chs(A8[0x3F48C8 : 0x3F48C8 + 20]))
# ptrs?
print("  ptrs to 3F48C8", [hex(h) for h in find_all(A8, ptr(0x3F48C8))])
# Check A8 header species 0x3F3DF4 vs 0x3F7D13
print("A8 hdr species table @3F3DF4:")
for i in range(5):
    row = A8[0x3F3DF4 + i * 11 : 0x3F3DF4 + (i + 1) * 11]
    print(f"  [{i}] {decode_chs(row)!r} / {decode_bytes(row)!r}")

# Battle HP bar: often uses nickname from pokemon struct (10 or 11 chars)
# Species name used when nickname empty / for wild
print("\n=== Wild battle species: GetSpeciesName callers ===")
# Already have getters. Check if battle uses gSpeciesNames or gSpeciesNamesEnglish

# Look for UPPERCASE species table used in battle?
print("TREECKO upper remaining:", [hex(h) for h in find_all(CN, encode_plain("TREECKO"), limit=5)])
print("Treecko EN remaining:", [hex(h) for h in find_all(CN, encode_plain("Treecko"), limit=5)])

# Expanded battle strings bank — does CN patch FD expansion source?
# Search for BufferMoveName / similar by finding 17 mul in battle code region
print("\n=== movs #17 in battle-ish ROM ranges ===")
ranges = [(0x10000, 0x40000), (0x40000, 0x80000), (0x80000, 0xC0000), (0xC0000, 0x100000)]
for a, b in ranges:
    count = 0
    sites = []
    for rn in range(8):
        pat = bytes([17, 0x20 + rn])
        for h in find_all(GOLD[a:b], pat, limit=20):
            count += 1
            sites.append((a + h, rn))
    print(f"  {a:X}-{b:X}: {count} hits sample={[ (hex(s), f'r{r}') for s,r in sites[:8]]}")

print("\nDone phase5")
