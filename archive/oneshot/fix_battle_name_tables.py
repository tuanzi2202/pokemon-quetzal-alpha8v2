#!/usr/bin/env python3
"""Rewrite battle name tables with fixed strides; clone moves to all lang banks; force GetMoveName→EN."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"
GLOSS = ROOT / "glossary"

# From ROM headers / GetMoveName
MOVE_BASE = 0x417D68
MOVE_STRIDE = 17
MOVE_COUNT = 850  # enough for Gen9 Quetzal list
MOVE_ES1 = 0x41BB90
MOVE_ES2 = 0x41F9B8

SPECIES_BASES = [0x40E308, 0x413038]
SPECIES_STRIDE = 13
SPECIES_COUNT = 1200  # Quetzal expanded

GET_MOVE_NAME = 0x9F0F4


def load_maps() -> tuple[dict[str, str], dict[str, str]]:
    moves = {
        r["name_en"].strip().lower(): r["name_zh"].strip()
        for r in json.loads((GLOSS / "move_list.json").read_text(encoding="utf-8"))
        if r.get("name_en") and r.get("name_zh")
    }
    # normalize keys
    extra = {}
    for k, v in list(moves.items()):
        extra[k.replace("-", " ").replace("'", "")] = v
        extra["".join(c for c in k if c.isalnum())] = v
    moves.update(extra)

    species = {
        r["name_en"].strip().lower(): r["name_zh"].strip()
        for r in json.loads((GLOSS / "simple_pokedex.json").read_text(encoding="utf-8"))
        if r.get("name_en") and r.get("name_zh")
    }
    for k, v in list(species.items()):
        species["".join(c for c in k if c.isalnum())] = v
    return moves, species


def lookup(name: str, table: dict[str, str]) -> str | None:
    n = name.strip()
    if not n or set(n) <= {"?", "-"}:
        return None
    key = n.lower()
    if key in table:
        return table[key]
    key2 = "".join(c for c in key if c.isalnum())
    if key2 in table:
        return table[key2]
    # regional
    for pref, zhpref in (
        ("alolan ", "阿罗拉"),
        ("galarian ", "伽勒尔"),
        ("hisuian ", "洗翠"),
        ("paldean ", "帕底亚"),
        ("mega ", "超级"),
        ("primal ", "原始"),
        ("gigantamax ", "超极巨"),
    ):
        if key.startswith(pref):
            base = lookup(n[len(pref) :], table)
            if base:
                return zhpref + base
    return None


def encode_slot(zh: str, stride: int) -> bytes | None:
    """Left-align like English: NAME + FF + 00 padding to stride."""
    enc, missing = encode_text_safe(zh)
    if missing:
        # still try
        pass
    if len(enc) > stride:
        # truncate chars
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > stride:
            cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        if len(enc) > stride:
            return None
    return enc + b"\x00" * (stride - len(enc))


def fill_fixed_table(
    data: bytearray,
    golden: bytes,
    base: int,
    stride: int,
    count: int,
    table: dict[str, str],
    label: str,
) -> tuple[int, int]:
    ok = miss = 0
    for i in range(count):
        off = base + i * stride
        if off + stride > len(golden):
            break
        slot = bytes(golden[off : off + stride])
        # decode until FF
        en = decode_bytes(slot + b"\xff" if 0xFF not in slot else slot)
        en = en.strip()
        if not en or set(en) <= {"?", "-"}:
            continue
        zh = lookup(en, table)
        if not zh:
            miss += 1
            continue
        blob = encode_slot(zh, stride)
        if not blob:
            miss += 1
            continue
        data[off : off + stride] = blob
        ok += 1
    print(f"{label}@{base:08X}: ok={ok} miss={miss}")
    return ok, miss


def force_get_move_name_en(data: bytearray, golden: bytes) -> None:
    """Patch GetMoveName language select to always use EN table 0x08417D68.

    Original (Thumb) roughly:
      lang&7; cmp #1 -> ES1; cmp #2 -> EN; else ES2
    We NOP the branches and force loading EN base.
    Safer approach: overwrite the two alternate base literals / branch targets
    by copying CN table onto ES banks (done separately). Here we also
    patch the immediate comparisons so every lang takes the EN path.
    """
    # Disassemble-free approach: find the three pool addresses near the function
    # and rewrite ES pointers to EN base.
    # Scan 0x9F0F4..0x9F180 for little-endian pointers to move tables.
    region = bytes(golden[GET_MOVE_NAME : GET_MOVE_NAME + 0xA0])
    en_ptr = struct.pack("<I", 0x08000000 + MOVE_BASE)
    es1_ptr = struct.pack("<I", 0x08000000 + MOVE_ES1)
    es2_ptr = struct.pack("<I", 0x08000000 + MOVE_ES2)
    patched = 0
    for needle in (es1_ptr, es2_ptr):
        idx = 0
        while True:
            j = region.find(needle, idx)
            if j < 0:
                break
            abs_off = GET_MOVE_NAME + j
            data[abs_off : abs_off + 4] = en_ptr
            patched += 1
            idx = j + 1
    print(f"GetMoveName ptr retargets={patched} (ES→EN)")


def main() -> int:
    moves, species = load_maps()
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes() if OUT.exists() else golden)

    # Restore move/species banks from golden first for clean slots
    for base in [MOVE_BASE, MOVE_ES1, MOVE_ES2]:
        size = MOVE_COUNT * MOVE_STRIDE
        data[base : base + size] = golden[base : base + size]
    for base in SPECIES_BASES:
        size = SPECIES_COUNT * SPECIES_STRIDE
        data[base : base + size] = golden[base : base + size]

    fill_fixed_table(data, golden, MOVE_BASE, MOVE_STRIDE, MOVE_COUNT, moves, "moves_en")
    # clone EN bank → ES banks (language-independent Chinese)
    size = MOVE_COUNT * MOVE_STRIDE
    data[MOVE_ES1 : MOVE_ES1 + size] = data[MOVE_BASE : MOVE_BASE + size]
    data[MOVE_ES2 : MOVE_ES2 + size] = data[MOVE_BASE : MOVE_BASE + size]
    print(f"cloned moves → ES1/ES2 ({size} bytes each)")

    for base in SPECIES_BASES:
        fill_fixed_table(data, golden, base, SPECIES_STRIDE, SPECIES_COUNT, species, "species")

    force_get_move_name_en(data, golden)

    FF = bytes([0xFF])
    # verify
    for i, lab in [(1, "Pound"), (33, "Tackle"), (10, "Scratch")]:
        off = MOVE_BASE + i * MOVE_STRIDE
        print(f"  move[{i}] {lab}: {decode_bytes(bytes(data[off : off + MOVE_STRIDE]) + FF)!r}")
    off = SPECIES_BASES[0] + 252 * SPECIES_STRIDE
    print(f"  Treecko: {decode_bytes(bytes(data[off : off + SPECIES_STRIDE]) + FF)!r}")
    off = MOVE_ES1 + 33 * MOVE_STRIDE
    print(f"  ES1 Tackle: {decode_bytes(bytes(data[off : off + MOVE_STRIDE]) + FF)!r}")

    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
