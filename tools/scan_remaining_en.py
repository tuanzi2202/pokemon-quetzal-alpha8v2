#!/usr/bin/env python3
"""Strict scan for remaining real English in CN ROM."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
REPORT = ROOT / "work" / "remaining_en_scan.jsonl"

WORD = re.compile(r"[A-Za-z]{3,}")
COMMON = set(
    """
    the and you are for that with this have from they will your pokemon
    what when where there their about would could should just like some
    more been were was not but can get got all out him her his she its
    our who how why yes no hey hi oh wow of to in on is it me my we us
    at by or if so do be as hello thanks thank please want need look
    battle train trainer route town city berry item use used using
    restore restores hp pp status poison burn sleep freeze confuse
    """.split()
)


def is_real_en(s: str) -> bool:
    if not s or len(s) < 8:
        return False
    plain = re.sub(r"\{[^}]+\}", "", s)
    plain = plain.replace("\n", " ").replace("\r", "")
    if len(plain) < 8:
        return False
    if plain.count("{") > 2:
        return False
    letters = sum(c.isalpha() for c in plain)
    if letters < 8:
        return False
    if letters / max(len(plain), 1) < 0.55:
        return False
    words = [w.lower() for w in WORD.findall(plain)]
    if len(words) < 2:
        return False
    if not any(w in COMMON for w in words):
        if not (plain[0].isupper() and any(c.islower() for c in plain)):
            return False
    if re.search(r"[0-9A-F]{8,}", plain):
        return False
    return True


BANKS = [
    (0x250000, 0x360000, "map_dlg"),
    (0xF80000, 0xFA0000, "item_desc"),
    (0xF9B000, 0xFA2000, "item_name"),
    (0xFF8000, 0x1000000, "battle_ui"),
    (0x1000000, 0x1040000, "menu_ui"),
    (0x1C00000, 0x1E00000, "extra"),
]


def main() -> int:
    g = GOLDEN.read_bytes()
    rom = OUT.read_bytes()
    hits: list[dict] = []
    by_bank: Counter[str] = Counter()

    for a, b, name in BANKS:
        off = a
        while off < b:
            eos = g.find(b"\xff", off)
            if eos < 0 or eos >= b or eos - off > 200 or eos - off < 8:
                off += 1
                continue
            en = decode_bytes(g[off : eos + 1])
            if not is_real_en(en):
                off = eos + 1
                continue
            same = bytes(rom[off : eos + 1]) == g[off : eos + 1]
            cur = decode_bytes(rom[off : eos + 1])
            still_en = is_real_en(cur)
            if same or still_en:
                hits.append(
                    {
                        "off": off,
                        "bank": name,
                        "en": en,
                        "cur": cur if not same else en,
                        "same": same,
                        "partial": still_en and not same,
                    }
                )
                by_bank[name] += 1
            off = eos + 1

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("w", encoding="utf-8") as f:
        for h in hits:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")

    print(f"total still-EN-ish: {len(hits)}")
    print("by bank:", dict(by_bank))
    for cat in ["map_dlg", "item_desc", "item_name", "battle_ui", "menu_ui", "extra"]:
        samp = [h for h in hits if h["bank"] == cat][:10]
        print(f"==== {cat} n={by_bank[cat]}")
        for h in samp:
            print(f"  {h['off']:08X} same={h['same']} {h['en'][:88]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
