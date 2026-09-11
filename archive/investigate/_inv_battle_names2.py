#!/usr/bin/env python3
"""Phase 2: find real battle name tables via pointers, fixed-width, A8 compare."""
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
A8 = Path(r"d:\aaaaaaa_bianyi\gba_decomp_gezhaer_alpha8v2\rom.gba").read_bytes()


def find_all(rom: bytes, needle: bytes, limit: int = 80) -> list[int]:
    out, start = [], 0
    while len(out) < limit:
        i = rom.find(needle, start)
        if i < 0:
            break
        out.append(i)
        start = i + 1
    return out


def ptr(off: int) -> bytes:
    return struct.pack("<I", 0x08000000 + off)


def find_ptrs(rom: bytes, off: int, limit: int = 50) -> list[int]:
    return find_all(rom, ptr(off), limit)


def dump(rom: bytes, off: int, n: int = 20) -> str:
    return decode_bytes(rom[off : off + n])


def decode_chs(data: bytes, to_str: dict[bytes, str], max_len: int = 32) -> str:
    parts = []
    i = 0
    while i < min(len(data), max_len):
        if data[i] == 0xFF:
            break
        # try 2-byte then 1-byte
        if i + 1 < len(data) and data[i : i + 2] in to_str:
            parts.append(to_str[data[i : i + 2]])
            i += 2
            continue
        if data[i : i + 1] in to_str:
            parts.append(to_str[data[i : i + 1]])
            i += 1
            continue
        # fallback gen3
        parts.append(decode_bytes(data[i : i + 1] + b"\xff") or f"[{data[i]:02X}]")
        i += 1
    return "".join(parts)


_, TO_STR = load_charmap()

# ---- 1) Exact string starts (GOLD) ----
print("=== GOLD exact string starts & inbound ptrs ===")
for name in ["Pound", "Karate Chop", "Tackle", "Scratch", "Treecko", "Grovyle", "Bulbasaur", "????????"]:
    needle = encode_plain(name)
    hits = find_all(GOLD, needle, limit=20)
    print(f"\n{name}: {[hex(h) for h in hits]}")
    for h in hits:
        ptrs = find_ptrs(GOLD, h)
        # also ptrs to nearby aligned starts (string may be after padding)
        nearby = []
        for delta in range(0, 16):
            nearby += [(h - delta, p) for p in find_ptrs(GOLD, h - delta)]
        print(f"  @{h:08X} direct_ptrs={[hex(p) for p in ptrs]}")
        if nearby:
            # unique ptr sites
            sites = sorted(set(p for _, p in nearby))
            print(f"  nearby_target_ptrs (target-16..0): {[hex(p) for p in sites[:15]]}")
            for tgt, p in nearby[:8]:
                print(f"    table@{p:08X} -> 0x{tgt:X} ({dump(GOLD,tgt)!r})")

# ---- 2) Second copies still EN in CN? ----
print("\n=== Alternate copies: GOLD vs CN ===")
alts = [
    (0x417D79, "Pound_varlen"),
    (0x417F99, "Tackle_varlen1"),
    (0x419445, "Tackle_varlen2"),
    (0x423E74, "Tackle_copy3"),
    (0x40EFD4, "Treecko_title1"),
    (0x413D04, "Treecko_title2"),
    (0x1024FD7, "TREECKO_upper"),
]
for off, lab in alts:
    g = dump(GOLD, off)
    c = dump(CN, off)
    same = GOLD[off : off + 16] == CN[off : off + 16]
    print(f"  0x{off:X} {lab}: GOLD={g!r} CN={c!r} same16={same} CN_chs={decode_chs(CN[off:off+16], TO_STR)!r}")

# ---- 3) Quetzal move table structure: walk from Pound ----
print("\n=== Walk Quetzal move names from 0x417D79 (varlen) first 20 ===")
p = 0x417D79
for i in range(20):
    eos = GOLD.find(b"\xff", p, p + 40)
    s = decode_bytes(GOLD[p : eos + 1])
    print(f"  [{i:3d}] 0x{p:X} len={eos-p+1:2d} {s!r}")
    p = eos + 1

# ---- 4) Find pointer TABLE that indexes move IDs ----
# Emerald: often array of pointers, or base+moveId*13
# Quetzal may use pointer array to each varlen string
print("\n=== Search for pointer arrays covering Pound..Karate.. ----")
pound = 0x417D79
karate = 0x417D8A
# Look for consecutive ptrs: [ptr Pound][ptr Karate]
pat = ptr(pound) + ptr(karate)
hits = find_all(GOLD, pat, limit=10)
print(f"  consecutive Pound+Karate ptrs: {[hex(h) for h in hits]}")
# Also try with padded starts used in fill script
for a, b in [(0x417D6A, 0x417D8A), (0x417D70, 0x417D8A), (0x417D78, 0x417D8A)]:
    pat2 = ptr(a) + ptr(b)
    hits2 = find_all(GOLD, pat2, limit=5)
    if hits2:
        print(f"  consec {a:X}+{b:X}: {[hex(h) for h in hits2]}")

# Broader: find any ptr to pound, then see if next dwords are ptrs into 0x417xxx
print("\n=== All ptrs to Pound 0x417D79; inspect following table ===")
for site in find_ptrs(GOLD, pound):
    print(f"  site 0x{site:X}")
    for i in range(8):
        val = struct.unpack_from("<I", GOLD, site + i * 4)[0]
        if 0x08000000 <= val < 0x0A000000:
            fo = val - 0x08000000
            print(f"    [{i}] -> 0x{fo:X} {dump(GOLD, fo)!r}")
        else:
            print(f"    [{i}] raw=0x{val:08X}")

# Maybe base pointer only (gMoveNames = start of table, index*stride)
print("\n=== Ptrs to table bases near moves/species ===")
for base in [0x417D79, 0x417D6A, 0x417D00, 0x417C00, 0x417800, 0x40E308, 0x40E300, 0x40EFD4, 0x40EFC0, 0x413D04, 0x413D00]:
    sites = find_ptrs(GOLD, base)
    if sites:
        print(f"  ->0x{base:X}: {[hex(s) for s in sites[:12]]}")

# ---- 5) A8 move table: find ptrs to 0x3FBC3F and species ----
print("\n=== A8 Chinese move table 0x3FBC3F decode + ptrs ===")
for i in range(10):
    r = A8[0x3FBC3F + i * 13 : 0x3FBC3F + (i + 1) * 13]
    print(f"  move[{i}] {decode_chs(r, TO_STR)!r} hex={r.hex()}")
a8_move_ptrs = find_ptrs(A8, 0x3FBC3F)
print(f"  ptrs->3FBC3F: {[hex(p) for p in a8_move_ptrs]}")
# search nearby bases
for base in range(0x3FBC30, 0x3FBC50):
    ps = find_ptrs(A8, base)
    if ps:
        print(f"  ptrs->0x{base:X}: {[hex(p) for p in ps[:8]]}")

# A8 species: Treecko at 0x3F87E7 — find table start (Bulbasaur / ????????)
print("\n=== A8 species around Treecko 0x3F87E7 (11-byte?) ===")
# walk backward by 11
for start_guess in [0x3F87E7 - 11 * 251, 0x3F8000, 0x3F8500]:
    pass
# Find Bulbasaur or ???????? in A8
for name in ["Bulbasaur", "??????????", "TREETO"]:
    pass
bulba = encode_plain("Bulbasaur")
print(f"  A8 Bulbasaur: {[hex(h) for h in find_all(A8, bulba)]}")
# Chinese species table: look for ptr patterns / known A8 offsets from docs
# Scan for 11-byte slots ending with FF densely
print("\n=== Find A8/GOLD fixed 11-byte species-like (Bulbasaur row) ===")
for rname, rom in [("GOLD", GOLD), ("A8", A8)]:
    for off in find_all(rom, encode_plain("Bulbasaur"), limit=10):
        # check if next rows are Ivysaur etc at +11
        ok = True
        names = []
        for i, expect in enumerate(["Bulbasaur", "Ivysaur", "Venusaur", "Charmander"]):
            row = rom[off + i * 11 : off + (i + 1) * 11]
            d = decode_bytes(row)
            names.append(d)
            if expect not in d and d != expect:
                # allow if Chinese
                ok = False
        print(f"  {rname} @{off:X} stride11 names={names} strict_ok={ok}")
        # also try stride 10,12,13
        for st in [10, 12, 13]:
            names2 = [decode_bytes(rom[off + i * st : off + (i + 1) * st]) for i in range(4)]
            print(f"    stride{st}: {names2}")

# Treecko as species #252 in national? In Hoenn dex #1 is Treecko in some tables
# Emerald gSpeciesNames[SPECIES_TREECKO] — SPECIES_TREECKO = 252, entry size 11
# So Bulbasaur is index 1, offset = base+11
print("\n=== Infer species table from Treecko (species 252) ===")
for rname, rom, tree_off in [
    ("GOLD", GOLD, 0x40EFD4),
    ("GOLD2", GOLD, 0x413D04),
    ("A8", A8, 0x3F87E7),
]:
    # if fixed 11 and Treecko is species 252:
    base252 = tree_off - 252 * 11
    base277 = tree_off - 277 * 11  # sometimes with egg etc
    for label, base in [("sp252", base252), ("sp277", base277), ("raw-252*10", tree_off - 252 * 10)]:
        if base < 0:
            continue
        # sample indices 1,4,7,252
        samples = []
        for idx in [0, 1, 4, 7, 25, 252]:
            o = base + idx * 11
            if 0 <= o < len(rom) - 11:
                samples.append(f"{idx}:{decode_bytes(rom[o:o+11])!r}")
        print(f"  {rname} {label} base=0x{base:X} {samples}")
        ps = find_ptrs(rom, base)
        if ps:
            print(f"    PTRS: {[hex(p) for p in ps[:10]]}")
        # also ptr to tree_off - 0 as start of hoenn-only?
        ps2 = find_ptrs(rom, tree_off)
        if label == "sp252" and ps2:
            print(f"    ptrs->treecko: {[hex(p) for p in ps2[:8]]}")

# ---- 6) LZ headers near English names? ----
print("\n=== Check LZ10/LZ11 magic near name tables ===")
# LZ10 = 0x10, LZ11 = 0x11 at start
for off in [0x417000, 0x40E000, 0x413000, 0x423000, 0x3F8000, 0x3FBC00]:
    for rname, rom in [("GOLD", GOLD), ("A8", A8)]:
        hdr = rom[off]
        print(f"  {rname}@{off:X} first=0x{hdr:02X}")

# ---- 7) Battle strings with FD vars (move name expansion) ----
print("\n=== Battle templates referencing move/mon names (GOLD) ===")
# FD:02 often MOVE_NAME, FD:0F nick, etc — scan bank
for base, end in [(0xFF9000, 0x1000000), (0x310000, 0x340000), (0xFC0000, 0xFD0000)]:
    count = 0
    p = base
    while p < end - 2 and count < 30:
        if GOLD[p] == 0xFD and GOLD[p + 1] in (0x02, 0x03, 0x0E, 0x0F, 0x13, 0x14, 0x00, 0x01):
            # show context string start
            # walk back to prev FF
            s0 = GOLD.rfind(b"\xff", max(base, p - 80), p)
            start = s0 + 1 if s0 >= 0 else p
            s = decode_bytes(GOLD[start : start + 60])
            if "FD" in s or True:
                if any(x in s for x in ["used", "Used", "move", "FIGHT", "sent", "faint", "attack"]):
                    print(f"  0x{start:X}: {s!r}")
                    count += 1
            p += 2
        else:
            p += 1

# Search literal ' used '
print("\n=== Search ' used' / 'used ' patterns ===")
for text in [" used ", " used\n", "used ", "'s attack", " attacks!"]:
    try:
        n = encode_plain(text)
    except Exception:
        continue
    hits = find_all(GOLD, n, limit=20)
    print(f"  {text!r}: {[hex(h) for h in hits]}")
    for h in hits[:5]:
        s0 = GOLD.rfind(b"\xff", max(0, h - 40), h) + 1
        print(f"    ctx 0x{s0:X}: {decode_bytes(GOLD[s0:s0+50])!r}")

print("\nDone phase2")
