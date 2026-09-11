#!/usr/bin/env python3
"""Dump still-EN map dialogues (same as golden) for translation."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from gen3_charmap import decode_bytes  # noqa: E402

g = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()
rom = (ROOT / "out" / "quetzal_084_cn.gba").read_bytes()
out: list[dict] = []
off = 0x260000
while off < 0x360000:
    eos = g.find(b"\xff", off)
    if eos < 0 or eos >= 0x360000 or eos - off > 180 or eos - off < 16:
        off += 1
        continue
    if rom[off : eos + 1] != g[off : eos + 1]:
        off = eos + 1
        continue
    en = decode_bytes(g[off : eos + 1])
    plain = re.sub(r"\{[^}]+\}", "", en)
    if sum(c.isalpha() for c in plain) < 16:
        off = eos + 1
        continue
    if len(re.findall(r"\{[0-9A-Fa-f]{2}\}", en)) > 4:
        off = eos + 1
        continue
    words = re.findall(r"[A-Za-z]{3,}", plain)
    if len(words) < 3 or (" " not in plain and "\n" not in en):
        off = eos + 1
        continue
    out.append({"off": off, "en": en})
    off = eos + 1

path = ROOT / "work" / "map_en_todo.jsonl"
path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in out) + "\n", encoding="utf-8")
print("map still-EN", len(out))
for x in out[:25]:
    print(f"{x['off']:08X} {x['en'][:90]!r}")
