#!/usr/bin/env python3
"""Merge hand translations for MT failures into gtrans_cache."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "work" / "gtrans_cache.json"
FAIL = ROOT / "work" / "gtrans_fail.json"

MANUAL = {
    "{FD:1C} {FD:1D} and\n{FD:2E} {FD:2F}{WAIT_SCROLL}want to battle!{WAIT_CLEAR}": "{FD:1C}{FD:1D}和\n{FD:2E}{FD:2F}{WAIT_SCROLL}想要战斗！{WAIT_CLEAR}",
    "{FD:1C} {FD:1D} and\n{FD:2E} {FD:2F}{WAIT_SCROLL}were defeated!{WAIT_CLEAR}": "{FD:1C}{FD:1D}和\n{FD:2E}{FD:2F}{WAIT_SCROLL}被打倒了！{WAIT_CLEAR}",
    "MON: {FD:02}!{WAIT_CLEAR}{FD:03}!{WAIT_CLEAR}{FD:04}!": "宝可梦：{FD:02}！{WAIT_CLEAR}{FD:03}！{WAIT_CLEAR}{FD:04}！",
    "{FD:16} allows the\nuse of only {FD:14}!{WAIT_CLEAR}": "{FD:16}只允许\n使用{FD:14}！{WAIT_CLEAR}",
    "Player defeated\n{FD:1C} {FD:1D}!{WAIT_CLEAR}": "打倒了\n{FD:1C}{FD:1D}！{WAIT_CLEAR}",
    "{FD:00} grew to\nLV. {FD:01}!{FC:0A}{WAIT_CLEAR}": "{FD:00}升到了\nLv.{FD:01}！{FC:0A}{WAIT_CLEAR}",
    "{FD:18} allows the\nuse of only {FD:14}!{WAIT_CLEAR}": "{FD:18}只允许\n使用{FD:14}！{WAIT_CLEAR}",
    "{FD:00}'s {FD:17}\nprevents switching!{WAIT_CLEAR}": "{FD:00}的{FD:17}\n无法交换宝可梦！{WAIT_CLEAR}",
    "{FD:13} prevents\nescape with {FD:1A}!{WAIT_CLEAR}": "{FD:13}的{FD:1A}\n让人无法逃走！{WAIT_CLEAR}",
    "{FD:00} learned\n{FD:01}!{FC:0A}{WAIT_CLEAR}": "{FD:00}学会了\n{FD:01}！{FC:0A}{WAIT_CLEAR}",
    "{FD:0F}'s {FD:14}\nis disabled!{WAIT_CLEAR}": "{FD:0F}的{FD:14}\n无法使用！{WAIT_CLEAR}",
    "{FD:00} forgot\n{FD:01}.{WAIT_CLEAR}": "{FD:00}忘记了\n{FD:01}。{WAIT_CLEAR}",
    "{FD:02} ate the\n{FD:03}.{FC:09}": "{FD:02}吃掉了\n{FD:03}。{FC:09}",
    "{FD:0F} became Ash-{FD:00}!{WAIT_CLEAR}": "{FD:0F}变成了小智-{FD:00}！{WAIT_CLEAR}",
    "{FD:23} picked up\n${FD:00}!{WAIT_CLEAR}": "{FD:23}捡到了\n¥{FD:00}！{WAIT_CLEAR}",
    "TERAPAGOS": "太乐巴戈斯",
    "OGERPON": "瓯柑柚",
    "DEXNAV": "图鉴导航",
    "GHECHIS": "魁奇思",
    "ACROMO": "阿克罗玛",
}


def norm(s: str) -> str:
    return s.replace("\r\n", "\n")


def main() -> int:
    fails = json.loads(FAIL.read_text(encoding="utf-8")) if FAIL.exists() else []
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    manual_n = {norm(k): v for k, v in MANUAL.items()}

    added = 0
    junk = 0
    still: list[str] = []
    for en in fails:
        n = norm(en)
        if n in manual_n:
            cache[en] = manual_n[n]
            added += 1
            continue
        if en.count("9") > 10 or en.count("R") > 10 or en.count("A") > 12:
            junk += 1
            continue
        if "a b c d e" in en or en.strip() in ("U VWXYZabc", "CD TwC", "QECx", "QECx "):
            junk += 1
            continue
        if sum(c.isalpha() for c in en) < 4:
            junk += 1
            continue
        if "Aah!" in en:
            cache[en] = en.replace("Aah!", "啊啊！")
            added += 1
            continue
        still.append(en)

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    FAIL.write_text(json.dumps(still, ensure_ascii=False), encoding="utf-8")
    print(f"manual_added={added} junk_skip={junk} still={len(still)} cache={len(cache)}")
    for s in still:
        print("STILL", repr(s[:140]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
