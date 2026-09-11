#!/usr/bin/env python3
"""In-place early dialogue Chinese (same 0x08 pointer) — proves render path."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chs_encode import encode_text_safe  # noqa: E402

ROM = ROOT / "work" / "cn_build.gba"
GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"

# High-priority early game / birch / mom offsets from dialogue_ptrs
PRIORITY = [
    0x270A1F,  # MAY littleroot
    0x35FD8B,  # Welcome to the
    0x289B65,  # PROF. BIRCH So
    0x289D54,  # PROF. BIRCH If you work
    0x276317,  # MOM introduce
    0x27664C,  # PROF. BIRCH spends days
    0x288B8D,  # Hey! Who are you
    0x288330,  # dream of becoming friends
]


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(ROM.read_bytes() if ROM.exists() else Path("out/quetzal_084_cn.gba").read_bytes())
    zh_by_off = {}
    for line in LOCALE.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        zh = (row.get("zh") or "").replace("[[10]]", "{WAIT_CLEAR}").replace("[[0]]", "{WAIT_CLEAR}")
        en = row.get("en") or ""
        if zh and zh != en and any("\u4e00" <= c <= "\u9fff" for c in zh):
            zh_by_off[int(row["offset"])] = zh

    # Also take first N dialogue_ptrs by offset for inplace if short enough
    extras = []
    for line in (ROOT / "dump" / "dialogue_ptrs.jsonl").read_text(encoding="utf-8").splitlines():
        off = int(json.loads(line)["offset"])
        if 0x270000 <= off < 0x2A0000:
            extras.append(off)
    targets = list(dict.fromkeys(PRIORITY + sorted(extras)[:200]))

    stats = {"inplace": 0, "skip_long": 0, "no_zh": 0, "restored_ptr": 0}
    for off in targets:
        zh = zh_by_off.get(off)
        if not zh:
            stats["no_zh"] += 1
            continue
        eos = golden.find(b"\xff", off)
        if eos < 0:
            continue
        capacity = eos - off + 1  # include FF
        enc, _missing = encode_text_safe(zh)
        if len(enc) > capacity:
            # truncate zh roughly
            cut = zh
            while cut and len(encode_text_safe(cut)[0]) > capacity:
                cut = cut[:-1]
            enc, _ = encode_text_safe(cut)
            if len(enc) > capacity:
                stats["skip_long"] += 1
                continue
        # enc ends with FF; pad remaining original slots with 00
        if len(enc) > capacity:
            stats["skip_long"] += 1
            continue
        blob = enc + (b"\x00" * (capacity - len(enc)))
        data[off : off + capacity] = blob
        # restore pointer to ORIGINAL 0x08 address (undo 0x09 reloc)
        ptr_sites = []
        needle = struct.pack("<I", 0x08000000 + off)
        i = 0
        while True:
            j = golden.find(needle, i)
            if j < 0:
                break
            if j % 4 == 0:
                ptr_sites.append(j)
            i = j + 1
        for s in ptr_sites:
            data[s : s + 4] = needle  # point back to inplace 0x08
            stats["restored_ptr"] += 1
        stats["inplace"] += 1
        if stats["inplace"] <= 10:
            print(f"INPLACE {off:08X} cap={capacity} used={len(enc)}", flush=True)

    ROM.write_bytes(data)
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
