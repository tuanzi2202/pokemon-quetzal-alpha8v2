#!/usr/bin/env python3
"""Bulk-translate all_en.jsonl -> locale/zh_CN/all_en_zh.jsonl.

Uses exact PHRASE overrides first, then merges prior zh files by offset,
then Google-translates remaining unique English (control tokens preserved).
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from translate_batch import PHRASES, translate_line  # noqa: E402

TOKEN_RE = re.compile(r"\{[A-Z0-9_]+(?::[0-9A-Fa-f]+)?\}")


def protect_tokens(s: str) -> tuple[str, list[str]]:
    toks: list[str] = []

    def repl(m: re.Match[str]) -> str:
        toks.append(m.group(0))
        return f"⟦{len(toks) - 1}⟧"

    return TOKEN_RE.sub(repl, s), toks


def restore_tokens(s: str, toks: list[str]) -> str:
    out = s
    for i, t in enumerate(toks):
        out = out.replace(f"⟦{i}⟧", t)
        out = out.replace(f"[{i}]", t)  # translator sometimes alters brackets
    return out


def load_offset_zh() -> dict[int, str]:
    out: dict[int, str] = {}
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
                out[int(row["offset"])] = zh
    return out


def main() -> int:
    src = ROOT / "dump" / "all_en.jsonl"
    dst = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"
    cache_path = ROOT / "work" / "gtrans_cache.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    cache: dict[str, str] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    prior = load_offset_zh()

    def make_backends():
        backends = []
        try:
            from deep_translator import MyMemoryTranslator

            backends.append(("mymemory", MyMemoryTranslator(source="en-GB", target="zh-CN")))
        except Exception as e:
            print("MyMemory unavailable:", e)
        # Google often blocked in-CN; skip unless MYTRANS_GOOGLE=1
        if __import__("os").environ.get("MYTRANS_GOOGLE") == "1":
            try:
                from deep_translator import GoogleTranslator

                backends.append(("google", GoogleTranslator(source="en", target="zh-CN")))
            except Exception as e:
                print("Google unavailable:", e)
        return backends

    backends = make_backends()
    print("backends:", [n for n, _ in backends])

    rows: list[dict] = []
    need_api: list[str] = []
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        en = row.get("en") or ""
        off = int(row["offset"])
        zh = translate_line(en)
        if zh == en and off in prior:
            zh = prior[off]
        if zh == en and en:
            if en in cache:
                zh = cache[en]
            elif en not in need_api:
                need_api.append(en)
        row["zh"] = zh
        rows.append(row)

    print(f"rows={len(rows)} unique_need_api={len(need_api)} prior={len(prior)} cache={len(cache)}")
    if backends and need_api:
        consecutive_fail = 0
        for i, en in enumerate(need_api):
            # Skip pure control / empty-ish
            if not en.strip() or (en.startswith("{") and len(en) < 24 and en.count("{") >= 1 and " " not in en):
                cache[en] = en
                continue
            # MyMemory free tier ~500 chars
            chunk = en if len(en) <= 450 else en[:450]
            protected, toks = protect_tokens(chunk)
            zh = en
            for name, tr in backends:
                try:
                    out = tr.translate(protected)
                    if out and out.strip():
                        zh = restore_tokens(out, toks)
                        consecutive_fail = 0
                        break
                except Exception as e:
                    print("fail", name, i, type(e).__name__, flush=True)
                    consecutive_fail += 1
                    # MyMemory rate-limit: cool down hard
                    if "TooMany" in type(e).__name__ or "TooMany" in str(e):
                        time.sleep(8.0)
                    else:
                        time.sleep(1.2)
            cache[en] = zh
            if (i + 1) % 25 == 0:
                cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
                print(f"  translated {i + 1}/{len(need_api)} cache={len(cache)}", flush=True)
                time.sleep(1.5)
            else:
                time.sleep(0.35)
            if consecutive_fail >= 40:
                print("too many failures; stopping early", flush=True)
                break
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    changed = 0
    with dst.open("w", encoding="utf-8") as fout:
        for row in rows:
            en = row.get("en") or ""
            zh = row.get("zh") or en
            if zh == en and en in cache:
                zh = cache[en]
            row["zh"] = zh
            if zh != en:
                changed += 1
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {dst} changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
