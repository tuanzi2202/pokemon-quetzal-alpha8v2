#!/usr/bin/env python3
"""Add one talkable NPC to Littleroot Town in the Alpha8v2 Quetzal ROM.

This is a small, reversible binary patch for the supplied Alpha8v2 build. It
copies the existing object-event table to free ROM space, appends one normal
NPC, adds a short script and message, then repoints the Littleroot Town event
header. The input is never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "work" / "alpha8v2_hanzh_work.gba"
DEFAULT_OUTPUT = ROOT / "out" / "alpha8v2_npc.gba"
MANIFEST = ROOT / "work" / "alpha8v2_npc_manifest.json"

EXPECTED_SHA1 = "28dfc29f4c809078dd9dc1e98e3aba5a403fa74b"
ROM_BASE = 0x08000000
MAP_GROUPS = 0x0061A5A8
MAP_GROUP = 0
MAP_NUM = 9  # Littleroot Town in the Emerald towns/routes group.
OBJECT_SIZE = 24
EVENT_HEADER_SIZE = 16

# The supplied ROM has a large unused 0xFF tail beginning here. Keep this
# offset explicit so the output remains reproducible and easy to inspect.
FREE_OFFSET = 0x01FEF400


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


def encode_message(text: str) -> bytes:
    # Reuse the project's Chinese Gen III character map. The import is kept
    # local so this script still gives a clear error when run standalone.
    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    from chs_encode import encode_text  # type: ignore

    return encode_text(text)


def find_free(data: bytes, start: int, size: int) -> int:
    end = start + size
    if end > len(data) or any(value != 0xFF for value in data[start:end]):
        raise ValueError(f"reserved free-space range is not empty: 0x{start:07X}-0x{end:07X}")
    return start


def locate_events(data: bytes) -> tuple[int, int, int, int, int]:
    """Return map header, events, object table, object count and object size."""
    group_ptr = u32(data, MAP_GROUPS + MAP_GROUP * 4)
    group_off = rom_offset(group_ptr)
    if group_off is None:
        raise ValueError("map group table pointer is invalid")
    map_ptr = u32(data, group_off + MAP_NUM * 4)
    map_header = rom_offset(map_ptr)
    if map_header is None:
        raise ValueError("Littleroot Town map header pointer is invalid")
    events_ptr = u32(data, map_header + 4)
    events_off = rom_offset(events_ptr)
    if events_off is None:
        raise ValueError("Littleroot Town events pointer is invalid")
    count = data[events_off]
    object_ptr = u32(data, events_off + 4)
    object_off = rom_offset(object_ptr)
    if object_off is None or count == 0 or count > 64:
        raise ValueError("Littleroot Town object-event table is invalid")
    if object_off + count * OBJECT_SIZE > len(data):
        raise ValueError("Littleroot Town object-event table exceeds ROM")
    return map_header, events_off, object_off, count, OBJECT_SIZE


def build_patch(source: Path, output: Path, message: str, x: int, y: int, graphics: int) -> dict:
    original = source.read_bytes()
    digest = sha1(original)
    if digest != EXPECTED_SHA1:
        raise ValueError(
            f"unexpected Alpha8v2 input SHA-1 {digest}; expected {EXPECTED_SHA1}. "
            "Use the supplied Alpha8v2 Han version as the base."
        )
    if len(original) != 0x02000000:
        raise ValueError("input must be an unheadered 32 MiB GBA ROM")
    if original[0xA0:0xAC].rstrip(b"\0 ") != b"PKM QUETZAL":
        raise ValueError("input does not have the PKM QUETZAL header")

    data = bytearray(original)
    map_header, events_off, object_off, object_count, object_size = locate_events(data)
    if object_count != 13:
        raise ValueError(f"expected 13 existing Littleroot Town objects, found {object_count}")
    if any(data[object_off + i * object_size] == 14 for i in range(object_count)):
        raise ValueError("local ID 14 is already present")
    if not (0 <= x <= 19 and 0 <= y <= 19):
        raise ValueError("NPC coordinates must be inside the 20x20 Littleroot Town map")
    if not (0 <= graphics <= 0xFF):
        raise ValueError("graphics ID must fit in one byte")

    text_bytes = encode_message(message)
    # lock; faceplayer; loadword 0, text; callstd MSGBOX_NPC; release; end
    script_size = 12  # lock, faceplayer, loadword, callstd, release, end
    object_table_size = (object_count + 1) * object_size
    table_off = find_free(data, FREE_OFFSET, object_table_size + script_size + len(text_bytes) + 8)
    script_off = table_off + object_table_size
    text_off = script_off + script_size

    old_objects = bytes(data[object_off : object_off + object_count * object_size])
    data[table_off : table_off + len(old_objects)] = old_objects

    # Start from an existing ordinary NPC record so Alpha8v2's object-event
    # extensions are preserved. Object 3 is a visible, talkable NPC template.
    npc = bytearray(old_objects[3 * object_size : 4 * object_size])
    npc[0] = 14  # local ID; object IDs are 1-based within a map
    npc[2] = graphics
    struct.pack_into("<hh", npc, 4, x, y)
    npc[8] = 3  # elevation
    npc[9] = 8  # MOVEMENT_TYPE_FACE_DOWN
    struct.pack_into("<H", npc, 10, 0)  # no movement range
    struct.pack_into("<H", npc, 12, 0)  # ordinary NPC, no trainer battle
    struct.pack_into("<H", npc, 14, 0)
    put_u32(npc, 16, pointer(script_off))
    struct.pack_into("<H", npc, 20, 0)  # visible from the start
    data[table_off + object_count * object_size : table_off + (object_count + 1) * object_size] = npc

    script = bytearray([0x6A, 0x5A, 0x0F, 0x00])
    script += struct.pack("<I", pointer(text_off))
    script += bytes([0x09, 0x02, 0x6C, 0x02])
    if len(script) != script_size:
        raise AssertionError(len(script))
    data[script_off : script_off + len(script)] = script
    data[text_off : text_off + len(text_bytes)] = text_bytes

    # Repoint the event header to the copied table and increase its count.
    data[events_off] = object_count + 1
    put_u32(data, events_off + 4, pointer(table_off))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    output_digest = sha1(data)
    manifest = {
        "base": str(source),
        "base_sha1": digest,
        "output": str(output),
        "output_sha1": output_digest,
        "map": {"group": MAP_GROUP, "number": MAP_NUM, "name": "Littleroot Town / 新手村"},
        "npc": {
            "local_id": 14,
            "graphics_id": graphics,
            "coordinates": [x, y],
            "movement_type": "FACE_DOWN",
            "dialogue": message,
            "object_table_offset": f"0x{table_off:07X}",
            "script_offset": f"0x{script_off:07X}",
            "text_offset": f"0x{text_off:07X}",
        },
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--message", default="你好！我是新NPC。{WAIT_CLEAR}欢迎来到新手村！")
    parser.add_argument("--x", type=int, default=9)
    parser.add_argument("--y", type=int, default=10)
    parser.add_argument("--graphics", type=int, default=26, help="Alpha8v2 overworld graphics ID (26 = Cook)")
    args = parser.parse_args()
    if not args.input.is_file():
        print(f"Input ROM not found: {args.input}")
        return 2
    try:
        manifest = build_patch(args.input, args.output, args.message, args.x, args.y, args.graphics)
    except (ValueError, KeyError) as exc:
        print(f"Patch failed: {exc}")
        return 3
    print(f"Wrote: {manifest['output']}")
    print(f"SHA-1: {manifest['output_sha1']}")
    print(f"NPC: map group {MAP_GROUP}, map {MAP_NUM}, local ID 14, xy=({args.x},{args.y})")
    print(f"Manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
