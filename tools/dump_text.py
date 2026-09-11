#!/usr/bin/env python3
"""Dump Gen3 strings from Quetzal 0.8.4 into JSONL banks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen3_charmap import decode_bytes, is_likely_text  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
DUMP_DIR = ROOT / "dump"

# High-value ranges (menus live near 0x101xxxx; dialogue denser mid-ROM)
RANGES = [
    ("menu_title", 0x101B000, 0x1028000),
    ("menu_extra", 0x1000000, 0x101B000),
    ("ui_mid", 0x0FC0000, 0x1000000),
    ("strings_2a", 0x2A0000, 0x360000),
    ("strings_low", 0x270000, 0x2A0000),
    ("mp_area", 0x4C0000, 0x4D0000),
    ("link_ui", 0x3C4000, 0x3D0000),
]


def dump_range(rom: bytes, start: int, end: int) -> list[dict]:
    hits = []
    i = max(0, start)
    end = min(len(rom), end)
    while i < end - 4:
        eos = rom.find(b"\xff", i, min(end, i + 220))
        if eos is None or eos < 0 or eos == i:
            i += 1
            continue
        chunk = rom[i : eos + 1]
        if is_likely_text(chunk, min_alpha=3):
            text = decode_bytes(chunk)
            # filter garbage
            if text.count("{") > 6:
                i = eos + 1
                continue
            hits.append(
                {
                    "id": f"{i:08X}",
                    "offset": i,
                    "length": len(chunk),
                    "en": text,
                    "hex": chunk.hex(),
                }
            )
            i = eos + 1
            continue
        i += 1
    return hits


def main() -> int:
    rom = GOLDEN.read_bytes()
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = []
    seen = set()
    for name, start, end in RANGES:
        rows = dump_range(rom, start, end)
        path = DUMP_DIR / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in rows:
                if r["offset"] in seen:
                    continue
                seen.add(r["offset"])
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                all_rows.append(r)
        print(f"{name}: {len(rows)} -> {path}")
    # master index
    master = DUMP_DIR / "all_en.jsonl"
    all_rows.sort(key=lambda r: r["offset"])
    with master.open("w", encoding="utf-8") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"master unique: {len(all_rows)} -> {master}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
