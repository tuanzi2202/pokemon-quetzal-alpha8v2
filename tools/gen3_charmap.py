"""Generation III (Western / Emerald) character map helpers."""
from __future__ import annotations

# Core Western Emerald mapping (readable glyphs). Control codes kept as placeholders.
CHARMAP: dict[int, str] = {}

for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    CHARMAP[0xBB + i] = c
for i, c in enumerate("abcdefghijklmnopqrstuvwxyz"):
    CHARMAP[0xD5 + i] = c
for i, c in enumerate("0123456789"):
    CHARMAP[0xA1 + i] = c

CHARMAP.update(
    {
        0x00: " ",
        0x1B: "é",  # POKéMON mid-dot e (critical for dialogue dump)
        0xAB: "!",
        0xAC: "?",
        0xAD: ".",
        0xAE: "-",
        0xB0: "…",
        0xB1: "“",
        0xB2: "”",
        0xB3: "‘",
        0xB4: "'",
        0xB5: "♂",
        0xB6: "♀",
        0xB7: "$",
        0xB8: ",",
        0xB9: "×",
        0xBA: "/",
        0xF0: ":",
        0xFE: "\n",
    }
)

REVERSE: dict[str, int] = {v: k for k, v in CHARMAP.items() if len(v) == 1}

# Control / escape markers preserved in decoded text
CTRL = {
    0xFA: "{WAIT_SCROLL}",
    0xFB: "{WAIT_CLEAR}",
    0xFC: "{FC}",  # multi-byte; handled specially
    0xFD: "{FD}",  # multi-byte string var
    0xF7: "{F7}",
    0xF8: "{F8}",
    0xF9: "{F9}",
}


def encode_plain(text: str) -> bytes:
    """Encode ASCII-like plain text (no control codes) to Gen3 bytes + EOS."""
    out = bytearray()
    for ch in text:
        if ch not in REVERSE:
            raise KeyError(f"unencodable char {ch!r}")
        out.append(REVERSE[ch])
    out.append(0xFF)
    return bytes(out)


def decode_bytes(data: bytes, max_len: int = 256) -> str:
    """Decode a Gen3 string starting at data[0] until EOS or max_len."""
    parts: list[str] = []
    i = 0
    n = min(len(data), max_len)
    while i < n:
        b = data[i]
        if b == 0xFF:
            break
        if b == 0xFC and i + 1 < n:
            parts.append(f"{{FC:{data[i+1]:02X}}}")
            i += 2
            continue
        if b == 0xFD and i + 1 < n:
            parts.append(f"{{FD:{data[i+1]:02X}}}")
            i += 2
            continue
        if b == 0xF9 and i + 1 < n:
            parts.append(f"{{F9:{data[i+1]:02X}}}")
            i += 2
            continue
        if b in CTRL:
            parts.append(CTRL[b])
            i += 1
            continue
        if b in CHARMAP:
            parts.append(CHARMAP[b])
        else:
            parts.append(f"{{{b:02X}}}")
        i += 1
    return "".join(parts)


def is_likely_text(data: bytes, min_alpha: int = 3) -> bool:
    """Heuristic: mostly mapped glyphs, ends with EOS, enough letters."""
    if not data or data[-1] != 0xFF:
        return False
    body = data[:-1]
    if not body or len(body) > 480:
        return False
    alpha = 0
    ok = 0
    i = 0
    while i < len(body):
        b = body[i]
        if b in (0xFC, 0xFD, 0xF9) and i + 1 < len(body):
            ok += 2
            i += 2
            continue
        if b in (0xFA, 0xFB, 0xFE) or b in CHARMAP:
            ok += 1
            if b in CHARMAP and CHARMAP[b].isalpha():
                alpha += 1
            i += 1
            continue
        return False
    return alpha >= min_alpha and ok == len(body)
