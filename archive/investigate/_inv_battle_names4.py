#!/usr/bin/env python3
"""Phase 4: verify move/species getters (mul size) and CN pointer integrity."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from gen3_charmap import decode_bytes, encode_plain  # noqa: E402
from chs_encode import encode_text, load_charmap  # noqa: E402

CN = bytearray((ROOT / "out" / "quetzal_084_cn.gba").read_bytes())
GOLD = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()
A8 = Path(r"d:\aaaaaaa_bianyi\gba_decomp_gezhaer_alpha8v2\rom.gba").read_bytes()
MYB = Path(r"d:\aaaaaaa_bianyi\MyBoyQuetzal\vendor\quetzal.gba").read_bytes()
_, TO_STR = load_charmap()


def u32(rom, off):
    return struct.unpack_from("<I", rom, off)[0]


def find_all(rom, needle, limit=80):
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


def dump_moves(rom, base, stride, n, label, chs=False):
    print(f"--- {label} ---")
    for i in range(n):
        row = bytes(rom[base + i * stride : base + (i + 1) * stride])
        t = decode_chs(row) if chs else decode_bytes(row)
        print(f"  [{i:3d}] @{base+i*stride:X} {row.hex()} | {t!r}")


print("=== Header name table pointers GOLD / CN / MyBoy / A8 ===")
for name, rom in [("GOLD", GOLD), ("CN", CN), ("MyBoy", MYB), ("A8", A8)]:
    for off in [0x140, 0x144, 0x148, 0x14C]:
        v = u32(rom, off)
        fo = v - 0x08000000 if 0x08000000 <= v < 0x0A000000 else None
        if fo is not None:
            sample = decode_bytes(bytes(rom[fo : fo + 20]))
            print(f"  {name} @{off:X} -> 0x{fo:X} '{sample}'")
        else:
            print(f"  {name} @{off:X} raw=0x{v:08X}")

print("\n=== Confirm Quetzal move table 17-byte @0x417D68 ===")
dump_moves(GOLD, 0x417D68, 17, 12, "GOLD moves stride17")
dump_moves(CN, 0x417D68, 17, 12, "CN moves stride17", chs=True)

# How many moves? find end
print("\n=== Move count / table end ===")
# Nihil Light mentioned as end marker in fill script MOVES_END=0x41B5C8
for text in ["Nihil Light", "Struggle", "Pound"]:
    hits = find_all(GOLD, encode_plain(text), limit=5)
    print(f"  {text}: {[hex(h) for h in hits]}")
# if stride 17 from 0x417D68, Struggle typically near end of gen3 then expanded
struggle = find_all(GOLD, encode_plain("Struggle"), limit=5)
if struggle:
    idx = (struggle[0] - 0x417D68) // 17
    print(f"  Struggle idx~{idx} rem={(struggle[0]-0x417D68)%17}")

print("\n=== Find ALL code refs to move table base 0x417D68 ===")
sites = find_all(GOLD, ptr(0x417D68))
print("  ptr sites:", [hex(s) for s in sites])
for site in sites:
    # show preceding 32 bytes as thumbish
    print(f"  --- site 0x{site:X} ---")
    pre = GOLD[site - 32 : site + 8]
    print(f"  bytes-32: {pre.hex()}")
    # decode nearby as possible mov imm for size
    window = GOLD[site - 64 : site + 16]
    # look for mov rX, #13 (0x0d) = 15 xx or 20 xx in thumb: movs r0,#0x0d -> 0D20
    for imm in [11, 12, 13, 14, 16, 17, 18, 20]:
        # Thumb movs rN, #imm : (imm<<8) | (0x20+N) for N=0..7
        for rn in range(8):
            pat = bytes([imm, 0x20 + rn])
            for hit in find_all(window, pat, limit=5):
                abs_off = site - 64 + hit
                print(f"    movs r{rn},#{imm} at 0x{abs_off:X} (rel {hit})")

print("\n=== Find ALL code refs to species 0x40E308 and secondary 0x413038 ===")
for base in [0x40E308, 0x413038]:
    sites = find_all(GOLD, ptr(base))
    print(f"  ->0x{base:X}: {[hex(s) for s in sites]}")
    for site in sites[:8]:
        window = GOLD[max(0, site - 80) : site + 8]
        found = []
        for imm in [11, 12, 13, 14, 16, 17]:
            for rn in range(8):
                pat = bytes([imm, 0x20 + rn])
                for hit in find_all(window, pat, limit=3):
                    found.append((site - len(window) + hit + (0 if site >= 80 else - (80 - site)), imm, rn))
                    # fix abs
        # simpler recompute
        found = []
        base_win = max(0, site - 80)
        window = GOLD[base_win : site + 8]
        for imm in [11, 12, 13, 14, 16, 17]:
            for rn in range(8):
                pat = bytes([imm, 0x20 + rn])
                for hit in find_all(window, pat, limit=5):
                    found.append((base_win + hit, imm, rn))
        print(f"    site 0x{site:X} nearby movs#: {[(hex(a), f'#{b}', f'r{c}') for a,b,c in found[:12]]}")

# Compare A8 getter sizes
print("\n=== A8 move/species getter mul immediates near ptr sites ===")
for label, base in [("A8moves", 0x3FBC32), ("A8species", 0x3F7D13), ("A8sp_hdr", 0x3F3DF4)]:
    sites = find_all(A8, ptr(base))
    print(f"  {label} ->0x{base:X} sites={[hex(s) for s in sites]}")
    for site in sites[:6]:
        base_win = max(0, site - 80)
        window = A8[base_win : site + 8]
        found = []
        for imm in [11, 12, 13, 14, 16, 17]:
            for rn in range(8):
                pat = bytes([imm, 0x20 + rn])
                for hit in find_all(window, pat, limit=5):
                    found.append((base_win + hit, imm, rn))
        print(f"    site 0x{site:X} movs: {[(hex(a), f'#{b}') for a,b,_ in found[:10]]}")

# Disassemble GetMoveName-like at Quetzal 0x9c-style — find function that loads 0x417D68
print("\n=== Thumb disasm sketch around first non-header move-ptr site ===")

def thumb_dis_rough(rom, start, n_ins=40):
    """Very rough thumb decode for movs/ldr/add/mul/bx."""
    pc = start & ~1
    for _ in range(n_ins):
        hw = struct.unpack_from("<H", rom, pc)[0]
        # movs rd, #imm
        if (hw & 0xE000) == 0x2000:
            rd = (hw >> 8) & 7
            imm = hw & 0xFF
            print(f"  {pc:08X}: movs r{rd}, #{imm}")
        elif (hw & 0xFF00) == 0x4800:
            rd = (hw >> 8) & 7
            imm = (hw & 0xFF) << 2
            # ldr rd, [pc, #imm]
            pool = ((pc + 4) & ~2) + imm
            val = u32(rom, pool) if pool + 4 <= len(rom) else 0
            fo = val - 0x08000000 if val >= 0x08000000 else val
            print(f"  {pc:08X}: ldr r{rd}, [pc, #{imm}] ; ->0x{fo:X}")
        elif (hw & 0xFFC0) == 0x4340:
            rm = (hw >> 3) & 7
            rd = hw & 7
            print(f"  {pc:08X}: mul r{rd}, r{rm}")
        elif (hw & 0xFE00) == 0x1800:
            rm = (hw >> 6) & 7
            rn = (hw >> 3) & 7
            rd = hw & 7
            print(f"  {pc:08X}: adds r{rd}, r{rn}, r{rm}")
        elif hw == 0x4770:
            print(f"  {pc:08X}: bx lr")
        elif (hw & 0xFF00) == 0xBC00:
            print(f"  {pc:08X}: pop {{{hw & 0xFF:02X}}}")
        else:
            print(f"  {pc:08X}: {hw:04X}")
        pc += 2

# Find non-header sites for move table
move_sites = [s for s in find_all(GOLD, ptr(0x417D68)) if s > 0x200]
print("move code sites:", [hex(s) for s in move_sites])
for site in move_sites[:5]:
    # find preceding ldr that references this pool
    # scan back for function start (push) 
    func = site
    for back in range(0, 0x80, 2):
        hw = struct.unpack_from("<H", GOLD, site - back)[0]
        if (hw & 0xFF00) == 0xB500:  # push {lr}
            func = site - back
            break
    print(f"\n## candidate func ~0x{func:X} (pool@0x{site:X})")
    thumb_dis_rough(GOLD, func, 30)

# Also check if CN patches corrupted slot alignment (EOS early leaving English remainder)
print("\n=== CN vs GOLD per-slot for first 15 moves (raw) ===")
for i in range(15):
    g = bytes(GOLD[0x417D68 + i * 17 : 0x417D68 + (i + 1) * 17])
    c = bytes(CN[0x417D68 + i * 17 : 0x417D68 + (i + 1) * 17])
    print(f"  [{i}] G={decode_bytes(g)!r:20s} C={decode_chs(c)!r:20s} same={g==c}")

print("\n=== CN vs GOLD species slots 0,1,25,252 ===")
for idx in [0, 1, 25, 252, 277]:
    off = 0x40E308 + idx * 13
    g = bytes(GOLD[off : off + 13])
    c = bytes(CN[off : off + 13])
    print(f"  sp[{idx}] @{off:X} G={decode_bytes(g)!r} C={decode_chs(c)!r}")
    off2 = 0x413038 + idx * 13
    g2 = bytes(GOLD[off2 : off2 + 13])
    c2 = bytes(CN[off2 : off2 + 13])
    print(f"         sec@{off2:X} G={decode_bytes(g2)!r} C={decode_chs(c2)!r}")

# Battle string FD:34 is move name — verify CN battle bank still English templates (OK)
# More important: is there DUPLICATE move name table used by battle?
print("\n=== Search other 17-byte Pound tables / second bases ===")
# After header ptr, any other table starting with '-' then Pound spaced 17?
dash_pound = encode_plain("-")[:-1]  # just dash? 
# pattern: AE FF then 15 bytes later Pound? move0 is AE FF padded to 17
row0 = GOLD[0x417D68 : 0x417D68 + 17]
print("row0:", row0.hex(), decode_bytes(row0))
# find other occurrences of row0 or of pound-row
pound_row = GOLD[0x417D79 : 0x417D79 + 17]
print("pound row 17:", pound_row.hex())
hits = find_all(GOLD, pound_row, limit=10)
print("exact pound-row copies:", [hex(h) for h in hits])
# also search Tackle row
tackle_off = 0x417D68 + 33 * 17  # MOVE_TACKLE = 33 in emerald
# verify
for i in range(30, 40):
    row = GOLD[0x417D68 + i * 17 : 0x417D68 + (i + 1) * 17]
    print(f"  move[{i}] {decode_bytes(row)!r}")

# Expanded ROM move names?
print("\n=== Scan high ROM for English 'Pound' / Chinese 拍击 outside main table ===")
zh = encode_text("拍击")[:-1]
print("CN all 拍击:", [hex(h) for h in find_all(CN, zh, limit=20)])
print("GOLD all Pound:", [hex(h) for h in find_all(GOLD, encode_plain("Pound"), limit=20)])
print("CN all Pound:", [hex(h) for h in find_all(CN, encode_plain("Pound"), limit=20)])
print("CN all Tackle:", [hex(h) for h in find_all(CN, encode_plain("Tackle"), limit=20)])
print("GOLD all Tackle:", [hex(h) for h in find_all(GOLD, encode_plain("Tackle"), limit=20)])

# MyBoy vs CN at critical tables
print("\n=== MyBoy vs CN at species/moves tables ===")
for a, b, lab in [
    (0x40E308, 0x40E308 + 13 * 400, "species_pri"),
    (0x413038, 0x413038 + 13 * 400, "species_sec"),
    (0x417D68, 0x417D68 + 17 * 900, "moves"),
    (0x144, 0x150, "header_ptrs"),
]:
    same = bytes(MYB[a:b]) == bytes(CN[a:b])
    diffs = sum(1 for x, y in zip(MYB[a:b], CN[a:b]) if x != y)
    print(f"  {lab} same={same} diffs={diffs}")

print("\nDone phase4")
