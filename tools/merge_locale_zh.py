#!/usr/bin/env python3
"""Rebuild locale/zh_CN/all_en_zh.jsonl from dump + phrases + official names + gtrans cache."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from translate_batch import translate_line  # noqa: E402
from official_names_zh import OFFICIAL_NAMES  # noqa: E402


def main() -> int:
    src = ROOT / "dump" / "all_en.jsonl"
    dst = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"
    cache_path = ROOT / "work" / "gtrans_cache.json"
    cache: dict[str, str] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    prior: dict[int, str] = {}
    for p in (ROOT / "locale" / "zh_CN").glob("*_zh.jsonl"):
        if p.name == "all_en_zh.jsonl":
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            zh = row.get("zh") or ""
            en = row.get("en") or ""
            if zh and zh != en:
                prior[int(row["offset"])] = zh

    changed = 0
    with src.open(encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            row = json.loads(line)
            en = row.get("en") or ""
            off = int(row["offset"])
            zh = OFFICIAL_NAMES.get(en) or translate_line(en)
            if zh == en and off in prior:
                zh = prior[off]
            if zh == en and en in cache:
                zh = cache[en]
            # Drop zero-width / BOM junk from machine translate
            if zh:
                zh = "".join(ch for ch in zh if ch not in "\u200b\u200c\u200d\ufeff")
            row["zh"] = zh
            if zh != en:
                changed += 1
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"locale changed={changed} cache={len(cache)} prior={len(prior)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
