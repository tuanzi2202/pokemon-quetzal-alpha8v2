#!/usr/bin/env python3
"""Hand-reloc leftover EN dialogues (e.g. Quetzal Wally lines).

Usage:
  python tools/fix_hand_dialogue_zh.py
"""
from __future__ import annotations

import json
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from gen3_charmap import REVERSE  # noqa: E402

ROM = ROOT / "work" / "cn_build.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
FREE_START = 0x01D9B5A8 + 0x30000
FREE_END = 0x01D9B5A8 + 0x264A58
FP_OFF = 0x1DCB5E0

HAND: dict[int, str] = {
    0x2699F8: (
        "我们的满充去哪儿了？{WAIT_CLEAR}"
        "我们很快就要出发去秋叶镇了……"
    ),
    0x2937C9: (
        "你是……\n"
        "啊，你一定是{FD:01}{FD:05}吧？{WAIT_CLEAR}"
        "谢谢你刚才陪满充玩。{WAIT_CLEAR}"
        "他从小就体弱多病。{WAIT_CLEAR}"
        "我们把他送到秋叶镇的亲戚家\n住一阵子。{WAIT_CLEAR}"
        "那里的空气比这里干净多了。{WAIT_CLEAR}"
        "什么？满充呢？\n"
        "他已经走了，我们的满充。{WAIT_CLEAR}"
        "不知道他现在走到哪儿了？"
    ),
}

# Mid-string dump offsets that share the same dialogue as a HAND entry
MID_TO_FULL: dict[int, int] = {
    0x29384E: 0x2937C9,
}


def enc_en(text: str) -> bytes:
    return bytes(REVERSE[c] for c in text)


def find_ptrs(rom: bytes, offset: int) -> list[int]:
    out: list[int] = []
    needle = struct.pack("<I", 0x08000000 + offset)
    idx = 0
    while True:
        i = rom.find(needle, idx)
        if i < 0:
            break
        out.append(i)
        idx = i + 1
        if len(out) > 80:
            break
    return sorted(set(out))


def main() -> int:
    if OUT.exists() and (not ROM.exists() or ROM.stat().st_mtime < OUT.stat().st_mtime):
        ROM.parent.mkdir(parents=True, exist_ok=True)
        ROM.write_bytes(OUT.read_bytes())
    if not ROM.exists():
        print("missing rom")
        return 1

    golden = GOLDEN.read_bytes()
    data = bytearray(ROM.read_bytes())
    cursor_path = ROOT / "work" / "free_cursor.txt"
    free_at = int(cursor_path.read_text().strip(), 0) if cursor_path.exists() else FREE_START
    stats = {"patched": 0, "no_ptr": 0, "fail": 0, "mid": 0}
    reloc: dict[int, int] = {}

    for off, zh in HAND.items():
        enc, missing = encode_text_safe(zh)
        if missing:
            print("missing glyphs", hex(off), missing)
            stats["fail"] += 1
            continue
        ptrs = find_ptrs(bytes(data), off) or find_ptrs(golden, off)
        if not ptrs:
            print("no ptr", hex(off))
            stats["no_ptr"] += 1
            continue
        need = len(enc)
        if free_at + need > FREE_END:
            print("free exhausted")
            stats["fail"] += 1
            break
        new_off = free_at
        data[new_off : new_off + need] = enc
        free_at += (need + 3) & ~3
        reloc[off] = new_off
        new_ptr = struct.pack("<I", 0x08000000 + new_off)
        wrote = 0
        for p in ptrs:
            cur = struct.unpack_from("<I", data, p)[0]
            if 0x08000000 <= cur <= 0x09FFFFFF:
                data[p : p + 4] = new_ptr
                wrote += 1
        stats["patched"] += 1
        print(f"OK {hex(off)} -> {hex(new_off)} ptrs={wrote}")

    for mid, full in MID_TO_FULL.items():
        dest = reloc.get(full)
        if dest is None:
            continue
        ptrs = find_ptrs(bytes(data), mid) or find_ptrs(golden, mid)
        new_ptr = struct.pack("<I", 0x08000000 + dest)
        wrote = 0
        for p in ptrs:
            cur = struct.unpack_from("<I", data, p)[0]
            if 0x08000000 <= cur <= 0x09FFFFFF:
                data[p : p + 4] = new_ptr
                wrote += 1
        stats["mid"] += wrote
        print(f"mid {hex(mid)} -> {hex(dest)} ptrs={wrote}")

    stamp = f"QH{int(time.time()) & 0xFFFFFFFF:08X}".encode("ascii")[:16].ljust(16, b"\x00")
    data[FP_OFF : FP_OFF + 16] = stamp

    ROM.write_bytes(data)
    OUT.write_bytes(data)
    cursor_path.write_text(hex(free_at), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False), "fp", stamp.decode())

    # Live ptr check: golden ptr site must now point at Chinese reloc
    for off in HAND:
        p = find_ptrs(golden, off)[0]
        live = struct.unpack_from("<I", data, p)[0] - 0x08000000
        probe = "Where has our WALLY" if off == 0x2699F8 else "Thank you for playing"
        en = enc_en(probe)
        print(
            "verify",
            hex(off),
            "->",
            hex(live),
            "still_EN",
            bytes(data[live : live + len(en)]) == en,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
