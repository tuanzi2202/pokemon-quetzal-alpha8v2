#!/usr/bin/env python3
"""Export ZH rows that still contain Latin spam (for manual fill)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_locale_zh import is_junk_en  # noqa: E402
from fill_and_apply_remaining import LOCALE, quality_ok, scrub  # noqa: E402

LATIN = re.compile(r"[A-Za-z]{4,}")
SKIP = {
    "lv", "hp", "pp", "exp", "tm", "hm", "gps", "npc", "wifi", "ok", "fc", "fd",
}


def main() -> int:
    rows = [json.loads(l) for l in LOCALE.open(encoding="utf-8") if l.strip()]
    out = []
    for r in rows:
        en = r.get("en") or ""
        zh = scrub(r.get("zh") or "")
        if is_junk_en(en) or not zh:
            continue
        if not quality_ok(en, zh) and not any("\u4e00" <= c <= "\u9fff" for c in zh):
            continue
        plain = re.sub(r"\{[^}]+\}", "", zh)
        hits = [x for x in LATIN.findall(plain) if x.lower() not in SKIP]
        if not hits:
            continue
        out.append({"offset": r["offset"], "en": en, "zh": zh, "hits": hits})
    path = ROOT / "work" / "latin_mix.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"count={len(out)} -> {path}")
    # unique english words
    words: dict[str, int] = {}
    for r in out:
        for h in r["hits"]:
            words[h] = words.get(h, 0) + 1
    top = sorted(words.items(), key=lambda x: -x[1])[:80]
    print("top words:")
    for w, n in top:
        print(f"  {n:4d}  {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
