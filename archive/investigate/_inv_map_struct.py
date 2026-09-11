#!/usr/bin/env python3
"""Read-only structural map/wild/save investigation for Quetzal 0.8.4."""
from __future__ import annotations

import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
CN = ROOT / "out" / "quetzal_084_cn.gba"

MAP_TYPE = {
    0: "NONE",
    1: "TOWN",
    2: "CITY",
    3: "ROUTE",
    4: "UNDERGROUND",
    5: "UNDERWATER",
    6: "OCEAN",
    7: "UNKNOWN7",
    8: "INDOOR",
    9: "SECRET_BASE",
}

# Emerald map IDs (group << 8 | num) — reference for naming
EMERALD_MAPS = {
    (3, 0): "OLDALE_TOWN",
    (5, 4): "OLDALE_POKEMON_CENTER_1F",
    (5, 5): "OLDALE_POKEMON_CENTER_2F",
    (3, 19): "ROUTE101",
    (0, 0): "PETALBURG_CITY",
    (1, 0): "LITTLEROOT_TOWN",
}


def u32(b: bytes, o: int) -> int:
    return struct.unpack_from("<I", b, o)[0]


def u16(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


def u8(b: bytes, o: int) -> int:
    return b[o]


def rom_off(p: int) -> int | None:
    if 0x08000000 <= p < 0x0A000000:
        return p - 0x08000000
    return None


def is_ptr(p: int) -> bool:
    return 0x08000000 <= p <= 0x09FFFFFF


def ptr_str(p: int) -> str:
    ro = rom_off(p)
    return f"{p:08X} (0x{ro:07X})" if ro is not None else f"{p:08X}"


@dataclass
class MapHeader:
    group: int
    num: int
    file_off: int
    layout_ptr: int
    events_ptr: int
    scripts_ptr: int
    connections_ptr: int
    music: int
    map_layout_id: int
    region_map_section: int
    cave: int
    weather: int
    map_type: int
    allow_biking: int
    flags: int
    battle_type: int

    @classmethod
    def parse(cls, b: bytes, off: int, group: int, num: int) -> MapHeader:
        return cls(
            group=group,
            num=num,
            file_off=off,
            layout_ptr=u32(b, off),
            events_ptr=u32(b, off + 4),
            scripts_ptr=u32(b, off + 8),
            connections_ptr=u32(b, off + 12),
            music=u16(b, off + 16),
            map_layout_id=u16(b, off + 18),
            region_map_section=u8(b, off + 20),
            cave=u8(b, off + 21),
            weather=u8(b, off + 22),
            map_type=u8(b, off + 23),
            allow_biking=u8(b, off + 24),
            flags=u8(b, off + 25),
            battle_type=u8(b, off + 26),
        )

    def as_dict(self) -> dict:
        name = EMERALD_MAPS.get((self.group, self.num), "")
        return {
            "name": name,
            "group": self.group,
            "num": self.num,
            "file_off": f"0x{self.file_off:07X}",
            "layout_ptr": ptr_str(self.layout_ptr),
            "events_ptr": ptr_str(self.events_ptr),
            "scripts_ptr": ptr_str(self.scripts_ptr),
            "connections_ptr": ptr_str(self.connections_ptr),
            "music": self.music,
            "map_layout_id": self.map_layout_id,
            "region_map_section": self.region_map_section,
            "cave": self.cave,
            "weather": self.weather,
            "map_type": f"{self.map_type} ({MAP_TYPE.get(self.map_type, '?')})",
            "allow_biking": self.allow_biking,
            "flags": f"0x{self.flags:02X}",
            "battle_type": self.battle_type,
        }


@dataclass
class MapLayout:
    file_off: int
    width: int
    height: int
    border_ptr: int
    map_ptr: int
    primary_tileset_ptr: int
    secondary_tileset_ptr: int

    @classmethod
    def parse(cls, b: bytes, off: int) -> MapLayout:
        return cls(
            file_off=off,
            width=u32(b, off),
            height=u32(b, off + 4),
            border_ptr=u32(b, off + 8),
            map_ptr=u32(b, off + 12),
            primary_tileset_ptr=u32(b, off + 16),
            secondary_tileset_ptr=u32(b, off + 20),
        )


@dataclass
class WildHeader:
    file_off: int
    map_group: int
    map_num: int
    land_ptr: int
    water_ptr: int
    rock_ptr: int
    fish_ptr: int


def find_map_groups(b: bytes) -> tuple[int, list[tuple[int, int, int]]]:
    """Return (table_off, [(group_idx, group_table_off, map_count), ...])."""
    best: tuple[int, list] | None = None
    for base in range(0x0400000, min(len(b) - 160, 0x0A00000), 4):
        groups: list[tuple[int, int, int]] = []
        for gi in range(40):
            gp = u32(b, base + gi * 4)
            if not is_ptr(gp):
                break
            gro = rom_off(gp)
            if gro is None or gro >= len(b) - 4:
                break
            # count consecutive map header ptrs in group
            mc = 0
            for mi in range(128):
                mp = u32(b, gro + mi * 4)
                if not is_ptr(mp):
                    break
                mro = rom_off(mp)
                if mro is None or mro + 28 > len(b):
                    break
                layout = u32(b, mro)
                events = u32(b, mro + 4)
                if not is_ptr(layout) or not is_ptr(events):
                    break
                mc += 1
            if mc < 1:
                break
            groups.append((gi, gro, mc))
        if len(groups) >= 35 and (best is None or len(groups) > len(best[1])):
            best = (base, groups)
    if best is None:
        raise RuntimeError("gMapGroups not found")
    return best


def parse_all_maps(b: bytes, groups_table: int, groups: list[tuple[int, int, int]]) -> dict[tuple[int, int], MapHeader]:
    out: dict[tuple[int, int], MapHeader] = {}
    for gi, gro, mc in groups:
        for mi in range(mc):
            mh_ptr = u32(b, gro + mi * 4)
            mro = rom_off(mh_ptr)
            assert mro is not None
            out[(gi, mi)] = MapHeader.parse(b, mro, gi, mi)
    return out


def find_wild_headers(b: bytes) -> tuple[int, list[WildHeader]]:
    """Find gWildMonHeaders: terminated by mapGroup=0xFF."""
    best: tuple[int, list[WildHeader]] | None = None
    for base in range(0x0400000, min(len(b) - 16, 0x0A00000), 4):
        entries: list[WildHeader] = []
        off = base
        while off + 16 <= len(b):
            mg, mn = u8(b, off), u8(b, off + 1)
            if mg == 0xFF:
                if len(entries) >= 80:
                    if best is None or len(entries) > len(best[1]):
                        best = (base, entries)
                break
            land = u32(b, off + 4)
            water = u32(b, off + 8)
            rock = u32(b, off + 12)
            fish = u32(b, off + 16) if off + 20 <= len(b) else 0
            # Actually WildPokemonHeader is 16 bytes: group, num, pad2, 4 ptrs
            if off + 16 > len(b):
                break
            land = u32(b, off + 4)
            water = u32(b, off + 8)
            rock = u32(b, off + 12)
            fish = u32(b, off + 16 - 4)  # last ptr at +12? check struct size

            # 16-byte struct: u8,u8,u8,u8, 4x u32
            land = u32(b, off + 4)
            water = u32(b, off + 8)
            rock = u32(b, off + 12)
            fish = u32(b, off + 12)  # wrong - fix below
            land = u32(b, off + 4)
            water = u32(b, off + 8)
            rock = u32(b, off + 12)
            # fishing at off+12 is wrong for 16 byte - land@4 water@8 rock@12 fish needs +16
            # struct size 16: group(1) num(1) filler(2) land(4) water(4) rock(4) fish(4) = 20!
            break
        # restart with correct struct size 20 bytes
    # Correct approach: 20-byte entries
    for base in range(0x0400000, min(len(b) - 20, 0x0A00000), 4):
        entries = []
        off = base
        valid = True
        while off + 20 <= len(b):
            mg, mn = u8(b, off), u8(b, off + 1)
            if mg == 0xFF:
                break
            if mg > 40 or mn > 127:
                valid = False
                break
            land, water, rock, fish = struct.unpack_from("<IIII", b, off + 4)
            # at least one ptr or all null for indoor-only maps in table
            ptrs = [land, water, rock, fish]
            if any(p != 0 and not is_ptr(p) for p in ptrs):
                valid = False
                break
            entries.append(
                WildHeader(off, mg, mn, land, water, rock, fish)
            )
            off += 20
        if valid and len(entries) >= 80:
            if best is None or len(entries) > len(best[1]):
                best = (base, entries)
    if best is None:
        raise RuntimeError("gWildMonHeaders not found")
    return best


def find_heal_locations(b: bytes) -> tuple[int, list[dict]]:
    """HealLocation struct: u8 group, u8 map, u16 x, u16 y (6 bytes). Table ends with 0xFFFF map?"""
    best: tuple[int, list] | None = None
    for base in range(0x0400000, min(len(b) - 6, 0x0A00000), 2):
        entries = []
        off = base
        ok = True
        while off + 6 <= len(b):
            mg, mn = u8(b, off), u8(b, off + 1)
            x, y = u16(b, off + 2), u16(b, off + 4)
            if mg == 0xFF and mn == 0xFF:
                break
            if mg > 40 or mn > 127 or x > 64 or y > 64:
                ok = False
                break
            entries.append({"off": off, "group": mg, "map": mn, "x": x, "y": y})
            off += 6
        if ok and len(entries) >= 15:
            if best is None or len(entries) > len(best[1]):
                best = (base, entries)
    if best is None:
        return 0, []
    return best


def layout_metatile_stats(b: bytes, layout_ptr: int) -> dict:
    lo = rom_off(layout_ptr)
    if lo is None:
        return {"error": "bad layout ptr"}
    layout = MapLayout.parse(b, lo)
    mo = rom_off(layout.map_ptr)
    if mo is None:
        return {"error": "bad map ptr", "layout_off": lo}
    w, h = layout.width, layout.height
    if w <= 0 or h <= 0 or w > 256 or h > 256:
        return {"error": "bad dims", "w": w, "h": h}
    total = w * h * 2
    if mo + total > len(b):
        return {"error": "map OOB"}
    tiles = b[mo : mo + total]
    # metatile entry: u16 with bottom 10 bits metatile id, bits 10-11 collision, 12-15 elevation
    encounter_tiles = []
    behavior_counts: dict[int, int] = {}
    for i in range(0, len(tiles), 2):
        entry = struct.unpack_from("<H", tiles, i)[0]
        metatile_id = entry & 0x3FF
        collision = (entry >> 10) & 3
        elevation = (entry >> 12) & 15
        tx, ty = (i // 2) % w, (i // 2) // w
        # collision 3 = impassable north/south? In gen3, bit patterns vary
        # Wild encounters triggered by metatile behavior from tileset, not map entry directly
        # Map entry collision 0=passable, 1=?, 2=?, 3=impassable
        if collision == 0 and elevation < 15:
            pass
    return {
        "layout_off": f"0x{lo:07X}",
        "map_data_off": f"0x{mo:07X}",
        "width": w,
        "height": h,
        "primary_tileset": ptr_str(layout.primary_tileset_ptr),
        "secondary_tileset": ptr_str(layout.secondary_tileset_ptr),
    }


def compare_headers(hg: MapHeader, hc: MapHeader) -> list[str]:
    diffs = []
    for field_name in (
        "layout_ptr", "events_ptr", "scripts_ptr", "connections_ptr",
        "music", "map_layout_id", "region_map_section", "cave", "weather",
        "map_type", "allow_biking", "flags", "battle_type",
    ):
        vg = getattr(hg, field_name)
        vc = getattr(hc, field_name)
        if vg != vc:
            diffs.append(f"  {field_name}: G={vg} CN={vc}")
    return diffs


def diff_region(g: bytes, c: bytes, start: int, end: int) -> list[tuple[int, int]]:
    out = []
    i = start
    while i < end:
        if g[i] != c[i]:
            j = i
            while j < end and g[j] != c[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def main() -> int:
    g = GOLDEN.read_bytes()
    cn = CN.read_bytes()

    print("=" * 72)
    print("QUETZAL 0.8.4 MAP / WILD / SAVE STRUCTURAL REPORT")
    print("=" * 72)
    print(f"Golden: {GOLDEN} ({len(g)} bytes)")
    print(f"CN:     {CN} ({len(cn)} bytes)")
    print(f"Total byte diffs: {sum(1 for a,b in zip(g,cn) if a!=b)}")

    # 1. Map groups
    print("\n## 1. gMapGroups discovery")
    vanilla_off = 0x0482D8C
    print(f"Vanilla Emerald offset 0x{vanilla_off:07X} probe:")
    for gi in range(3):
        gp = u32(g, vanilla_off + gi * 4)
        print(f"  group[{gi}] = {ptr_str(gp)}")

    mg_off, groups = find_map_groups(g)
    mg_off_cn, groups_cn = find_map_groups(cn)
    print(f"\nDiscovered gMapGroups @ 0x{mg_off:07X} ({len(groups)} groups) [golden]")
    print(f"Discovered gMapGroups @ 0x{mg_off_cn:07X} ({len(groups_cn)} groups) [CN]")
    print(f"Table offset match: {mg_off == mg_off_cn}")

    maps_g = parse_all_maps(g, mg_off, groups)
    maps_c = parse_all_maps(cn, mg_off_cn, groups_cn)

    # 2. Oldale PC
    print("\n## 2. Oldale Pokemon Center (group 5, map 4)")
    key = (5, 4)
    for label, maps, rom in [("GOLDEN", maps_g, g), ("CN", maps_c, cn)]:
        if key not in maps:
            print(f"  {label}: NOT FOUND")
            continue
        h = maps[key]
        print(f"\n  [{label}] MapHeader @ 0x{h.file_off:07X}")
        for k, v in h.as_dict().items():
            print(f"    {k}: {v}")
        lo = rom_off(h.layout_ptr)
        if lo:
            lay = MapLayout.parse(rom, lo)
            print(f"    MapLayout @ 0x{lo:07X}: {lay.width}x{lay.height}")
            stats = layout_metatile_stats(rom, h.layout_ptr)
            for sk, sv in stats.items():
                print(f"      {sk}: {sv}")

    if key in maps_g and key in maps_c:
        diffs = compare_headers(maps_g[key], maps_c[key])
        print("\n  Header field diffs (G vs CN):")
        if diffs:
            print("\n".join(diffs))
        else:
            print("    (none — identical)")

        # Raw 28-byte compare
        go, co = maps_g[key].file_off, maps_c[key].file_off
        if g[go:go+28] != cn[co:co+28]:
            print(f"    RAW header bytes differ!")
            print(f"    G:  {g[go:go+28].hex()}")
            print(f"    CN: {cn[co:co+28].hex()}")
        else:
            print("    RAW 28-byte header: identical")

        # Events/scripts blob compare
        for pname, ptr in [("events", maps_g[key].events_ptr), ("scripts", maps_g[key].scripts_ptr)]:
            ro = rom_off(ptr)
            if ro:
                # events header: objectCount(4), warpCount(4), ...
                eg = g[ro:ro+64]
                ec = cn[ro:ro+64]
                if eg != ec:
                    dr = diff_region(g, cn, ro, ro + 256)
                    print(f"  {pname} @ 0x{ro:07X}: {len(dr)} diff region(s) in first 256B")
                    for a, b in dr[:5]:
                        print(f"    0x{a:07X}-0x{b:07X} ({b-a} bytes)")

    # Also check Oldale town outdoor
    print("\n## 2b. Oldale Town (group 3, map 0)")
    for k2 in [(3, 0), (5, 5), (3, 19)]:
        name = EMERALD_MAPS.get(k2, "?")
        print(f"\n  Map {k2} ({name}):")
        for label, maps in [("G", maps_g), ("CN", maps_c)]:
            if k2 not in maps:
                print(f"    {label}: missing")
                continue
            h = maps[k2]
            print(f"    {label}: hdr@0x{h.file_off:07X} type={h.map_type} battle={h.battle_type} flags=0x{h.flags:02X} layout={ptr_str(h.layout_ptr)}")
        if k2 in maps_g and k2 in maps_c:
            d = compare_headers(maps_g[k2], maps_c[k2])
            if d:
                print("    DIFFS:")
                print("\n".join(d))

    # 3. Wild encounter table
    print("\n## 3. gWildMonHeaders")
    try:
        wh_off, wild_g = find_wild_headers(g)
        wh_off_cn, wild_c = find_wild_headers(cn)
        print(f"Golden @ 0x{wh_off:07X} ({len(wild_g)} entries)")
        print(f"CN     @ 0x{wh_off_cn:07X} ({len(wild_c)} entries)")
        print(f"Table offset match: {wh_off == wh_off_cn}")

        def wild_for(mg, mn, wild_list):
            for w in wild_list:
                if w.map_group == mg and w.map_num == mn:
                    return w
            return None

        for mg, mn, label in [(5, 4, "Oldale PC 1F"), (3, 0, "Oldale Town"), (3, 19, "Route 101")]:
            wg = wild_for(mg, mn, wild_g)
            wc = wild_for(mg, mn, wild_c)
            print(f"\n  {label} (group {mg}, map {mn}):")
            if wg:
                print(f"    G: entry@0x{wg.file_off:07X} land={ptr_str(wg.land_ptr)} water={ptr_str(wg.water_ptr)}")
            else:
                print("    G: no entry")
            if wc:
                print(f"    CN: entry@0x{wc.file_off:07X} land={ptr_str(wc.land_ptr)} water={ptr_str(wc.water_ptr)}")
            else:
                print("    CN: no entry")
            if wg and wc:
                if g[wg.file_off:wg.file_off+20] != cn[wc.file_off:wc.file_off+20]:
                    print(f"    ENTRY BYTES DIFFER")
                    print(f"      G:  {g[wg.file_off:wg.file_off+20].hex()}")
                    print(f"      CN: {cn[wc.file_off:wc.file_off+20].hex()}")
    except RuntimeError as e:
        print(f"  ERROR: {e}")

    # 4. Heal locations (save warp targets)
    print("\n## 4. Heal locations table")
    hl_off, heal_g = find_heal_locations(g)
    hl_off_cn, heal_c = find_heal_locations(cn)
    if heal_g:
        print(f"Golden @ 0x{hl_off:07X} ({len(heal_g)} entries)")
        print(f"CN     @ 0x{hl_off_cn:07X} ({len(heal_c)} entries)")
        # Oldale PC heal is typically index for Petalburg/Oldale region
        for i, (eg, ec) in enumerate(zip(heal_g, heal_c)):
            if eg != ec:
                print(f"  entry[{i}] DIFF: G={eg} CN={ec}")
        # show first 20
        print("  First 20 heal entries (golden):")
        for e in heal_g[:20]:
            nm = EMERALD_MAPS.get((e["group"], e["map"]), "")
            print(f"    @{e['off']:07X} group={e['group']} map={e['map']} ({nm}) x={e['x']} y={e['y']}")
    else:
        print("  Heal table not auto-found")

    # 5. Pointer corruption scan in map region
    print("\n## 5. Pointer corruption in map/script region (0x100000-0x220000)")
    free_bad_g = free_bad_c = ptr_diff = 0
    for i in range(0x100000, 0x220000, 4):
        pg, pc = u32(g, i), u32(cn, i)
        if pg != pc:
            ptr_diff += 1
        for p in (pc,):
            if 0x09DC0000 <= p <= 0x09FFFFFF:
                free_bad_c += 1
            if 0x09DC0000 <= p <= 0x09FFFFFF:
                free_bad_g += 1
    print(f"  Dword diffs in range: {ptr_diff}")
    print(f"  Free-space ptrs (0x09DCxxxx) in CN: {free_bad_c}")
    print(f"  Free-space ptrs (0x09DCxxxx) in G:  {free_bad_g}")

    # Sample remaining diffs near Oldale PC scripts
    print("\n## 6. Known PC script region 0x297200-0x297400")
    dr = diff_region(g, cn, 0x297200, 0x297400)
    print(f"  Diff regions: {len(dr)} total bytes={sum(b-a for a,b in dr)}")
    for a, b in dr[:8]:
        print(f"    0x{a:07X}-0x{b:07X} ({b-a})")
        print(f"      G:  {g[a:min(b,a+32)].hex()}")
        print(f"      CN: {cn[a:min(b,a+32)].hex()}")

    # 7. Save struct constants in ROM
    print("\n## 7. Save-block related ROM constants")
    # Search for SAVE_BLOCK sizes / version markers
    for needle, name in [
        (b"PokemonSioInfo", "Link marker"),
        (b"PKM QUETZAL", "Quetzal marker"),
    ]:
        idx = g.find(needle)
        print(f"  {name}: golden @ 0x{idx:07X}" if idx >= 0 else f"  {name}: not found")

    # Compare full map header table region
    print("\n## 8. All map header byte diffs (CN vs G)")
    hdr_diff_maps = []
    for k, hg in maps_g.items():
        if k not in maps_c:
            continue
        hc = maps_c[k]
        if g[hg.file_off:hg.file_off+28] != cn[hc.file_off:hc.file_off+28]:
            hdr_diff_maps.append(k)
    print(f"  Maps with differing headers: {len(hdr_diff_maps)}")
    for k in hdr_diff_maps[:15]:
        print(f"    group={k[0]} map={k[1]} ({EMERALD_MAPS.get(k,'?')})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
