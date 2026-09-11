#!/usr/bin/env python3
"""Translate high-priority new-game / character-select dialogue first."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from official_names_zh import OFFICIAL_NAMES  # noqa: E402
from translate_batch import translate_line  # noqa: E402

CACHE = ROOT / "work" / "gtrans_cache.json"


def main() -> int:
    from deep_translator import MyMemoryTranslator

    tr = MyMemoryTranslator(source="en-GB", target="zh-CN")
    cache: dict[str, str] = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    pri: list[str] = []
    for line in (ROOT / "dump" / "all_en.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        en = r.get("en") or ""
        off = int(r["offset"])
        if not en or en in cache:
            continue
        if translate_line(en) != en:
            continue
        if OFFICIAL_NAMES.get(en):
            continue
        low = en.lower()
        if 0x1018000 <= off <= 0x1030000 and len(en) >= 16:
            pri.append(en)
        elif any(
            k in low
            for k in (
                "birch",
                "brendan",
                "littleroot",
                "choose",
                "region",
                "character",
                "professor",
                "pokemon world",
                "are you a boy",
                "your name",
                "rival",
            )
        ):
            pri.append(en)
    seen: set[str] = set()
    uniq = []
    for e in pri:
        if e not in seen:
            seen.add(e)
            uniq.append(e)
    print("priority", len(uniq), "cache", len(cache), flush=True)
    ok = 0
    for i, en in enumerate(uniq[:200]):
        try:
            chunk = en if len(en) <= 450 else en[:450]
            zh = tr.translate(chunk)
            if zh and zh.strip():
                cache[en] = zh
                ok += 1
        except Exception as e:
            print("fail", i, type(e).__name__, flush=True)
            time.sleep(1.0)
        if (i + 1) % 10 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print("prio", i + 1, "ok", ok, flush=True)
        time.sleep(0.08)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print("done ok", ok, "cache", len(cache), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
