#!/usr/bin/env python3
"""Second sweep: food/chocolate descs + apply MT cache to remaining dialogues."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from fill_and_apply_remaining import (  # noqa: E402
    CACHE,
    quality_ok,
    scrub,
    looks_full_line,
    translate_one,
)
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"

SKIP = [(0x279E71, 0x27A0D5), (0x2972B0, 0x297360), (0xFFFB50, 0xFFFC00)]

FOOD_DESCS: dict[int, str] = {
    0xF8BB19: "能回复20点HP的\n甜巧克力。",
    0xF8B83D: "能回复70点HP的\n非常甜的饮料。",
}

# Also scan+translate remaining food descs by English template
FOOD_TEMPLATES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"(?is)^A sweet chocolate\nthat restores HP\nby (\d+) points\.$"),
        "能回复{0}点HP的\n甜巧克力。",
    ),
    (
        re.compile(r"(?is)^A very sweet drink\nthat restores HP\nby (\d+) points\.$"),
        "能回复{0}点HP的\n非常甜的饮料。",
    ),
    (
        re.compile(r"(?is)^A tasty snack that\nrestores HP by\n(\d+) points\.$"),
        "能回复{0}点HP的\n美味零食。",
    ),
    (
        re.compile(r"(?is)^.*cures all the\nstatus problems of\none POK[EÉ]MON\.$"),
        "能治愈一只宝可梦的\n所有异常状态。",
    ),
]


def in_skip(off: int) -> bool:
    return any(a <= off < b for a, b in SKIP)


def put(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    cap = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    while len(body) + 1 > cap and zh:
        zh = zh[:-1]
        enc, _ = encode_text_safe(zh)
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        body = enc[:-1]
    if len(body) + 1 > cap:
        return "long"
    data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))
    return "ok"


def apply_food(data: bytearray, golden: bytes) -> int:
    n = 0
    for off, zh in FOOD_DESCS.items():
        if put(data, golden, off, zh) == "ok":
            n += 1
            print(f"  food {off:08X}")
    off = 0xF8B000
    while off < 0xF8E000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0xF8E000 or eos - off > 120 or eos - off < 20:
            off += 1
            continue
        en = decode_bytes(golden[off : eos + 1])
        for pat, tmpl in FOOD_TEMPLATES:
            m = pat.match(en)
            if not m:
                continue
            zh = tmpl.format(*m.groups()) if m.groups() else tmpl
            if put(data, golden, off, zh) == "ok":
                n += 1
                print(f"  tmpl {off:08X}")
            break
        off = eos + 1
    return n


def mt_and_apply(data: bytearray, golden: bytes, limit: int = 200) -> tuple[int, int]:
    cache: dict[str, str] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    cands: list[tuple[int, str]] = []
    for a, b in [(0x260000, 0x360000)]:
        off = a
        while off < b and len(cands) < limit:
            if in_skip(off):
                off += 1
                continue
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= b or eos - off > 160 or eos - off < 20:
                off += 1
                continue
            if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
                off = eos + 1
                continue
            en = decode_bytes(golden[off : eos + 1])
            if not looks_full_line(en) or sum(c.isalpha() for c in en) < 12:
                off = eos + 1
                continue
            if en.count("{FD:") > 3:
                off = eos + 1
                continue
            cands.append((off, en))
            off = eos + 1

    applied = 0
    # first apply cache
    for off, en in cands:
        zh = scrub(cache.get(en, ""))
        if quality_ok(en, zh):
            # keep FD tokens
            if all(t in zh for t in re.findall(r"\{FD:[0-9A-Fa-f]{2}\}", en)):
                if put(data, golden, off, zh) == "ok":
                    applied += 1

    # MT remaining (bounded)
    need = [(o, e) for o, e in cands if bytes(data[o : golden.find(b"\xff", o) + 1]) == golden[o : golden.find(b"\xff", o) + 1]]
    print(f"  still need MT: {len(need)}")
    mt_ok = 0
    for engine in ("google", "bing"):
        for off, en in need[:120]:
            if en in cache and quality_ok(en, scrub(cache[en])):
                zh = scrub(cache[en])
            else:
                zh = translate_one(en, engine)
                if zh:
                    cache[en] = zh
            if not zh or not quality_ok(en, zh):
                continue
            if not all(t in zh for t in re.findall(r"\{FD:[0-9A-Fa-f]{2}\}", en)):
                continue
            if put(data, golden, off, zh) == "ok":
                applied += 1
                mt_ok += 1
                if mt_ok <= 8:
                    print(f"  MT {off:08X} {en[:36]!r}")
        if mt_ok >= 20:
            break

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return applied, mt_ok


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    print("1) food/chocolate descs")
    print(f"   {apply_food(data, golden)}")

    print("2) MT/cache remaining dialogues")
    applied, mt_ok = mt_and_apply(data, golden, limit=500)
    print(f"   applied={applied} mt_new={mt_ok}")

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("5566778899AABBCCDDEEFF0011223344")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    # verify chocolate
    off = 0xF8BB19
    eos = golden.find(b"\xff", off)
    print("choco", decode_bytes(data[off : eos + 1]))

    # remaining EN count in road bank
    rem = 0
    for off in range(0x2A0000, 0x2E0000):
        pass
    off = 0x2A0000
    while off < 0x2E0000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0x2E0000 or eos - off > 120 or eos - off < 16:
            off += 1
            continue
        en = decode_bytes(golden[off : eos + 1])
        if sum(c.isalpha() for c in en) >= 12 and bytes(data[off : eos + 1]) == golden[off : eos + 1]:
            rem += 1
        off = eos + 1
    print(f"remaining same-EN in 2A-2E: {rem}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
