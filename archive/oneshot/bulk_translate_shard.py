#!/usr/bin/env python3
"""Sharded parallel bulk EN->ZH (translators). Args: shard_id shard_count."""
from __future__ import annotations

import json
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
CACHE_DIR = ROOT / "work" / "ts_shards"
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
        for form in (f"[[T{i}]]", f"[T{i}]"):
            out = out.replace(form, t)
    return "".join(ch for ch in out if ch not in "\u200b\u200c\u200d\ufeff").strip()


def main() -> int:
    shard = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    nshards = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    import translators as ts

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    shard_path = CACHE_DIR / f"shard_{shard}.json"
    # also seed from main cache
    cache: dict[str, str] = {}
    main_cache = ROOT / "work" / "gtrans_cache.json"
    if main_cache.exists():
        try:
            cache.update(json.loads(main_cache.read_text(encoding="utf-8")))
        except Exception:
            pass
    if shard_path.exists():
        try:
            cache.update(json.loads(shard_path.read_text(encoding="utf-8")))
        except Exception:
            pass
    # merge sibling shards for skip
    for p in CACHE_DIR.glob("shard_*.json"):
        try:
            cache.update(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass

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
            continue
        if hash(en) % nshards != shard:
            continue
        need.append(en)
    need.sort(key=lambda s: (-len(s), s))
    print(f"shard={shard}/{nshards} need={len(need)} known={len(cache)}", flush=True)

    eng_i = shard % len(ENGINES)
    ok = fail = 0
    t0 = time.time()
    local: dict[str, str] = {}
    if shard_path.exists():
        try:
            local = json.loads(shard_path.read_text(encoding="utf-8"))
        except Exception:
            local = {}

    for i, en in enumerate(need):
        chunk = en if len(en) <= 900 else en[:900]
        protected, toks = protect_tokens(chunk.replace("\r", ""))
        zh = None
        last = None
        for t in range(len(ENGINES)):
            eng = ENGINES[(eng_i + t) % len(ENGINES)]
            try:
                out = ts.translate_text(
                    protected, translator=eng, from_language="en", to_language="zh"
                )
                if out and str(out).strip() and str(out).strip() != protected:
                    zh = restore_tokens(str(out), toks)
                    eng_i = (eng_i + t + 1) % len(ENGINES)
                    break
            except Exception as e:
                last = f"{eng}:{type(e).__name__}"
                time.sleep(0.5)
        if zh and zh != en:
            local[en] = zh
            ok += 1
            time.sleep(0.12 + random.random() * 0.08)
        else:
            fail += 1
            if fail % 15 == 1:
                print(f"fail {i} {last}", flush=True)
            time.sleep(1.0)

        if (i + 1) % 15 == 0:
            shard_path.write_text(json.dumps(local, ensure_ascii=False), encoding="utf-8")
            rate = (i + 1) / max(time.time() - t0, 0.1)
            print(
                f"  s{shard} {i+1}/{len(need)} ok={ok} fail={fail} local={len(local)} {rate:.2f}/s",
                flush=True,
            )

    shard_path.write_text(json.dumps(local, ensure_ascii=False), encoding="utf-8")
    print(f"DONE shard={shard} ok={ok} local={len(local)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
