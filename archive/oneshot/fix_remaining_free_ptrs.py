#!/usr/bin/env python3
"""Restore remaining free-space pointer retargets (same class as Birch/PC bugs)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"


def u32(b: bytes | bytearray, o: int) -> int:
    return int.from_bytes(b[o : o + 4], "little")


def is_free(p: int) -> bool:
    return 0x09DC0000 <= p <= 0x09FFFFFF


def looks_ptr(p: int) -> bool:
    return 0x08000000 <= p <= 0x09FFFFFF


def ptr_neighbors(golden: bytes, i: int, window: int = 5) -> int:
    n = 0
    for k in range(-window, window + 1):
        j = i + k * 4
        if j < 0 or j + 4 > len(golden):
            continue
        if looks_ptr(u32(golden, j)):
            n += 1
    return n


def restore_free_retargets(
    data: bytearray,
    golden: bytes,
    start: int,
    end: int,
    *,
    min_neighbors: int,
) -> int:
    n = 0
    end = min(end, len(data) - 3)
    for i in range(start, end, 4):
        p, pg = u32(data, i), u32(golden, i)
        if p == pg:
            continue
        if not (is_free(p) and looks_ptr(pg)):
            continue
        if ptr_neighbors(golden, i) < min_neighbors:
            continue
        data[i : i + 4] = golden[i : i + 4]
        n += 1
    return n


def put(data: bytearray, golden: bytes, off: int, zh: str) -> None:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return
    cap = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    if len(body) + 1 > cap:
        return
    data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    print("=== restore free-space ptr retargets ===")
    # Maps already clean; still run with high bar
    ranges = [
        ("low_engine", 0x000000, 0x100000, 3),
        ("maps", 0x100000, 0x270000, 3),
        # dialogue bank: stricter — only dense pointer tables (scripts mixed in text)
        ("dialogue_scripts", 0x270000, 0x360000, 5),
        ("mid_pools", 0x360000, 0xFC0000, 3),
        ("fc_upper", 0xFC0000, 0x2000000, 3),
    ]
    total = 0
    for name, a, b, neigh in ranges:
        n = restore_free_retargets(data, golden, a, b, min_neighbors=neigh)
        print(f"  {name}: restored={n}")
        total += n
    print(f"  TOTAL restored={total}")

    # Fix residual GREAT BALL text near map end (not a ptr bug, but leftover)
    print("=== fix residual GREAT BALL @26F100 ===")
    put(data, golden, 0x26F100, "超级球！")
    put(data, golden, 0x26F13C, "超级球。")

    # Keep route101 script table golden
    data[0x279E71:0x27A0D5] = golden[0x279E71:0x27A0D5]

    # Keep time UI English labels
    keep = {
        "SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY",
        "AM", "PM", "A.M.", "P.M.", "TIME", "CANCEL",
    }
    off = 0xFC0000
    while off < 0xFD0000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0xFD0000 or eos - off > 24 or eos - off < 1:
            off = eos + 1 if 0 <= eos < 0xFD0000 else off + 1
            continue
        en = decode_bytes(golden[off : eos + 1]).strip()
        if en in keep:
            data[off : eos + 1] = golden[off : eos + 1]
        off = eos + 1

    # Re-assert key early dialogues (inplace only)
    from fix_stabilize_ptrs_dialogue import HAND  # noqa: E402

    for off, zh in HAND.items():
        put(data, golden, off, zh)

    # battle menu
    def zb(s: str) -> bytes:
        e, _ = encode_text_safe(s)
        return e[:-1] if e.endswith(b"\xff") else e

    off = 0xFFFB50
    eos = golden.find(b"\xff", off)
    cap = eos - off + 1
    blob = (
        zb("战斗")
        + bytes([0xFC, 0x13, 0x38])
        + zb("背包")
        + bytes([0xFE])
        + zb("宝可梦")
        + bytes([0xFC, 0x13, 0x38])
        + zb("逃跑")
        + b"\xff"
    )
    data[off : off + cap] = blob + b"\x00" * (cap - len(blob))

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("7172737475767778797A7B7C7D7E7F80")

    OUT.write_bytes(data)
    ROM.write_bytes(data)

    # verify
    left = 0
    samples = []
    for i in range(0, len(data) - 3, 4):
        # skip free zone itself and dialogue false-positive heavy? count strict only
        if 0x270000 <= i < 0x360000:
            min_n = 5
        elif 0x1DC0000 <= i < 0x1F00000:
            continue
        else:
            min_n = 3
        p, pg = u32(data, i), u32(golden, i)
        if p != pg and is_free(p) and looks_ptr(pg) and ptr_neighbors(golden, i) >= min_n:
            left += 1
            if len(samples) < 15:
                samples.append(i)
    print(f"=== remaining strict free-retargets={left} ===")
    for i in samples:
        print(f"  @{i:08X} g={u32(golden,i):08X} c={u32(data,i):08X}")

    maps_diff = sum(1 for i in range(0x100000, 0x270000) if data[i] != golden[i])
    print(f"maps byte diffs={maps_diff}")
    print("menu", data[0xFFFB50:0xFFFB62].hex())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
