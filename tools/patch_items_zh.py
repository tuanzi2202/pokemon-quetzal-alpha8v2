#!/usr/bin/env python3
"""Apply committed Simplified Chinese item names and descriptions.

All writes are in-place against the verified Quetzal 0.8.4 English layout.
Names remain right-aligned in their original records; descriptions terminate
early and zero-fill the unused tail. No network service or translation cache
is consulted during a normal build.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe, load_charmap  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
ROM = ROOT / "work" / "cn_build.gba"
NAME_GLOSSARY = ROOT / "glossary" / "item_names_zh.json"
DESC_GLOSSARY = ROOT / "glossary" / "item_descriptions_zh.json"
EXPECTED_NAMES = 827
EXPECTED_DESCRIPTIONS = 800


def decode_chs(raw: bytes, table: dict[bytes, str]) -> str:
    parts: list[str] = []
    i = 0
    while i < len(raw):
        if raw[i] == 0xFF:
            break
        if raw[i] == 0xFE:
            parts.append("\n")
            i += 1
            continue
        if i + 1 < len(raw) and raw[i:i + 2] in table:
            two, one = table[raw[i:i + 2]], table.get(raw[i:i + 1])
            if one and one.isascii() and not two.isascii():
                parts.append(one)
                i += 1
            else:
                parts.append(two)
                i += 2
            continue
        parts.append(table.get(raw[i:i + 1], "?"))
        i += 1
    return "".join(parts).strip()


def load_rows(path: Path, expected: int) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("items")
    if not isinstance(rows, list) or len(rows) != expected:
        found = len(rows) if isinstance(rows, list) else "invalid"
        raise RuntimeError(f"{path.name}: expected {expected} rows, found {found}")
    return rows


def encode_checked(zh: str, capacity: int, label: str) -> bytes:
    encoded, missing = encode_text_safe(zh)
    if missing:
        chars = ", ".join(f"{ch!r}/U+{ord(ch):04X}" for ch in missing)
        raise ValueError(f"{label}: missing glyphs: {chars}")
    if len(encoded) > capacity:
        raise ValueError(f"{label}: need {len(encoded)} bytes, capacity={capacity}")
    return encoded


def verify_source(golden: bytes, off: int, en: str, label: str) -> int:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        raise ValueError(f"{label}: source terminator not found")
    actual = decode_bytes(golden[off:eos + 1]).strip()
    if actual != en:
        raise ValueError(f"{label}: source mismatch: {actual!r} != {en!r}")
    return eos + 1


def main() -> int:
    if not GOLDEN.exists() or not ROM.exists():
        print("missing golden/en_0.8.4.gba or work/cn_build.gba", file=sys.stderr)
        return 1
    golden = GOLDEN.read_bytes()
    data = bytearray(ROM.read_bytes())
    if len(data) != len(golden):
        raise ValueError(f"ROM size mismatch: {len(data)} != {len(golden)}")

    name_rows = load_rows(NAME_GLOSSARY, EXPECTED_NAMES)
    desc_rows = load_rows(DESC_GLOSSARY, EXPECTED_DESCRIPTIONS)

    for row in name_rows:
        off, en, zh = int(row["offset"]), str(row["en"]), str(row["zh"])
        end = verify_source(golden, off, en, f"name {off:08X}")
        capacity = end - off
        encoded = encode_checked(zh, capacity, f"name {off:08X} {en}")
        data[off:end] = b"\x00" * (capacity - len(encoded)) + encoded

    for row in desc_rows:
        off, en, zh = int(row["offset"]), str(row["en"]), str(row["zh"])
        end = verify_source(golden, off, en, f"description {off:08X}")
        capacity = end - off
        encoded = encode_checked(zh, capacity, f"description {off:08X}")
        data[off:end] = encoded + b"\x00" * (capacity - len(encoded))

    _, decode_table = load_charmap()
    bad_names: list[str] = []
    for row in name_rows:
        off = int(row["offset"])
        end = golden.find(b"\xff", off) + 1
        zh = decode_chs(bytes(data[off:end]), decode_table)
        if sum("\u3400" <= ch <= "\u9fff" for ch in zh) < 1 or "?" in zh:
            bad_names.append(f"{off:08X}:{zh}")

    bad_descs: list[str] = []
    for row in desc_rows:
        off = int(row["offset"])
        end = golden.find(b"\xff", off) + 1
        zh = decode_chs(bytes(data[off:end]), decode_table)
        check = re.sub(r"(?i)(HP|PP|IV|EV|EXP|TM|HM)", "", zh)
        if (
            sum("\u3400" <= ch <= "\u9fff" for ch in zh) < 4
            or re.search(r"[A-Za-z]{2,}", check)
            or "?" in zh
        ):
            bad_descs.append(f"{off:08X}:{zh}")
    if bad_names or bad_descs:
        raise ValueError(
            f"post-write verification failed: names={bad_names[:3]} "
            f"descriptions={bad_descs[:3]}"
        )

    ROM.write_bytes(data)
    print(json.dumps({
        "item_names_written": len(name_rows),
        "item_descriptions_written": len(desc_rows),
        "untranslated_names": len(bad_names),
        "incomplete_descriptions": len(bad_descs),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
