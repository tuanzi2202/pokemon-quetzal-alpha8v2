#!/usr/bin/env python3
"""Deterministically patch species, move, and ability name tables."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
ROM = ROOT / "work" / "cn_build.gba"
GLOSSARY = ROOT / "glossary"

SPECIES_BASES = (0x40E308, 0x413038)
SPECIES_STRIDE = 13
SPECIES_COUNT = 1200
MOVE_BASES = (0x417D68, 0x41BB90, 0x41F9B8)
MOVE_STRIDE = 17
MOVE_COUNT = 850
ABILITY_START = 0x426FE0
ABILITY_END = 0x429F00

MOVE_ALIASES = {
    "Hyprspace Hole": "Hyperspace Hole",
    "Floral Healng": "Floral Healing",
    "Jungle Healng": "Jungle Healing",
    "Double Slap": "DoubleSlap",
    "Vise Grip": "Vice Grip",
    "Thunder Punch": "ThunderPunch",
    "Poison Powder": "PoisonPowder",
    "Thunder Shock": "ThunderShock",
    "Bubble Beam": "BubbleBeam",
    "Sonic Boom": "SonicBoom",
    "Self-Destruct": "SelfDestruct",
    "Hi Jump Kick": "High Jump Kick",
    "Feint Attack": "Faint Attack",
    "Smelling Salts": "SmellingSalt",
    "Ancient Power": "AncientPower",
    "Extreme Speed": "ExtremeSpeed",
    "Dragon Breath": "DragonBreath",
    "Dynamic Punch": "DynamicPunch",
}

NAME_OVERRIDES = {
    "Porygon2": "多边兽2",
    "Porygon-Z": "多边兽乙型",
    "Mimikyu": "谜拟Q",
    "Tapu Koko": "卡璞鸣鸣",
    "Tapu Lele": "卡璞蝶蝶",
    "Tapu Bulu": "卡璞哞哞",
    "Tapu Fini": "卡璞鳍鳍",
    "Type: Null": "属性:空",
    "Conversion 2": "纹理2",
    "V-create": "V热焰",
    "Darkest Lariat": "DD金勾臂",
    "Ceaseless Edge": "秘剑千重涛",
    "RKS System": "AR系统",
    "Costar": "同台演",
}


def normalized(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return "".join(ch.lower() for ch in text if ch.isalnum())


def load_map(filename: str) -> dict[str, str]:
    rows = json.loads((GLOSSARY / filename).read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    compact: dict[str, str] = {}
    for row in rows:
        en = str(row.get("name_en") or "").strip()
        zh = str(row.get("name_zh") or "").strip()
        if not en or not zh:
            continue
        zh = unicodedata.normalize("NFKC", zh).replace("・", "").replace("·", "")
        result[en.lower()] = zh
        compact.setdefault(normalized(en), zh)
    result.update({f"@{key}": value for key, value in compact.items()})
    return result


def lookup(name: str, table: dict[str, str]) -> str | None:
    if name in NAME_OVERRIDES:
        return NAME_OVERRIDES[name]
    hit = table.get(name.lower()) or table.get("@" + normalized(name))
    if hit:
        return hit
    alias = MOVE_ALIASES.get(name)
    if alias:
        name = alias
    hit = table.get(name.lower()) or table.get("@" + normalized(name))
    if hit:
        return hit
    prefixes = (
        ("Alolan ", "阿罗拉"), ("Galarian ", "伽勒尔"),
        ("Hisuian ", "洗翠"), ("Paldean ", "帕底亚"),
        ("Mega ", "超级"), ("Primal ", "原始"),
        ("Gigantamax ", "超极巨"), ("Shadow ", "暗影"),
    )
    for prefix, zh_prefix in prefixes:
        if name.startswith(prefix):
            base = lookup(name[len(prefix):], table)
            if base:
                return zh_prefix + base
    return None


def encode_slot(zh: str, stride: int, label: str) -> bytes:
    zh = unicodedata.normalize("NFKC", zh).replace("・", "").replace("·", "")
    encoded, missing = encode_text_safe(zh)
    if missing:
        chars = ", ".join(f"{ch!r}/U+{ord(ch):04X}" for ch in missing)
        raise ValueError(f"{label}: missing glyphs {chars}")
    if len(encoded) > stride:
        raise ValueError(f"{label}: need={len(encoded)} stride={stride} text={zh!r}")
    return encoded + b"\x00" * (stride - len(encoded))


def fill_fixed(
    data: bytearray,
    golden: bytes,
    base: int,
    stride: int,
    count: int,
    table: dict[str, str],
    label: str,
) -> tuple[int, int]:
    written = nonempty = 0
    for index in range(count):
        off = base + index * stride
        slot = golden[off:off + stride]
        if 0xFF not in slot:
            continue
        en = decode_bytes(slot).strip()
        if not en or set(en) <= {"?", "-", " "}:
            continue
        nonempty += 1
        if label.startswith("species") and index == 772 and "Cero" in en:
            zh = NAME_OVERRIDES["Type: Null"]
        else:
            zh = lookup(en, table)
        if zh is None:
            raise KeyError(f"{label}[{index}] {off:08X}: unmapped {en!r}")
        data[off:off + stride] = encode_slot(zh, stride, f"{label}[{index}] {en}")
        written += 1
    print(f"{label}: written={written} nonempty={nonempty}")
    return written, nonempty


def walk_strings(rom: bytes, start: int, end: int) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    off = start
    while off < end:
        eos = rom.find(b"\xff", off, end)
        if eos < 0:
            break
        if eos - off <= 48:
            rows.append((off, eos + 1, decode_bytes(rom[off:eos + 1]).strip()))
        off = eos + 1
    return rows


def fill_abilities(
    data: bytearray, golden: bytes, table: dict[str, str]
) -> tuple[int, int]:
    written = matched = 0
    for off, end, en in walk_strings(golden, ABILITY_START, ABILITY_END):
        zh = lookup(en, table)
        if zh is None:
            continue
        matched += 1
        capacity = end - off
        encoded = encode_slot(zh, capacity, f"ability {off:08X} {en}")
        data[off:end] = b"\x00" * (capacity - len(encoded.rstrip(b"\x00"))) + encoded.rstrip(b"\x00")
        written += 1
    if matched != 314:
        raise RuntimeError(f"expected 314 mapped ability strings, found {matched}")
    print(f"abilities: written={written} matched={matched}")
    return written, matched


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(ROM.read_bytes())
    if len(data) != len(golden):
        raise ValueError("working ROM does not match golden ROM size")
    species = load_map("simple_pokedex.json")
    moves = load_map("move_list.json")
    abilities = load_map("ability_list.json")

    for bank, base in enumerate(SPECIES_BASES):
        fill_fixed(
            data, golden, base, SPECIES_STRIDE, SPECIES_COUNT,
            species, f"species-{bank}",
        )
    fill_fixed(data, golden, MOVE_BASES[0], MOVE_STRIDE, MOVE_COUNT, moves, "moves")
    size = MOVE_STRIDE * MOVE_COUNT
    for base in MOVE_BASES[1:]:
        data[base:base + size] = data[MOVE_BASES[0]:MOVE_BASES[0] + size]
    print(f"moves: cloned {size} bytes to {len(MOVE_BASES) - 1} language banks")
    fill_abilities(data, golden, abilities)

    ROM.write_bytes(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
