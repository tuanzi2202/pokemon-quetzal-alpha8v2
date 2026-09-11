#!/usr/bin/env python3
"""Force-reloc high-value UI labels by English payload match (all ptr-backed copies)."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chs_encode import encode_text_safe  # noqa: E402

ROM = ROOT / "work" / "cn_build.gba"
FREE_START = 0x01D9B5A8 + 0x30000
FREE_END = 0x01D9B5A8 + 0x264A58

# Exact EN hex (incl. FF EOS) -> zh, optional raw prefix prepended to encoded zh
FORCED_HEX: list[tuple[str, str, str]] = [
    # Title
    ("c8bfd100c1bbc7bfff", "新游戏", ""),
    ("bdc9c8cec3c8cfbfff", "继续游戏", ""),
    ("c9cacec3c9c8ff", "选项", ""),
    ("c7d3cdcebfccd300c1c3c0ceff", "神秘礼物", ""),
    ("c7d3cdcebfccd300bfd0bfc8cecdff", "神秘事件", ""),
    # Start menu
    ("cac9c51bbebfd2ff", "图鉴", ""),
    ("cac9c51bc7c9c8ff", "宝可梦", ""),
    ("cac9c51bc8bbd0ff", "导航", ""),
    ("bcbbc1ff", "背包", ""),
    ("cdbbd0bfff", "保存", ""),
    ("bfd2c3ceff", "退出", ""),
    # Gender (plain)
    ("bcc9d3ff", "男孩", ""),
    ("c1c3ccc6ff", "女孩", ""),
    # Gender with FC arrow/color (pointer aims at FC)
    ("fc0106fc0307bcc9d3ff", "男孩", "fc0106fc0307"),
    ("fc0106fc0307c1c3ccc6ff", "女孩", "fc0106fc0307"),
    # Difficulty / mode
    ("d0bfccd300bfbbcdd3ff", "非常简单", ""),
    ("bfbbcdd3ff", "简单", ""),
    ("c8c9ccc7bbc6ff", "普通", ""),
    ("c2bbccbeff", "困难", ""),
    ("d0bfccd300c2bbccbeff", "非常困难", ""),
    ("bddce3e3e7d900dbd5e1d900e1e3d8d9adff", "选择游戏模式。", ""),
    ("bddce3e3e7d900dbd5e1d900d8dddadaddd7e9e0e8edadff", "选择游戏难度。", ""),
    ("bdc2bfbbcecdff", "作弊", ""),
    ("c8c9ccc7bbc600c7c9bebfff", "普通模式", ""),
    ("bdc9c9ca00c7c9bebfff", "协作模式", ""),
    ("bfaec7c9bebfff", "E模式", ""),
    ("c1aec7c9bebfff", "G模式", ""),
    ("d3bfcdff", "是", ""),
]

# Title strings that fit in original slots — also rewrite inplace so MyBoy
# ROM fingerprint (NEWGAME@101B9C8) changes and hot-swap actually recopies.
TITLE_INPLACE: list[tuple[int, int, str]] = [
    (0x101B9C8, 9, "新游戏"),
    (0x101B9D1, 9, "继续游戏"),
    (0x101B9DA, 7, "选项"),
]


def find_ptrs(rom: bytes, offset: int) -> list[int]:
    out: list[int] = []
    candidates = {0x08000000 + offset}
    if offset >= 0x01000000:
        candidates.add(0x09000000 + (offset & 0x00FFFFFF))
    # Also try raw 0x09|offset without mask for mid mirrors already covered above
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
            if len(out) > 60:
                break
    return sorted(set(out))


def main() -> int:
    data = bytearray(ROM.read_bytes())
    cursor_path = ROOT / "work" / "free_cursor.txt"
    free_at = int(cursor_path.read_text().strip(), 0) if cursor_path.exists() else FREE_START
    stats = {"patched": 0, "sites": 0, "fail": 0, "skip_no_ptr": 0}

    # Longer hex first so FC-prefixed / VERY EASY beat short EASY/BOY
    for en_hex, zh, prefix_hex in sorted(FORCED_HEX, key=lambda x: -len(x[0])):
        needle = bytes.fromhex(en_hex)
        enc, missing = encode_text_safe(zh)
        if missing:
            print("missing", zh, missing)
            stats["fail"] += 1
            continue
        if prefix_hex:
            # EN needle already includes prefix; zh body only after prefix
            enc = bytes.fromhex(prefix_hex) + enc
        sites: list[int] = []
        idx = 0
        while True:
            i = bytes(data).find(needle, idx)
            if i < 0:
                break
            sites.append(i)
            idx = i + 1
            if len(sites) > 80:
                break
        for off in sites:
            stats["sites"] += 1
            ptrs = find_ptrs(bytes(data), off)
            if not ptrs:
                stats["skip_no_ptr"] += 1
                continue
            need = len(enc)
            if free_at + need > FREE_END:
                print("free exhausted")
                print(json.dumps(stats, ensure_ascii=False))
                return 1
            new_off = free_at
            data[new_off : new_off + need] = enc
            free_at += (need + 3) & ~3
            new_ptr = struct.pack("<I", 0x08000000 + new_off)
            wrote = 0
            for p in ptrs:
                if p % 4 != 0:
                    continue
                cur = struct.unpack_from("<I", data, p)[0]
                if 0x08000000 <= cur <= 0x09FFFFFF:
                    data[p : p + 4] = new_ptr
                    wrote += 1
            if wrote:
                stats["patched"] += 1
                print(f"OK {hex(off)} -> {hex(new_off)} {zh} ptrs={wrote}")
            else:
                stats["fail"] += 1

    for off, old_len, zh in TITLE_INPLACE:
        enc, missing = encode_text_safe(zh)
        if missing or len(enc) > old_len:
            print("inplace fail", zh, missing, len(enc), old_len)
            stats["fail"] += 1
            continue
        data[off : off + len(enc)] = enc
        for j in range(off + len(enc), off + old_len):
            data[j] = 0x00
        stats["patched"] += 1
        print(f"INPLACE {hex(off)} {zh}")

    ROM.write_bytes(data)
    cursor_path.write_text(hex(free_at), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
