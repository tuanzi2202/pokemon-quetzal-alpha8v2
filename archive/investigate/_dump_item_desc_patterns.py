#!/usr/bin/env python3
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from gen3_charmap import decode_bytes  # noqa: E402

g = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()
rom = (ROOT / "out" / "quetzal_084_cn.gba").read_bytes()
pat: Counter[str] = Counter()
off = 0xF8B000
while off < 0xF9A000:
    eos = g.find(b"\xff", off)
    if eos < 0 or eos >= 0xF9A000 or eos - off > 160 or eos - off < 15:
        off += 1
        continue
    if rom[off : eos + 1] != g[off : eos + 1]:
        off = eos + 1
        continue
    en = decode_bytes(g[off : eos + 1])
    if sum(c.isalpha() for c in en) < 12 or en.count("{") > 3:
        off = eos + 1
        continue
    key = re.sub(r"\d+", "N", en)
    key = re.sub(r"\s+", " ", key).strip()
    pat[key] += 1
    off = eos + 1
print("unique", len(pat), "total", sum(pat.values()))
for k, c in pat.most_common(60):
    print(f"{c:4d} {k[:120]!r}")
