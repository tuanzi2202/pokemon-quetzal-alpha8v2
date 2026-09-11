#!/usr/bin/env python3
"""Force-reloc official character/region names (52poke), incl. FC-prefixed menus."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chs_encode import encode_text_safe  # noqa: E402
from official_names_zh import OFFICIAL_NAMES  # noqa: E402

ROM = ROOT / "work" / "cn_build.gba"
GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"
FREE_START = 0x01D9B5A8 + 0x30000
FREE_END = 0x01D9B5A8 + 0x264A58
FC_PREFIX = bytes.fromhex("fc0106fc0307")


def find_ptrs(rom: bytes, offset: int) -> list[int]:
    out: list[int] = []
    candidates = {0x08000000 + offset}
    if offset >= 0x01000000:
        candidates.add(0x09000000 + (offset & 0x00FFFFFF))
    for ptr in candidates:
        if not (0x08000000 <= ptr <= 0x09FFFFFF):
            continue
        needle = struct.pack("<I", ptr)
        idx = 0
        while True:
            i = rom.find(needle, idx)
            if i < 0:
                break
            if i % 4 == 0:
                out.append(i)
            idx = i + 1
            if len(out) > 40:
                break
    return sorted(set(out))


def en_to_bytes(en: str) -> bytes | None:
    """Encode Latin UI name the same way dump does (Pokemon charset approx)."""
    # Prefer hex from locale row when available; fallback simple map
    m = {**{chr(65 + i): 0xBB + i for i in range(26)}, " ": 0x00, ".": 0xAD, "-": 0xAE, "'": 0xB8}
    out = bytearray()
    for ch in en:
        if ch not in m:
            return None
        out.append(m[ch])
    out.append(0xFF)
    return bytes(out)


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(ROM.read_bytes())
    cursor_path = ROOT / "work" / "free_cursor.txt"
    free_at = int(cursor_path.read_text().strip(), 0) if cursor_path.exists() else FREE_START
    stats = {"patched": 0, "no_ptr": 0, "fail": 0}

    # Collect (offset_or_fc_offset, zh, with_fc)
    jobs: list[tuple[int, str, bool]] = []
    seen_off: set[int] = set()

    for line in LOCALE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        en = row.get("en") or ""
        zh = OFFICIAL_NAMES.get(en)
        if not zh:
            continue
        off = int(row["offset"])
        hx = row.get("hex")
        if hx:
            en_bytes = bytes.fromhex(hx)
        else:
            en_bytes = en_to_bytes(en)
            if not en_bytes:
                continue

        # Plain pointer to Latin start
        if off not in seen_off:
            jobs.append((off, zh, False))
            seen_off.add(off)

        # FC-prefixed copy used by character/region grids
        needle = FC_PREFIX + en_bytes
        idx = 0
        while True:
            i = golden.find(needle, idx)
            if i < 0:
                break
            if i not in seen_off:
                jobs.append((i, zh, True))
                seen_off.add(i)
            idx = i + 1
            if idx > 0x1200000:
                break

    for off, zh, with_fc in jobs:
        enc, missing = encode_text_safe(zh)
        if missing:
            print("missing", zh, missing)
            stats["fail"] += 1
            continue
        if with_fc:
            enc = FC_PREFIX + enc
        ptrs = [
            p
            for p in find_ptrs(golden, off)
            if 0x08000000 <= struct.unpack_from("<I", data, p)[0] <= 0x09FFFFFF
        ]
        if not ptrs:
            stats["no_ptr"] += 1
            continue
        if free_at + len(enc) > FREE_END:
            print("free exhausted")
            break
        new_off = free_at
        data[new_off : new_off + len(enc)] = enc
        free_at += (len(enc) + 3) & ~3
        new_ptr = struct.pack("<I", 0x08000000 + new_off)
        for p in ptrs:
            data[p : p + 4] = new_ptr
        stats["patched"] += 1
        if stats["patched"] <= 50:
            print(f"OK {off:08X} fc={with_fc} {zh} ptrs={len(ptrs)}")

    ROM.write_bytes(data)
    cursor_path.write_text(hex(free_at), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
