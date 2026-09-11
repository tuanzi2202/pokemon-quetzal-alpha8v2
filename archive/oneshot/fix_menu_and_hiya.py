#!/usr/bin/env python3
"""Restore smashed start-menu EN needles, force_ui reloc, fix Hiya by hand."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe, load_charmap  # noqa: E402
from force_ui_zh import FORCED_HEX, TITLE_INPLACE, FREE_END, FREE_START, find_ptrs  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"
CURSOR = ROOT / "work" / "free_cursor.txt"

HIYA = (
    "嗨!你该不会是…\n新手训练家吧?{WAIT_CLEAR}"
    "你知道宝可梦训练家\n到了新城镇会先做什么吗?{WAIT_CLEAR}"
    "他们会先看看镇上\n有什么样的道馆。"
)


def decode_chs(data: bytes, to_str: dict[bytes, str]) -> str:
    parts: list[str] = []
    i = 0
    while i < len(data):
        if data[i] == 0xFF:
            break
        if data[i] == 0xFE:
            parts.append("\n")
            i += 1
            continue
        if data[i] in (0xFA, 0xFB):
            parts.append("{W}")
            i += 1
            continue
        if i + 1 < len(data) and data[i : i + 2] in to_str:
            s2 = to_str[data[i : i + 2]]
            s1 = to_str.get(data[i : i + 1])
            if s1 and s1.isascii() and not s2.isascii():
                parts.append(s1)
                i += 1
                continue
            parts.append(s2)
            i += 2
            continue
        if data[i : i + 1] in to_str:
            parts.append(to_str[data[i : i + 1]])
            i += 1
            continue
        parts.append("?")
        i += 1
    return "".join(parts)


def put(data: bytearray, golden: bytes, off: int, zh: str) -> bool:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return False
    cap = eos - off + 1
    text = zh
    while text:
        enc, _ = encode_text_safe(text)
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        body = enc[:-1]
        if len(body) + 1 <= cap:
            data[off : off + cap] = body + b"\xff" + bytes(cap - 1 - len(body))
            return True
        text = text[:-1]
    return False


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    free_at = int(CURSOR.read_text().strip(), 0) if CURSOR.exists() else FREE_START

    # 1) restore EN menu needles from golden so force_ui can find them
    restored = 0
    for en_hex, zh, _prefix in FORCED_HEX:
        needle = bytes.fromhex(en_hex)
        idx = 0
        while True:
            i = golden.find(needle, idx)
            if i < 0:
                break
            if data[i : i + len(needle)] != needle:
                data[i : i + len(needle)] = needle
                restored += 1
            idx = i + 1
    print(f"restored EN needles: {restored}")

    # 2) force reloc like force_ui_zh
    patched = 0
    for en_hex, zh, prefix_hex in sorted(FORCED_HEX, key=lambda x: -len(x[0])):
        needle = bytes.fromhex(en_hex)
        enc, missing = encode_text_safe(zh)
        if missing:
            continue
        if prefix_hex:
            enc = bytes.fromhex(prefix_hex) + enc
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        idx = 0
        sites = []
        while True:
            i = bytes(data).find(needle, idx)
            if i < 0:
                break
            sites.append(i)
            idx = i + 1
        for off in sites:
            ptrs = find_ptrs(bytes(data), off)
            if not ptrs:
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
                if p % 4 != 0:
                    continue
                cur = struct.unpack_from("<I", data, p)[0]
                if 0x08000000 <= cur <= 0x09FFFFFF:
                    data[p : p + 4] = new_ptr
                    wrote += 1
            if wrote:
                patched += 1
                print(f"OK {off:08X}->{new_off:08X} {zh} ptrs={wrote}")
    for off, old_len, zh in TITLE_INPLACE:
        enc, missing = encode_text_safe(zh)
        if missing or len(enc) > old_len:
            continue
        data[off : off + len(enc)] = enc
        for j in range(off + len(enc), off + old_len):
            data[j] = 0
        patched += 1
        print(f"INPLACE {off:08X} {zh}")

    # 3) Hiya full CN
    put(data, golden, 0x269A42, HIYA)

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("FF00112233445566778899AABBCCDDEE")
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    CURSOR.write_text(hex(free_at), encoding="utf-8")

    _, to_str = load_charmap()
    print(f"patched labels={patched}")
    print("hiya", decode_chs(bytes(data[0x269A42 : golden.find(b"\xff", 0x269A42) + 1]), to_str)[:90])
    # verify BAG via ptr
    bag_needle = bytes.fromhex("bcbbc1ff")
    i = golden.find(bag_needle)
    if i >= 0:
        ptrs = find_ptrs(bytes(data), i)
        print("BAG golden", hex(i), "ptrs", len(ptrs))
        if ptrs:
            dest = struct.unpack_from("<I", data, ptrs[0])[0] & 0x01FFFFFF
            print("BAG points", hex(dest), decode_chs(bytes(data[dest : data.find(b"\xff", dest) + 1]), to_str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
