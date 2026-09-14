#!/usr/bin/env python3
"""Import the reviewed Easy Chat glossary from pokeemerald-expansion Chinese."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUTPUT = ROOT / "locale" / "zh_CN" / "easy_chat_zh.jsonl"
DEFAULT_REFERENCE = ROOT / "work" / "reference_pokeemerald_zh"

# The Quetzal 0.8.4 ROM keeps the original Emerald Easy Chat word arrays at
# fixed addresses. Shorter strings are absent from dump/all_en.jsonl, so the
# complete table has to be walked by group count rather than dump heuristics.
GROUP_LAYOUT: tuple[tuple[str, int, int], ...] = (
    ("trainer", 0x00FC2FC8, 27),
    ("status", 0x00FC31CC, 109),
    ("battle", 0x00FC3AD4, 63),
    ("greetings", 0x00FC3F9C, 42),
    ("people", 0x00FC42E0, 75),
    ("voices", 0x00FC4828, 63),
    ("speech", 0x00FC4C80, 60),
    ("endings", 0x00FC50F0, 69),
    ("feelings", 0x00FC55A4, 69),
    ("conditions", 0x00FC5AC4, 69),
    ("actions", 0x00FC5FF0, 78),
    ("lifestyle", 0x00FC6594, 45),
    ("hobbies", 0x00FC68F8, 54),
    ("time", 0x00FC6CFC, 45),
    ("misc", 0x00FC704C, 42),
    ("adjectives", 0x00FC7350, 36),
    ("events", 0x00FC7620, 29),
    ("trendy_saying", 0x00FC7B20, 33),
)

TEXT_RE = re.compile(r'\.text\s*=\s*COMPOUND_STRING\("([^"\\]*(?:\\.[^"\\]*)*)"\)')

def extract_reference_words(reference: Path, group: str) -> list[str]:
    path = reference / "src" / "data" / "easy_chat" / f"easy_chat_group_{group}.h"
    text = path.read_text(encoding="utf-8")
    escapes = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"'}
    return [
        re.sub(r"\\(.)", lambda match: escapes.get(match.group(1), match.group(0)), value)
        for value in TEXT_RE.findall(text)
    ]


def read_rom_words(rom: bytes, start: int, count: int) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    offset = start
    for _index in range(count):
        end = rom.find(b"\xff", offset)
        if end < 0:
            raise ValueError(f"unterminated Easy Chat word at {offset:#x}")
        slot = end - offset + 1
        rows.append((offset, slot, decode_bytes(rom[offset:end + 1], max_len=slot)))
        offset = end + 1
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    rom = GOLDEN.read_bytes()
    output: list[dict[str, object]] = []
    failures: list[str] = []
    overflows = 0
    for group, start, count in GROUP_LAYOUT:
        zh_words = extract_reference_words(args.reference, group)
        en_words = read_rom_words(rom, start, count)
        if len(zh_words) != count:
            failures.append(f"{group}: expected {count} reference words, got {len(zh_words)}")
            continue
        for index, ((offset, slot, en), zh) in enumerate(zip(en_words, zh_words)):
            encoded, missing = encode_text_safe(zh)
            if missing:
                failures.append(f"{group}[{index}] {en!r}: missing glyphs {sorted(set(missing))}")
            if len(encoded) > slot:
                overflows += 1
            output.append({
                "group": group,
                "index": index,
                "offset": offset,
                "slot": slot,
                "en": en,
                "zh": zh,
                "source": "rh-hideout-chinese/pokeemerald-expansion",
            })

    if failures:
        print("\n".join(failures))
        print(json.dumps({"rows": len(output), "failures": len(failures)}, ensure_ascii=False))
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "rows": len(output),
        "groups": len(GROUP_LAYOUT),
        "relocated_overflows": overflows,
        "failures": 0,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
