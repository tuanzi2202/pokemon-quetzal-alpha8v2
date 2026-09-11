#!/usr/bin/env python3
"""Merge ts_shards + gtrans_cache into gtrans_cache.json, then rebuild locale."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    cache_path = ROOT / "work" / "gtrans_cache.json"
    cache: dict[str, str] = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    shard_dir = ROOT / "work" / "ts_shards"
    if shard_dir.exists():
        for p in sorted(shard_dir.glob("shard_*.json")):
            try:
                part = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            for k, v in part.items():
                if v and v != k:
                    cache[k] = v
    # drop useless identity
    cache = {k: v for k, v in cache.items() if v and v != k}
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"merged cache={len(cache)}")
    # rebuild locale
    from merge_locale_zh import main as merge_main

    return merge_main()


if __name__ == "__main__":
    raise SystemExit(main())
