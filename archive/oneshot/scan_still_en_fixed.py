#!/usr/bin/env python3
"""Rescan still-EN treating FE as newline (not CJK 换行)."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import load_charmap  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

OUT = ROOT / "out" / "quetzal_084_cn.gba"
GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
REPORT = ROOT / "work" / "still_en_fixed.jsonl"

WORD = re.compile(r"[A-Za-z]{3,}")
COMMON = set(
    """
    the and you are for that with this have from they will your what when where
    there about just like some more been were was not but can get all out him
    her his she its our who how why yes hey hello thanks please want need look
    battle trainer route town city berry pokemon gym excuse see this face water
    clothes item hold restores points mineral soda milk bitter sweet chocolate
    cookie juice powder herb medicine raise raises boosts heals heal heal
    paralysis poison burn sleep freeze confuse status fainted usable
    """.split()
)


def decode_chs(data: bytes, to_str: dict[bytes, str]) -> str:
    parts: list[str] = []
    i = 0
    while i < len(data):
        b = data[i]
        if b == 0xFF:
            break
        if b == 0xFE:
            parts.append("\n")
            i += 1
            continue
        if b == 0xFA:
            parts.append("{WAIT_SCROLL}")
            i += 1
            continue
        if b == 0xFB:
            parts.append("{WAIT_CLEAR}")
            i += 1
            continue
        if b == 0xFD and i + 1 < len(data):
            parts.append(f"{{FD:{data[i+1]:02X}}}")
            i += 2
            continue
        if b == 0xFC and i + 1 < len(data):
            parts.append(f"{{FC:{data[i+1]:02X}}}")
            i += 2
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
        parts.append(f"[{b:02X}]")
        i += 1
    return "".join(parts)


def main() -> int:
    rom = OUT.read_bytes()
    g = GOLDEN.read_bytes()
    _, to_str = load_charmap()
    hits: list[dict] = []
    banks = [
        (0x250000, 0x360000, "map"),
        (0xF8B000, 0xF9A000, "idesc"),
        (0xF9B000, 0xFA2000, "iname"),
        (0xFF8000, 0x1000000, "battle"),
        (0x1000000, 0x1040000, "menu"),
    ]
    for a, b, name in banks:
        off = a
        while off < b:
            eos = rom.find(b"\xff", off)
            if eos < 0 or eos >= b or eos - off > 200 or eos - off < 10:
                off += 1
                continue
            chs = decode_chs(rom[off : eos + 1], to_str)
            plain = re.sub(r"\{[^}]+\}", "", chs)
            plain = re.sub(r"\[[0-9A-Fa-f]{2}\]", "", plain)
            cjk = sum(1 for c in plain if "\u4e00" <= c <= "\u9fff")
            words = [w.lower() for w in WORD.findall(plain)]
            letters = sum(c.isalpha() and c.isascii() for c in plain)
            if (
                letters >= 10
                and len(words) >= 2
                and cjk <= 1
                and any(w in COMMON for w in words)
            ):
                en = decode_bytes(g[off : eos + 1]) if off < len(g) else chs
                hits.append({"off": off, "bank": name, "en": en, "chs": chs})
            off = eos + 1

    REPORT.write_text(
        "\n".join(json.dumps(h, ensure_ascii=False) for h in hits) + "\n",
        encoding="utf-8",
    )
    print("total", len(hits), dict(Counter(h["bank"] for h in hits)))
    for bank in ["map", "idesc", "iname", "battle", "menu"]:
        xs = [h for h in hits if h["bank"] == bank]
        print(f"==== {bank} {len(xs)}")
        for h in xs[:20]:
            print(f"  {h['off']:08X} {h['en'][:100]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
