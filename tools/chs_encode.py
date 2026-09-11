#!/usr/bin/env python3
"""Encode/decode Quetzal strings with Gen3 + Wokann Chinese charmap."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHARMAP_PATH = ROOT / "fontpatch" / "PMRSEFRLG_charmap.txt"

# Control tokens preserved in JSONL English text
CTRL_RE = re.compile(r"\{([A-Z0-9_]+)(?::([0-9A-Fa-f]{2}))?\}")
# Raw single-byte tokens like {06}{07} used after {FC:01} color cmds
RAW_BYTE_RE = re.compile(r"\{([0-9A-Fa-f]{2})\}")


def load_charmap(path: Path = CHARMAP_PATH) -> tuple[dict[str, bytes], dict[bytes, str]]:
    to_bytes: dict[str, bytes] = {}
    to_str: dict[bytes, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("@") or "=" not in line:
            continue
        left, right = line.split("=", 1)
        left = left.strip()
        right = right.strip()
        if not right:
            continue
        # skip multi-equal compound keys like 5354=
        if not re.fullmatch(r"[0-9A-Fa-f]{2,4}", left):
            continue
        raw = bytes.fromhex(left)
        # unescape \'
        if right.startswith("\\"):
            right = bytes(right, "utf-8").decode("unicode_escape")
        to_bytes[right] = raw
        to_str[raw] = right
    # ensure space
    to_bytes.setdefault(" ", bytes.fromhex("00"))
    to_str[b"\x00"] = " "
    return to_bytes, to_str


_TO_BYTES: dict[str, bytes] | None = None


def get_to_bytes() -> dict[str, bytes]:
    global _TO_BYTES
    if _TO_BYTES is None:
        _TO_BYTES, _ = load_charmap()
    return _TO_BYTES


def encode_text(text: str) -> bytes:
    """Encode translated text (may include {FC:xx} tokens) to Gen3/CHS bytes + EOS."""
    to_b = get_to_bytes()
    out = bytearray()
    i = 0
    while i < len(text):
        if text[i] == "{":
            m = CTRL_RE.match(text, i)
            if m:
                name, arg = m.group(1), m.group(2)
                if name == "FC" and arg:
                    out.append(0xFC)
                    out.append(int(arg, 16))
                elif name == "FD" and arg:
                    out.append(0xFD)
                    out.append(int(arg, 16))
                elif name == "F9" and arg:
                    out.append(0xF9)
                    out.append(int(arg, 16))
                elif name == "WAIT_SCROLL":
                    out.append(0xFA)
                elif name == "WAIT_CLEAR":
                    out.append(0xFB)
                elif name == "F7":
                    out.append(0xF7)
                elif name == "F8":
                    out.append(0xF8)
                elif re.fullmatch(r"[0-9A-Fa-f]{2}", name):
                    out.append(int(name, 16))
                else:
                    # unknown token: keep as empty
                    pass
                i = m.end()
                continue
        if text[i] == "\n":
            out.append(0xFE)
            i += 1
            continue
        ch = text[i]
        if ch in ("$", "¥"):
            out.append(0xB7)
            i += 1
            continue
        # try digraphs / longer first for PKMN etc - single char
        if ch in to_b:
            out.extend(to_b[ch])
            i += 1
            continue
        # try 2-char punctuation already in map as single unicode
        raise KeyError(f"cannot encode {ch!r} at {i} in {text!r}")
    out.append(0xFF)
    return bytes(out)


def encode_text_safe(text: str) -> tuple[bytes, list[str]]:
    """Encode, replacing missing glyphs with '?' (0xAC) and logging."""
    to_b = get_to_bytes()
    missing: list[str] = []
    out = bytearray()
    i = 0
    while i < len(text):
        if text[i] == "{":
            m = CTRL_RE.match(text, i)
            if m:
                name, arg = m.group(1), m.group(2)
                if name == "FC" and arg:
                    out += bytes([0xFC, int(arg, 16)])
                elif name == "FD" and arg:
                    out += bytes([0xFD, int(arg, 16)])
                elif name == "F9" and arg:
                    out += bytes([0xF9, int(arg, 16)])
                elif name == "WAIT_SCROLL":
                    out.append(0xFA)
                elif name == "WAIT_CLEAR":
                    out.append(0xFB)
                elif re.fullmatch(r"[0-9A-Fa-f]{2}", name):
                    out.append(int(name, 16))
                i = m.end()
                continue
        if text[i] == "\n":
            out.append(0xFE)
            i += 1
            continue
        ch = text[i]
        # Western '$' and CJK '¥' share Gen3 byte 0xB7 (money glyph).
        if ch in ("$", "¥"):
            out.append(0xB7)
            i += 1
            continue
        if ch in to_b:
            out.extend(to_b[ch])
        else:
            missing.append(ch)
            out.extend(to_b.get("?", bytes([0xAC])))
        i += 1
    out.append(0xFF)
    return bytes(out), missing
