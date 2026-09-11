#!/usr/bin/env python3
"""Apply zh_CN JSONL into cn_build.gba — reloc-only, never inplace.

Inplace overwrites in packed UI tables (gender/options) shorten strings with
FF/00 padding and wipe adjacent labels / FC arrow prefixes → blank or missing
menu rows. Only rewrite via pointer retarget into free space.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chs_encode import encode_text_safe  # noqa: E402

FREE_START = 0x01D9B5A8 + 0x30000
FREE_END = 0x01D9B5A8 + 0x264A58

# Do not retarget "pointers" inside these ranges — false positives trash UI gfx
# (0xFC0000-0xFD0000: wall-clock + item text tables; ~590 bad retargets → pixel trash).
PTR_SEARCH_BLACKLIST = [
    (0x0FC0000, 0x0FD0000),
]


def find_ptrs(rom: bytes | bytearray, offset: int) -> list[int]:
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
            out.append(i)
            idx = i + 1
            if len(out) > 50:
                break
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("locale_jsonl")
    ap.add_argument("--rom", default=str(ROOT / "work" / "cn_build.gba"))
    ap.add_argument("--cursor", default=str(ROOT / "work" / "free_cursor.txt"))
    args = ap.parse_args()

    rom_path = Path(args.rom)
    data = bytearray(rom_path.read_bytes())
    # Search pointers on a frozen view (English text offsets). Rebuilding
    # bytes(data) every row copies 32MB and made full-locale apply hang.
    haystack = bytes(data)
    cursor_path = Path(args.cursor)
    free_at = int(cursor_path.read_text().strip(), 0) if cursor_path.exists() else FREE_START

    n_reloc = 0
    n_skip_same = 0
    n_skip_fit = 0
    n_skip_ctrl = 0
    n_missing = 0
    n_err = 0
    missing_chars: set[str] = set()
    rows = [json.loads(line) for line in Path(args.locale_jsonl).read_text(encoding="utf-8").splitlines() if line.strip()]
    total = len(rows)

    for i, row in enumerate(rows):
        off = int(row["offset"])
        zh = row.get("zh") or ""
        en = row.get("en") or ""
        if not zh or zh == en:
            n_skip_same += 1
            continue
        if en.startswith("{FC") or en.count("{FC") >= 2:
            n_skip_ctrl += 1
            continue
        try:
            encoded, missing = encode_text_safe(zh)
        except Exception as e:
            print("encode fail", row.get("id"), e)
            n_err += 1
            continue
        if missing:
            n_missing += 1
            missing_chars.update(missing)

        ptrs = [p for p in find_ptrs(haystack, off) if p % 4 == 0]
        ptrs = [
            p
            for p in ptrs
            if not any(a <= p < b for a, b in PTR_SEARCH_BLACKLIST)
        ]
        if not ptrs:
            n_skip_fit += 1
            continue
        need = len(encoded)
        if free_at + need > FREE_END:
            print("FREE SPACE EXHAUSTED at", hex(off))
            n_err += 1
            break
        new_off = free_at
        data[new_off : new_off + need] = encoded
        free_at += (need + 3) & ~3
        new_ptr = struct.pack("<I", 0x08000000 + new_off)
        for p in ptrs:
            # Aligned only — rejects Thumb false-positives (e.g. unaligned 0x17ce7).
            # Title menu ptrs live at 0x2Cxxx and MUST be updated.
            data[p : p + 4] = new_ptr
        n_reloc += 1
        if (i + 1) % 500 == 0:
            print(f"  apply {i + 1}/{total} reloc={n_reloc}", flush=True)

    rom_path.write_bytes(data)
    cursor_path.write_text(hex(free_at), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok_exists": 0,
                "ok_reloc": n_reloc,
                "skip_no_fit": n_skip_fit,
                "skip_same": n_skip_same,
                "skip_ctrl": n_skip_ctrl,
                "missing_glyphs": n_missing,
                "errors": n_err,
            },
            ensure_ascii=False,
        )
    )
    if missing_chars:
        sample = "".join(ch for ch in sorted(missing_chars) if ch.isprintable() and ord(ch) < 0x10000)[:80]
        try:
            print("missing sample:", sample)
        except UnicodeEncodeError:
            print("missing sample:", sample.encode("unicode_escape").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
