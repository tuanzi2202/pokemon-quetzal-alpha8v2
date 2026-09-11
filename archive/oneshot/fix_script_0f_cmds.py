#!/usr/bin/env python3
"""Restore script opcodes (0F 00 <ptr> …) smashed by Chinese text overflows."""
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


def u32(b: bytes | bytearray, o: int) -> int:
    return int.from_bytes(b[o : o + 4], "little")


def looks(p: int) -> bool:
    return 0x08000000 <= p <= 0x09FFFFFF and not (0x09DC0000 <= p <= 0x09FFFFFF)


def restore_loadpointer_cmds(data: bytearray, golden: bytes, start: int, end: int) -> int:
    """Restore 0F 00 <romptr> [and following 09-xx script bytes] from golden."""
    n = 0
    i = start
    while i < end - 6:
        if golden[i] == 0x0F and golden[i + 1] == 0x00:
            p = u32(golden, i + 2)
            if looks(p):
                # include common trailer: 09 ?? ?? ... up to 8 extra bytes if match script-ish
                length = 6
                j = i + 6
                # extend while golden looks like script continuation and differs
                while j < i + 14 and j < end:
                    b = golden[j]
                    # typical: 09 calls, 02 ends, 6c/6b/25/05 ops, 86 menus, 00 pads
                    if b in (0x09, 0x02, 0x6C, 0x6B, 0x25, 0x05, 0x86, 0x00, 0x01, 0x03, 0x04, 0x06, 0x5C):
                        length = j - i + 1
                        j += 1
                        continue
                    break
                if bytes(data[i : i + length]) != golden[i : i + length]:
                    data[i : i + length] = golden[i : i + length]
                    n += 1
                i += length
                continue
        i += 1
    return n


def restore_nurse_sigs(data: bytearray, golden: bytes) -> int:
    n = 0
    off = 0
    while True:
        j = golden.find(SIG, off)
        if j < 0:
            break
        if data[j : j + len(SIG)] != golden[j : j + len(SIG)]:
            data[j - 8 : j + 0xA8] = golden[j - 8 : j + 0xA8]
            n += 1
        off = j + 1
    return n


def restore_ff0f(data: bytearray, golden: bytes) -> int:
    n = 0
    for i in range(0x260000, 0x360000 - 3):
        if golden[i : i + 3] == b"\xff\x0f\x00" and data[i : i + 3] != b"\xff\x0f\x00":
            data[i : i + 3] = b"\xff\x0f\x00"
            n += 1
    return n


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    print("1) restore 0F 00 ptr script cmds")
    n1 = restore_loadpointer_cmds(data, golden, 0x260000, 0x360000)
    print(f"   fixed {n1}")

    print("2) restore FF 0F 00 prefixes")
    print(f"   fixed {restore_ff0f(data, golden)}")

    print("3) re-check nurse sigs")
    print(f"   restored {restore_nurse_sigs(data, golden)}")

    # recount broken
    broken = 0
    for i in range(0x260000, 0x360000 - 6):
        if golden[i] == 0x0F and golden[i + 1] == 0x00 and looks(u32(golden, i + 2)):
            if data[i : i + 6] != golden[i : i + 6]:
                broken += 1
    print(f"4) broken 0F00 left: {broken}")

    # keep welcome CN (after script restores; string site only)
    from gen3_charmap import decode_bytes  # noqa: E402

    off = 0x309C60
    eos = golden.find(b"\xff", off)
    zh = "欢迎光临！{WAIT_CLEAR}需要我为你做些什么？"
    enc, _ = encode_text_safe(zh)
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    cap = eos - off + 1
    if len(body) + 1 <= cap:
        data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))
        print("5) nurse welcome CN ok")
    else:
        print("5) nurse welcome skip (too long)")

    # POKéMON scrub only where golden has exact 7-byte word (won't touch scripts)
    poke = bytes([0xCA, 0xC9, 0xC5, 0x1B, 0xC7, 0xC9, 0xC8])
    bao = encode_text_safe("宝可梦")[0]
    bao = bao[:-1] if bao.endswith(b"\xff") else bao
    n = 0
    i = 0
    while True:
        j = golden.find(poke, i)
        if j < 0:
            break
        if data[j : j + 7] == poke:
            data[j : j + 7] = bao + b"\x00" * (7 - len(bao))
            n += 1
        i = j + 1
    print(f"6) residual POKéMON scrub {n}")

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("F1F2F3F4F5F6F7F8A1A2A3A4A5A6A7A8")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    # verify key sites
    for i in (0x27C71E, 0x292570, 0x29257A, 0x293438, 0x29D19D):
        print(f"  @{i:08X} g={golden[i:i+10].hex()} r={data[i:i+10].hex()} ok={golden[i:i+10]==data[i:i+10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
