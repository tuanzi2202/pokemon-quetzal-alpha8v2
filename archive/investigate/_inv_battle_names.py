#!/usr/bin/env python3
"""Investigate which move/species tables battle actually uses."""
from __future__ import annotations

import hashlib
import struct
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from gen3_charmap import decode_bytes, encode_plain  # noqa: E402

CN = (ROOT / "out" / "quetzal_084_cn.gba").read_bytes()
GOLD = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()
A8 = Path(r"d:\aaaaaaa_bianyi\gba_decomp_gezhaer_alpha8v2\rom.gba").read_bytes()
MYB = Path(r"d:\aaaaaaa_bianyi\MyBoyQuetzal\vendor\quetzal.gba").read_bytes()


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def find_all(rom: bytes, needle: bytes, limit: int = 50) -> list[int]:
    out: list[int] = []
    start = 0
    while len(out) < limit:
        i = rom.find(needle, start)
        if i < 0:
            break
        out.append(i)
        start = i + 1
    return out


def ptr_bytes(file_off: int) -> bytes:
    """GBA ROM pointer for file offset (08xxxxxx)."""
    return struct.pack("<I", 0x08000000 + file_off)


def find_ptrs_to(rom: bytes, file_off: int, limit: int = 40) -> list[int]:
    return find_all(rom, ptr_bytes(file_off), limit=limit)


def dump_str(rom: bytes, off: int, n: int = 24) -> str:
    return decode_bytes(rom[off : off + n])


def scan_fixed_width_table(
    rom: bytes, needle: bytes, widths: list[int] = [11, 12, 13, 14]
) -> list[tuple[int, int, str]]:
    """Find needle aligned as row0 of fixed-width table; verify next rows look like text."""
    hits: list[tuple[int, int, str]] = []
    for w in widths:
        for off in find_all(rom, needle[: min(len(needle), w)], limit=80):
            # Prefer exact padded row: needle content then FF/00 pad within width
            row = rom[off : off + w]
            if 0xFF not in row and len(needle) < w:
                # maybe null-padded or space-padded without EOS in slot
                pass
            # check a few following rows decode as mostly letters / EOS
            ok = 0
            samples = []
            for i in range(1, 6):
                r = rom[off + i * w : off + (i + 1) * w]
                if len(r) < w:
                    break
                s = decode_bytes(r)
                samples.append(s)
                if s and all(c.isalnum() or c in " -'." for c in s.replace("é", "e")):
                    ok += 1
            if ok >= 3:
                hits.append((off, w, " | ".join(samples[:4])))
    return hits


def walk_varlen(rom: bytes, start: int, end: int, max_n: int = 20) -> list[tuple[int, str]]:
    rows = []
    p = start
    while p < end and len(rows) < max_n:
        eos = rom.find(b"\xff", p, min(p + 64, end))
        if eos < 0:
            break
        rows.append((p, decode_bytes(rom[p : eos + 1])))
        p = eos + 1
    return rows


print("=== ROM MD5s ===")
for name, b in [("CN", CN), ("GOLD", GOLD), ("A8", A8), ("MyBoy", MYB)]:
    print(f"{name}: size={len(b)} md5={md5(b)}")
print(f"CN==MyBoy: {CN == MYB}")
print(f"CN==GOLD: {CN == GOLD}")
print(f"GOLD==MyBoy: {GOLD == MYB}")

# Diff MyBoy vs CN summary
if CN != MYB:
    diffs = sum(1 for a, b in zip(CN, MYB) if a != b)
    print(f"MyBoy vs CN byte diffs: {diffs}")
    # first differing regions
    regions = []
    i = 0
    n = min(len(CN), len(MYB))
    while i < n:
        if CN[i] != MYB[i]:
            j = i
            while j < n and CN[j] != MYB[j]:
                j += 1
            regions.append((i, j - i))
            i = j
        else:
            i += 1
    print(f"diff regions: {len(regions)}; first 15:")
    for a, ln in regions[:15]:
        print(f"  0x{a:08X} len=0x{ln:X}")

print("\n=== Encoded needles ===")
needles = {
    "Pound": encode_plain("Pound"),
    "Tackle": encode_plain("Tackle"),
    "Treecko": encode_plain("Treecko"),
    "POUND": encode_plain("POUND"),
    "TACKLE": encode_plain("TACKLE"),
    "TREECKO": encode_plain("TREECKO"),
    "Karate Chop": encode_plain("Karate Chop"),
    "Scratch": encode_plain("Scratch"),
}
for k, v in needles.items():
    print(f"  {k}: {v.hex()}")

print("\n=== Occurrences in GOLD / CN / A8 ===")
for label, needle in needles.items():
    for rname, rom in [("GOLD", GOLD), ("CN", CN), ("A8", A8)]:
        hits = find_all(rom, needle, limit=30)
        if hits:
            print(f"  {rname} {label}: {[hex(h) for h in hits]}")

print("\n=== Known offsets GOLD vs CN vs A8 ===")
for off, label in [
    (0x40E308, "species_start?"),
    (0x40EFCE, "Treecko_title"),
    (0x417D6A, "Pound_title"),
    (0x417F93, "Tackle_title"),
    (0x3FBC3F, "A8_moves_13?"),
]:
    for rname, rom in [("GOLD", GOLD), ("CN", CN), ("A8", A8)]:
        if off + 32 > len(rom):
            continue
        chunk = rom[off : off + 32]
        print(f"  {rname} @{off:08X} {label}: {chunk[:20].hex()} | {dump_str(rom, off)!r}")

print("\n=== Pointers TO known Quetzal Title-Case strings (GOLD) ===")
targets = {
    "Pound@417D6A": 0x417D6A,
    "Tackle@417F93": 0x417F93,
    "Treecko@40EFCE": 0x40EFCE,
    "species_start@40E308": 0x40E308,
}
for label, off in targets.items():
    hits = find_ptrs_to(GOLD, off)
    print(f"  ptrs -> {label}: {[hex(h) for h in hits]}")
    # also check CN same
    hits_cn = find_ptrs_to(CN, off)
    if hits_cn != hits:
        print(f"    CN differs: {[hex(h) for h in hits_cn]}")

# Emerald vanilla typically: gMoveNames is fixed 13-byte, gSpeciesNames fixed 11-byte
# Search for Pound as start of 13-byte rows
print("\n=== Fixed-width table candidates (Pound / Treecko) ===")
for rname, rom in [("GOLD", GOLD), ("A8", A8)]:
    print(f"--- {rname} Pound ---")
    for off, w, samp in scan_fixed_width_table(rom, encode_plain("Pound")[:-1]):  # no EOS? keep with EOS
        print(f"  off=0x{off:X} w={w} next=[{samp}]")
    # with EOS included in first row search
    for off, w, samp in scan_fixed_width_table(rom, encode_plain("Pound")):
        print(f"  (w/EOS) off=0x{off:X} w={w} next=[{samp}]")
    print(f"--- {rname} Treecko ---")
    for off, w, samp in scan_fixed_width_table(rom, encode_plain("Treecko")):
        print(f"  (w/EOS) off=0x{off:X} w={w} next=[{samp}]")
    for off, w, samp in scan_fixed_width_table(rom, encode_plain("Treecko")[:-1]):
        print(f"  (noEOS) off=0x{off:X} w={w} next=[{samp}]")

print("\n=== A8 region around 0x3FBC3F (13-byte moves?) ===")
off = 0x3FBC3F
# try align: dump as 13-byte rows
for base_try in [0x3FBC3F, 0x3FBC40, 0x3FBC30, 0x3FBC20, 0x3FBC00]:
    print(f"  try base 0x{base_try:X}:")
    for i in range(8):
        r = A8[base_try + i * 13 : base_try + (i + 1) * 13]
        print(f"    [{i}] {r.hex()} | {decode_bytes(r)!r}")

print("\n=== Search A8 for Chinese move-like double-byte patterns near known ===")
# Find where A8 differs from a typical EN Pound encoding region
# Look for pointers in A8 to 0x3FBC3F area
for cand in range(0x3FB000, 0x3FD000, 0x10):
    pass
a8_pound_ptrs = find_ptrs_to(A8, 0x3FBC3F)
print(f"  ptrs -> A8 0x3FBC3F: {[hex(h) for h in a8_pound_ptrs[:20]]}")

# Find gMoveNames-like by searching consecutive Pound, Karate Chop spacing
print("\n=== Spacing between Pound and Karate Chop / Tackle ===")
for rname, rom in [("GOLD", GOLD), ("A8", A8)]:
    p = find_all(rom, encode_plain("Pound"), limit=10)
    k = find_all(rom, encode_plain("Karate Chop"), limit=10)
    t = find_all(rom, encode_plain("Tackle"), limit=10)
    print(f"  {rname} Pound={list(map(hex,p))} Karate={list(map(hex,k))} Tackle={list(map(hex,t))}")
    if p and k:
        print(f"    Karate-Pound delta = {k[0]-p[0]} (expect 13 for fixed)")
    if p and t:
        print(f"    Tackle-Pound delta = {t[0]-p[0]}")

print("\n=== UPPERCASE copies ===")
for label in ["POUND", "TACKLE", "TREECKO", "SCRATCH"]:
    needle = encode_plain(label if label != "SCRATCH" else "SCRATCH")
    # fix
    pass
for label, text in [("POUND", "POUND"), ("TACKLE", "TACKLE"), ("TREECKO", "TREECKO"), ("SCRATCH", "SCRATCH")]:
    needle = encode_plain(text)
    for rname, rom in [("GOLD", GOLD), ("CN", CN)]:
        hits = find_all(rom, needle, limit=20)
        print(f"  {rname} {label}: {[hex(h) for h in hits]}")

print("\n=== Battle string bank FF9xxx / near expanded ===")
# Scan for ' used ' pattern or battle templates
for text in [" used ", "used the", "fainted!", "sent out", "FIGHT", "Fight"]:
    try:
        n = encode_plain(text)
    except KeyError:
        continue
    for rname, rom in [("GOLD", GOLD), ("CN", CN)]:
        hits = find_all(rom, n, limit=15)
        if hits:
            print(f"  {rname} {text!r}: {[hex(h) for h in hits]}")

# Look at 0xFF9000 region
print("\n=== Strings near 0xFF9000 GOLD ===")
for base in [0xFF9000, 0xFFA000, 0xFFB000, 0x0FC0000, 0x0FC8000]:
    rows = walk_varlen(GOLD, base, base + 0x400, max_n=12)
    if rows:
        print(f"  bank 0x{base:X}:")
        for off, s in rows[:8]:
            if s.strip():
                print(f"    0x{off:X}: {s!r}")

print("\nDone phase1")
