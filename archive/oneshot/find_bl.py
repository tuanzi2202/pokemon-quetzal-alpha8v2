#!/usr/bin/env python3
"""Find Thumb BL targets to CopyGlyphToWindow inside relocated RenderText."""
from __future__ import annotations

import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rom = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()


def decode_bl(rom: bytes, i: int) -> int | None:
    hw1, hw2 = struct.unpack_from("<HH", rom, i)
    if (hw1 & 0xF800) != 0xF000 or (hw2 & 0xF800) != 0xF800:
        return None
    imm10 = hw1 & 0x3FF
    imm11 = hw2 & 0x7FF
    s = (hw1 >> 10) & 1
    j1 = (hw2 >> 13) & 1
    j2 = (hw2 >> 11) & 1
    i1 = 1 - (j1 ^ s)
    i2 = 1 - (j2 ^ s)
    imm32 = (s << 24) | (i1 << 23) | (i2 << 22) | (imm10 << 12) | (imm11 << 1)
    if s:
        imm32 |= ~((1 << 25) - 1)
        imm32 = imm32 - (1 << 32) if imm32 >= (1 << 31) else imm32
    pc = i + 4
    return (pc + imm32) & ~1


def main() -> None:
    targets = {0x4DA0, 0x4C08, 0x4C10, 0x6840, 0x57B4, 0x21C9BC}
    print("Scanning BL in 0x21C000-0x21E000 ...")
    for i in range(0x21C000, 0x21E000, 2):
        dest = decode_bl(rom, i)
        if dest is None:
            continue
        if dest in targets or (0x4C00 <= dest <= 0x5200):
            print(f"  BL @{i:08X} -> {dest:08X}")

    print("Scanning BL to CopyGlyph-like from 0x5000-0x7000 callers in first 0x10000...")
    for i in range(0x5000, 0x10000, 2):
        dest = decode_bl(rom, i)
        if dest == 0x4DA0:
            print(f"  early BL @{i:08X} -> CopyGlyph")


if __name__ == "__main__":
    main()
