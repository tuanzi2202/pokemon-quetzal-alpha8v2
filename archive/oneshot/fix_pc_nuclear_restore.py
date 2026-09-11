#!/usr/bin/env python3
"""Nuclear restore of Pokemon Center shared script/text banks from golden.

Map headers/layouts already match golden. Remaining PC wild-battle class bugs
come from smashed dialogue/script *content* around nurse blocks (0x29xxxx).
Old saves may still carry bad randomizer/script state — ROM fix alone may not
clear that; user should verify with New Game.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"

SIG = bytes.fromhex("5ddc3008036edb3008000458df3008020454e1300802047de23008")

# Large contiguous restores (shared PC dialogue + early town PC scripts)
FORCE_RANGES = [
    (0x28B000, 0x28C000),
    (0x28F000, 0x291000),  # includes Oldale PC scripts area
    (0x291000, 0x293000),
    (0x293000, 0x295000),
    (0x295000, 0x298000),  # includes heavily smashed 0x297000
    (0x298000, 0x29A000),
    (0x29C000, 0x29E000),
    (0x2A0000, 0x2A2000),
    (0x2A4000, 0x2A8000),
    (0x2AC000, 0x2AE000),
    (0x2B1000, 0x2B3000),
    (0x2B6000, 0x2B8000),
    (0x2B9000, 0x2BB000),
    (0x2FE000, 0x2FF000),
]


def put(data: bytearray, golden: bytes, off: int, zh: str) -> bool:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return False
    cap = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if enc.endswith(b"\xff"):
        enc = enc[:-1]
    while len(enc) + 1 > cap and zh:
        zh = zh[:-1]
        enc, _ = encode_text_safe(zh)
        if enc.endswith(b"\xff"):
            enc = enc[:-1]
    if len(enc) + 1 > cap:
        return False
    data[off : off + cap] = enc + b"\xff" + b"\x00" * (cap - 1 - len(enc))
    return True


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    print("1) force-restore PC script/text ranges from golden")
    total = 0
    for a, b in FORCE_RANGES:
        before = sum(1 for i in range(a, b) if data[i] != golden[i])
        data[a:b] = golden[a:b]
        total += before
        print(f"   {a:08X}-{b:08X} restored_diff_bytes={before}")
    print(f"   total bytes touched≈{total}")

    print("2) SIG windows ±0x100")
    off = 0
    nsig = 0
    while True:
        j = golden.find(SIG, off)
        if j < 0:
            break
        a, b = max(0, j - 0x100), min(len(golden), j + 0x100)
        if data[a:b] != golden[a:b]:
            data[a:b] = golden[a:b]
            nsig += 1
        off = j + 1
    print(f"   windows refreshed={nsig}")

    print("3) re-CN safe short nurse lines (inplace, no overflow)")
    # Only strings fully inside restored banks with known caps
    hand = {
        0x309C60: "欢迎光临！{WAIT_CLEAR}需要我为你做些什么？",
    }
    for o, zh in hand.items():
        print(f"   {o:08X} {put(data, golden, o, zh)}")

    # POKéMON → 宝可梦 only in restored ranges, fixed 7-byte slot, NUL pad
    poke = bytes([0xCA, 0xC9, 0xC5, 0x1B, 0xC7, 0xC9, 0xC8])
    bao = encode_text_safe("宝可梦")[0]
    if bao.endswith(b"\xff"):
        bao = bao[:-1]
    pad = bao + bytes(7 - len(bao))
    n = 0
    for a, b in FORCE_RANGES:
        i = a
        while True:
            j = golden.find(poke, i, b)
            if j < 0:
                break
            data[j : j + 7] = pad
            n += 1
            i = j + 1
    print(f"4) POKéMON scrub in restored ranges: {n}")

    # verify
    d297 = sum(1 for i in range(0x297000, 0x297400) if data[i] != golden[i])
    print(f"5) 297000-297400 remaining diffs (expect POKéMON only): {d297}")
    bad = 0
    off = 0
    while True:
        j = golden.find(SIG, off)
        if j < 0:
            break
        if data[j : j + len(SIG)] != golden[j : j + len(SIG)]:
            bad += 1
        off = j + 1
    print(f"6) nurse SIG bad: {bad}")

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("AABBCCDDEEFF00112233445566778899")
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
