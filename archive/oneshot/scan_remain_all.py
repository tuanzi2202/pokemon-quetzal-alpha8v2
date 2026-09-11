#!/usr/bin/env python3
"""Scan remaining English by category (moves/species/HP/dialogue/FC pool)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_locale_zh import is_junk_en  # noqa: E402
from fill_and_apply_remaining import scrub  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"
EN = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()
CN = (ROOT / "out" / "quetzal_084_cn.gba").read_bytes()


def has_cjk(t: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in t)


def main() -> int:
    rows = [json.loads(l) for l in LOCALE.open(encoding="utf-8") if l.strip()]
    days = {"SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"}

    fc_en = []
    no_cjk = []
    mix = []
    for r in rows:
        off = int(r["offset"])
        en = r.get("en") or ""
        zh = scrub(r.get("zh") or "")
        if is_junk_en(en) or not en.strip():
            continue
        e = en.strip()
        if e.upper() in days:
            continue
        in_fc = 0x0FC0000 <= off < 0x0FD0000
        # ROM body still English?
        eos = EN.find(b"\xff", off)
        rom_same = False
        if 0 < eos - off <= 200:
            rom_same = CN[off : eos + 1] == EN[off : eos + 1]
        if in_fc and rom_same and re.search(r"[A-Za-z]{3,}", e):
            fc_en.append((off, e[:40], zh[:30]))
        if not zh or not has_cjk(zh):
            if sum(c.isalpha() for c in e) >= 3:
                no_cjk.append((off, e[:50], in_fc, rom_same))
        else:
            plain = re.sub(r"\{[^}]+\}", "", zh)
            hits = [w for w in re.findall(r"[A-Za-z]{3,}", plain) if w.upper() not in {"HP", "PP", "TM", "HM", "LV", "SELECT", "START", "SAVE", "GBA"}]
            if hits:
                mix.append((off, e[:40], zh[:50], hits[:4]))

    print("FC_pool_ROM_still_EN", len(fc_en))
    for x in fc_en[:25]:
        print(" ", f"{x[0]:08X}", x[1])
    print("locale_no_cjk", len(no_cjk))
    for x in no_cjk[:20]:
        print(" ", f"{x[0]:08X}", "fc" if x[2] else "  ", "sameROM" if x[3] else "diffROM", x[1])
    print("locale_mixed_latin", len(mix))
    for x in mix[:15]:
        print(" ", f"{x[0]:08X}", x[3], x[2])

    # sample battle UI strings in FC
    print("=== sample FC decode EN vs CN ===")
    for off, label in [
        (0x0FC303E, "MON"),
        (0x0FC3053, "LEVEL"),
        (0x0FC2FE2, "SAPPHIRE"),
        (0x0FC31D1, "STENCH"),
    ]:
        eos = EN.find(b"\xff", off)
        print(label, "EN", decode_bytes(EN[off : eos + 1]), "CN", decode_bytes(CN[off : eos + 1]))

    Path(ROOT / "work" / "remain_fc_en.json").write_text(
        json.dumps([{"offset": o, "en": e, "zh": z} for o, e, z in fc_en], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    Path(ROOT / "work" / "remain_no_cjk.json").write_text(
        json.dumps([{"offset": o, "en": e, "fc": f, "rom_same": s} for o, e, f, s in no_cjk], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
