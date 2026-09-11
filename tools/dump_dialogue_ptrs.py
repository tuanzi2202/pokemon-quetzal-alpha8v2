#!/usr/bin/env python3
"""Dump Gen3 strings by following ROM pointers into text banks (dialogue-safe)."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen3_charmap import decode_bytes, is_likely_text  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
DUMP_DIR = ROOT / "dump"

# ROM file-offset ranges that hold dialogue / NPC text
TEXT_BANKS = [
    (0x270000, 0x360000),
    (0x1A0000, 0x220000),
    (0x4C0000, 0x4E0000),
]


def in_banks(off: int) -> bool:
    return any(a <= off < b for a, b in TEXT_BANKS)


def collect_ptr_targets(rom: bytes) -> dict[int, list[int]]:
    """Map text offset -> list of aligned pointer sites."""
    targets: dict[int, list[int]] = {}
    n = len(rom) - 3
    for i in range(0, n, 4):
        v = struct.unpack_from("<I", rom, i)[0]
        if not (0x08000000 <= v <= 0x09FFFFFF):
            continue
        off = v - 0x08000000 if v < 0x09000000 else 0x01000000 + (v & 0x00FFFFFF)
        if off >= len(rom) or not in_banks(off):
            continue
        if rom[off] == 0xFF:
            continue
        targets.setdefault(off, []).append(i)
    return targets


def main() -> int:
    rom = GOLDEN.read_bytes()
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    print("scanning pointers…", flush=True)
    targets = collect_ptr_targets(rom)
    print(f"ptr targets in text banks: {len(targets)}", flush=True)

    rows: list[dict] = []
    skipped = 0
    for off in sorted(targets):
        eos = rom.find(b"\xff", off, min(len(rom), off + 500))
        if eos < 0:
            skipped += 1
            continue
        chunk = rom[off : eos + 1]
        if not is_likely_text(chunk, min_alpha=2):
            skipped += 1
            continue
        text = decode_bytes(chunk)
        if text.count("{") > 12:
            skipped += 1
            continue
        rows.append(
            {
                "id": f"{off:08X}",
                "offset": off,
                "length": len(chunk),
                "en": text,
                "hex": chunk.hex(),
                "ptr_count": len(targets[off]),
            }
        )

    out = DUMP_DIR / "dialogue_ptrs.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} strings -> {out} skipped={skipped}", flush=True)

    # merge into all_en.jsonl (prefer pointer rows; keep existing unique offsets)
    master = DUMP_DIR / "all_en.jsonl"
    by_off: dict[int, dict] = {}
    if master.exists():
        for line in master.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            by_off[int(r["offset"])] = r
    for r in rows:
        by_off[int(r["offset"])] = r  # pointer-backed wins
    merged = [by_off[k] for k in sorted(by_off)]
    with master.open("w", encoding="utf-8") as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"all_en.jsonl now {len(merged)} rows", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
