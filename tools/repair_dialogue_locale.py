#!/usr/bin/env python3
"""Apply reviewed/generated dialogue repairs to the canonical locale JSONL."""

from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path

from audit_dialogue_zh import CONTROL_RE, controls, flags_for
from localization_terms_zh import canonicalize_source_entities, canonicalize_zh
from official_names_zh import OFFICIAL_NAMES

ROOT = Path(__file__).resolve().parents[1]
DIALOGUE = ROOT / "dump" / "dialogue_ptrs.jsonl"
LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"
REPAIRS = ROOT / "locale" / "zh_CN" / "dialogue_repairs_zh.jsonl"
FAIL_REPORT = ROOT / "work" / "dialogue_repair_remaining_scan.jsonl"


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def row_offset(row: dict[str, object]) -> int:
    value = row["offset"]
    return int(value, 0) if isinstance(value, str) else int(value)


def _visible_positions(text: str) -> tuple[str, list[tuple[str, int]]]:
    plain: list[str] = []
    events: list[tuple[str, int]] = []
    cursor = 0
    for match in CONTROL_RE.finditer(text):
        plain.append(text[cursor:match.start()])
        visible = sum(len(part) for part in plain)
        events.append((match.group(0), visible))
        cursor = match.end()
    plain.append(text[cursor:])
    return "".join(plain), events


def _snap_wait_position(text: str, position: int) -> int:
    if position <= 1 or position >= len(text) - 1:
        return max(0, min(position, len(text)))
    boundaries = "。！？!?…\n"
    candidates = [
        index + 1
        for index in range(max(0, position - 8), min(len(text), position + 8))
        if text[index] in boundaries
    ]
    return min(candidates, key=lambda index: abs(index - position)) if candidates else position


def restore_control_sequence(source: str, translated: str) -> str:
    """Restore source controls while retaining aligned controls already in zh.

    SequenceMatcher anchors controls that survived machine translation. Missing
    controls are interpolated between those anchors, then WAIT controls snap to
    nearby sentence/newline boundaries. The output always has the exact source
    control sequence.
    """
    source_plain, source_events = _visible_positions(source)
    target_plain, target_events = _visible_positions(translated)
    source_tokens = [token for token, _position in source_events]
    target_tokens = [token for token, _position in target_events]
    if source_tokens == target_tokens:
        return translated
    if not source_tokens:
        return target_plain

    anchors: dict[int, int] = {}
    matcher = difflib.SequenceMatcher(a=source_tokens, b=target_tokens, autojunk=False)
    for block in matcher.get_matching_blocks():
        for delta in range(block.size):
            anchors[block.a + delta] = target_events[block.b + delta][1]

    source_length = max(1, len(source_plain))
    positions: list[int] = []
    for index, (token, source_position) in enumerate(source_events):
        if index in anchors:
            position = anchors[index]
        else:
            left = max((key for key in anchors if key < index), default=None)
            right = min((key for key in anchors if key > index), default=None)
            if left is not None and right is not None:
                left_source = source_events[left][1]
                right_source = source_events[right][1]
                span = max(1, right_source - left_source)
                fraction = (source_position - left_source) / span
                position = round(anchors[left] + fraction * (anchors[right] - anchors[left]))
            else:
                position = round((source_position / source_length) * len(target_plain))
        position = max(0, min(position, len(target_plain)))
        if token.startswith("{WAIT_"):
            position = _snap_wait_position(target_plain, position)
        if positions:
            position = max(positions[-1], position)
        positions.append(position)

    buckets: dict[int, list[str]] = {}
    for position, token in zip(positions, source_tokens):
        buckets.setdefault(position, []).append(token)
    output: list[str] = []
    for position in range(len(target_plain) + 1):
        output.extend(buckets.get(position, []))
        if position < len(target_plain):
            output.append(target_plain[position])
    return "".join(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate without writing")
    args = parser.parse_args()

    dialogue = {int(row["offset"]): str(row["en"]) for row in read_jsonl(DIALOGUE)}
    repairs = (
        {row_offset(row): row for row in read_jsonl(REPAIRS)}
        if REPAIRS.exists()
        else {}
    )
    locale = read_jsonl(LOCALE)

    stale: list[int] = []
    for offset, repair in repairs.items():
        expected = repair.get("en")
        if expected is not None and dialogue.get(offset) != str(expected):
            stale.append(offset)
    if stale:
        print("stale repair offsets:", ", ".join(hex(offset) for offset in stale[:20]))
        return 2

    changed = 0
    matched_repairs = 0
    failures: list[dict[str, object]] = []
    for row in locale:
        offset = int(row["offset"])
        source = dialogue.get(offset)
        repair = repairs.get(offset) if source is not None else None
        value = str(repair["zh"]) if repair else str(row.get("zh") or "")
        value = canonicalize_zh(value)
        english = str(row.get("en") or "")
        if value and english in OFFICIAL_NAMES:
            value = OFFICIAL_NAMES[english]
        if source is not None:
            value = restore_control_sequence(source, value)
            value = canonicalize_source_entities(source, value)
            value = canonicalize_zh(value)
            flags, _details = flags_for(source, value)
            if flags:
                failures.append({"offset": offset, "en": source, "zh": value, "flags": flags})
        if value != str(row.get("zh") or ""):
            row["zh"] = value
            changed += 1
        if repair:
            matched_repairs += 1

    print(json.dumps({
        "dialogue_rows": len(dialogue),
        "repair_rows": len(repairs),
        "matched_repairs": matched_repairs,
        "changed": changed,
        "remaining_issues": len(failures),
    }, ensure_ascii=False))
    if failures:
        FAIL_REPORT.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in failures),
            encoding="utf-8",
            newline="\n",
        )
        for failure in failures[:20]:
            print(hex(int(failure["offset"])), ",".join(failure["flags"]))
        return 3
    if not args.check:
        LOCALE.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in locale),
            encoding="utf-8",
            newline="\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
