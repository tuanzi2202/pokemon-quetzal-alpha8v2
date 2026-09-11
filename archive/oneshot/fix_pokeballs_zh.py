#!/usr/bin/env python3
"""Translate Poké Ball item names + dialogue mentions; force fingerprint bump."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from gen3_charmap import decode_bytes, encode_plain  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"
LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"

BALL_EXACT = {
    "Master Ball": "大师球",
    "Ultra Ball": "高级球",
    "Great Ball": "超级球",
    "Poke Ball": "精灵球",
    "Poké Ball": "精灵球",
    "Safari Ball": "狩猎球",
    "Net Ball": "捕网球",
    "Dive Ball": "潜水球",
    "Nest Ball": "巢穴球",
    "Repeat Ball": "重复球",
    "Timer Ball": "计时球",
    "Luxury Ball": "豪华球",
    "Premier Ball": "纪念球",
    "Heal Ball": "治愈球",
    "Quick Ball": "先机球",
    "Dusk Ball": "黑暗球",
    "Sport Ball": "竞速球",
    "Friend Ball": "友友球",
    "Love Ball": "甜蜜球",
    "Level Ball": "等级球",
    "Lure Ball": "诱饵球",
    "Moon Ball": "月亮球",
    "Heavy Ball": "沉重球",
    "Fast Ball": "速度球",
    "Beast Ball": "究极球",
    "Dream Ball": "梦境球",
    "Cherish Ball": "贵重球",
    "Park Ball": "公园球",
    "POKé BALL": "精灵球",
    "POKE BALL": "精灵球",
    "GREAT BALL": "超级球",
    "ULTRA BALL": "高级球",
    "MASTER BALL": "大师球",
    "SAFARI BALL": "狩猎球",
    "NET BALL": "捕网球",
    "DIVE BALL": "潜水球",
    "NEST BALL": "巢穴球",
    "REPEAT BALL": "重复球",
    "TIMER BALL": "计时球",
    "LUXURY BALL": "豪华球",
    "PREMIER BALL": "纪念球",
}

BALL_PHRASE = [
    (re.compile(r"(?i)POK[EÉ]\s*BALLS?"), "精灵球"),
    (re.compile(r"(?i)GREAT\s*BALLS?"), "超级球"),
    (re.compile(r"(?i)ULTRA\s*BALLS?"), "高级球"),
    (re.compile(r"(?i)MASTER\s*BALLS?"), "大师球"),
    (re.compile(r"(?i)SAFARI\s*BALLS?"), "狩猎球"),
    (re.compile(r"(?i)NET\s*BALLS?"), "捕网球"),
    (re.compile(r"(?i)DIVE\s*BALLS?"), "潜水球"),
    (re.compile(r"(?i)NEST\s*BALLS?"), "巢穴球"),
    (re.compile(r"(?i)REPEAT\s*BALLS?"), "重复球"),
    (re.compile(r"(?i)TIMER\s*BALLS?"), "计时球"),
    (re.compile(r"(?i)LUXURY\s*BALLS?"), "豪华球"),
    (re.compile(r"(?i)PREMIER\s*BALLS?"), "纪念球"),
    (re.compile(r"(?i)HEAL\s*BALLS?"), "治愈球"),
    (re.compile(r"(?i)QUICK\s*BALLS?"), "先机球"),
    (re.compile(r"(?i)DUSK\s*BALLS?"), "黑暗球"),
]


def inplace(data: bytearray, golden: bytes, off: int, zh: str) -> bool:
    eos = golden.find(b"\xff", off)
    if eos < 0 or eos - off > 400:
        return False
    capacity = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if len(enc) > capacity:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > capacity:
            cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        if len(enc) > capacity:
            return False
    data[off : off + capacity] = enc + b"\x00" * (capacity - len(enc))
    return True


def patch_exact_names(data: bytearray, golden: bytes) -> int:
    n = 0
    for en_name, zh in sorted(BALL_EXACT.items(), key=lambda x: -len(x[0])):
        try:
            needle = encode_plain(en_name)
        except KeyError:
            continue
        i = 0
        while True:
            j = golden.find(needle, i)
            if j < 0:
                break
            # only if this is the full string (or starts a longer ball name we handle)
            eos = golden.find(b"\xff", j)
            full = decode_bytes(golden[j : eos + 1]).strip()
            if full == en_name or full.upper() == en_name.upper():
                if inplace(data, golden, j, zh):
                    n += 1
            i = j + 1
    print(f"exact ball names patched={n}")
    return n


def patch_locale(data: bytearray, golden: bytes) -> int:
    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    n_loc = n_rom = 0
    for r in rows:
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        changed = False
        # exact
        if en.strip() in BALL_EXACT:
            r["zh"] = BALL_EXACT[en.strip()]
            changed = True
        else:
            z2 = zh
            for pat, rep in BALL_PHRASE:
                z2 = pat.sub(rep, z2)
                en2 = pat.sub(rep, en)  # if zh empty, translate from en
            if not zh or not any("\u4e00" <= c <= "\u9fff" for c in zh):
                z2 = en
                for pat, rep in BALL_PHRASE:
                    z2 = pat.sub(rep, z2)
            else:
                for pat, rep in BALL_PHRASE:
                    z2 = pat.sub(rep, z2)
            # also scrub leftover English ball words in zh
            for pat, rep in BALL_PHRASE:
                if pat.search(z2):
                    z2 = pat.sub(rep, z2)
            if z2 != zh and any("\u4e00" <= c <= "\u9fff" for c in z2):
                r["zh"] = z2
                changed = True
        if changed:
            n_loc += 1
            off = int(r["offset"])
            if inplace(data, golden, off, r["zh"]):
                n_rom += 1
    LOCALE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(f"locale ball rows={n_loc} rom_applied={n_rom}")
    return n_rom


def bump_fingerprint(data: bytearray) -> None:
    """Nudge freeZh marker so weak fingerprints still diverge if needed."""
    # 0x1DCB5E0 is in free space fingerprint — flip last byte of marker
    off = 0x1DCB5E0
    data[off + 15] = (data[off + 15] + 1) & 0xFF


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    patch_exact_names(data, golden)
    patch_locale(data, golden)
    bump_fingerprint(data)
    # sanity: battle names still CN
    print("Tackle", decode_bytes(bytes(data[0x417F99 : 0x417F99 + 17]) + b"\xff"))
    print("Treecko", decode_bytes(bytes(data[0x40EFD4 : 0x40EFD4 + 13]) + b"\xff"))
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
