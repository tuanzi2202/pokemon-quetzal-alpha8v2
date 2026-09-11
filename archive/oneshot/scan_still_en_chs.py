#!/usr/bin/env python3
"""Find strings that still look English under CHS decode."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import load_charmap  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

OUT = ROOT / "out" / "quetzal_084_cn.gba"
GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
REPORT = ROOT / "work" / "still_en_chs.jsonl"

WORD = re.compile(r"[A-Za-z]{3,}")
COMMON = set(
    "the and you are for that with this have from they will your what when where "
    "there about would could should just like some more been were was not but can "
    "get all out him her his she its our who how why yes hey hello thanks please "
    "want need look battle trainer route town city berry pokemon pokémon gym "
    "excuse see this look face water clothes".split()
)


def decode_chs(data: bytes, to_str: dict[bytes, str], max_len: int = 200) -> str:
    parts: list[str] = []
    i = 0
    while i < min(len(data), max_len):
        if data[i] == 0xFF:
            break
        if i + 1 < len(data) and data[i : i + 2] in to_str:
            parts.append(to_str[data[i : i + 2]])
            i += 2
            continue
        if data[i : i + 1] in to_str:
            parts.append(to_str[data[i : i + 1]])
            i += 1
            continue
        parts.append(f"[{data[i]:02X}]")
        i += 1
    return "".join(parts)


def is_still_en(chs: str) -> bool:
    plain = re.sub(r"\[[0-9A-Fa-f]{2}\]", "", chs)
    plain = plain.replace("{WAIT_CLEAR}", " ").replace("{WAIT_SCROLL}", " ")
    cjk = sum(1 for c in plain if "\u4e00" <= c <= "\u9fff")
    words = [w.lower() for w in WORD.findall(plain)]
    letters = sum(c.isalpha() and c.isascii() for c in plain)
    if letters < 12 or len(words) < 3:
        return False
    if cjk >= 4:
        return False
    if letters > cjk * 3 and any(w in COMMON for w in words):
        return True
    if cjk <= 1 and " " in plain and any(w in COMMON for w in words):
        return True
    return False


BANKS = [
    (0x250000, 0x360000, "map"),
    (0xF8B000, 0xF9A000, "idesc"),
    (0xF9B000, 0xFA2000, "iname"),
    (0xFF8000, 0x1000000, "battle"),
    (0x1000000, 0x1040000, "menu"),
    (0x09DC0000, 0x09E00000, "freespace"),  # may not exist
]


def main() -> int:
    rom = OUT.read_bytes()
    g = GOLDEN.read_bytes()
    _, to_str = load_charmap()
    hits: list[dict] = []

    for a, b, name in BANKS:
        if a >= len(rom):
            continue
        b = min(b, len(rom))
        off = a
        while off < b:
            eos = rom.find(b"\xff", off)
            if eos < 0 or eos >= b or eos - off > 200 or eos - off < 12:
                off += 1
                continue
            chs = decode_chs(rom[off : eos + 1], to_str)
            if is_still_en(chs):
                same = False
                en_g = ""
                if off + (eos - off) < len(g):
                    same = bytes(rom[off : eos + 1]) == g[off : eos + 1]
                    en_g = decode_bytes(g[off : eos + 1])
                hits.append(
                    {
                        "off": off,
                        "bank": name,
                        "chs": chs[:160],
                        "en": en_g[:160],
                        "same": same,
                    }
                )
            off = eos + 1

    REPORT.write_text(
        "\n".join(json.dumps(h, ensure_ascii=False) for h in hits) + ("\n" if hits else ""),
        encoding="utf-8",
    )
    from collections import Counter

    c = Counter(h["bank"] for h in hits)
    print(f"total still-EN (CHS): {len(hits)} by={dict(c)}")
    for bank, _ in c.most_common():
        print(f"==== {bank}")
        for h in [x for x in hits if x["bank"] == bank][:12]:
            print(f"  {h['off']:08X} same={h['same']} {h['chs'][:100]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
