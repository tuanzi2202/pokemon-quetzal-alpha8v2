#!/usr/bin/env python3
"""Parallel bulk EN->ZH via translators (one engine per worker, shared cache)."""
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
LOCK = ROOT / "work" / "gtrans_cache.lock"
NEED = ROOT / "work" / "gtrans_need.json"


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


def looks_translated(en: str, zh: str) -> bool:
    if not zh or zh == en:
        return False
    # Require some CJK — reject captcha/garbage like "u01dtc1gd3jkak2et2kl"
    cjk = sum(1 for ch in zh if "\u4e00" <= ch <= "\u9fff")
    if cjk < 1:
        return False
    # Too little Chinese relative to length for longer lines
    if len(en) > 40 and cjk < 2:
        return False
    return True


def with_lock(fn, retries: int = 80):
    for _ in range(retries):
        try:
            fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            try:
                return fn()
            finally:
                try:
                    LOCK.unlink()
                except FileNotFoundError:
                    pass
        except FileExistsError:
            time.sleep(0.05 + random.random() * 0.05)
    raise RuntimeError("lock timeout")


def load_cache() -> dict[str, str]:
    if not CACHE.exists():
        return {}
    return json.loads(CACHE.read_text(encoding="utf-8"))


def save_cache(cache: dict[str, str]) -> None:
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def build_need() -> list[str]:
    cache = load_cache()
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
        need.append(en)
    need.sort(key=lambda s: (-len(s), s))
    NEED.write_text(json.dumps(need, ensure_ascii=False), encoding="utf-8")
    return need


def claim_batch(worker: int, workers: int, batch: int = 25) -> list[str]:
    def _claim():
        need = json.loads(NEED.read_text(encoding="utf-8")) if NEED.exists() else []
        cache = load_cache()
        # drop already done
        need = [e for e in need if not (e in cache and cache[e] and cache[e] != e)]
        # sticky partition by hash so workers don't fight
        mine = [e for e in need if (hash(e) % workers) == worker]
        take = mine[:batch]
        # remove claimed from shared need
        take_set = set(take)
        rest = [e for e in need if e not in take_set]
        NEED.write_text(json.dumps(rest, ensure_ascii=False), encoding="utf-8")
        return take

    return with_lock(_claim)


def merge_results(pairs: dict[str, str]) -> int:
    def _merge():
        cache = load_cache()
        before = len(cache)
        cache.update(pairs)
        save_cache(cache)
        return len(cache) - before

    return with_lock(_merge)


def worker_main(engine: str, worker: int, workers: int) -> int:
    import translators as ts

    print(f"worker{worker} engine={engine}", flush=True)
    ok = fail = 0
    t0 = time.time()
    while True:
        batch = claim_batch(worker, workers, batch=20)
        if not batch:
            break
        pairs: dict[str, str] = {}
        for en in batch:
            chunk = en if len(en) <= 900 else en[:900]
            protected, toks = protect_tokens(chunk.replace("\r", ""))
            try:
                out = ts.translate_text(
                    protected,
                    translator=engine,
                    from_language="en",
                    to_language="zh",
                )
                zh = clean_zh(restore_tokens(str(out or ""), toks))
                if looks_translated(en, zh):
                    pairs[en] = zh
                    ok += 1
                else:
                    fail += 1
                time.sleep(0.05)
            except Exception as e:
                fail += 1
                if "TooMany" in type(e).__name__ or "429" in str(e):
                    time.sleep(3.0)
                else:
                    time.sleep(0.8)
        added = merge_results(pairs)
        rate = (ok + fail) / max(time.time() - t0, 0.1)
        cache_n = len(load_cache())
        print(
            f"w{worker}/{engine} +{added} ok={ok} fail={fail} cache={cache_n} {rate:.2f}/s",
            flush=True,
        )
    print(f"worker{worker} DONE ok={ok} fail={fail}", flush=True)
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    if mode == "prepare":
        need = build_need()
        print(f"need={len(need)} cache={len(load_cache())}", flush=True)
        return 0
    if mode == "worker":
        engine = sys.argv[2]
        worker = int(sys.argv[3])
        workers = int(sys.argv[4])
        return worker_main(engine, worker, workers)
    print("usage: prepare | worker <engine> <i> <n>")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
