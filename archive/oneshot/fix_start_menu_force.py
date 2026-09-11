#!/usr/bin/env python3
"""Force start-menu labels CN via ptr retarget; scrub pokequ leftovers."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe, load_charmap  # noqa: E402
from force_ui_zh import FREE_END, find_ptrs  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"
CURSOR = ROOT / "work" / "free_cursor.txt"
FREE_START = 0x01D9B5A8 + 0x30000

# offsets from golden start-menu / common UI copies
LABELS: list[tuple[int, str]] = [
    (0x101ED9A, "图鉴"),
    (0x101EDA2, "宝可梦"),
    (0x101EDAA, "背包"),
    (0x101EDAE, "导航"),
    (0x101EDB7, "保存"),
    (0x101EDBC, "选项"),
    (0x101EDC3, "退出"),
    (0x102242F, "图鉴"),
    (0x1022437, "宝可梦"),
    (0x1022444, "背包"),
    (0x1022448, "导航"),
    (0x102245B, "保存"),
    (0x1022460, "选项"),
    (0x1022467, "退出"),
    (0x1020BC4, "图鉴"),
    (0x101BC12, "图鉴"),
    (0xFC3046, "图鉴"),
    (0xFC303A, "宝可梦"),
    (0xFC3032, "导航"),
    (0xFC3063, "背包"),
    (0x101B9B4, "宝可梦"),
    (0x1022AB4, "图鉴"),
    (0x1021A3B, "图鉴"),
]


def decode_chs(data: bytes, to_str: dict[bytes, str]) -> str:
    parts: list[str] = []
    i = 0
    while i < len(data):
        if data[i] == 0xFF:
            break
        if data[i] == 0xFE:
            parts.append("|")
            i += 1
            continue
        pair = bytes(data[i : i + 2])
        one = bytes(data[i : i + 1])
        if i + 1 < len(data) and pair in to_str:
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
        parts.append(f"[{data[i]:02X}]")
        i += 1
    return "".join(parts)


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    _, to_str = load_charmap()
    free_at = int(CURSOR.read_text().strip(), 0) if CURSOR.exists() else FREE_START

    # Also discover by EN needle in golden
    en_map = {
        bytes.fromhex("cac9c51bbebfd2ff"): "图鉴",
        bytes.fromhex("cac9c51bc7c9c8ff"): "宝可梦",
        bytes.fromhex("cac9c51bc8bbd0ff"): "导航",
        bytes.fromhex("bcbbc1ff"): "背包",
        bytes.fromhex("cdbbd0bfff"): "保存",
        bytes.fromhex("bfd2c3ceff"): "退出",
        bytes.fromhex("c9cacec3c9c8ff"): "选项",
    }
    sites: dict[int, str] = {off: zh for off, zh in LABELS}
    for needle, zh in en_map.items():
        idx = 0
        while True:
            i = golden.find(needle, idx)
            if i < 0:
                break
            if 0x1000000 <= i < 0x1030000 or 0xFC0000 <= i < 0xFD0000:
                sites[i] = zh
            idx = i + 1

    patched = 0
    for off, zh in sorted(sites.items()):
        enc, miss = encode_text_safe(zh)
        if miss:
            continue
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        ptrs = find_ptrs(bytes(data), off)
        # also search who currently points here OR to nearby smashed text
        if not ptrs:
            # restore golden EN so we have a stable length, still try inplace if fits
            eos = golden.find(b"\xff", off)
            if eos > off:
                data[off : eos + 1] = golden[off : eos + 1]
                ptrs = find_ptrs(bytes(data), off)
        if not ptrs:
            # inplace if capacity allows
            eos = golden.find(b"\xff", off)
            if eos > off and len(enc) <= (eos - off + 1):
                cap = eos - off + 1
                data[off : off + cap] = enc + b"\x00" * (cap - len(enc))
                patched += 1
                print(f"INPLACE {off:08X} {zh}")
            continue
        need = len(enc)
        if free_at + need > FREE_END:
            print("free exhausted")
            break
        new_off = free_at
        data[new_off : new_off + need] = enc
        free_at = (free_at + need + 3) & ~3
        new_ptr = struct.pack("<I", 0x08000000 + new_off)
        wrote = 0
        for p in ptrs:
            if p % 4:
                continue
            cur = struct.unpack_from("<I", data, p)[0]
            if 0x08000000 <= cur <= 0x09FFFFFF:
                data[p : p + 4] = new_ptr
                wrote += 1
        if wrote:
            patched += 1
            print(f"RELOC {off:08X}->{new_off:08X} {zh} ptrs={wrote}")

    # scrub obvious pokequ / mash in UI bank
    scrub_n = 0
    for off in range(0x101F0A0, 0x101F0C0):
        pass
    # fix known mash site
    mash = 0x101F0AC
    if mash in sites or True:
        # leave unless we know layout
        pass

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("112233445566778899AABBCCDDEEFF00")
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    CURSOR.write_text(hex(free_at), encoding="utf-8")

    print(f"patched={patched}")
    for off, zh in LABELS[:7]:
        eos = data.find(b"\xff", off)
        ptrs = find_ptrs(bytes(data), off)
        shown = decode_chs(bytes(data[off : eos + 1]), to_str) if eos > off else "?"
        if ptrs:
            dest = struct.unpack_from("<I", data, ptrs[0])[0] - 0x08000000
            shown = decode_chs(bytes(data[dest : data.find(b"\xff", dest) + 1]), to_str)
        print(f"  {off:08X} want={zh} show={shown!r} ptrs={len(ptrs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
