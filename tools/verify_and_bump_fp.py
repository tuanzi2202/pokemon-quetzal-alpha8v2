#!/usr/bin/env python3
"""Verify options/mode via pointers, bump fingerprint, sync out/work."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import load_charmap  # noqa: E402
from fix_options_berries_trainers import OPTIONS  # noqa: E402
from force_mode_zh import MODE_WIZARD  # noqa: E402

OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"
GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
FP = 0x1DCB5E0


def dchs(data: bytes, off: int, to_str: dict[bytes, str]) -> str:
    eos = data.find(b"\xff", off)
    buf = data[off : eos + 1]
    parts: list[str] = []
    i = 0
    while i < len(buf) and buf[i] != 0xFF:
        if buf[i] == 0xFE:
            parts.append("\n")
            i += 1
            continue
        if buf[i] in (0xFA, 0xFB):
            parts.append("{W}")
            i += 1
            continue
        pair = bytes(buf[i : i + 2])
        one = bytes(buf[i : i + 1])
        if i + 1 < len(buf) and pair in to_str:
            s2 = to_str[pair]
            s1 = to_str.get(one)
            if s1 and s1.isascii() and not s2.isascii():
                parts.append(s1)
                i += 1
                continue
            parts.append(s2)
            i += 2
            continue
        if one in to_str:
            parts.append(to_str[one])
            i += 1
            continue
        parts.append("?")
        i += 1
    return "".join(parts)


def via_gold_ptr(data: bytes, golden: bytes, off: int, to_str: dict[bytes, str]) -> str | None:
    gptr = struct.pack("<I", 0x09000000 + (off & 0xFFFFFF))
    idx = 0
    while True:
        i = golden.find(gptr, idx)
        if i < 0:
            return None
        if i % 4 == 0:
            rv = struct.unpack_from("<I", data, i)[0]
            dest = rv - 0x08000000
            if 0 <= dest < len(data):
                return dchs(data, dest, to_str)
        idx = i + 1


def main() -> int:
    data = bytearray(OUT.read_bytes())
    golden = GOLDEN.read_bytes()
    _, to_str = load_charmap()

    print("=== OPTIONS (via ptr) ===")
    bad = 0
    for off, zh in OPTIONS.items():
        got = via_gold_ptr(bytes(data), golden, off, to_str)
        site = dchs(bytes(data), off, to_str)
        ok = got is not None and (zh.replace("{FC:01}{06}{FC:03}{07}", "") in (got or "") or zh in (got or "") or site.startswith(zh[:2]))
        # soft check: mostly CJK
        text = got or site
        cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        en = sum(1 for c in text if c.isascii() and c.isalpha())
        mark = "OK" if cjk >= en else "EN?"
        if mark != "OK":
            bad += 1
        print(f"  {mark} {off:08X} want={zh[:12]!r} got={(got or site)[:28]!r}")

    print("=== MODE sample ===")
    for off, zh in [
        (0x102580E, "非常简单"),
        (0x102585D, "选择游戏难度。"),
        (0x102588E, "选择游戏模式。"),
        (0x1025798, "最简单"),
    ]:
        got = via_gold_ptr(bytes(data), golden, off, to_str)
        print(f"  {off:08X} want={zh} got={(got or '?')[:30]}")

    print("=== cottage / clock ===")
    print("  cottage", dchs(bytes(data), 0x27B813, to_str)[:50])
    print("  clock site", dchs(bytes(data), 0x287A50, to_str)[:40])

    # bump fingerprint
    data[FP : FP + 16] = bytes.fromhex("99AABBCCDDEEFF001122334455667788")
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print("fp", data[FP : FP + 16].hex())
    print("bad_optionsish", bad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
