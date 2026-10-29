#!/usr/bin/env python3
"""Add a two-way warp from Littleroot Town to an independent empty map.

The Alpha8v2 ROM has an unused map slot at group 27, map 0.  This patch
repurposes that slot, builds a small 20x20 ground layout, and adds one warp
in each direction.  The source ROM is never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "out" / "alpha8v2_npc.gba"
DEFAULT_OUTPUT = ROOT / "out" / "alpha8v2_gate.gba"
MANIFEST = ROOT / "work" / "alpha8v2_gate_manifest.json"

EXPECTED_SHA1 = "d8071746acf47bc980cdd24440d78ec64ed28360"
ROM_BASE = 0x08000000
MAP_GROUPS = 0x0061A5A8
LITTLEROOT_HEADER = 0x006165E4
LITTLEROOT_EVENTS = 0x01061554
GROUP27_TABLE = 0x0061A550
NEW_GROUP = 27
NEW_MAP = 0
OBJECT_SIZE = 24
EVENT_HEADER_SIZE = 20
MAP_HEADER_SIZE = 28
LAYOUT_SIZE = 24
FREE_OFFSET = 0x01FEF600
GROUND_BLOCK = 0x3001
DOOR_BLOCK = 0x0648


def u32(data: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def put_u32(data: bytearray, off: int, value: int) -> None:
    struct.pack_into("<I", data, off, value)


def rom_offset(pointer: int) -> int | None:
    if ROM_BASE <= pointer < ROM_BASE + 0x02000000:
        return pointer - ROM_BASE
    return None


def pointer(off: int) -> int:
    return ROM_BASE + off


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def find_free(data: bytes, start: int, size: int) -> int:
    end = start + size
    if end > len(data) or any(value != 0xFF for value in data[start:end]):
        raise ValueError(f"reserved free-space range is not empty: 0x{start:07X}-0x{end:07X}")
    return start


def validate_pointer(data: bytes, address: int, label: str) -> int:
    off = rom_offset(u32(data, address))
    if off is None:
        raise ValueError(f"{label} pointer is invalid at 0x{address:07X}")
    return off


def build_patch(source: Path, output: Path, source_x: int, source_y: int,
                destination_x: int, destination_y: int) -> dict[str, object]:
    original = source.read_bytes()
    digest = sha1(original)
    if digest != EXPECTED_SHA1:
        raise ValueError(f"unexpected Alpha8v2 NPC input SHA-1 {digest}; expected {EXPECTED_SHA1}")
    if len(original) != 0x02000000:
        raise ValueError("input must be an unheadered 32 MiB GBA ROM")
    if original[0xA0:0xAC].rstrip(b"\0 ") != b"PKM QUETZAL":
        raise ValueError("input does not have the PKM QUETZAL header")
    for x, y, label in ((source_x, source_y, "source warp"), (destination_x, destination_y, "destination warp")):
        if not (0 <= x < 20 and 0 <= y < 20):
            raise ValueError(f"{label} coordinates must be inside the 20x20 map")

    data = bytearray(original)
    source_events = validate_pointer(data, LITTLEROOT_HEADER + 4, "Littleroot events")
    if source_events != LITTLEROOT_EVENTS:
        raise ValueError(f"unexpected Littleroot events offset 0x{source_events:07X}")
    object_count, old_warp_count, coord_count, bg_count = data[source_events:source_events + 4]
    if object_count != 14 or old_warp_count != 3:
        raise ValueError(f"unexpected Littleroot event counts: objects={object_count}, warps={old_warp_count}")
    old_object_off = validate_pointer(data, source_events + 4, "Littleroot objects")
    old_warp_off = validate_pointer(data, source_events + 8, "Littleroot warps")
    coord_ptr = u32(data, source_events + 12)
    bg_ptr = u32(data, source_events + 16)

    # Source event header + copied warp table, destination map header/layout,
    # and destination event/warp data.
    source_header_off = FREE_OFFSET
    source_warps_off = source_header_off + EVENT_HEADER_SIZE
    map_header_off = source_warps_off + (old_warp_count + 1) * 8
    layout_off = map_header_off + MAP_HEADER_SIZE
    blockdata_off = layout_off + LAYOUT_SIZE
    dest_events_off = blockdata_off + 20 * 20 * 2
    dest_warp_off = dest_events_off + EVENT_HEADER_SIZE
    source_layout_copy_off = dest_warp_off + 8
    source_blockdata_copy_off = source_layout_copy_off + LAYOUT_SIZE
    total_size = (source_blockdata_copy_off + 20 * 20 * 2) - FREE_OFFSET
    find_free(data, FREE_OFFSET, total_size)

    # Copy and extend Littleroot's event header and warp list.
    data[source_header_off:source_header_off + EVENT_HEADER_SIZE] = data[source_events:source_events + EVENT_HEADER_SIZE]
    data[source_header_off] = object_count
    data[source_header_off + 1] = old_warp_count + 1
    data[source_warps_off:source_warps_off + old_warp_count * 8] = data[old_warp_off:old_warp_off + old_warp_count * 8]
    struct.pack_into("<hhHBB", data, source_warps_off + old_warp_count * 8,
                     source_x, source_y, 0, NEW_MAP, NEW_GROUP)
    put_u32(data, source_header_off + 8, pointer(source_warps_off))
    put_u32(data, LITTLEROOT_HEADER + 4, pointer(source_header_off))

    # Build the new map header from the known unused group-27/map-0 header.
    group27_old_header = rom_offset(u32(data, GROUP27_TABLE))
    if group27_old_header is None:
        raise ValueError("group 27 map 0 header pointer is invalid")
    data[map_header_off:map_header_off + MAP_HEADER_SIZE] = data[group27_old_header:group27_old_header + MAP_HEADER_SIZE]
    put_u32(data, map_header_off, pointer(layout_off))
    put_u32(data, map_header_off + 4, pointer(dest_events_off))
    put_u32(data, GROUP27_TABLE, pointer(map_header_off))

    # Reuse Littleroot's tested border and tilesets, but make every block a
    # common passable ground block for a visually empty 20x20 area.
    source_layout = validate_pointer(data, LITTLEROOT_HEADER, "Littleroot layout")
    data[layout_off:layout_off + LAYOUT_SIZE] = data[source_layout:source_layout + LAYOUT_SIZE]
    struct.pack_into("<II", data, layout_off, 20, 20)
    put_u32(data, layout_off + 12, pointer(blockdata_off))
    for i in range(20 * 20):
        struct.pack_into("<H", data, blockdata_off + i * 2, GROUND_BLOCK)
    struct.pack_into("<H", data, blockdata_off + (destination_y * 20 + destination_x) * 2, DOOR_BLOCK)

    # Give the source map a visible doorway without mutating the shared
    # layout/grid used by any other map.
    data[source_layout_copy_off:source_layout_copy_off + LAYOUT_SIZE] = data[source_layout:source_layout + LAYOUT_SIZE]
    put_u32(data, source_layout_copy_off + 12, pointer(source_blockdata_copy_off))
    source_blockdata = validate_pointer(data, source_layout + 12, "Littleroot block data")
    data[source_blockdata_copy_off:source_blockdata_copy_off + 20 * 20 * 2] = data[source_blockdata:source_blockdata + 20 * 20 * 2]
    struct.pack_into("<H", data, source_blockdata_copy_off + (source_y * 20 + source_x) * 2, DOOR_BLOCK)
    put_u32(data, LITTLEROOT_HEADER, pointer(source_layout_copy_off))

    # New map has no objects, scripts, coordinates, or background events, only
    # one warp back to Littleroot. Warp ID 0 resolves to this record.
    data[dest_events_off:dest_events_off + EVENT_HEADER_SIZE] = bytes(EVENT_HEADER_SIZE)
    data[dest_events_off] = 0
    data[dest_events_off + 1] = 1
    put_u32(data, dest_events_off + 8, pointer(dest_warp_off))
    struct.pack_into("<hhHBB", data, dest_warp_off,
                     destination_x, destination_y, 0, 9, 0)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    output_digest = sha1(data)
    manifest = {
        "base": str(source),
        "base_sha1": digest,
        "output": str(output),
        "output_sha1": output_digest,
        "source_map": {"group": 0, "number": 9, "name": "Littleroot Town / 新手村"},
        "destination_map": {"group": NEW_GROUP, "number": NEW_MAP, "name": "Alpha8v2 Empty Field / 新空地"},
        "warps": {
            "source": {"xy": [source_x, source_y], "destination": [NEW_GROUP, NEW_MAP, 0]},
            "destination": {"xy": [destination_x, destination_y], "destination": [0, 9, 0]},
        },
        "layout": {"width": 20, "height": 20, "ground_block": GROUND_BLOCK, "door_block": DOOR_BLOCK},
        "offsets": {
            "source_event_header": f"0x{source_header_off:07X}",
            "source_warps": f"0x{source_warps_off:07X}",
            "map_header": f"0x{map_header_off:07X}",
            "layout": f"0x{layout_off:07X}",
            "blockdata": f"0x{blockdata_off:07X}",
            "destination_events": f"0x{dest_events_off:07X}",
            "destination_warp": f"0x{dest_warp_off:07X}",
            "source_layout_copy": f"0x{source_layout_copy_off:07X}",
            "source_blockdata_copy": f"0x{source_blockdata_copy_off:07X}",
        },
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-x", type=int, default=12)
    parser.add_argument("--source-y", type=int, default=10)
    parser.add_argument("--destination-x", type=int, default=10)
    parser.add_argument("--destination-y", type=int, default=10)
    args = parser.parse_args()
    if not args.input.is_file():
        print(f"Input ROM not found: {args.input}")
        return 2
    try:
        manifest = build_patch(args.input, args.output, args.source_x, args.source_y,
                               args.destination_x, args.destination_y)
    except ValueError as exc:
        print(f"Patch failed: {exc}")
        return 3
    print(f"Wrote: {manifest['output']}")
    print(f"SHA-1: {manifest['output_sha1']}")
    print("Warp: Littleroot Town (0,9) -> Empty Field (27,0), with return warp")
    print(f"Manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
