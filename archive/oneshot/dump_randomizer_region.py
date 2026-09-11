#!/usr/bin/env python3
"""Decode randomizer region help strings to English for translation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
en = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()

CHAR = {
    **{0xBB + i: chr(65 + i) for i in range(26)},
    **{0xD5 + i: chr(97 + i) for i in range(26)},
    0x00: " ",
    0xAD: ".",
    0xFE: "\n",
    0x1B: "e",
    0xB4: "e",
    0xB6: "?",
    0xB7: "!",
    0xAE: "-",
    0xAB: "...",
    0xB0: "-",
    0xB8: "'",
    0xAC: "...",
}
for i in range(10):
    CHAR[0xA1 + i] = str(i)


def decode(raw: bytes) -> str:
    out = []
    j = 0
    while j < len(raw) - 1:
        b = raw[j]
        if b == 0xFC and j + 2 < len(raw):
            out.append(f"{{FC:{raw[j+1]:02X}{raw[j+2]:02X}}}")
            j += 3
            continue
        if b == 0xFD and j + 1 < len(raw):
            out.append(f"{{FD:{raw[j+1]:02X}}}")
            j += 2
            continue
        out.append(CHAR.get(b, f"[{b:02X}]"))
        j += 1
    return "".join(out)


def dump(start: int, end: int):
    i = start
    while i < end:
        if en[i] == 0xFF:
            i += 1
            continue
        s = i
        while i < end and en[i] != 0xFF:
            i += 1
        if i >= end:
            break
        raw = en[s : i + 1]
        # skip if mostly pointer-like (09 bank bytes densly)
        if raw.count(0x09) >= 3 and len(raw) > 8:
            i += 1
            continue
        text = decode(raw)
        if sum(c.isalpha() for c in text) >= 3:
            print(f"{s:08X}\t{text}")
        i += 1


print("=== LABELS+HELP ===")
dump(0x17017B0, 0x1702300)
print("=== TABS+VALUES ===")
dump(0x1703E80, 0x1704100)
