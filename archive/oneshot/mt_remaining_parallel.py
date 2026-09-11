#!/usr/bin/env python3
"""Parallel MT: free-for-all claim queue + fail dump for manual fill."""
from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fill_and_apply_remaining import (  # noqa: E402
    CACHE,
    LOCALE,
    OFFICIAL_NAMES,
    looks_full_line,
    quality_ok,
    scrub,
    translate_one,
)

LOCK = ROOT / "work" / "gtrans_cache.lock"
NEED = ROOT / "work" / "gtrans_need.json"
FAIL = ROOT / "work" / "gtrans_fail.json"


def with_lock(fn, retries: int = 200):
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
            time.sleep(0.03 + random.random() * 0.05)
    raise RuntimeError("lock timeout")


def prepare() -> int:
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    need: list[str] = []
    seen: set[str] = set()
    for r in rows:
        en = r.get("en") or ""
        zh = scrub(r.get("zh") or "")
        if not en or en in seen:
            continue
        if OFFICIAL_NAMES.get(en):
            continue
        if en in cache and quality_ok(en, scrub(cache[en])):
            continue
        if quality_ok(en, zh):
            continue
        if not looks_full_line(en):
            continue
        seen.add(en)
        need.append(en)
    need.sort(key=lambda s: (-len(s), s))
    NEED.write_text(json.dumps(need, ensure_ascii=False), encoding="utf-8")
    # reset fail list for this run (keep old fails that still need work)
    old_fail = []
    if FAIL.exists():
        try:
            old_fail = json.loads(FAIL.read_text(encoding="utf-8"))
        except Exception:
            old_fail = []
    still = [e for e in old_fail if e in seen and not (e in cache and quality_ok(e, scrub(cache[e])))]
    FAIL.write_text(json.dumps(still, ensure_ascii=False), encoding="utf-8")
    print(f"need={len(need)} cache={len(cache)} prev_fail_kept={len(still)}", flush=True)
    return 0


def claim(batch: int = 10) -> list[str]:
    """Any worker takes next batch from head — no sticky partition."""

    def _claim():
        need = json.loads(NEED.read_text(encoding="utf-8")) if NEED.exists() else []
        cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
        need = [e for e in need if not (e in cache and quality_ok(e, scrub(cache[e])))]
        take = need[:batch]
        rest = need[batch:]
        NEED.write_text(json.dumps(rest, ensure_ascii=False), encoding="utf-8")
        return take

    return with_lock(_claim)


def merge_ok(pairs: dict[str, str]) -> int:
    def _merge():
        cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
        before = len(cache)
        cache.update(pairs)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        return len(cache) - before

    return with_lock(_merge)


def merge_fail(failed: list[str]) -> None:
    if not failed:
        return

    def _merge():
        cur = []
        if FAIL.exists():
            try:
                cur = json.loads(FAIL.read_text(encoding="utf-8"))
            except Exception:
                cur = []
        seen = set(cur)
        for e in failed:
            if e not in seen:
                cur.append(e)
                seen.add(e)
        FAIL.write_text(json.dumps(cur, ensure_ascii=False), encoding="utf-8")

    with_lock(_merge)


def worker_main(engines: list[str], worker: int) -> int:
    print(f"worker{worker} engines={engines}", flush=True)
    ok = fail = 0
    t0 = time.time()
    while True:
        batch = claim(batch=8)
        if not batch:
            break
        pairs: dict[str, str] = {}
        failed: list[str] = []
        for en in batch:
            zh = None
            for eng in engines:
                zh = translate_one(en, eng)
                if zh:
                    break
                time.sleep(0.05)
            if zh:
                pairs[en] = zh
                ok += 1
            else:
                failed.append(en)
                fail += 1
            time.sleep(0.02)
        added = merge_ok(pairs)
        merge_fail(failed)
        left = 0
        if NEED.exists():
            left = len(json.loads(NEED.read_text(encoding="utf-8")))
        rate = (ok + fail) / max(time.time() - t0, 0.1)
        print(
            f"w{worker} +{added} ok={ok} fail={fail} {rate:.2f}/s left={left}",
            flush=True,
        )
    print(f"worker{worker} DONE ok={ok} fail={fail}", flush=True)
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    if mode == "prepare":
        return prepare()
    if mode == "worker":
        engines = sys.argv[2].split(",")
        worker = int(sys.argv[3])
        return worker_main(engines, worker)
    print("usage: prepare | worker <eng1,eng2> <id>")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
