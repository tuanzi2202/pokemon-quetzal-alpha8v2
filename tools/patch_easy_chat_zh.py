#!/usr/bin/env python3
"""Patch all fixed-slot Easy Chat words and verify the resulting ROM."""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text, encode_text_safe  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
LOCALE = ROOT / "locale" / "zh_CN" / "easy_chat_zh.jsonl"
DEFAULT_ROM = ROOT / "work" / "cn_build.gba"
CURSOR = ROOT / "work" / "free_cursor.txt"
FREE_START = 0x01D9B5A8 + 0x30000
FREE_END = 0x02000000
PTR_REGION_START = 0x00FC0000
PTR_REGION_END = 0x00FD0000


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def index_pointer_sites(golden: bytes, offsets: set[int]) -> dict[int, list[int]]:
    sites = {offset: [] for offset in offsets}
    for site in range(PTR_REGION_START, PTR_REGION_END - 3, 4):
        value = struct.unpack_from("<I", golden, site)[0]
        offset = value - 0x08000000
        if offset in sites:
            sites[offset].append(site)
    return sites


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM)
    parser.add_argument("--locale", type=Path, default=LOCALE)
    parser.add_argument("--check", action="store_true", help="validate locale and ROM without writing")
    args = parser.parse_args()

    golden = GOLDEN.read_bytes()
    data = bytearray(args.rom.read_bytes())
    rows = read_jsonl(args.locale)
    failures: list[str] = []
    seen: set[int] = set()
    mismatches = 0
    groups: set[str] = set()
    offsets = {int(row["offset"]) for row in rows}
    pointer_sites = index_pointer_sites(golden, offsets)
    free_at = int(CURSOR.read_text(encoding="utf-8").strip(), 0) if CURSOR.exists() else FREE_START
    for row in rows:
        offset = int(row["offset"])
        slot = int(row["slot"])
        en = str(row["en"])
        zh = str(row["zh"])
        groups.add(str(row["group"]))
        if offset in seen:
            failures.append(f"duplicate offset {offset:#x}")
            continue
        seen.add(offset)
        expected = encode_text(en)
        if len(expected) != slot or golden[offset:offset + slot] != expected:
            failures.append(f"stale source at {offset:#x}: {en!r}")
            continue
        encoded, missing = encode_text_safe(zh)
        if not zh or (zh == en and re.search(r"[A-Za-z]", zh)):
            failures.append(f"untranslated at {offset:#x}: {en!r}")
            continue
        if missing:
            failures.append(f"missing glyphs at {offset:#x}: {sorted(set(missing))}")
            continue
        sites = pointer_sites.get(offset, [])
        if not sites:
            failures.append(f"no Easy Chat pointer at {offset:#x}: {en!r}")
            continue
        if args.check:
            for site in sites:
                target = struct.unpack_from("<I", data, site)[0] - 0x08000000
                if target < 0 or data[target:target + len(encoded)] != encoded:
                    mismatches += 1
                    break
            continue
        if free_at + len(encoded) > FREE_END:
            failures.append(f"free space exhausted at {offset:#x}")
            break
        target = free_at
        data[target:target + len(encoded)] = encoded
        free_at += (len(encoded) + 3) & ~3
        pointer = struct.pack("<I", 0x08000000 + target)
        for site in sites:
            data[site:site + 4] = pointer

    if len(rows) != 1008:
        failures.append(f"expected 1008 Easy Chat words, got {len(rows)}")
    if len(groups) != 18:
        failures.append(f"expected 18 Easy Chat groups, got {len(groups)}")
    summary = {
        "rows": len(rows),
        "groups": len(groups),
        "pointer_mismatches": mismatches,
        "failures": len(failures),
        "check": args.check,
    }
    print(json.dumps(summary, ensure_ascii=False))
    if failures:
        print("\n".join(failures[:50]))
        return 2
    if args.check and mismatches:
        return 2
    if not args.check:
        args.rom.write_bytes(data)
        CURSOR.write_text(hex(free_at), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
