#!/usr/bin/env python3
"""Deep map/wild/save investigation part 2."""
from __future__ import annotations

import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
G = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()
CN = (ROOT / "out" / "quetzal_084_cn.gba").read_bytes()

MAP_GROUPS = 0x061310C


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def u8(b, o):
    return b[o]


def ro(p):
    return p - 0x08000000 if 0x08000000 <= p < 0x0A000000 else None


def map_hdr(b, group, num):
    gt = ro(u32(b, MAP_GROUPS + group * 4))
    hp = u32(b, gt + num * 4)
    return ro(hp), hp


def find_wild_table(b):
    """Find real gWildMonHeaders: >=120 entries, includes R101 (3,19) with land ptr."""
    best = None
    for base in range(0x400000, 0x700000, 4):
        entries = []
        off = base
        ok = True
        while off + 20 <= len(b):
            mg, mn = u8(b, off), u8(b, off + 1)
            if mg == 0xFF:
                break
            if mg > 40 or mn > 127:
                ok = False
                break
            land, water, rock, fish = struct.unpack_from("<IIII", b, off + 4)
            for p in (land, water, rock, fish):
                if p != 0 and not (0x08000000 <= p <= 0x09FFFFFF):
                    ok = False
                    break
            if not ok:
                break
            entries.append((off, mg, mn, land, water, rock, fish))
            off += 20
        if not ok or len(entries) < 100:
            continue
        has_r101 = any(mg == 3 and mn == 19 and land != 0 for _, mg, mn, land, _, _, _ in entries)
        has_pc_absent = not any(mg == 5 and mn == 4 and land != 0 for _, mg, mn, land, _, _, _ in entries)
        if has_r101 and has_pc_absent:
            if best is None or len(entries) > len(best[1]):
                best = (base, entries)
    return best


def find_heal_table(b):
    """Find gHealLocations: >=15 entries, includes g5m4 Oldale PC coords."""
    best = None
    for base in range(0x400000, 0x700000, 2):
        entries = []
        off = base
        ok = True
        while off + 6 <= len(b):
            mg, mn = u8(b, off), u8(b, off + 1)
            if mg == 0xFF and mn == 0xFF:
                break
            if mg == 0xFF:
                break
            x, y = u16(b, off + 2), u16(b, off + 4)
            if mg > 40 or mn > 127 or x > 64 or y > 64:
                ok = False
                break
            entries.append((off, mg, mn, x, y))
            off += 6
        if not ok or len(entries) < 15:
            continue
        has_oldale_pc = any(mg == 5 and mn == 4 for _, mg, mn, _, _ in entries)
        if has_oldale_pc:
            if best is None or len(entries) > len(best[1]):
                best = (base, entries)
    return best


def scan_free_ptrs(b, start, end):
    n = 0
    hits = []
    for i in range(start, end, 4):
        p = u32(b, i)
        if 0x09DC0000 <= p <= 0x09FFFFFF:
            n += 1
            if len(hits) < 20:
                hits.append(i)
    return n, hits


def diff_ranges(a, b, start, end, limit=20):
    out = []
    i = start
    while i < end:
        if a[i] != b[i]:
            j = i
            while j < end and a[j] != b[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


print("=" * 72)
print("QUETZAL MAP STRUCTURE REPORT (part 2)")
print("=" * 72)

# --- Wild table ---
wild = find_wild_table(G)
wild_cn = find_wild_table(CN)
if wild:
    base, entries = wild
    print(f"\n## gWildMonHeaders @ ROM 0x{base:07X} ({len(entries)} entries)")
    if wild_cn:
        print(f"   CN table @ 0x{wild_cn[0]:07X} ({len(wild_cn[1])} entries) match={wild_cn[0]==base}")
    for mg, mn, label in [(5, 4, "Oldale PC 1F"), (3, 19, "Route 101"), (3, 0, "Oldale Town")]:
        e = next(((o, l, w, r, f) for o, g, m, l, w, r, f in entries if g == mg and m == mn), None)
        if e:
            o, land, water, rock, fish = e
            print(f"  {label} (g{mg} m{mn}) @0x{o:07X}: land={land:08X} water={water:08X}")
            print(f"    G:  {G[o:o+20].hex()}")
            print(f"    CN: {CN[o:o+20].hex()} same={G[o:o+20]==CN[o:o+20]}")
        else:
            print(f"  {label} (g{mg} m{mn}): NO ENTRY")
else:
    print("\n## gWildMonHeaders: NOT FOUND")

# --- Heal locations ---
heal = find_heal_table(G)
heal_cn = find_heal_table(CN)
if heal:
    base, entries = heal
    print(f"\n## gHealLocations @ ROM 0x{base:07X} ({len(entries)} entries)")
    if heal_cn:
        print(f"   CN @ 0x{heal_cn[0]:07X} ({len(heal_cn[1])}) match={heal_cn[0]==base}")
    for i, (off, mg, mn, x, y) in enumerate(entries):
        cn_bytes = CN[off : off + 6]
        g_bytes = G[off : off + 6]
        tag = " DIFF" if g_bytes != cn_bytes else ""
        nm = ""
        if mg == 5 and mn == 4:
            nm = " OLDALE_PC"
        elif mg == 3 and mn == 0:
            nm = " OLDALE"
        elif mg == 1 and mn == 0:
            nm = " LITTLEROOT"
        print(f"  [{i:02d}]@0x{off:07X} g{mg} m{mn} ({x},{y}){nm}{tag}")
    print(f"  Full table identical: {G[base:entries[-1][0]+6]==CN[base:entries[-1][0]+6]}")
else:
    print("\n## gHealLocations: NOT FOUND")

# --- Map header table region ---
print(f"\n## gMapGroups @ 0x{MAP_GROUPS:07X}")
print(f"  Table identical G vs CN: {G[MAP_GROUPS:MAP_GROUPS+34*4]==CN[MAP_GROUPS:MAP_GROUPS+34*4]}")

# --- Pointer corruption zones ---
print("\n## Free-space pointer pollution (0x09DCxxxx)")
for label, b, (a, c) in [
    ("maps 0x100000-0x220000", G, (0x100000, 0x220000)),
    ("maps CN", CN, (0x100000, 0x220000)),
    ("map hdrs 0x600000-0x614000", G, (0x600000, 0x614000)),
    ("map hdrs CN", CN, (0x600000, 0x614000)),
    ("scripts 0x290000-0x298000", G, (0x290000, 0x298000)),
]:
    ng, hg = scan_free_ptrs(b, a, c)
    print(f"  {label}: {ng} free ptrs")

# Compare free ptr positions G vs CN in map region
print("\n## Dword ptr diffs maps 0x100000-0x220000 (G vs CN)")
ptr_diffs = []
for i in range(0x100000, 0x220000, 4):
    if u32(G, i) != u32(CN, i):
        ptr_diffs.append(i)
print(f"  count={len(ptr_diffs)}")
for i in ptr_diffs[:15]:
    print(f"    0x{i:07X}: G={u32(G,i):08X} CN={u32(CN,i):08X}")

# --- Script region around nurse 0x297200 ---
print("\n## Nurse/PC script region 0x297000-0x297400")
dr = diff_ranges(G, CN, 0x297000, 0x297400)
print(f"  diff regions={len(dr)} bytes={sum(b-a for a,b in dr)}")
for a, b in dr[:10]:
    print(f"    0x{a:07X}-0x{b:07X} ({b-a})")
    print(f"      G:  {G[a:min(b,a+24)].hex()}")
    print(f"      CN: {CN[a:min(b,a+24)].hex()}")

# --- Oldale PC script pointer table at 0x2972BC area ---
print("\n## Pointer table @ 0x2972B4-0x297360")
print(f"  identical: {G[0x2972B4:0x297360]==CN[0x2972B4:0x297360]}")
if G[0x2972B4:0x297360] != CN[0x2972B4:0x297360]:
    for off in range(0x2972B4, 0x297360, 4):
        pg, pc = u32(G, off), u32(CN, off)
        if pg != pc:
            print(f"    0x{off:07X}: G={pg:08X} CN={pc:08X}")

# --- Check for wild battle script commands in PC script diffs ---
# MRS/Machine: setwildbattle=0x6B, wildbattle=0x61 in pokeemerald?
print("\n## Script opcode scan in diff region 0x290000-0x298000")
dr = diff_ranges(G, CN, 0x290000, 0x298000)
wild_ops = {0x61, 0x6B, 0x91, 0x92}  # common battle-related
for a, b in dr:
    for rom, label in [(G, "G"), (CN, "CN")]:
        for i in range(a, b):
            if rom[i] in wild_ops:
                ctx = rom[max(a, i - 4) : min(b, i + 8)]
                print(f"  battle opcode 0x{rom[i]:02X} in {label} @0x{i:07X} ctx={ctx.hex()}")

# --- Save block: search for HEAL_LOCATION index table used at runtime ---
# Look for consecutive small integers referencing heal table size
print("\n## ROM header / Quetzal identity")
print(f"  Title: {G[0xA0:0xAC]}")
print(f"  Game code: {G[0xAC:0xB0]}")
print(f"  PKM QUETZAL @ 0x{G.find(b'PKM QUETZAL'):07X}")

# Vanilla Emerald offsets probe
print("\n## Vanilla Emerald reference offsets (expected wrong for Quetzal)")
for name, off in [
    ("vanilla gMapGroups", 0x0482D8C),
    ("vanilla gWildMon", 0x043F564),
    ("vanilla gHealLoc", 0x0458CFC),
]:
    print(f"  {name} @0x{off:07X}: {G[off:off+16].hex()}")

# --- All map headers diff count ---
print("\n## Map header diffs (all maps)")
BASE = MAP_GROUPS
diff_maps = []
for gi in range(34):
    gt = ro(u32(G, BASE + gi * 4))
    for mi in range(64):
        hp_g = u32(G, gt + mi * 4)
        hp_c = u32(CN, gt + mi * 4)
        ho_g, ho_c = ro(hp_g), ro(hp_c)
        if ho_g is None or ho_c is None:
            break
        if G[ho_g : ho_g + 28] != CN[ho_c : ho_c + 28]:
            diff_maps.append((gi, mi, ho_g))
print(f"  differing headers: {len(diff_maps)}")
for gi, mi, ho in diff_maps[:20]:
    print(f"    group={gi} map={mi} @0x{ho:07X}")
