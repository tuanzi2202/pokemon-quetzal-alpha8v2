#!/usr/bin/env python3
"""Force early-game dialogue into 0x08-bank free space (avoid 0x09 script issues)."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chs_encode import encode_text_safe  # noqa: E402

ROM = ROOT / "work" / "cn_build.gba"
GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"
# First-16MB free holes (DISCOVER)
FREE_HOLES = [
    (0x0179FD48, 0x0179FD48 + 0x11624),
    (0x00EB5A20, 0x00EB5A20 + 0x3E3C),
    (0x00ED9A1C, 0x00ED9A1C + 0x3D00),
    (0x01030771, 0x01030771 + 0xD477),
]


def find_ptrs(rom: bytes, offset: int) -> list[int]:
    out: list[int] = []
    for ptr in (0x08000000 + offset,):
        needle = struct.pack("<I", ptr)
        idx = 0
        while True:
            i = rom.find(needle, idx)
            if i < 0:
                break
            if i % 4 == 0:
                out.append(i)
            idx = i + 1
            if len(out) > 20:
                break
    return out


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(ROM.read_bytes())
    by_off: dict[int, str] = {}
    for line in LOCALE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        zh = row.get("zh") or ""
        en = row.get("en") or ""
        if zh and zh != en and any("\u4e00" <= c <= "\u9fff" for c in zh):
            # strip broken MT token leftovers
            zh = zh.replace("[[10]]", "{WAIT_CLEAR}").replace("[[0]]", "{WAIT_CLEAR}")
            by_off[int(row["offset"])] = zh

    # Prefer pointer-backed dialogue list
    targets: list[int] = []
    dlg = ROOT / "dump" / "dialogue_ptrs.jsonl"
    if dlg.exists():
        for line in dlg.read_text(encoding="utf-8").splitlines():
            targets.append(int(json.loads(line)["offset"]))
    else:
        targets = sorted(by_off)

    hole_i = 0
    cursor = FREE_HOLES[0][0]
    stats = {"patched": 0, "no_zh": 0, "no_ptr": 0, "no_space": 0, "fail": 0}

    for off in targets:
        zh = by_off.get(off)
        if not zh:
            stats["no_zh"] += 1
            continue
        ptrs = find_ptrs(golden, off)
        if not ptrs:
            stats["no_ptr"] += 1
            continue
        enc, missing = encode_text_safe(zh)
        if missing and len(missing) > 8:
            stats["fail"] += 1
            continue
        # place in 0x08 hole
        while hole_i < len(FREE_HOLES) and cursor + len(enc) > FREE_HOLES[hole_i][1]:
            hole_i += 1
            if hole_i < len(FREE_HOLES):
                cursor = FREE_HOLES[hole_i][0]
        if hole_i >= len(FREE_HOLES):
            stats["no_space"] += 1
            break
        new_off = cursor
        data[new_off : new_off + len(enc)] = enc
        cursor += (len(enc) + 3) & ~3
        new_ptr = struct.pack("<I", 0x08000000 + new_off)  # stays in 0x08 bank
        for p in ptrs:
            data[p : p + 4] = new_ptr
        stats["patched"] += 1
        if stats["patched"] <= 8:
            print(f"OK {off:08X} -> {new_off:08X} ptrs={len(ptrs)}", flush=True)

    ROM.write_bytes(data)
    print(json.dumps(stats, ensure_ascii=False))
    print(f"cursor hole={hole_i} at {cursor:#x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
