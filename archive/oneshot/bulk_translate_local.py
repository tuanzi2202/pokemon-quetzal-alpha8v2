#!/usr/bin/env python3
"""Offline bulk EN->ZH via Helsinki-NLP/opus-mt-en-zh (local, no rate limit)."""
from __future__ import annotations

import json
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
MODEL_ID = "Helsinki-NLP/opus-mt-en-zh"


def protect_tokens(s: str) -> tuple[str, list[str]]:
    toks: list[str] = []

    def repl(m: re.Match) -> str:
        toks.append(m.group(0))
        return f"[[T{len(toks) - 1}]]"

    return TOKEN_RE.sub(repl, s), toks


def restore_tokens(s: str, toks: list[str]) -> str:
    out = s
    for i, t in enumerate(toks):
        for form in (f"[[T{i}]]", f"[T{i}]", f"【T{i}】", f"（T{i}）"):
            out = out.replace(form, t)
    return out


def clean_zh(zh: str) -> str:
    return "".join(ch for ch in zh if ch not in "\u200b\u200c\u200d\ufeff").strip()


def main() -> int:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import torch

    print("loading", MODEL_ID, flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    model.eval()
    print("device", device, flush=True)

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
        if OFFICIAL_NAMES.get(en):
            continue
        if translate_line(en) != en:
            continue
        if en in cache and cache[en] and cache[en] != en:
            continue
        # skip pure controls
        if not en.strip() or (en.startswith("{") and " " not in en and len(en) < 24):
            cache[en] = en
            continue
        need.append(en)

    print(f"need={len(need)} cache={len(cache)} unique={len(seen)}", flush=True)
    batch_size = 16 if device == "cuda" else 8
    t0 = time.time()
    done = 0
    for i in range(0, len(need), batch_size):
        batch = need[i : i + batch_size]
        protected = []
        toks_list = []
        for en in batch:
            p, toks = protect_tokens(en.replace("\n", " ").strip())
            # model input length cap
            if len(p) > 400:
                p = p[:400]
            protected.append(p)
            toks_list.append(toks)
        enc = tok(protected, return_tensors="pt", padding=True, truncation=True, max_length=128)
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            out = model.generate(**enc, max_length=160, num_beams=2)
        texts = tok.batch_decode(out, skip_special_tokens=True)
        for en, zh, toks in zip(batch, texts, toks_list):
            zh = clean_zh(restore_tokens(zh, toks))
            if not zh:
                zh = en
            cache[en] = zh
        done += len(batch)
        if done % 64 == 0 or i + batch_size >= len(need):
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            rate = done / max(time.time() - t0, 0.1)
            print(f"  {done}/{len(need)} cache={len(cache)} {rate:.1f}/s", flush=True)

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print("DONE cache", len(cache), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
