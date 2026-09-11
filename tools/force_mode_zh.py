#!/usr/bin/env python3
"""Force-reloc Quetzal new-game mode wizard strings (difficulty → unlocks)."""
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

# (offset, zh) — mode/difficulty/unlock wizard only
MODE_WIZARD: list[tuple[int, str]] = [
    (0x1025798, "最简单"),
    (0x10257A0, "最难"),
    (0x10257A8, "请选择以下默认选项之一。"),
    (0x10257CD, "自定义选项"),
    (0x10257DC, "默认选项"),
    (0x10257EC, "选择自定义或默认选项。"),
    (0x102578A, "自定义"),
    (0x1025985, "自定义"),
    (0x102580E, "非常简单"),
    (0x1025818, "简单"),
    (0x102581D, "普通"),
    (0x1025824, "困难"),
    (0x1025829, "非常困难"),
    (0x102585D, "选择游戏难度。"),
    (0x1025875, "普通"),
    (0x102587C, "随机"),
    (0x1025883, "作弊"),
    (0x102588E, "选择游戏模式。"),
    (0x10258A0, "解锁作弊？"),
    (0x10258AF, "从不"),
    (0x10258B5, "极低"),
    (0x10258BE, "低"),
    (0x10258C2, "普通"),
    (0x10258C9, "高"),
    (0x10258CE, "极高"),
    (0x10258D8, "总是"),
    (0x10258DF, "选择闪光概率。"),
    (0x10258F9, "选择光耀概率。"),
    (0x1025915, "普通模式"),
    (0x1025921, "殿堂后解锁地区"),
    (0x1025941, "开局解锁地区"),
    (0x102595B, "选择图鉴模式。"),
    (0x1025970, "徽章等级上限？"),
    (0x102598C, "殿堂后解锁全部杂项"),
    (0x10259AF, "开局解锁全部杂项"),
    (0x10259CC, "解锁全部杂项？"),
    (0x10259E6, "殿堂后解锁"),
    (0x1025A00, "开局解锁"),
    (0x1025A14, "解锁经验分享全体？"),
    (0x1025A2B, "解锁经验倍率？"),
    (0x1025A42, "第6枚徽章后解锁"),
    (0x1025A59, "殿堂后解锁"),
    (0x1025A73, "开局解锁"),
    (0x1025A87, "解锁传送？"),
    (0x1025A98, "殿堂后解锁"),
    (0x1025AB2, "开局解锁"),
    (0x1025AC6, "解锁道具/树果刷新？"),
    (0x1025AE4, "殿堂后解锁"),
    (0x1025AFE, "开局解锁"),
    (0x1025B12, "解锁再战？"),
    (0x1025B2B, "解锁便携电脑治疗？"),
    (0x1025B4D, "闪光概率："),
    (0x1025B5A, "光耀概率："),
]


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


def main() -> int:
    data = bytearray(ROM.read_bytes())
    cursor_path = ROOT / "work" / "free_cursor.txt"
    free_at = int(cursor_path.read_text().strip(), 0) if cursor_path.exists() else FREE_START
    stats = {"patched": 0, "fail": 0, "no_ptr": 0}

    for off, zh in MODE_WIZARD:
        enc, missing = encode_text_safe(zh)
        if missing:
            print("missing", hex(off), zh, missing)
            stats["fail"] += 1
            continue
        ptrs = find_ptrs(bytes(data), off)
        if not ptrs:
            print("no ptr", hex(off), zh)
            stats["no_ptr"] += 1
            continue
        need = len(enc)
        if free_at + need > FREE_END:
            print("free exhausted")
            break
        new_off = free_at
        data[new_off : new_off + need] = enc
        free_at += (need + 3) & ~3
        new_ptr = struct.pack("<I", 0x08000000 + new_off)
        wrote = 0
        for p in ptrs:
            cur = struct.unpack_from("<I", data, p)[0]
            if 0x08000000 <= cur <= 0x09FFFFFF:
                data[p : p + 4] = new_ptr
                wrote += 1
        if wrote:
            stats["patched"] += 1
            print(f"OK {hex(off)} -> {hex(new_off)} {zh} ptrs={wrote}")
        else:
            stats["fail"] += 1

    ROM.write_bytes(data)
    (ROOT / "out" / "quetzal_084_cn.gba").write_bytes(data)
    cursor_path.write_text(hex(free_at), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
