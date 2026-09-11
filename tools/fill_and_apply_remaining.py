#!/usr/bin/env python3
"""Inplace-apply locale ZH that already exists; optionally MT the gaps.

Usage:
  python tools/fill_and_apply_remaining.py apply     # apply existing good ZH
  python tools/fill_and_apply_remaining.py mt         # translate missing, update locale
  python tools/fill_and_apply_remaining.py all        # mt then apply
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chs_encode import encode_text_safe  # noqa: E402
from official_names_zh import OFFICIAL_NAMES  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"
LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"
CACHE = ROOT / "work" / "gtrans_cache.json"
# FC pool may be patched inplace by fill_battle_names_zh / fill_short_en.
# Do NOT reloc strings here (apply_text blacklist). Inplace apply is OK.
SKIP_RANGES: list[tuple[int, int]] = []

SCRUB = [
    (r"poksammon", "宝可梦"),
    (r"poksamdex", "宝可梦图鉴"),
    (r"poksamn", "宝可梦"),
    (r"pok[eé]?mon\s*dex", "宝可梦图鉴"),
    (r"pok[eé]?mon\s*nav(?:igator)?", "宝可梦导航器"),
    (r"pok[eé]?mon\s*center", "宝可梦中心"),
    (r"pok[eé]?mon\s*league", "宝可梦联盟"),
    (r"pok[eé]?mon", "宝可梦"),
    (r"pok[eé]?dex", "宝可梦图鉴"),
    (r"pok[eé]?nav", "宝可梦导航器"),
    (r"\[\[10\]\]", "{WAIT_CLEAR}"),
    (r"\[\[0\]\]", "{WAIT_CLEAR}"),
    (r"\[\[1\]\]", "{WAIT_SCROLL}"),
    (r"\[\[2\]\]", "{WAIT_CLEAR}"),
    (r"\[\[3\]\]", "{WAIT_CLEAR}"),
    (r"\[10\]", "{WAIT_CLEAR}"),
    (r"\[1\]", "{WAIT_SCROLL}"),
    (r"\[2\]", "{WAIT_CLEAR}"),
    (r"TEAM AQUA", "水舰队"),
    (r"TEAM MAGMA", "熔岩队"),
    (r"PROF\. BIRCH", "小田卷博士"),
    (r"PROF\. COZMO", "科兹莫博士"),
    (r"MR\. BRINEY", "哈奇老人"),
    (r"RUNNING SHOES", "跑步鞋"),
    (r"BATTLE FRONTIER", "对战开拓区"),
    (r"BATTLE TENT", "对战帐篷"),
    (r"MOVE DELETER", "忘却爷爷"),
]


def has_cjk(t: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in t)


def has_latin(t: str, n: int = 5) -> bool:
    return bool(re.search(rf"[A-Za-z]{{{n},}}", t))


def scrub(zh: str) -> str:
    out = zh or ""
    for a, b in SCRUB:
        out = re.sub(a, b, out, flags=re.IGNORECASE)
    # truncated POKéMON dump prefix
    out = re.sub(r"(^|[\n{])MON(?=[ :，,!.。！？\n{])", r"\1宝可梦", out)
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\ufffd"):
        out = out.replace(ch, "")
    out = re.sub(r"(?:\.\.\.|…|……|\u2026){2,}", "……", out)
    out = re.sub(r"(?:…\s*){2,}", "……", out)
    return out


def in_skip(off: int) -> bool:
    return any(a <= off < b for a, b in SKIP_RANGES)


def quality_ok(en: str, zh: str) -> bool:
    if not zh or zh == en:
        return False
    if not has_cjk(zh):
        return False
    # Ignore {FD:00}/{WAIT_*} control tokens when scoring Latin bleed
    plain = re.sub(r"\{[A-Z0-9_]+(?::[0-9A-Fa-f]+)?\}", "", zh)
    latin = sum(1 for c in plain if c.isascii() and c.isalpha())
    cjk = sum(1 for c in zh if "\u4e00" <= c <= "\u9fff")
    if len(en) > 30 and cjk < 2:
        return False
    if latin > max(cjk * 2, 12) and cjk < 4:
        return False
    return True


def looks_full_line(en: str) -> bool:
    """Accept real dialogue; allow truncated POKéMON dump prefix 'MON'."""
    if not en or len(en) < 6:
        return False
    if sum(c.isalpha() for c in en) < 6:
        return False
    # junk / mid-sentence fragments (keep MON — dump truncates POKéMON)
    if en.startswith((" ", "\t", "t ", "n ", "ou ", "are ", "ay!", "ld ", "ve ")):
        return False
    if en[:1].islower() and not en.startswith(("i ", "i'", "it ", "it's", "a ", "an ", "the ")):
        if "{WAIT_" not in en and "\n" not in en and len(en) < 24:
            return False
    return True


def translate_one(en: str, engine: str) -> str | None:
    try:
        import translators as ts
    except ImportError:
        return None
    toks: list[str] = []

    def repl(m: re.Match) -> str:
        toks.append(m.group(0))
        return f"[[T{len(toks) - 1}]]"

    # Dump often loses POKé → leading "MON …"
    src = ("POKEMON" + en[3:]) if en.startswith("MON") else en
    protected = re.sub(r"\{[A-Z0-9_]+(?::[0-9A-Fa-f]+)?\}", repl, src)
    try:
        out = ts.translate_text(
            protected[:900],
            translator=engine,
            from_language="en",
            to_language="zh",
        )
    except Exception:
        return None
    zh = str(out or "").strip()
    for i, t in enumerate(toks):
        for form in (f"[[T{i}]]", f"[T{i}]", f"【T{i}】"):
            zh = zh.replace(form, t)
    zh = scrub(zh)
    return zh if quality_ok(en, zh) else None


def inplace(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    capacity = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if len(enc) > capacity:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > capacity:
            if "{WAIT_" in cut:
                cut = cut.rsplit("{WAIT_", 1)[0]
                if cut.endswith("}"):
                    pass
            else:
                cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        if len(enc) > capacity:
            return "too_long"
    data[off : off + capacity] = enc + b"\x00" * (capacity - len(enc))
    return "ok"


def load_rows() -> list[dict]:
    return [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]


def save_rows(rows: list[dict]) -> None:
    LOCALE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def do_mt() -> int:
    cache: dict[str, str] = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    rows = load_rows()
    need: list[str] = []
    seen: set[str] = set()
    for r in rows:
        en = r.get("en") or ""
        zh = scrub(r.get("zh") or "")
        if OFFICIAL_NAMES.get(en):
            r["zh"] = OFFICIAL_NAMES[en]
            continue
        if en in cache and quality_ok(en, scrub(cache[en])):
            if not quality_ok(en, zh):
                r["zh"] = scrub(cache[en])
            continue
        if quality_ok(en, zh):
            r["zh"] = zh
            continue
        if looks_full_line(en) and en not in seen:
            seen.add(en)
            need.append(en)

    print(f"need_mt unique={len(need)}", flush=True)
    engines = ["bing", "alibaba", "youdao"]
    ok = 0
    for i, en in enumerate(need):
        zh = None
        for eng in engines:
            zh = translate_one(en, eng)
            if zh:
                break
            time.sleep(0.12)
        if zh:
            cache[en] = zh
            ok += 1
        if (i + 1) % 20 == 0:
            print(f"  mt {i+1}/{len(need)} ok={ok}", flush=True)
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        time.sleep(0.06)

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    for r in rows:
        en = r.get("en") or ""
        if OFFICIAL_NAMES.get(en):
            r["zh"] = OFFICIAL_NAMES[en]
        elif en in cache and quality_ok(en, scrub(cache[en])):
            r["zh"] = scrub(cache[en])
        else:
            r["zh"] = scrub(r.get("zh") or "")
    save_rows(rows)
    print(f"mt_done ok={ok} cache={len(cache)}")
    return 0


def do_apply() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes() if OUT.exists() else ROM.read_bytes())
    cache: dict[str, str] = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))

    rows = load_rows()
    # refresh weak from cache
    for r in rows:
        en = r.get("en") or ""
        zh = scrub(r.get("zh") or "")
        if OFFICIAL_NAMES.get(en):
            zh = OFFICIAL_NAMES[en]
        elif (not quality_ok(en, zh)) and en in cache and quality_ok(en, scrub(cache[en])):
            zh = scrub(cache[en])
        r["zh"] = zh
    save_rows(rows)

    n_ok = n_long = n_bad = 0
    for r in rows:
        off = int(r["offset"])
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        if in_skip(off):
            continue
        if not quality_ok(en, zh):
            n_bad += 1
            continue
        st = inplace(data, golden, off, zh)
        if st == "ok":
            n_ok += 1
        elif st == "too_long":
            n_long += 1
        if n_ok and n_ok % 800 == 0:
            print(f"  applied {n_ok}...", flush=True)

    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print(f"applied={n_ok} too_long={n_long} bad_zh={n_bad}")
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "apply"
    if mode == "mt":
        return do_mt()
    if mode == "apply":
        return do_apply()
    if mode == "all":
        do_mt()
        return do_apply()
    print("usage: apply | mt | all")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
