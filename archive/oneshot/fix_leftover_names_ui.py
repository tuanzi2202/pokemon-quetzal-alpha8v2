#!/usr/bin/env python3
"""Patch leftover item names + clear EN UI/battle/map fragments."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe, load_charmap  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"

# Exact EN (stripped) -> ZH; leading spaces preserved from golden
NAMES: dict[str, str] = {
    "Water Stone": "水之石",
    "Water Memory": "清水记忆碟",
    "Poison Memory": "毒净记忆碟",
    "Metal Powder": "金属粉",
    "Quick Powder": "速度粉",
    "Mystic Water": "神秘水滴",
    "Poison Barb": "毒针",
    "Silver Powder": "银粉",
    "Bright Powder": "光粉",
    "Mental Herb": "心灵香草",
    "Berry Pouch": "树果袋",
    "Mirror Herb": "镜面香草",
    "Poison Tera Shard": "毒太晶碎块",
    "Water Tera Shard": "水太晶碎块",
    "Mineral Evolutivo": "进化矿石",
}

HAND: dict[int, str] = {
    0xFFBD48: "搞定!\n{FD:39}被抓住了!{FC:0A}{FC:0B}{60}{01}{FC:08}{7F}",
    0xFFFEF2: "{FD:1C} {FD:1D}派出了\n{FD:06}!{WAIT_CLEAR}{FD:2E} {FD:2F}派出了\n{FD:08}!",
    0x101D838: "要对这个{53}{54}\n做什么?",
    0x10229D0: "不能选相同的{53}{54}。",
    0x318F40: "下次表现得\n更好吧!",
    0x32A7D9: "按键就行。{WAIT_CLEAR}就这么简单。\n试一下就知道了。",
}


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
        parts.append(f"[{data[i]:02X}]")
        i += 1
    return "".join(parts)


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    n = 0

    # names bank
    off = 0xF9B000
    while off < 0xFA2000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0xFA2000 or eos - off > 40 or eos - off < 3:
            off += 1
            continue
        raw = decode_bytes(golden[off : eos + 1])
        key = raw.strip()
        if key in NAMES and bytes(data[off : eos + 1]) == golden[off : eos + 1]:
            pad = len(raw) - len(raw.lstrip(" "))
            zh = (" " * pad) + NAMES[key]
            if put(data, golden, off, zh):
                n += 1
                print(f"  name {off:08X} {key} -> {NAMES[key]}")
        off = eos + 1

    for off, zh in HAND.items():
        eos = golden.find(b"\xff", off)
        if eos < 0:
            continue
        if put(data, golden, off, zh):
            n += 1
            print(f"  hand {off:08X}")

    # shop herb names (keep price FC layout from golden prefix if present)
    shop = {
        0x101F217: "回复粉{FC:13}{72}{FC:06} 50",
        0x101F22B: "复活草{FC:13}{6C}{FC:06} 300",
        0x1020988: "白色香草{FC:13}{5E}48BP",
        0x10209AC: "心灵香草{FC:13}{5E}48BP",
    }
    for off, zh in shop.items():
        if put(data, golden, off, zh):
            n += 1
            print(f"  shop {off:08X}")

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("DDEEFF00112233445566778899AABBCC")
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    _, to_str = load_charmap()
    print(f"patched {n}")
    for lab, o in [("waterstone", 0xF9C2CF), ("gotcha", 0xFFBD48), ("gym", 0x269ADC)]:
        eos = golden.find(b"\xff", o)
        print(lab, decode_chs(bytes(data[o : eos + 1]), to_str)[:60])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
