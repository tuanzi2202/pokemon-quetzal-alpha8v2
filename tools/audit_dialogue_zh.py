#!/usr/bin/env python3
"""Audit pointer-backed dialogue translations for high-confidence defects."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from localization_terms_zh import (  # noqa: E402
    BAD_ZH_REPLACEMENTS,
    PERSON_NAMES,
    location_present,
    mentioned_locations,
    source_mentions,
)
from official_names_zh import OFFICIAL_NAMES  # noqa: E402

DIALOGUE = ROOT / "dump" / "dialogue_ptrs.jsonl"
LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"
REPORT = ROOT / "work" / "remaining_dialogue_scan.jsonl"
TERMS_REPORT = ROOT / "work" / "remaining_locale_terms_scan.jsonl"

CONTROL_RE = re.compile(
    r"\{(?:WAIT_SCROLL|WAIT_CLEAR|F[CD9]:[0-9A-Fa-f]{2}|[0-9A-Fa-f]{2})\}"
)
TOKEN_RE = re.compile(r"\{[^}]+\}")
LATIN_RE = re.compile(r"[A-Za-z]{2,}")
RAW_GARBAGE_RE = re.compile(
    r"\[[0-9A-Fa-f]{2}\]|\{(?:MN|PK|PO|KE|BL|OC|K|Lv|er)\}|"
    r"\{_\}|\[\(\)\]|\?\d+\?|\[\[|\]\]|"
    r"\[(?:译文|参考译文|中文译文|qh|au:?)\]?|<s:\d+>"
)
BAD_TERMS_RE = re.compile(
    "|".join(re.escape(old) for old, _new in BAD_ZH_REPLACEMENTS)
    + r"|(?<!朱)红色宝珠|(?<!靛)蓝色宝珠|斯莱特|罗斯伯|彼得堡|杜弗|\ufffd|Ã|Â",
    re.IGNORECASE,
)
ALLOWED_LATIN = {
    "A", "B", "L", "R", "HP", "PP", "TM", "HM", "EXP", "EV", "IV",
    "NPC", "RTC", "PC", "TV", "BP", "GBA", "ID", "NO", "OK", "LV",
}


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def controls(text: str) -> list[str]:
    return CONTROL_RE.findall(text or "")


def latin_words(text: str) -> list[str]:
    plain = TOKEN_RE.sub(" ", text or "")
    return [word for word in LATIN_RE.findall(plain) if word.upper() not in ALLOWED_LATIN]


def flags_for(en: str, zh: str) -> tuple[list[str], dict[str, object]]:
    flags: list[str] = []
    details: dict[str, object] = {}
    words = latin_words(zh)
    has_cjk = any("\u3400" <= char <= "\u9fff" for char in zh)
    if not zh or zh == en or (words and not has_cjk):
        flags.append("untranslated")
    if words and has_cjk:
        flags.append("mixed_latin")
        details["latin"] = words
    if controls(en) != controls(zh):
        flags.append("control_mismatch")
        details["en_controls"] = controls(en)
        details["zh_controls"] = controls(zh)
    if BAD_TERMS_RE.search(zh):
        flags.append("bad_terms")
    if RAW_GARBAGE_RE.search(zh):
        flags.append("raw_garbage")
    _, missing = encode_text_safe(zh)
    if missing:
        flags.append("missing_glyph")
        details["missing"] = sorted(set(missing))
    return flags, details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--fail-on-issues", action="store_true")
    args = parser.parse_args()

    dialogue = read_jsonl(DIALOGUE)
    locale = {int(row["offset"]): row for row in read_jsonl(LOCALE)}
    issues: list[dict[str, object]] = []
    term_issues: list[dict[str, object]] = []
    locale_missing_glyphs: list[dict[str, object]] = []
    official_mismatches: list[dict[str, object]] = []
    dialogue_entity_mismatches: list[dict[str, object]] = []
    dialogue_location_mismatches: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    matched = 0
    for row in dialogue:
        offset = int(row["offset"])
        translated = locale.get(offset)
        if translated is None:
            flags, details = ["missing_locale"], {}
            zh = ""
        else:
            matched += 1
            zh = str(translated.get("zh") or "")
            flags, details = flags_for(str(row.get("en") or ""), zh)
        if not flags:
            pass
        else:
            counts.update(set(flags))
            issues.append({
                "offset": offset,
                "en": row.get("en") or "",
                "zh": zh,
                "flags": flags,
                **details,
            })
        en = str(row.get("en") or "")
        for key in PERSON_NAMES:
            expected = OFFICIAL_NAMES[key]
            if source_mentions(en, key) and expected not in zh:
                dialogue_entity_mismatches.append({
                    "offset": offset,
                    "key": key,
                    "expected": expected,
                    "en": en,
                    "zh": zh,
                })
        for key in mentioned_locations(en):
            if not location_present(key, zh):
                dialogue_location_mismatches.append({
                    "offset": offset,
                    "key": key,
                    "en": en,
                    "zh": zh,
                })

    for row in locale.values():
        zh = str(row.get("zh") or "")
        _, missing = encode_text_safe(zh)
        if missing:
            locale_missing_glyphs.append({
                "offset": int(row["offset"]),
                "en": row.get("en") or "",
                "zh": zh,
                "missing": sorted(set(missing)),
            })
        matches = sorted(set(match.group(0) for match in BAD_TERMS_RE.finditer(zh)))
        if matches:
            term_issues.append({
                "offset": int(row["offset"]),
                "en": row.get("en") or "",
                "zh": zh,
                "matches": matches,
            })
        en = str(row.get("en") or "")
        expected = OFFICIAL_NAMES.get(en)
        if zh and expected is not None and zh != expected:
            official_mismatches.append({
                "offset": int(row["offset"]),
                "en": en,
                "zh": zh,
                "expected": expected,
            })

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in issues),
        encoding="utf-8",
        newline="\n",
    )
    TERMS_REPORT.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n"
            for row in [
                *(dict(row, issue_type="bad_term") for row in term_issues),
                *(dict(row, issue_type="official_exact") for row in official_mismatches),
                *(dict(row, issue_type="person") for row in dialogue_entity_mismatches),
                *(dict(row, issue_type="location") for row in dialogue_location_mismatches),
                *(dict(row, issue_type="missing_glyph") for row in locale_missing_glyphs),
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    summary = {
        "dialogue_rows": len(dialogue),
        "matched_locale": matched,
        "issue_rows": len(issues),
        "flags": dict(sorted(counts.items())),
        "locale_bad_term_rows": len(term_issues),
        "locale_missing_glyph_rows": len(locale_missing_glyphs),
        "official_exact_mismatches": len(official_mismatches),
        "dialogue_entity_mismatches": len(dialogue_entity_mismatches),
        "dialogue_location_mismatches": len(dialogue_location_mismatches),
        "report": str(args.report),
    }
    print(json.dumps(summary, ensure_ascii=False))
    if args.fail_on_issues and (
        issues or term_issues or locale_missing_glyphs or official_mismatches or dialogue_entity_mismatches
        or dialogue_location_mismatches
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
