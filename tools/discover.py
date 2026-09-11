#!/usr/bin/env python3
"""Discover Gen3 strings, free space, and link-sensitive markers in Quetzal 0.8.4."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen3_charmap import decode_bytes, encode_plain, is_likely_text  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT_JSON = ROOT / "blacklists" / "regions.json"
OUT_SAMPLE = ROOT / "dump" / "discover_sample.jsonl"
OUT_REPORT = ROOT / "docs" / "DISCOVER.txt"


def find_all(rom: bytes, needle: bytes, limit: int = 20) -> list[int]:
    out: list[int] = []
    idx = 0
    while len(out) < limit:
        i = rom.find(needle, idx)
        if i < 0:
            break
        out.append(i)
        idx = i + 1
    return out


def scan_strings(rom: bytes, start: int = 0x100000, end: int | None = None, max_hits: int = 5000):
    if end is None:
        end = len(rom)
    hits = []
    i = start
    while i < end - 4 and len(hits) < max_hits:
        # potential string: printable-ish Gen3 start
        if rom[i] in range(0xA1, 0xF1) or rom[i] in (0x00, 0xFD, 0xFC):
            # find EOS within 200 bytes
            eos = rom.find(b"\xff", i, i + 200)
            if eos < 0 or eos == i:
                i += 1
                continue
            chunk = rom[i : eos + 1]
            if is_likely_text(chunk, min_alpha=4):
                text = decode_bytes(chunk)
                hits.append({"offset": i, "length": len(chunk), "en": text, "hex": chunk.hex()})
                i = eos + 1
                continue
        i += 1
    return hits


def find_free_runs(rom: bytes, min_len: int = 0x1000) -> list[dict]:
    runs = []
    i = 0
    n = len(rom)
    while i < n:
        if rom[i] in (0x00, 0xFF):
            val = rom[i]
            j = i
            while j < n and rom[j] == val:
                j += 1
            length = j - i
            if length >= min_len:
                runs.append({"offset": i, "length": length, "fill": val})
            i = j
        else:
            i += 1
    runs.sort(key=lambda r: -r["length"])
    return runs


def main() -> int:
    rom = GOLDEN.read_bytes()
    markers = {
        "PokemonSioInfo": find_all(rom, b"PokemonSioInfo"),
        "LINK_LOSS": find_all(rom, b"LINK LOSS"),
        "NOWSLOT": find_all(rom, b"NOWSLOT"),
        "PKM_QUETZAL": find_all(rom, b"PKM QUETZAL"),
    }
    menu_needles = [
        "NEW GAME",
        "CONTINUE",
        "OPTIONS",
        "BAG",
        "SAVE",
        "POKeMON",
        "PLAYER",
        "YES",
        "NO",
        "CANCEL",
        "TEXT SPEED",
        "BATTLE STYLE",
        "SOUND",
        "BUTTON MODE",
        "FRAME",
        "CANCEL",
        "CONFIRM",
        "MULTIPLAYER",
        "Multiplayer",
    ]
    menu_hits = {}
    for name in menu_needles:
        try:
            # POKeMON: e as normal e in Gen3 (no accent in encode)
            key = name.replace("é", "e")
            menu_hits[name] = find_all(rom, encode_plain(key)[:-1], limit=10)
        except KeyError:
            menu_hits[name] = []

    strings = scan_strings(rom, start=0x1C0000, end=0x3E0000, max_hits=8000)
    free = find_free_runs(rom, min_len=0x800)

    # Allowed rewrite regions: dense string clusters + free space candidates
    # Cluster strings into approximate banks by 64KB windows
    banks: Counter = Counter()
    for h in strings:
        banks[h["offset"] // 0x10000] += 1
    top_banks = banks.most_common(20)

    # Link keep zones: ±0x2000 around each marker
    keep_ranges = []
    for label, offs in markers.items():
        for o in offs:
            keep_ranges.append(
                {
                    "label": label,
                    "start": max(0, o - 0x2000),
                    "end": min(len(rom), o + 0x4000),
                }
            )
    # Header / interrupt vector
    keep_ranges.append({"label": "rom_header", "start": 0, "end": 0x200})

    # Candidate text rewrite: top banks with many strings
    allow_ranges = []
    for bank, count in top_banks:
        if count < 30:
            continue
        allow_ranges.append(
            {
                "label": f"string_bank_{bank:02X}",
                "start": bank * 0x10000,
                "end": min(len(rom), (bank + 1) * 0x10000),
                "string_hits": count,
            }
        )
    # Top free runs as expansion area (exclude if overlap keep)
    for r in free[:12]:
        allow_ranges.append(
            {
                "label": f"free_{r['offset']:08X}",
                "start": r["offset"],
                "end": r["offset"] + r["length"],
                "fill": r["fill"],
            }
        )

    regions = {
        "rom_size": len(rom),
        "sha256": __import__("hashlib").sha256(rom).hexdigest(),
        "markers": markers,
        "menu_hits": menu_hits,
        "keep_ranges": keep_ranges,
        "allow_ranges": allow_ranges,
        "free_top": free[:20],
        "string_scan": {"count": len(strings), "start": 0x1C0000, "end": 0x3E0000},
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(regions, indent=2), encoding="utf-8")

    with OUT_SAMPLE.open("w", encoding="utf-8") as f:
        # Prefer menu-like / short UI strings
        interesting = [
            h
            for h in strings
            if 4 <= len(h["en"]) <= 48 and "\n" not in h["en"] and "{" not in h["en"]
        ]
        interesting.sort(key=lambda h: h["offset"])
        for h in interesting[:2000]:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")

    lines = [
        "Quetzal 0.8.4 discover report",
        "============================",
        f"ROM size: {len(rom)}",
        f"SHA256: {regions['sha256']}",
        "",
        "Link markers:",
    ]
    for k, v in markers.items():
        lines.append(f"  {k}: {[hex(x) for x in v]}")
    lines.append("")
    lines.append("Menu needle offsets (Gen3 bytes, no EOS):")
    for k, v in menu_hits.items():
        lines.append(f"  {k}: {[hex(x) for x in v[:5]]}")
    lines.append("")
    lines.append(f"Scanned strings: {len(strings)}")
    lines.append("Top string banks (64KB):")
    for bank, count in top_banks[:12]:
        lines.append(f"  bank 0x{bank:02X}0000 count={count}")
    lines.append("")
    lines.append("Top free runs (>=0x800):")
    for r in free[:10]:
        lines.append(f"  0x{r['offset']:08X} len=0x{r['length']:X} fill=0x{r['fill']:02X}")
    lines.append("")
    lines.append(f"Wrote {OUT_JSON}")
    lines.append(f"Wrote {OUT_SAMPLE}")
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
