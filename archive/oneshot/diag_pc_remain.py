#!/usr/bin/env python3
"""Diagnose remaining Pokemon Center / script issues."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

rom = (ROOT / "out" / "quetzal_084_cn.gba").read_bytes()
g = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()


def u32(b: bytes, o: int) -> int:
    return int.from_bytes(b[o : o + 4], "little")


def looks(p: int) -> bool:
    return 0x08000000 <= p <= 0x09FFFFFF


print("=== nurse 297200-297400 diffs ===")
i = 0x297200
while i < 0x297400:
    if rom[i] != g[i]:
        j = i
        while j < 0x297400 and rom[j] != g[j]:
            j += 1
        gd = decode_bytes(g[i:j] + b"\xff")[:50]
        rd = decode_bytes(rom[i:j] + b"\xff")[:50]
        print(f"  @{i:08X}-{j:08X} ({j-i})")
        print(f"    g={g[i:min(j,i+24)].hex()}")
        print(f"    r={rom[i:min(j,i+24)].hex()}")
        print(f"    gdec={gd!r}")
        print(f"    rdec={rd!r}")
        i = j
    else:
        i += 1

print("\n=== pointer-table slice 2972B4-297360 ===")
print("same", rom[0x2972B4:0x297360] == g[0x2972B4:0x297360])
print("g", g[0x2972B4:0x297360].hex())
print("r", rom[0x2972B4:0x297360].hex())

print("\n=== lost ptrs ===")
for i in (0x293438, 0x29D1A8):
    print(f"@{i:08X}")
    print("  g", g[i - 12 : i + 16].hex())
    print("  r", rom[i - 12 : i + 16].hex())
    print("  ptr g", hex(u32(g, i)), "r", hex(u32(rom, i)))

# Follow nurse menu scripts at golden targets
print("\n=== nurse script targets ===")
# from table at 2972BC
for off in range(0x2972BC, 0x2972E0, 4):
    pg = u32(g, off)
    pr = u32(rom, off)
    if looks(pg):
        go = pg - 0x08000000
        print(f"  slot@{off:08X} g={pg:08X} r={pr:08X} same={pg==pr}")
        print(f"    tgt g={g[go:go+16].hex()} r={rom[go:go+16].hex()} tsame={g[go:go+16]==rom[go:go+16]}")

# Scrub damage: bao where golden was not POKéMON
poke = bytes([0xCA, 0xC9, 0xC5, 0x1B, 0xC7, 0xC9, 0xC8])
bao = encode_text_safe("宝可梦")[0]
bao = bao[:-1] if bao.endswith(b"\xff") else bao
print("\n=== scrub false hits in 0x26-0x36 (bao len pad over non-POKéMON) ===")
false = []
i = 0x260000
while True:
    j = rom.find(bao, i, 0x360000)
    if j < 0:
        break
    if g[j : j + 7] != poke:
        # if golden had different bytes and we overwrote with bao+pad zeros
        old = g[j : j + max(len(bao), 7)]
        # skip if this was already Chinese / intentional inplace
        if old != rom[j : j + len(old)]:
            # check pad zeros after bao matching shortened POKéMON
            false.append(j)
    i = j + 1
print("candidates", len(false))
for j in false[:15]:
    print(f"  @{j:08X} g={g[j:j+12].hex()} r={rom[j:j+12].hex()}")

# Find Oldale Pokemon Center by text and nearby map scripts
print("\n=== POKEMON CENTER string ptrs (early) ===")
# CENTER in charmapped
center = bytes([0xBD, 0xBF, 0xC8, 0xCE, 0xBF, 0xCC])
off = 0x260000
hits = []
while len(hits) < 30:
    j = g.find(center, off, 0x360000)
    if j < 0:
        break
    # decode line
    start = j
    while start > 0 and g[start - 1] not in (0xFF, 0xFB, 0xFA):
        start -= 1
        if j - start > 40:
            break
    eos = g.find(b"\xff", j)
    t = decode_bytes(g[start : eos + 1]) if eos > j else ""
    if "CENTER" in t.upper() or "POK" in t.upper():
        hits.append((j, t[:60]))
    off = j + 1
for j, t in hits[:12]:
    print(f"  @{j:08X} {t!r}")
