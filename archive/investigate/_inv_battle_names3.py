#!/usr/bin/env python3
"""Phase 3: confirm strides, live pointer sites, battle name getters."""
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
A8 = Path(r"d:\aaaaaaa_bianyi\gba_decomp_gezhaer_alpha8v2\rom.gba").read_bytes()
_, TO_STR = load_charmap()


def decode_chs(data: bytes, max_len: int = 32) -> str:
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


def find_ptrs(rom, off):
    return find_all(rom, ptr(off))


def u32(rom, off):
    return struct.unpack_from("<I", rom, off)[0]


def dump_rows(rom, base, stride, n, label, chs=False):
    print(f"--- {label} base=0x{base:X} stride={stride} ---")
    for i in range(n):
        row = rom[base + i * stride : base + (i + 1) * stride]
        text = decode_chs(row) if chs else decode_bytes(row)
        print(f"  [{i:3d}] {row.hex()} | {text!r}")


print("=== GOLD move table hex @0x417D5D (13 before Pound pad) ===")
print(GOLD[0x417D5D : 0x417D5D + 13 * 12].hex())
dump_rows(GOLD, 0x417D5D, 13, 12, "GOLD moves from 0x417D5D")
dump_rows(GOLD, 0x417D6A, 13, 12, "GOLD moves from 0x417D6A")
dump_rows(GOLD, 0x417D70, 13, 12, "GOLD moves from 0x417D70")
dump_rows(GOLD, 0x417D72, 13, 12, "GOLD moves from 0x417D72")

# Try stride 17 (Karate-Pound string delta)
dump_rows(GOLD, 0x417D79, 17, 8, "GOLD from Pound@79 stride17")

# Find MOVE_NONE / ----- / - pattern before Pound
print("\n=== Search dashes / NONE near moves ===")
for text in ["-----", "-------", "--------", "NONE", "Pound"]:
    try:
        n = encode_plain(text)
    except Exception as e:
        print(text, e)
        continue
    hits = find_all(GOLD, n, limit=15)
    print(f"  {text!r}: {[hex(h) for h in hits]}")

# Species: confirm 13-byte from ???????? base
print("\n=== GOLD species 13-byte from 0x40E308 ===")
dump_rows(GOLD, 0x40E308, 13, 15, "species primary")
dump_rows(CN, 0x40E308, 13, 8, "CN species primary", chs=True)
print("Treecko index check:")
# Bulbasaur at 0x40E315 = base+13 → species 1. Treecko national 252 → base+252*13
tree_off = 0x40E308 + 252 * 13
print(f"  calc Treecko @0x{tree_off:X} = {decode_bytes(GOLD[tree_off:tree_off+13])!r}")
print(f"  actual Treecko string @0x40EFD4")
# 0x40EFD4 - 0x40E308 = ?
print(f"  delta Treecko-base = {0x40EFD4-0x40E308} /13 = {(0x40EFD4-0x40E308)/13}")

# Secondary table
print("\n=== GOLD species secondary 0x413038 ===")
dump_rows(GOLD, 0x413038, 13, 8, "species secondary")
tree2 = 0x413038 + 252 * 13
print(f"  calc Treecko2 @0x{tree2:X} = {decode_bytes(GOLD[tree2:tree2+13])!r}")

# Inspect pointer sites — what code refs them?
print("\n=== Inspect species pointer sites (context) ===")
for site in [0x144, 0x99F3C, 0x9F0DC, 0x9F0F0, 0x99F20, 0x9F0CC]:
    vals = [hex(u32(GOLD, site + i * 4)) for i in range(4)]
    print(f"  site 0x{site:X}: {vals}")
    # search Thumb BL/LDR refs: pointer value appears in code as literal pool
    # Also find refs TO the pointer site itself (less common)
    # Search ARM/Thumb PC-relative: look for the absolute pointer bytes in nearby pools
    # Find code that loads 0x0840E308
    target_ptr = 0x08000000 + 0x40E308
    # already have sites. Disassemble nearby as LDR pools by finding functions that reference site.

# A8 move base 0x3FBC32
print("\n=== A8 moves from ptr base 0x3FBC32 ===")
dump_rows(A8, 0x3FBC32, 13, 12, "A8 moves", chs=True)
print(f"  ptr sites: {[hex(p) for p in find_ptrs(A8, 0x3FBC32)]}")
for site in find_ptrs(A8, 0x3FBC32):
    print(f"  site 0x{site:X} neighbors: {[hex(u32(A8, site+i*4)) for i in range(6)]}")

print("\n=== A8 species from 0x3F7D13 ===")
dump_rows(A8, 0x3F7D13, 11, 10, "A8 species EN still?", chs=False)
# check if Chinese species elsewhere
print("A8 Treecko EN at", hex(0x3F87E7), decode_bytes(A8[0x3F87E7:0x3F87E7+11]))
# Chinese 木守宫 encode
try:
    from chs_encode import encode_text
    zh = encode_text("木守宫")
    print("encode 木守宫:", zh.hex(), "hits A8", [hex(h) for h in find_all(A8, zh[:-1], limit=10)])
    print("hits CN", [hex(h) for h in find_all(CN, zh[:-1], limit=10)])
    print("hits GOLD", [hex(h) for h in find_all(GOLD, zh[:-1], limit=5)])
except Exception as e:
    print("encode err", e)

zh_pound = encode_text("拍击")
print("encode 拍击:", zh_pound.hex())
print("  A8 hits", [hex(h) for h in find_all(A8, zh_pound[:-1], limit=10)])
print("  CN hits", [hex(h) for h in find_all(CN, zh_pound[:-1], limit=20)])

# ---- Find Quetzal move table stride by matching known move order ----
print("\n=== Infer Quetzal move stride via known names order ===")
# Emerald move order: 1 Pound, 2 Karate Chop, 3 Double Slap, 4 Comet Punch, 5 Mega Punch
names = ["Pound", "Karate Chop", "Double Slap", "Comet Punch", "Mega Punch", "Pay Day", "Fire Punch", "Ice Punch", "Thunder Punch", "Scratch"]
offs = {n: find_all(GOLD, encode_plain(n))[0] for n in names}
print("  offsets:", {k: hex(v) for k, v in offs.items()})
# For each candidate base/stride, score how many land on slot starts
for stride in range(8, 40):
    base = offs["Pound"]  # if left-aligned at name start
    # or base such that Pound is move index 1
    ok = 0
    for idx, n in enumerate(names, start=1):
        expect = base + (idx - 1) * stride
        # allow name to start anywhere in slot [expect, expect+stride)
        if expect <= offs[n] < expect + stride:
            ok += 1
    if ok >= 8:
        print(f"  stride={stride} base=Pound@name ok={ok}/10")

# Better: find base where each name's FIRST byte is at base+(id)*stride OR right-aligned
for stride in [13, 16, 17, 18, 20, 24, 32]:
    for base in [offs["Pound"], offs["Pound"] - stride, 0x417D6A, 0x417D5D, 0x417D00]:
        ok = 0
        details = []
        for idx, n in enumerate(names, start=1):
            slot = base + idx * stride  # try move id indexing from 1
            slot0 = base + (idx - 1) * stride
            for s in (slot, slot0):
                if s <= offs[n] < s + stride:
                    ok += 1
                    details.append((n, hex(s), offs[n] - s))
                    break
        if ok >= 8:
            print(f"  CAND stride={stride} base=0x{base:X} ok={ok} {details[:5]}")

# Right-aligned 13-byte: name ends at slot_end-1 (before FF at end)
print("\n=== Right-aligned 13-byte hypothesis ===")
# Each slot: [pad...][name][FF] totaling 13
for i, n in enumerate(names[:6], start=1):
    o = offs[n]
    # find FF after name
    eos = GOLD.find(b"\xff", o)
    # slot end = eos+1, slot start = eos+1-13
    slot_end = eos + 1
    slot_start = slot_end - 13
    print(f"  {n}: name@{o:X} eos@{eos:X} => slot 0x{slot_start:X}-0x{slot_end:X} row={GOLD[slot_start:slot_end].hex()}")

# If consistent, slot_start[i+1]-slot_start[i] should be 13
starts = []
for n in names:
    o = offs[n]
    eos = GOLD.find(b"\xff", o)
    starts.append(eos + 1 - 13)
print("  slot starts:", [hex(s) for s in starts])
print("  deltas:", [starts[i+1]-starts[i] for i in range(len(starts)-1)])

# ---- Code refs: search LDR pools for move table ----
# Find what 0x99F3C / 0x9F0DC refer to in decomp sense - read surrounding symbols if any
print("\n=== Bytes at pointer sites / likely gSpeciesNames / gMoveNames pools ===")
for site in [0x99F00, 0x99F20, 0x99F3C, 0x9C100, 0x9F0C0, 0x9F0DC, 0x140, 0x148]:
    chunk = GOLD[site : site + 32]
    print(f"  GOLD 0x{site:X}: {chunk.hex()}")
    # decode as ptrs
    for i in range(0, 32, 4):
        v = u32(GOLD, site + i)
        if 0x08000000 <= v < 0x0A000000:
            fo = v - 0x08000000
            print(f"    +{i:02X} -> 0x{fo:X} '{decode_bytes(GOLD[fo:fo+16])[:20]}'")

print("\n=== Same pointer sites on A8 ===")
for site in [0x140, 0x144, 0x148, 0x9727C, 0x9C104, 0x9C144]:
    if site + 4 > len(A8):
        continue
    for i in range(0, 16, 4):
        v = u32(A8, site + i)
        if 0x08000000 <= v < 0x0A000000:
            fo = v - 0x08000000
            print(f"  A8 0x{site+i:X} -> 0x{fo:X} chs={decode_chs(A8[fo:fo+16])!r} en={decode_bytes(A8[fo:fo+16])!r}")

# ---- Fight menu: where are move names copied? Search GetMoveName / buffer ----
# Look for second move name table used in summary vs battle
print("\n=== CN still-English Tackle@423E74 context (Z-move / max move?) ===")
ctx = 0x423E00
for i in range(0, 0x200, 13):
    row = GOLD[ctx + i : ctx + i + 13]
    d = decode_bytes(row)
    if d.strip():
        print(f"  0x{ctx+i:X}: {d!r}")

# Walk strings around 423E74
p = 0x423C00
count = 0
while p < 0x424200 and count < 40:
    eos = GOLD.find(b"\xff", p, p + 40)
    if eos < 0:
        break
    s = decode_bytes(GOLD[p : eos + 1])
    if s.strip() and any(c.isalpha() for c in s):
        print(f"  str 0x{p:X}: {s!r}")
        count += 1
    p = eos + 1

print("\nDone phase3")
