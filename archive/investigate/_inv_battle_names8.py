#!/usr/bin/env python3
"""Phase 8: language-vs-font theory; force-lang; nickname length; other GetMoveName."""
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


# Search docs/tools for language forcing
print("=== Grep project for language / LANGUAGE_ ===")
import re
for path in (ROOT / "tools").glob("*.py"):
    t = path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"language|LANGUAGE|0x2E1|gSaveBlock2", t, re.I):
        hits = [line.strip() for line in t.splitlines() if re.search(r"language|0x2E1|SaveBlock", line, re.I)]
        if hits:
            print(f"  {path.name}:")
            for h in hits[:8]:
                print(f"    {h[:120]}")

# Disassemble species getter language condition fully
print("\n=== Species GetSpeciesName lang gate 0x9F0A0 ===")
print(GOLD[0x9F0A0:0x9F0F4].hex())
"""
Reads save+0x2E0? 
21B8 0089 = mov r1,#184; lsl r1,#2 => r1=736=0x2E0
adds to save ptr, ldrb
and 0xE0, cmp 0x20 / 0x40 -> secondary table
else primary
So species uses bits 0xE0 of options byte, NOT language enum 1/2/7!
Different field from move names!
"""

print("\n=== Move lang uses save+0x2E1; species uses save+0x2E0 bits ===")
# Confirm offsets in both functions
# Move func: ldr r1,=0x2E1 at pool 0x9F11C
print("move pool 0x9F11C", hex(u32(GOLD, 0x9F11C)))
print("species pool 0x9F0C8 save?", hex(u32(GOLD, 0x9F0C8)))
# species adds 0x2E0 via 184*4

# Check if Chinese patch or options default changes language
print("\n=== Options LANGUAGE string & nearby values ===")
off = 0x1024D7C  # ENGLISH
print("ctx", decode_bytes(GOLD[off - 40 : off + 80]))
print("CN ctx", decode_bytes(CN[off - 40 : off + 80]))

# Find default language init in code
print("\n=== Search movs #2 near language init (default ENGLISH) ===")
# Emerald SetDefaultOptions language = ENGLISH (2)

# Pokemon nickname length constant usage
print("\n=== Nickname length: movs #10 / #11 / #12 near species name copy ===")
# GetSpeciesName returns ptr; StringCopy uses N=11 typically

# Verify battle callers of GetMoveName at 0xd55c2
print("\n=== Context around BL GetMoveName @0xD55C2 (battle?) ===")
pc = 0xD55C2
print(GOLD[pc - 16 : pc + 8].hex())
# and @0x1C7034
for pc in [0xD55C2, 0x1C7034, 0x1C70A8, 0x8B07C, 0x6767C]:
    print(f"  @{pc:X}: {GOLD[pc-8:pc+4].hex()}")

# Force-switch recommendation: patch cmp/branch at move getter to always use 0x417D68
print("\n=== Exact bytes to force English/CN move table ===")
# At 0x9F10A: cmp r1,#1 ; bne
# At 0x9F124: cmp r1,#2
# Simplest: change both branches to always take *17 + 0x417D68 path
print("switcher bytes", GOLD[0x9F0F4:0x9F144].hex())

# Alt: patch Spanish tables with same Chinese as main (849*17 bytes)
print("\n=== Byte cost to clone CN main -> Spanish alts ===")
main = CN[0x417D68 : 0x417D68 + 849 * 17]
print(f"main table bytes {len(main)}; alt1 currently differs from main? ", main != CN[0x41BB90:0x41BB90+len(main)])
print(f"alt1 differs from GOLD alt1?", CN[0x41BB90:0x41BB90+100] != GOLD[0x41BB90:0x41BB90+100])

# Check docs PIPELINE for known issues
pipe = (ROOT / "docs" / "PIPELINE.txt").read_text(encoding="utf-8", errors="replace")
for line in pipe.splitlines():
    if any(k in line.lower() for k in ("move", "species", "battle", "name", "417", "40e")):
        print("PIPE:", line[:140])

print("\nDone phase8")
