#!/usr/bin/env python3
"""Find DAD / Aren't you going / leftover mixed EN+宝可梦 dialogues."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import load_charmap  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"


def decode_chs(data: bytes, to_str: dict[bytes, str]) -> str:
    parts: list[str] = []
    i = 0
    while i < len(data):
        if data[i] == 0xFF:
            break
        if data[i] == 0xFE:
            parts.append("\n")
            i += 1
            continue
        if data[i] in (0xFA, 0xFB):
            parts.append("{WAIT_SCROLL}" if data[i] == 0xFA else "{WAIT_CLEAR}")
            i += 1
            continue
        if data[i] == 0xFD and i + 1 < len(data):
            parts.append(f"{{FD:{data[i+1]:02X}}}")
            i += 2
            continue
        pair = bytes(data[i : i + 2])
        one = bytes(data[i : i + 1])
        if i + 1 < len(data) and pair in to_str:
            s2 = to_str[pair]
            s1 = to_str.get(one)
            if s1 and s1.isascii() and not s2.isascii():
                parts.append(s1)
                i += 1
                continue
            parts.append(s2)
            i += 2
            continue
        if one in to_str:
            parts.append(to_str[one])
            i += 1
            continue
        parts.append(f"[{data[i]:02X}]")
        i += 1
    return "".join(parts)


def main() -> int:
    g = GOLDEN.read_bytes()
    rom = OUT.read_bytes()
    _, to_str = load_charmap()

    # DAD: = BE BB BE F0
    dad = bytes([0xBE, 0xBB, 0xBE, 0xF0])
    print("=== DAD: strings mentioning going/Aren/Hm/POK ===")
    idx = 0
    n = 0
    while n < 40:
        i = g.find(dad, idx)
        if i < 0:
            break
        eos = g.find(b"\xff", i)
        if eos > i and eos - i < 220:
            en = decode_bytes(g[i : eos + 1])
            low = en.lower()
            if any(k in low for k in ("going", "aren", "hm?", "gym", "pok")):
                cur = decode_chs(rom[i : eos + 1], to_str)
                print(f"{i:08X}")
                print(f"  EN {en[:140]!r}")
                print(f"  CN {cur[:140]!r}")
                n += 1
        idx = i + 1

    print("\n=== EN with 'aren't you going' ===")
    off = 0x250000
    while off < 0x380000:
        eos = g.find(b"\xff", off, min(off + 200, 0x380000))
        if eos < 0:
            nxt = g.find(b"\xff", off, 0x380000)
            off = nxt + 1 if nxt >= 0 else 0x380000
            continue
        if eos - off < 20:
            off = eos + 1
            continue
        en = decode_bytes(g[off : eos + 1])
        if re.search(r"(?i)aren.?t you going", en) or (
            "Hm?" in en and "going" in en.lower()
        ):
            cur = decode_chs(rom[off : eos + 1], to_str)
            print(f"{off:08X}")
            print(f"  EN {en!r}")
            print(f"  CN {cur!r}")
        off = eos + 1

    print("\n=== mixed leftover: Latin + 宝可梦 still mostly EN ===")
    mixed = 0
    samples = []
    off = 0x250000
    while off < 0x360000:
        eos = g.find(b"\xff", off, min(off + 200, 0x360000))
        if eos < 0:
            nxt = g.find(b"\xff", off, 0x360000)
            off = nxt + 1 if nxt >= 0 else 0x360000
            continue
        if eos - off < 24:
            off = eos + 1
            continue
        cur = decode_chs(rom[off : eos + 1], to_str)
        if "宝可梦" not in cur and "POK" not in cur.upper():
            # also catch pure EN leftovers
            pass
        plain = re.sub(r"\{[^}]+\}", "", cur)
        letters = sum(c.isalpha() and c.isascii() for c in plain)
        cjk = sum(1 for c in plain if "\u4e00" <= c <= "\u9fff")
        words = re.findall(r"[A-Za-z]{3,}", plain)
        if letters >= 10 and letters > cjk and len(words) >= 2:
            # real-looking dialogue
            if any(
                w.lower()
                in {
                    "the",
                    "you",
                    "are",
                    "going",
                    "dad",
                    "mom",
                    "gym",
                    "aren",
                    "hm",
                    "what",
                    "this",
                    "that",
                    "have",
                    "will",
                    "your",
                }
                for w in words
            ) or ("宝可梦" in cur and letters >= 8):
                mixed += 1
                if len(samples) < 25:
                    en = decode_bytes(g[off : eos + 1])
                    samples.append((off, en[:100], cur[:100]))
        off = eos + 1
    print(f"count~{mixed}")
    for o, e, c in samples:
        print(f"{o:08X} EN={e!r}")
        print(f"         CN={c!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
