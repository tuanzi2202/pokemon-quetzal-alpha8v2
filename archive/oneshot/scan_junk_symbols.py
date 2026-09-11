#!/usr/bin/env python3
"""Scan locale + ROM CN for garbled / odd symbols."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_locale_zh import is_junk_en  # noqa: E402
from fill_and_apply_remaining import LOCALE, quality_ok  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

ZW = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff\u2060]")
BOX = re.compile(r"[\u2500-\u257F\u2580-\u259F]")
PUA = re.compile(r"[\ue000-\uf8ff]")
ODD = re.compile(r"[□■◆●★☆※〓�]|[|]{2,}|\${2,}|@{2,}|&{2,}|#{2,}|\*{3,}|~{3,}|={3,}|_{3,}|`{2,}")
MOJI = re.compile(r"[ÃÂÅÆÐÑØÞßæ]")
QRUN = re.compile(r"[?]{3,}|？{3,}|！{4,}|!{4,}")
LATIN = re.compile(r"[A-Za-z]{6,}")
POK = re.compile(r"(?i)pok[eé]?mon|(^|\n)MON[ :]")
ELLIP = re.compile(r"(?:\.\s*){4,}|(?:…\s*){4,}|……{2,}")
BAD_MIX = re.compile(r"[\u4e00-\u9fff].{0,8}[A-Za-z]{5,}|[A-Za-z]{5,}.{0,8}[\u4e00-\u9fff]")


def main() -> int:
    rows = [json.loads(l) for l in LOCALE.open(encoding="utf-8") if l.strip()]
    golden = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()
    cn = (ROOT / "out" / "quetzal_084_cn.gba").read_bytes()

    cats: Counter[str] = Counter()
    samples: dict[str, list] = {k: [] for k in [
        "repl", "zwsp", "box", "pua", "odd_punct", "mojibake", "qmark_run",
        "pokemon", "latin_spam", "ellip_spam", "ctrl", "rom_weird",
    ]}

    def add(cat: str, msg) -> None:
        cats[cat] += 1
        if len(samples[cat]) < 8:
            samples[cat].append(msg)

    for r in rows:
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        off = int(r["offset"])
        if is_junk_en(en) or not zh:
            continue
        if "\ufffd" in zh:
            add("repl", (off, zh[:100]))
        if ZW.search(zh):
            add("zwsp", (off, repr(zh[:80])))
        if BOX.search(zh):
            add("box", (off, zh[:100]))
        if PUA.search(zh):
            add("pua", (off, zh[:100]))
        if ODD.search(zh):
            add("odd_punct", (off, zh[:100]))
        if MOJI.search(zh):
            add("mojibake", (off, zh[:100]))
        if QRUN.search(zh):
            add("qmark_run", (off, zh[:100]))
        if POK.search(zh):
            add("pokemon", (off, zh[:100]))
        if ELLIP.search(zh):
            add("ellip_spam", (off, zh[:100]))
        # non-printable
        for ch in zh:
            o = ord(ch)
            if ch not in "\n\t" and o < 32:
                add("ctrl", (off, repr(zh[:80])))
                break
        plain = re.sub(r"\{[^}]+\}", "", zh)
        if any("\u4e00" <= c <= "\u9fff" for c in plain):
            hits = [x for x in LATIN.findall(plain) if x.lower() not in {
                "lv", "hp", "pp", "exp", "tm", "hm", "gps", "npc", "wifi", "ok"
            }]
            if hits:
                add("latin_spam", (off, zh[:110], hits[:4]))

        if quality_ok(en, zh):
            eos = golden.find(b"\xff", off)
            if 0 < eos - off <= 500:
                tc = decode_bytes(cn[off : eos + 1])
                if "\ufffd" in tc or BOX.search(tc) or POK.search(tc) or ODD.search(tc):
                    add("rom_weird", (off, tc[:100]))

    print("=== COUNTS ===")
    for k, v in cats.most_common():
        print(f"{k}: {v}")
    if not cats:
        print("(none)")
    print("=== SAMPLES ===")
    for k, items in samples.items():
        if not items:
            continue
        print(f"--- {k} ---")
        for s in items:
            print(s)
    # write report
    report = ROOT / "work" / "junk_scan_report.json"
    report.write_text(
        json.dumps({"counts": dict(cats), "samples": samples}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("wrote", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
