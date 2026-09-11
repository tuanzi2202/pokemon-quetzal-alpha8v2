#!/usr/bin/env python3
"""Diagnose opening Mom / Birch help / poksammon / T1 junk."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chs_encode import encode_text_safe  # noqa: E402
from fix_clock_and_mom_open import OPENING  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

EN = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()
CN = (ROOT / "out" / "quetzal_084_cn.gba").read_bytes()
LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"


def main() -> int:
    print("=== MOM OPENING match ===")
    for off, zh in sorted(OPENING.items())[:10]:
        enc, _ = encode_text_safe(zh)
        match = CN[off : off + len(enc)] == enc
        eos = EN.find(b"\xff", off)
        te = decode_bytes(EN[off : eos + 1])[:70]
        print(f"{off:08X} match={match} EN={te!r}")

    rows = [json.loads(l) for l in LOCALE.open(encoding="utf-8") if l.strip()]
    print("=== HELP ME / BIRCH ===")
    for r in rows:
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        if re.search(r"(?i)help me|PROF\. BIRCH|birch.*help|someone.*help", en):
            print(f"{int(r['offset']):08X}")
            print(" EN", en[:120].replace("\n", " / "))
            print(" ZH", zh[:120].replace("\n", " / "))

    print("=== poksam / pokemon leftovers in ZH ===")
    n = 0
    for r in rows:
        zh = r.get("zh") or ""
        if re.search(r"(?i)poksam|pokemon|POKéMON|POKeMON", zh):
            n += 1
            if n <= 20:
                print(f"{int(r['offset']):08X}", zh[:100].replace("\n", " / "))
    print("count", n)

    print("=== T1 / [[T / ???? junk ===")
    n2 = 0
    for r in rows:
        zh = r.get("zh") or ""
        if re.search(r"\[\[\s*T\d|\[T\d\]|(?<![A-Za-z0-9{])T[0-9](?![0-9A-Za-z])|\?\?\?\?|\.{5,}", zh):
            n2 += 1
            if n2 <= 20:
                print(f"{int(r['offset']):08X}", zh[:110].replace("\n", " / "))
    print("count", n2)

    # ROM scan for Help me string
    print("=== ROM contains Help me ===")
    needle = b"Help me"  # rough - gen3 encoded differently
    # search decoded locale offsets only
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
