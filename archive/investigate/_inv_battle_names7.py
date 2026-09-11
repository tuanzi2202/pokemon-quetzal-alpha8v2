#!/usr/bin/env python3
"""Phase 7: more species lang tables; battle buffer paths; A8 compare; nickname vs species."""
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
_, TO_STR = load_charmap()


def u16(rom, off):
    return struct.unpack_from("<H", rom, off)[0]


def u32(rom, off):
    return struct.unpack_from("<I", rom, off)[0]


def find_all(rom, needle, limit=60):
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


# Find all Bulbasaur-like 13-byte tables (species lang copies)
print("=== All ?????????? 13-byte species table starts (GOLD) ===")
needle = encode_plain("??????????")
# also padded form used in table: 10x AC + FF + 00 00
row0 = GOLD[0x40E308 : 0x40E308 + 13]
print("row0 hex", row0.hex())
for hit in find_all(GOLD, row0, limit=30):
    bulba = decode_bytes(GOLD[hit + 13 : hit + 26])
    print(f"  @{hit:X} next={bulba!r} ptrs={[hex(p) for p in find_all(GOLD, ptr(hit), limit=8)]}")

print("\n=== A8 header species (Chinese) vs battle English table ===")
# A8 0x144 -> 0x3F3DF4 Chinese 11-byte
# A8 0x3F7D13 English 11-byte still
print("hdr[1]", decode_chs(A8[0x3F3DF4 + 11 : 0x3F3DF4 + 22]))
print("en[1]", decode_bytes(A8[0x3F7D13 + 11 : 0x3F7D13 + 22]))
print("Which does A8 GetSpeciesName use?")
# From earlier: 0x9727c / 0x9c104 -> 0x3F7D13 ENGLISH
# Header 0x144 -> 0x3F3DF4 Chinese — maybe used by different API
for site in find_all(A8, ptr(0x3F3DF4)):
    print(f"  ptr->3F3DF4 @{site:X}")
for site in find_all(A8, ptr(0x3F7D13)):
    print(f"  ptr->3F7D13 @{site:X}")

# Disasm A8 move getter language logic like Quetzal
print("\n=== A8 move getter @0x9C144 area ===")
# find func
for pc in range(0x9C100, 0x9C180, 2):
    hw = u16(A8, pc)
    if (hw & 0xF800) == 0x4800:
        imm = (hw & 0xFF) << 2
        pool = ((pc + 4) & ~2) + imm
        val = u32(A8, pool)
        if val == 0x083FBC32:
            print(f"ldr @0x{pc:X} -> moves")
            # dump 64 bytes before
            print(A8[pc - 48 : pc + 16].hex())

# Simulate: if lang!=2 would Quetzal show Spanish (looks Latin/English-ish to Chinese user)?
# User said ENGLISH - Placaje is Spanish. Pound is English.
# So they likely have lang=ENGLISH and should see CN table...

# Unless fight menu does NOT call 0x9F0F4
print("\n=== Find BL to 0x9F0F4/5 (GetMoveName) ===")
# Thumb BL: bits encoding
# BL to target T: 
# offset = T - (pc+4); split into two hi/lo

def find_bl_to(rom, target_thumb, search_start=0, search_end=0x200000):
    """target_thumb includes thumb bit (addr|1) or even addr."""
    target = target_thumb & ~1
    hits = []
    for pc in range(search_start & ~1, search_end, 2):
        hw1 = u16(rom, pc)
        hw2 = u16(rom, pc + 2)
        if (hw1 & 0xF800) != 0xF000:
            continue
        if (hw2 & 0xF800) != 0xF800:
            continue
        imm10 = hw1 & 0x7FF
        imm11 = hw2 & 0x7FF
        # older thumb BL
        s = (imm10 >> 10) & 1
        # actually classic: offset = SignExtend(imm10:imm11:0, 23)
        rel = ((imm10 << 12) | (imm11 << 1))
        if rel & (1 << 22):
            rel |= ~((1 << 23) - 1)
        dest = pc + 4 + rel
        if dest == target:
            hits.append(pc)
            if len(hits) >= 40:
                break
    return hits


bls = find_bl_to(GOLD, 0x9F0F4, 0, 0x400000)
print(f"BL to 0x9F0F4: {len(bls)} hits: {[hex(h) for h in bls[:30]]}")
# also try 0x9F0F5
bls2 = find_bl_to(GOLD, 0x9F0F5, 0, 0x100000)
print(f"BL to 0x9F0F5: {len(bls2)} {[hex(h) for h in bls2[:20]]}")

# Maybe function starts at 0x9F0F5? Check align
print("bytes at 9F0F0", GOLD[0x9F0F0:0x9F0F8].hex())

# Try finding callers via push pattern - search for bl with looser
# Alternative approach: string expansion for battle uses CopyMoveName
# Search code that does mov #17 near battle text
print("\n=== Functions that load 0x417D68 without language (direct) ===")
# Only header + one site - so ALL software paths go through switcher or header const

# Check Emerald-style gMoveToIndex in battle - maybe uses move description name field?
print("\n=== Move data struct name pointer fields? ===")
# Quetzal expanded moves - check if each move has a name pointer in battle move struct
# Emerald gBattleMoves doesn't include name; names are parallel array.

# Buffer string FD:34 — find who writes to string var 0x34
# In emerald StringVar expansion, case 0x34 might be MOVE_NAME

print("\n=== Battle string used-move template in CN ===")
# 0xFFB9DB: '{FD:0F} used\n{FD:34}!'
off = 0xFFB9DB
print("GOLD:", decode_bytes(GOLD[off : off + 40]))
print("CN  :", decode_bytes(CN[off : off + 40]))
print("CN chs:", decode_chs(CN[off : off + 40]))

# Check if there's English move name mirror in WRAM init from wrong table
# Look at 0x41BB90 - if somehow English save corrupted to lang=1, user sees Spanish
# User insists English - so lang=2 and table should be CN

# POSSIBLE BUG: fill script left leading 0x00 spaces; does battle menu use fixed 12-char 
# window that reads WRONG if first bytes are 0x00 treated as EOS?
# In Gen3, 0x00 is SPACE not EOS! EOS is 0xFF. So leading spaces OK.

# Another bug: Chinese double-byte 0x0A 0x21 - could 0x0A be interpreted as newline control?
# In Gen3 Western, 0x0A is not a special control (controls are FA-FF, FC, FD).
# But Wokann Chinese uses high bytes - need font hook to interpret as lead byte.
# If font hook works for dialogue, should work for move names too.

print("\n=== Verify font hook present in CN ===")
# From DEBUG_PROBES: CharRead 0x0800596C
print("CN==GOLD at 0x596C?", CN[0x596C:0x59A0] == GOLD[0x596C:0x59A0])
# check for hook differences in low code
diff_low = sum(1 for a, b in zip(CN[:0x10000], GOLD[:0x10000]) if a != b)
print(f"diffs in first 64KB: {diff_low}")

# Compare A8 approach: Chinese in 13-byte table matching Emerald size
print("\n=== Summary compare Quetzal vs A8 layout ===")
print("Quetzal species: 13-byte @0x40E308 (hdr 0x144) + copy @0x413038")
print("A8 species CN: 11-byte @0x3F3DF4 (hdr 0x144); EN leftover @0x3F7D13")
print("Quetzal moves: 17-byte @0x417D68 (hdr 0x148) + ES @0x41BB90 + ES2 @0x41F9B8")
print("A8 moves CN: 13-byte @0x3FBC32 (hdr 0x148)")

# Critical: does battle HP use species or nickname?
# Search "GetMonData" nickname - can't easily. Document both.

# Check expanded ROM for ENGLISH move name copies used by custom battle UI
print("\n=== Search high ROM for Title-Case Pound/Tackle/Treecko ===")
for text in ["Pound", "Tackle", "Treecko", "Scratch", "Ember"]:
    n = encode_plain(text)
    for rname, rom in [("GOLD", GOLD), ("CN", CN)]:
        hits = [h for h in find_all(rom, n, limit=20) if h > 0x800000 or h < 0x400000]
        # all hits
        hits = find_all(rom, n, limit=15)
        if hits:
            print(f"  {rname} {text}: {[hex(h) for h in hits]}")

# Double-check fill_battle_names: species walk was varlen between SPECIES_START and MOVES_START
# With 13-byte fixed slots containing internal FF, varlen walk works per slot.
# Moves: walk from 0x417D6A - starts 2 bytes into move0 slot; still finds Pound etc.
# Stops at MOVES_END 0x41B5C8 = end of English table — CORRECT for main table.
# Does NOT patch Spanish alts — OK if lang=English.

print("\n=== Language enum check: byte values near options strings ===")
for text in ["ENGLISH", "Espa", "FRANCAIS", "DEUTSCH", "Language", "LANGUAGE"]:
    try:
        n = encode_plain(text)
    except Exception:
        continue
    hits = find_all(GOLD, n, limit=8)
    if hits:
        print(f"  {text!r}: {[hex(h) for h in hits]}")

# Final: check if MyBoy APK ships English ROM as default
print("\n=== MD5 reminder ===")
import hashlib
print("out CN", hashlib.md5(CN).hexdigest())
print("golden", hashlib.md5(GOLD).hexdigest())

# One more angle: maybe fight menu uses move *description* header or contest name?
print("\n=== Contest/move short names table? ===")
# Search for "TACKLE" style short
for text in ["TACKLE", "POUND", "SCRATCH", "EMBER"]:
    hits = find_all(GOLD, encode_plain(text), limit=10)
    print(f"  {text}: {[hex(h) for h in hits]}")

print("\nDone phase7")
