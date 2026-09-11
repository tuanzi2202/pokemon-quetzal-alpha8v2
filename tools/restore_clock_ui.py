#!/usr/bin/env python3
"""Restore opening wall-clock UI to golden English (day names + clock prompts only).

IMPORTANT: Do NOT wholesale-copy 0xFC0000–0xFD0000 — that wiped abilities/types/UI CN.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fill_and_apply_remaining import GOLDEN, LOCALE, OUT, ROM  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

FC_POOL = (0x0FC0000, 0x0FD0000)

CLOCK_OFFSETS = {
    0x287A50,  # The clock is stopped…
    0x0FC6D5C,  # FRIDAY
    0x0FC6D63,  # MONDAY
    0x0FC6D8C,  # WEDNESDAY
    0x0FC6DCF,  # SUNDAY
    0x101BB9F,  # internal battery / clock events
    0x1020666,  # The clock has been reset…
    0x10206EF,  # in-game clock adjustment system…
}

DAY = re.compile(
    r"^(SUNDAY|MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY)$", re.I
)
CLOCK_EN = re.compile(
    r"(?i)"
    r"the clock is stopped"
    r"|better set it and start"
    r"|the clock has been reset"
    r"|in-game clock adjustment"
    r"|internal battery has run dry"
    r"|clock events"
    r"|^(A\.M\.|P\.M\.)$"
)


def restore_body(data: bytearray, golden: bytes, off: int) -> bool:
    eos = golden.find(b"\xff", off)
    if eos < 0 or eos - off > 500:
        return False
    capacity = eos - off + 1
    data[off : off + capacity] = golden[off : off + capacity]
    return True


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    offs = set(CLOCK_OFFSETS)
    cleared = 0
    for r in rows:
        off = int(r["offset"])
        en = (r.get("en") or "").strip()
        hit = off in CLOCK_OFFSETS or DAY.match(en) or CLOCK_EN.search(en)
        if not hit:
            continue
        offs.add(off)
        if r.get("zh"):
            r["zh"] = ""
            cleared += 1

    # Also pick day names inside FC by scanning golden bodies
    a, b = FC_POOL
    off = a
    while off < b:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= b or eos - off > 40:
            off += 1
            continue
        text = decode_bytes(golden[off : eos + 1]).strip()
        if DAY.match(text) or CLOCK_EN.search(text):
            offs.add(off)
        off = eos + 1

    n = 0
    for off in sorted(offs):
        if restore_body(data, golden, off):
            n += 1

    LOCALE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )

    from fix_clock_and_mom_open import OPENING, inplace  # noqa: E402

    for off, zh in OPENING.items():
        if off == 0x287A50:
            continue
        inplace(data, golden, off, zh)

    for off in (0x287A50, 0x101BB9F, 0x1020666, 0x10206EF):
        restore_body(data, golden, off)

    OUT.write_bytes(data)
    ROM.write_bytes(data)

    print(f"restored_bodies={n} locale_zh_cleared={cleared} (no wholesale FC copy)")
    for off, name in [
        (0xFC6DCF, "SUNDAY"),
        (0xFC6D63, "MONDAY"),
        (0x287A50, "stopped"),
        (0x1020666, "reset"),
        (0x286F5E, "mom_set"),
        (0xFC31D1, "STENCH_should_stay_if_cn"),
    ]:
        eos = golden.find(b"\xff", off)
        print(f"  {name}: {decode_bytes(data[off:eos+1])[:70]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
