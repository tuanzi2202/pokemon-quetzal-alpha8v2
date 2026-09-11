#!/usr/bin/env python3
"""Expand item-desc CN coverage with more templates + MT leftovers."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe, load_charmap  # noqa: E402
from fill_and_apply_remaining import CACHE, quality_ok, scrub, translate_one  # noqa: E402
from fix_full_en_sweep4 import translate_item_desc  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"

# Extra templates beyond sweep4
EXTRA: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"(?is)^A hold item that\nraises the Atk and\nSp\. Atk of Pikachu\.$"),
        "携带后提高皮卡丘的\n攻击和特攻。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nraises Farfetch'd's\ncritical-hit ratio\.$"),
        "携带后提高大葱鸭的\n击中要害率。",
    ),
    (
        re.compile(r"(?is)^A hold item that\s*\nraises Cubone or\nMarowak's Attack\.$"),
        "携带后提高可拉可拉或\n嘎啦嘎啦的攻击。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nraises Chansey's\ncritical-hit rate\.$"),
        "携带后提高吉利蛋的\n击中要害率。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nraises Ditto's\nDefense\.$"),
        "携带后提高百变怪的防御。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nraises the Sp\. Def\nof Clamperl\.$"),
        "携带后提高珍珠贝的特防。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nraises the Sp\. Atk\nof Clamperl\.$"),
        "携带后提高珍珠贝的特攻。",
    ),
    (
        re.compile(r"(?is)^A medicine that\nrestores HP by\n(\d+) points\.$"),
        "能回复{0}点HP的药。",
    ),
    (
        re.compile(r"(?is)^A medicine that\nfully restores the\nHP of a Pok[eé]mon\.$"),
        "能让宝可梦的HP\n完全回复的药。",
    ),
    (
        re.compile(r"(?is)^A medicine that\nrevives a fainted\nPok[eé]mon\.$"),
        "能让濒死的宝可梦\n复活的药。",
    ),
    (
        re.compile(
            r"(?is)^A medicine that\nrevives a fainted\nPok[eé]mon and fully\nrestores its HP\.$"
        ),
        "能让濒死宝可梦复活\n并完全回复HP的药。",
    ),
    (
        re.compile(r"(?is)^Heals a poisoned\nPok[eé]mon\.$"),
        "治愈中毒的宝可梦。",
    ),
    (
        re.compile(r"(?is)^Heals a burned\nPok[eé]mon\.$"),
        "治愈灼伤的宝可梦。",
    ),
    (
        re.compile(r"(?is)^Awakens a sleeping\nPok[eé]mon\.$"),
        "唤醒睡眠中的宝可梦。",
    ),
    (
        re.compile(r"(?is)^Defrosts a frozen\nPok[eé]mon\.$"),
        "解除冰冻的宝可梦。",
    ),
    (
        re.compile(r"(?is)^Heals a paralyzed\nPok[eé]mon\.$"),
        "治愈麻痹的宝可梦。",
    ),
    (
        re.compile(r"(?is)^A piece of a prehistoric\nPok[eé]-?\s*mon's (head|armor|claw|root|skull|shell)\.$"),
        "史前宝可梦的{0}化石碎片。",
    ),
]


FOSSIL_ZH = {
    "head": "头部",
    "armor": "甲壳",
    "claw": "爪子",
    "root": "根茎",
    "skull": "头骨",
    "shell": "贝壳",
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


def translate_extra(en: str) -> str | None:
    zh = translate_item_desc(en)
    if zh:
        return zh
    for pat, tmpl in EXTRA:
        m = pat.match(en.strip())
        if not m:
            continue
        if m.groups():
            groups = list(m.groups())
            if groups[0].lower() in FOSSIL_ZH:
                groups[0] = FOSSIL_ZH[groups[0].lower()]
            return tmpl.format(*groups)
        return tmpl
    return None


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    cache: dict[str, str] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    cands: list[tuple[int, str]] = []
    off = 0xF8B000
    while off < 0xF9A000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0xF9A000 or eos - off > 160 or eos - off < 15:
            off += 1
            continue
        if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
            off = eos + 1
            continue
        en = decode_bytes(golden[off : eos + 1])
        if sum(c.isalpha() for c in en) < 12 or en.count("{") > 4:
            off = eos + 1
            continue
        cands.append((off, en))
        off = eos + 1
    print(f"item-desc candidates: {len(cands)}")

    tmpl_n = mt_n = 0
    for i, (off, en) in enumerate(cands):
        zh = translate_extra(en)
        if zh:
            if put(data, golden, off, zh):
                tmpl_n += 1
            continue
        # MT leftover (cap)
        if mt_n >= 250:
            continue
        cached = scrub(cache.get(en, ""))
        if cached and quality_ok(en, cached):
            zh = cached
        else:
            raw = translate_one(en, "bing")
            if not raw:
                continue
            zh = scrub(raw)
            cache[en] = zh
            time.sleep(0.1)
        if quality_ok(en, zh) and put(data, golden, off, zh):
            mt_n += 1
            if mt_n <= 6 or mt_n % 40 == 0:
                print(f"  MT {mt_n} {off:08X} {en[:50]!r}")
        if (i + 1) % 40 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            OUT.write_bytes(data)
            print(f"  progress {i+1}/{len(cands)} tmpl={tmpl_n} mt={mt_n}")

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("AABBCCDDEEFF00112233445566778899")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    rem = sum(
        1
        for o, e in cands
        if bytes(data[o : golden.find(b"\xff", o) + 1]) == golden[o : golden.find(b"\xff", o) + 1]
    )
    print(f"done tmpl={tmpl_n} mt={mt_n} remaining_same={rem}")
    _, to_str = load_charmap()
    off = 0xF8B80B
    eos = golden.find(b"\xff", off)
    from fix_full_en_sweep4 import decode_chs  # type: ignore

    print("soda", decode_chs(bytes(data[off : eos + 1]), to_str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
