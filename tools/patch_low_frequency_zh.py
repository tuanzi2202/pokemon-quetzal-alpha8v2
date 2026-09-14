#!/usr/bin/env python3
"""Patch verified unaligned script pointers found by dynamic acceptance."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text  # noqa: E402

ROM = ROOT / "work" / "cn_build.gba"
GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
DATA = ROOT / "locale" / "zh_CN" / "low_frequency_unaligned_zh.jsonl"
CURSOR = ROOT / "work" / "free_cursor.txt"
FREE_START = 0x01D9B5A8 + 0x30000
FREE_END = 0x01D9B5A8 + 0x264A58


def load_entries() -> list[dict[str, object]]:
    return [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]


def pointer_value(offset: int) -> bytes:
    return struct.pack("<I", 0x08000000 + offset)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    data = bytearray(ROM.read_bytes())
    golden = GOLDEN.read_bytes()
    entries = load_entries()
    failures: list[str] = []
    patched = 0
    patched_in_place = 0
    cursor = int(CURSOR.read_text().strip(), 0) if CURSOR.exists() else FREE_START

    for row in entries:
        offset = int(row["offset"])
        en = str(row["en"])
        zh = str(row["zh"])
        sites = [int(site) for site in row["pointer_sites"]]
        in_place = bool(row.get("in_place"))
        source = encode_text(en)
        encoded = encode_text(zh)
        expected_pointer = pointer_value(offset)

        if golden[offset:offset + len(source)] != source:
            failures.append(f"source drift at {offset:#x}")
            continue
        for site in sites:
            if golden[site:site + 4] != expected_pointer:
                failures.append(f"pointer source drift at {site:#x} -> {offset:#x}")

        if in_place:
            if len(encoded) > len(source):
                failures.append(f"in-place overflow at {offset:#x}: {len(encoded)} > {len(source)}")
                continue
            if args.check:
                if data[offset:offset + len(encoded)] != encoded:
                    failures.append(f"in-place translation mismatch at {offset:#x}")
            elif data[offset:offset + len(source)] != source:
                failures.append(f"build source drift for in-place entry {offset:#x}")
            else:
                data[offset:offset + len(source)] = encoded + b"\xFF" * (len(source) - len(encoded))
                patched_in_place += 1
            continue

        if args.check:
            for site in sites:
                value = struct.unpack_from("<I", data, site)[0]
                target = value - 0x08000000
                if not (FREE_START <= target < FREE_END):
                    failures.append(f"pointer not relocated at {site:#x}: {value:#x}")
                elif data[target:target + len(encoded)] != encoded:
                    failures.append(f"translation mismatch at {site:#x}: {target:#x}")
            continue

        if any(data[site:site + 4] != expected_pointer for site in sites):
            failures.append(f"build pointer drift for {offset:#x}")
            continue
        if cursor + len(encoded) > FREE_END:
            failures.append(f"free space exhausted at {offset:#x}")
            continue
        target = cursor
        data[target:target + len(encoded)] = encoded
        cursor += (len(encoded) + 3) & ~3
        new_pointer = pointer_value(target)
        for site in sites:
            data[site:site + 4] = new_pointer
            patched += 1

    if not args.check:
        ROM.write_bytes(data)
        CURSOR.write_text(hex(cursor), encoding="utf-8")
    print(json.dumps({"entries": len(entries), "pointer_sites": patched if not args.check else sum(len(row["pointer_sites"]) for row in entries), "in_place": patched_in_place if not args.check else sum(bool(row.get("in_place")) for row in entries), "failures": len(failures), "check": args.check}, ensure_ascii=False))
    if failures:
        print("\n".join(failures))
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
