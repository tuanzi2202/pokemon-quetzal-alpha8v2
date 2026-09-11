#!/usr/bin/env python3
"""Bulk EN->ZH via translators lib (bing/alibaba/sogou/youdao), resume-safe."""
from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from translate_batch import translate_line  # noqa: E402
from official_names_zh import OFFICIAL_NAMES  # noqa: E402

TOKEN_RE = re.compile(r"\{[A-Z0-9_]+(?::[0-9A-Fa-f]+)?\}")
CACHE = ROOT / "work" / "gtrans_cache.json"
ENGINES = ["bing", "alibaba", "sogou", "youdao"]


def protect_tokens(s: str) -> tuple[str, list[str]]:
    toks: list[str] = []

    def repl(m: re.Match) -> str:
        toks.append(m.group(0))
        return f"[[T{len(toks) - 1}]]"

    return TOKEN_RE.sub(repl, s), toks


def restore_tokens(s: str, toks: list[str]) -> str:
    out = s
    for i, t in enumerate(toks):
        for form in (f"[[T{i}]]", f"[T{i}]", f"【T{i}】"):
            out = out.replace(form, t)
    return out


def clean_zh(zh: str) -> str:
    return "".join(ch for ch in zh if ch not in "\u200b\u200c\u200d\ufeff").strip()


def main() -> int:
    import translators as ts

    cache: dict[str, str] = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))

    need: list[str] = []
    seen: set[str] = set()
    for line in (ROOT / "dump" / "all_en.jsonl").open(encoding="utf-8"):
        en = json.loads(line).get("en") or ""
        if not en or en in seen:
            continue
        seen.add(en)
        if OFFICIAL_NAMES.get(en) or translate_line(en) != en:
            continue
        if en in cache and cache[en] and cache[en] != en:
            continue
        if not en.strip() or (en.startswith("{") and " " not in en and len(en) < 24):
            cache[en] = en
            continue
        need.append(en)

    # Prefer longer dialogue first
    need.sort(key=lambda s: (-len(s), s))
    limit = int(os.environ.get("TS_LIMIT", "0") or "0")
    if limit > 0:
        need = need[:limit]

    print(f"need={len(need)} cache={len(cache)}", flush=True)
    eng_i = 0
    ok = fail = 0
    t0 = time.time()
    for i, en in enumerate(need):
        chunk = en if len(en) <= 900 else en[:900]
        protected, toks = protect_tokens(chunk.replace("\r", ""))
        zh = None
        last_err = None
        for _try in range(len(ENGINES)):
            eng = ENGINES[(eng_i + _try) % len(ENGINES)]
            try:
                out = ts.translate_text(
                    protected,
                    translator=eng,
                    from_language="en",
                    to_language="zh",
                )
                if out and str(out).strip():
                    zh = clean_zh(restore_tokens(str(out), toks))
                    eng_i = (eng_i + _try + 1) % len(ENGINES)
                    break
            except Exception as e:
                last_err = f"{eng}:{type(e).__name__}"
                time.sleep(0.6 + random.random() * 0.4)
        if not zh:
            fail += 1
            cache[en] = en  # mark attempted as en to avoid hot-loop; optional skip
            # don't cache failure as en permanently — leave uncached
            cache.pop(en, None)
            if fail % 20 == 1:
                print(f"fail {i} {last_err}", flush=True)
            time.sleep(1.5)
        else:
            # reject if still mostly ascii same as en
            if zh == en:
                fail += 1
            else:
                cache[en] = zh
                ok += 1
            time.sleep(0.15 + random.random() * 0.1)

        if (i + 1) % 20 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            rate = (i + 1) / max(time.time() - t0, 0.1)
            print(
                f"  {i + 1}/{len(need)} ok={ok} fail={fail} cache={len(cache)} {rate:.2f}/s",
                flush=True,
            )
        # soft stop if too many consecutive fails — env override
        if fail > 80 and ok < 10:
            print("too many fails early; exit", flush=True)
            break

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"DONE ok={ok} fail={fail} cache={len(cache)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
