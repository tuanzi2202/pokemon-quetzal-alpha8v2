#!/usr/bin/env python3
"""Restore remaining wiped Pokemon-Center nurse script tables + lost ptrs."""
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

# Shared nurse heal-menu pointer signature (inside each PC block)
SIG = bytes.fromhex("5ddc3008036edb3008000458df3008020454e1300802047de23008")


def u32(b: bytes | bytearray, o: int) -> int:
    return int.from_bytes(b[o : o + 4], "little")


def put(data: bytearray, golden: bytes, off: int, zh: str) -> bool:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return False
    cap = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    while len(body) + 1 > cap and zh:
        zh = zh[:-1]
        enc, _ = encode_text_safe(zh)
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        body = enc[:-1]
    if len(body) + 1 > cap:
        return False
    data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))
    return True


def restore_nurse_blocks(data: bytearray, golden: bytes) -> list[int]:
    fixed = []
    off = 0
    while True:
        j = golden.find(SIG, off)
        if j < 0:
            break
        if data[j : j + len(SIG)] != golden[j : j + len(SIG)]:
            # Restore from a few bytes before sig through typical menu tail.
            # Emerald-style PC block: ptrs + two 0x86 menus + follow-up text ptrs.
            start = j - 8
            end = j + 0xB0
            # Don't clobber next unrelated content if golden already matches further
            # Extend end while golden still looks like script/menu (0x0f ptr loads, 0x86, etc.)
            while end < j + 0x120 and end < len(golden):
                # stop if we hit a long ASCII/Latin sentence start after FF gap
                if golden[end] == 0xFF:
                    break
                end += 1
            # Prefer fixed window that matched working Oldale block
            end = max(end, j + 0xA8)
            data[start:end] = golden[start:end]
            fixed.append(j)
        off = j + 1
    return fixed


def restore_lost_ptrs(data: bytearray, golden: bytes) -> int:
    n = 0
    for i in range(0x260000, 0x360000, 4):
        pg = u32(golden, i)
        pr = u32(data, i)
        if pr == 0 and 0x08000000 <= pg <= 0x09FFFFFF and not (0x09DC0000 <= pg <= 0x09FFFFFF):
            # restore dword; if surrounding was text-corrupted, restore small window
            data[i : i + 4] = golden[i : i + 4]
            # if neighbors also zeroed vs golden ptrs, expand
            lo, hi = i, i + 4
            while lo >= 0x260000 and data[lo - 4 : lo] == b"\x00\x00\x00\x00":
                gp = u32(golden, lo - 4)
                if 0x08000000 <= gp <= 0x09FFFFFF or golden[lo - 4 : lo] != b"\x00\x00\x00\x00":
                    if golden[lo - 4 : lo] != b"\x00\x00\x00\x00":
                        lo -= 4
                    else:
                        break
                else:
                    break
            while hi < 0x360000 and data[hi : hi + 4] == b"\x00\x00\x00\x00":
                if golden[hi : hi + 4] != b"\x00\x00\x00\x00":
                    hi += 4
                else:
                    break
            if hi - lo > 4:
                data[lo:hi] = golden[lo:hi]
            n += 1
    return n


def scrub_pokemon_text_only(data: bytearray, golden: bytes) -> int:
    """Replace POKéMON only inside golden text that actually contains that word.
    Never write into script-looking regions (no overflow pad into following bytes beyond slot).
    """
    poke = bytes([0xCA, 0xC9, 0xC5, 0x1B, 0xC7, 0xC9, 0xC8])  # POKéMON 7 bytes
    poke_t = bytes([0xCA, 0xE3, 0xDF, 0x1B, 0xC7, 0xC9, 0xC8])  # PokéMON rare
    bao = encode_text_safe("宝可梦")[0]
    bao = bao[:-1] if bao.endswith(b"\xff") else bao
    assert len(bao) <= 7
    n = 0
    for pat in (poke, poke_t):
        i = 0
        while True:
            j = golden.find(pat, i)
            if j < 0:
                break
            # only if still English pattern OR already bao
            cur = bytes(data[j : j + 7])
            if cur == pat or cur[: len(bao)] != bao:
                data[j : j + 7] = bao + b"\x00" * (7 - len(bao))
                n += 1
            i = j + 1
    return n


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    print("1) restore broken nurse script signatures")
    fixed = restore_nurse_blocks(data, golden)
    print(f"   fixed {len(fixed)} sites:", [f"{x:08X}" for x in fixed])

    print("2) restore lost ptr dwords in dialogue bank")
    print(f"   restored {restore_lost_ptrs(data, golden)}")

    print("3) safe POKéMON→宝可梦 (golden-anchored, fixed 7-byte slot)")
    print(f"   scrubbed {scrub_pokemon_text_only(data, golden)}")

    # nurse welcome keep CN if still fits
    put(data, golden, 0x309C60, "欢迎光临！{WAIT_CLEAR}需要我为你做些什么？")

    # verify all nurse sigs
    off = 0
    bad = 0
    while True:
        j = golden.find(SIG, off)
        if j < 0:
            break
        if data[j : j + len(SIG)] != golden[j : j + len(SIG)]:
            bad += 1
            print(f"   STILL BAD @{j:08X}")
        off = j + 1
    print(f"4) nurse sigs still bad: {bad}")

    # lost ptrs left
    lost = 0
    for i in range(0x260000, 0x360000, 4):
        pg, pr = u32(golden, i), u32(data, i)
        if pr == 0 and 0x08000000 <= pg <= 0x09FFFFFF and not (0x09DC0000 <= pg <= 0x09FFFFFF):
            lost += 1
    print(f"5) lost ptrs left: {lost}")

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("D1D2D3D4D5D6D7D8E1E2E3E4E5E6E7E8")
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
