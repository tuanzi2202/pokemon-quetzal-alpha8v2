#!/usr/bin/env python3
"""Guard: allow font/hooks/free-space/text slots; flag unexpected code edits."""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FREE0 = 0x01D9B5A8
FREE1 = FREE0 + 0x264A58
# Executable Chinese handler (low 16MB zero-fill)
CODE0 = 0x00EB9878
CODE1 = CODE0 + 0x5000


def allowed_ranges() -> list[tuple[int, int]]:
    rs = [
        (FREE0, FREE1),
        (CODE0, CODE1),
        (0x596C, 0x596C + 0x10),  # real CharRead divert (FontNormal→RenderText@588C)
        (0x9F0F0, 0x9F180),  # GetMoveName language base ptrs forced→EN
        (0x21CC68, 0x21CC68 + 0x10),  # dead relocated copy (optional leftover)
        (0x21CFD4, 0x21CFD4 + 0x10),  # legacy GlyphDispatch (unused)
        (0x5EE2, 0x5F20),
        (0x60F8, 0x6120),
        (0x612E, 0x6132),
        (0x270000, 0x360000),
        (0x3C4000, 0x3E0000),
        (0x4065EC, 0x4065EC + 66 * 13),  # trainer class name slots
        (0x40E000, 0x42A000),  # Title-Case species/moves/abilities name pools
        (0x42C000, 0x430000),  # battle/status HP & related short UI
        (0x4C0000, 0x4E0000),
        (0x0F80000, 0x1100000),
        (0x100000, 0x300000),
        (0x2C000, 0x30000),  # title-screen string pointer tables
    ]
    loc = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"
    if loc.exists():
        for line in loc.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            o = int(row["offset"])
            ln = int(row.get("length") or 8)
            rs.append((o, o + max(ln, 8)))
    from chs_encode import encode_text
    from force_mode_zh import INPLACE_MODE_WIZARD
    from force_randomizer_zh import INPLACE_FORCED
    for off, en, _zh in (*INPLACE_MODE_WIZARD, *INPLACE_FORCED):
        rs.append((off, off + len(encode_text(en))))
    from patch_low_frequency_zh import load_entries
    for row in load_entries():
        if row.get("in_place"):
            rs.append((int(row["offset"]), int(row["offset"]) + len(encode_text(str(row["en"])))))
        for site in row["pointer_sites"]:
            rs.append((int(site), int(site) + 4))
    return rs


def in_range(off: int, ranges: list[tuple[int, int]]) -> bool:
    for a, b in ranges:
        if a <= off < b:
            return True
    return False


def is_ptr_to_free(build: bytes, off: int) -> bool:
    if off + 4 > len(build) or (off % 4) != 0:
        return False
    v = struct.unpack_from("<I", build, off)[0]
    if not (0x08000000 <= v < 0x0A000000):
        return False
    rom_off = v - 0x08000000
    return (FREE0 <= rom_off < FREE1) or (CODE0 <= rom_off < CODE1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", default=str(ROOT / "golden" / "en_0.8.4.gba"))
    ap.add_argument("--build", default=str(ROOT / "work" / "cn_build.gba"))
    args = ap.parse_args()
    golden = Path(args.golden).read_bytes()
    build = Path(args.build).read_bytes()
    if len(golden) != len(build):
        print("FAIL size", len(golden), len(build))
        return 1
    ranges = allowed_ranges()
    bad = []
    i = 0
    n = len(golden)
    while i < n:
        if golden[i] == build[i]:
            i += 1
            continue
        if in_range(i, ranges) or is_ptr_to_free(build, i & ~3):
            i += 1
            continue
        bad.append(i)
        if len(bad) >= 25:
            break
        i += 1
    diffs = sum(1 for a, b in zip(golden, build) if a != b)
    if bad:
        print("FAIL unexpected diffs:", [hex(x) for x in bad[:20]], "total_diffs", diffs)
        return 2
    print(f"OK guarded diffs={diffs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
