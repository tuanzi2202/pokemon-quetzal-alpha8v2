#!/usr/bin/env python3
"""Validate a user-supplied Pokémon Quetzal 0.8.4 ROM and stage a private copy.

The ROM is intentionally not included in this repository.  Put a legally
dumped, version-matching ROM at golden/en_0.8.4.gba (or pass --rom) and run:

    python tools/prepare_rom.py

The script checks the expected 32 MiB size and SHA-256 before copying it to
work/base_quetzal_084.gba.  It never downloads or modifies the source ROM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROM = ROOT / "golden" / "en_0.8.4.gba"
STAGED_ROM = ROOT / "work" / "base_quetzal_084.gba"
MANIFEST = ROOT / "work" / "rom_manifest.json"

# Quetzal CN 0.8.4 project reference dump (32 MiB, unheadered).
EXPECTED_SIZE = 0x02000000
EXPECTED_SHA256 = "e9fc9cf506ad11db7642e7d65774e2bb0e5f174eb9aceda725cd961ab9aee070"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def header_info(path: Path) -> dict[str, object]:
    with path.open("rb") as fh:
        header = fh.read(0xC0)
    # GBA title is 0xA0..0xAB and game code is 0xAC..0xAF.
    title = header[0xA0:0xAC].rstrip(b"\0 ").decode("ascii", "replace")
    game_code = header[0xAC:0xB0].decode("ascii", "replace")
    version = header[0xBC] if len(header) > 0xBC else None
    return {"title": title, "game_code": game_code, "version": version}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, default=DEFAULT_ROM,
                        help=f"path to your legal ROM dump (default: {DEFAULT_ROM})")
    parser.add_argument("--force", action="store_true",
                        help="replace an existing staged copy after validation")
    args = parser.parse_args()
    source = args.rom.expanduser().resolve()

    if not source.is_file():
        print(f"ROM not found: {source}")
        print("Place your own legally dumped, version-matching Quetzal 0.8.4 ROM at:")
        print(f"  {DEFAULT_ROM}")
        return 2

    size = source.stat().st_size
    digest = sha256(source)
    print(f"ROM:    {source}")
    print(f"Size:   {size} bytes (expected {EXPECTED_SIZE})")
    print(f"SHA256: {digest}")
    print(f"Header: {header_info(source)}")

    problems: list[str] = []
    if size != EXPECTED_SIZE:
        problems.append("size does not match the 32 MiB Quetzal 0.8.4 reference")
    if digest.lower() != EXPECTED_SHA256:
        problems.append("SHA-256 does not match the Quetzal 0.8.4 reference dump")
    if problems:
        print("\nREJECTED:")
        for problem in problems:
            print(f"- {problem}")
        print("If you meant another Quetzal release (for example 8.2), keep it separate and update the project metadata only after confirming the exact release.")
        return 3

    STAGED_ROM.parent.mkdir(parents=True, exist_ok=True)
    if STAGED_ROM.exists() and not args.force:
        if sha256(STAGED_ROM) == digest:
            print(f"Already staged: {STAGED_ROM}")
        else:
            print(f"Staged file exists and differs: {STAGED_ROM}")
            print("Use --force only if you intentionally want to replace it.")
            return 4
    else:
        shutil.copy2(source, STAGED_ROM)
        print(f"Staged private working copy: {STAGED_ROM}")

    manifest = {
        "name": "Pokemon Quetzal 0.8.4",
        "source": str(source),
        "size": size,
        "sha256": digest,
        "header": header_info(source),
        "staged": str(STAGED_ROM),
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest: {MANIFEST}")
    print("Next: copy the staged ROM to work/cn_build.gba before running build_all.ps1, or use the build script after adding your own mod steps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
