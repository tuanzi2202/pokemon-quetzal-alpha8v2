#!/usr/bin/env python3
"""MT remaining map dialogues with Bing, then apply inplace."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from fill_and_apply_remaining import CACHE, quality_ok, scrub, translate_one  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"
MAP_TODO = ROOT / "work" / "map_en_todo.jsonl"

PLACE = [
    (r"PETALBURG CITY", "橙华市"),
    (r"PETALBURG", "橙华"),
    (r"SLATEPORT CITY", "凯那市"),
    (r"SLATEPORT", "凯那"),
    (r"MAUVILLE CITY", "紫堇市"),
    (r"MAUVILLE", "紫堇"),
    (r"RUSTBORO CITY", "卡那兹市"),
    (r"RUSTBORO", "卡那兹"),
    (r"DEWFORD TOWN", "武斗镇"),
    (r"DEWFORD", "武斗"),
    (r"OLDALE TOWN", "古辰镇"),
    (r"OLDALE", "古辰"),
    (r"LITTLEROOT TOWN", "未白镇"),
    (r"LITTLEROOT", "未白"),
    (r"TEAM AQUA", "水舰队"),
    (r"TEAM MAGMA", "熔岩队"),
    (r"POK[EÉ]MON", "宝可梦"),
    (r"TRAINERS?", "训练家"),
    (r"\bGYM\b", "道馆"),
    (r"MUSEUM", "博物馆"),
    (r"EFFORT RIBBON", "努力奖章"),
]


def place_scrub(zh: str) -> str:
    out = scrub(zh)
    for a, b in PLACE:
        out = re.sub(a, b, out, flags=re.IGNORECASE)
    return out


def tokens_ok(en: str, zh: str) -> bool:
    for tok in re.findall(r"\{(?:FD|FC):[0-9A-Fa-f]{2}\}|\{WAIT_(?:CLEAR|SCROLL)\}", en):
        if tok not in zh:
            return False
    return True


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
    todos = [json.loads(l) for l in MAP_TODO.read_text(encoding="utf-8").splitlines() if l.strip()]
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    cache: dict[str, str] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    need = []
    for item in todos:
        off, en = item["off"], item["en"]
        eos = golden.find(b"\xff", off)
        if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
            continue
        need.append((off, en))
    print(f"need MT/apply: {len(need)}")

    applied = 0
    mt_new = 0
    for i, (off, en) in enumerate(need):
        zh = ""
        cached = place_scrub(cache.get(en, ""))
        if cached and quality_ok(en, cached) and tokens_ok(en, cached):
            zh = cached
        else:
            raw = translate_one(en, "bing")
            if raw:
                zh = place_scrub(raw)
                cache[en] = zh
                mt_new += 1
                time.sleep(0.12)
        if not zh or not quality_ok(en, zh) or not tokens_ok(en, zh):
            if applied < 3 and i < 8:
                print("skip", hex(off), repr(en[:55]), "->", repr((zh or "")[:55]))
            continue
        if put(data, golden, off, zh):
            applied += 1
            if applied <= 10 or applied % 30 == 0:
                print(f"  ok {applied} {off:08X} {en[:42]!r}")
        if (i + 1) % 25 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            OUT.write_bytes(data)
            print(f"  progress {i+1}/{len(need)} applied={applied} mt_new={mt_new}")

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("99AABBCCDDEEFF001122334455667788")
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print(f"done applied={applied} mt_new={mt_new} cache={len(cache)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
