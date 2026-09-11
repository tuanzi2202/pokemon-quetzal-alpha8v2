#!/usr/bin/env python3
"""Force Chinese trainer class names (dialogue/battle nameplate).

Table: gTrainerClassNames @ 0x4065EC, 66 entries × 13 bytes (Emerald layout).
Inplace only — fixed stride, no reloc.

Usage:
  python tools/force_trainer_class_zh.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

ROM = ROOT / "work" / "cn_build.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
BASE = 0x4065EC
STRIDE = 13
COUNT = 66
FP_OFF = 0x1DCB5E0

# EN strip() key -> 简中（须 ≤12 字节 + FF）
# {53}{54} = PKMN 缩写图块；用户要的「精灵训练家 + 中文名」
CLASS_ZH: dict[str, str] = {
    "{53}{54} TRAINER": "精灵训练家",
    "HIKER": "登山男",
    "TEAM AQUA": "海洋队",
    "{53}{54} BREEDER": "培育家",
    "COOLTRAINER": "精英训练家",
    "BIRD KEEPER": "养鸟人",
    "COLLECTOR": "收藏家",
    "SWIMMER♂": "游泳男",
    "TEAM MAGMA": "熔岩队",
    "EXPERT": "达人",
    "AQUA ADMIN": "海洋队干部",
    "BLACK BELT": "空手道王",
    "AQUA LEADER": "海洋队老大",
    "HEX MANIAC": "灵异迷",
    "AROMA LADY": "香氛姐姐",
    "RUIN MANIAC": "遗迹迷",
    "INTERVIEWER": "采访者",
    "TUBER": "泳圈少年",
    "LADY": "千金小姐",
    "BEAUTY": "美女",
    "RICH BOY": "富家少爷",
    "POKéMANIAC": "宝可梦痴",
    "GUITARIST": "吉他手",
    "KINDLER": "营火专家",
    "CAMPER": "露营少年",
    "PICNICKER": "野餐女孩",
    "BUG MANIAC": "昆虫狂",
    "PSYCHIC": "超能力者",
    "GENTLEMAN": "绅士",
    "ELITE FOUR": "四天王",
    "LEADER": "馆主",
    "SCHOOL KID": "小学生",
    "SR. AND JR.": "年上年下",
    "WINSTRATE": "连胜家族",
    "POKéFAN": "爱好者",
    "YOUNGSTER": "少年",
    "CHAMPION": "冠军",
    "FISHERMAN": "垂钓者",
    "TRIATHLETE": "铁人三项",
    "DRAGON TAMER": "驯龙师",
    "NINJA BOY": "忍者少年",
    "BATTLE GIRL": "对战女孩",
    "PARASOL LADY": "阳伞姐姐",
    "SWIMMER♀": "游泳女",
    "TWINS": "双胞胎",
    "SAILOR": "水手",
    "MAGMA ADMIN": "熔岩队干部",
    "BUG CATCHER": "捕虫少年",
    "{53}{54} RANGER": "巡护员",
    "MAGMA LEADER": "熔岩队老大",
    "LASS": "迷你裙",
    "YOUNG COUPLE": "年轻夫妇",
    "OLD COUPLE": "黄金夫妇",
    "SIS AND BRO": "兄妹组合",
    "SALON MAIDEN": "管道天后",
    "DOME ACE": "巨蛋天王",
    "PALACE MAVEN": "宫殿管家",
    "ARENA TYCOON": "竞技大亨",
    "FACTORY HEAD": "工厂头目",
    "PIKE QUEEN": "选择女王",
    "PYRAMID KING": "金字塔王",
}


def pack13(zh: str) -> bytes:
    enc, missing = encode_text_safe(zh)
    if missing:
        raise ValueError(f"missing glyphs {missing} in {zh!r}")
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    if len(enc) > STRIDE:
        raise ValueError(f"too long {zh!r} need={len(enc)}")
    # leading-space pad (English style centering)
    pad = STRIDE - len(enc)
    return (b"\x00" * pad) + enc


def main() -> int:
    if OUT.exists() and (not ROM.exists() or ROM.stat().st_mtime < OUT.stat().st_mtime):
        ROM.parent.mkdir(parents=True, exist_ok=True)
        ROM.write_bytes(OUT.read_bytes())
    if not ROM.exists():
        print("missing rom")
        return 1

    golden = GOLDEN.read_bytes()
    data = bytearray(ROM.read_bytes())
    stats = {"ok": 0, "skip": 0, "fail": 0, "missing_map": 0}

    for i in range(COUNT):
        off = BASE + i * STRIDE
        chunk = golden[off : off + STRIDE]
        if 0xFF not in chunk:
            stats["fail"] += 1
            print("no eos", i, hex(off))
            continue
        eos = chunk.index(0xFF)
        en = decode_bytes(chunk[:eos]).strip()
        zh = CLASS_ZH.get(en)
        if zh is None:
            stats["missing_map"] += 1
            print("unmapped", i, repr(en))
            continue
        try:
            packed = pack13(zh)
        except ValueError as e:
            stats["fail"] += 1
            print("fail", i, e)
            continue
        if data[off : off + STRIDE] == packed:
            stats["skip"] += 1
            continue
        data[off : off + STRIDE] = packed
        stats["ok"] += 1
        print(f"OK {i:02d} {hex(off)} {en!r} -> {zh}")

    stamp = f"QH{int(time.time()) & 0xFFFFFFFF:08X}".encode("ascii")[:16].ljust(16, b"\x00")
    data[FP_OFF : FP_OFF + 16] = stamp

    ROM.write_bytes(data)
    OUT.write_bytes(data)
    print(json.dumps(stats, ensure_ascii=False), "fp", stamp.decode())
    return 0 if stats["fail"] == 0 and stats["missing_map"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
