#!/usr/bin/env python3
"""Re-apply skipped map lines by reinjecting WAIT/FD tokens into MT zh."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from fill_and_apply_remaining import CACHE, quality_ok, scrub  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"
MAP_TODO = ROOT / "work" / "map_en_todo.jsonl"


def put(data: bytearray, golden: bytes, off: int, zh: str) -> bool:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return False
    cap = eos - off + 1
    text = zh
    while text:
        enc, _ = encode_text_safe(text)
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        body = enc[:-1]
        if len(body) + 1 <= cap:
            data[off : off + cap] = body + b"\xff" + bytes(cap - 1 - len(body))
            return True
        text = text[:-1]
    return False


def reinject(en: str, zh: str) -> str:
    """Best-effort: append missing control tokens in EN order."""
    out = scrub(zh)
    # restore FD/FC exactly if missing
    for tok in re.findall(r"\{(?:FD|FC):[0-9A-Fa-f]{2}\}", en):
        if tok not in out:
            # try replace Chinese placeholder leftovers
            out = out + tok if out.endswith(("。", "！", "？", "…")) else tok + out
    # WAIT tokens: insert at paragraph breaks
    waits = re.findall(r"\{WAIT_(?:CLEAR|SCROLL)\}", en)
    for w in waits:
        if w in out:
            continue
        # split on 。！？… first sentence end
        m = re.search(r"[。！？…]", out)
        if m:
            i = m.end()
            out = out[:i] + w + out[i:]
        else:
            out = out + w
    return out


def tokens_ok(en: str, zh: str) -> bool:
    return all(
        t in zh
        for t in re.findall(r"\{(?:FD|FC):[0-9A-Fa-f]{2}\}|\{WAIT_(?:CLEAR|SCROLL)\}", en)
    )


def main() -> int:
    todos = [json.loads(l) for l in MAP_TODO.read_text(encoding="utf-8").splitlines() if l.strip()]
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    n = 0
    for item in todos:
        off, en = item["off"], item["en"]
        eos = golden.find(b"\xff", off)
        if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
            continue
        zh = scrub(cache.get(en, ""))
        if not zh:
            continue
        if not tokens_ok(en, zh):
            zh = reinject(en, zh)
        if not quality_ok(en, zh) or not tokens_ok(en, zh):
            continue
        if put(data, golden, off, zh):
            n += 1
            cache[en] = zh
            if n <= 8:
                print(f"  {off:08X} {en[:40]!r} -> {zh[:40]!r}")

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print(f"recovered {n}")
    rem = sum(
        1
        for item in todos
        if bytes(data[item["off"] : golden.find(b"\xff", item["off"]) + 1])
        == golden[item["off"] : golden.find(b"\xff", item["off"]) + 1]
    )
    print(f"still same-EN map todo: {rem}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
