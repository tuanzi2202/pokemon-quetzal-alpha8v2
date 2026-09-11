#!/usr/bin/env python3
"""Force-fix remaining POKé BALL dialogue / UI English leftovers."""
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

# Longer first
REPL = [
    (re.compile(r"(?i)POK[EÉ]\s*BALLS"), "精灵球"),
    (re.compile(r"(?i)POK[EÉ]\s*BALL"), "精灵球"),
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
    (re.compile(r"(?i)POK[EÉ]\s*MON"), "宝可梦"),
]


def scrub(text: str) -> str:
    out = text
    for pat, rep in REPL:
        out = pat.sub(rep, out)
    return out


def inplace(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    capacity = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if len(enc) > capacity:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > capacity:
            cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        if len(enc) > capacity:
            return "long"
    data[off : off + capacity] = enc + b"\x00" * (capacity - len(enc))
    return "ok"


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    # 1) locale rows
    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    n_loc = n_apply = 0
    for r in rows:
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        src = zh if zh else en
        if not re.search(r"(?i)ball|pok[eé]", src) and not re.search(r"(?i)ball|pok[eé]", en):
            continue
        z2 = scrub(src)
        # if zh still latin-heavy for ball lines, scrub from EN then
        if re.search(r"(?i)POK[EÉ]\s*BALL|GREAT\s*BALL|ULTRA\s*BALL|MASTER\s*BALL", z2):
            z2 = scrub(en) if not any("\u4e00" <= c <= "\u9fff" for c in scrub(zh or en)) else scrub(zh or en)
            # prefer: apply scrub to existing zh; if still has BALL english, rebuild from en scrubbed+translated lightly
            z2 = scrub(zh) if zh else scrub(en)
            if re.search(r"(?i)[A-Z]{3,}", re.sub(r"\{[^}]+\}", "", z2)) and zh:
                # mix: scrub zh then also replace from en tokens
                z2 = scrub(zh)
        if z2 != zh and any("\u4e00" <= c <= "\u9fff" for c in z2):
            r["zh"] = z2
            n_loc += 1
            if inplace(data, golden, int(r["offset"]), z2) == "ok":
                n_apply += 1
    LOCALE.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n",
        encoding="utf-8",
    )
    print(f"locale scrubbed={n_loc} applied={n_apply}")

    # 2) raw ROM scan for POKé BALL bytes still present in CN
    needle = encode_plain("POKé BALL")[:-1]  # includes é as 0x1B via charmap?
    # encode_plain uses REVERSE — é is in CHARMAP as 0x1B
    n_raw = 0
    i = 0
    while True:
        j = data.find(needle, i)
        if j < 0:
            break
        eos = golden.find(b"\xff", j)
        if eos < 0 or eos - j > 220:
            i = j + 1
            continue
        en_text = decode_bytes(golden[j : eos + 1])
        zh = scrub(en_text)
        if zh != en_text and any("\u4e00" <= c <= "\u9fff" for c in zh):
            if inplace(data, golden, j, zh) == "ok":
                n_raw += 1
                print(f"  raw {j:08X} -> {zh[:60]!r}")
        i = j + 1
    print(f"raw POKe BALL patches={n_raw}")

    # also GREAT/ULTRA/MASTER BALL leftover English in CN body
    for en_name, zh_name in [
        ("GREAT BALL", "超级球"),
        ("ULTRA BALL", "高级球"),
        ("MASTER BALL", "大师球"),
        ("SAFARI BALL", "狩猎球"),
    ]:
        core = encode_plain(en_name)[:-1]
        i = 0
        c = 0
        while True:
            j = data.find(core, i)
            if j < 0:
                break
            eos = golden.find(b"\xff", j)
            if 0 < eos - j <= 40:
                full = decode_bytes(golden[j : eos + 1]).strip()
                if full.upper().startswith(en_name):
                    # if string is exactly the ball or ball+punct
                    zh = scrub(decode_bytes(golden[j : eos + 1]))
                    if inplace(data, golden, j, zh) == "ok":
                        c += 1
            i = j + 1
        print(f"  {en_name} leftover patches={c}")

    # fingerprint nudge so internal cache must re-copy
    data[0x1DCB5E0 + 14] = (data[0x1DCB5E0 + 14] + 1) & 0xFF

    OUT.write_bytes(data)
    ROM.write_bytes(data)

    # verify samples
    for off in (0x279C65, 0x276D93, 0x27B9A8):
        eos = golden.find(b"\xff", off)
        print(f"{off:08X} CN={decode_bytes(bytes(data[off:eos+1]))[:70]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
