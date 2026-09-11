#!/usr/bin/env python3
"""Translate remaining pure-English / no-CJK locale rows (mostly short UI)."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_locale_zh import is_junk_en  # noqa: E402
from chs_encode import encode_text_safe  # noqa: E402
from fill_and_apply_remaining import (  # noqa: E402
    CACHE,
    GOLDEN,
    LOCALE,
    OUT,
    ROM,
    quality_ok,
    scrub,
    translate_one,
)
from fill_latin_mix import apply_glossary  # noqa: E402
from restore_clock_ui import CLOCK_EN, DAY, FC_POOL  # noqa: E402

# Exact short UI map (common Gen3 / link strings)
EXACT: dict[str, str] = {
    "YES": "是",
    "NO": "否",
    "OK": "确定",
    "CANCEL": "取消",
    "CONFIRM": "确认",
    "QUIT": "退出",
    "EXIT": "退出",
    "MALE": "男性",
    "FEMALE": "女性",
    "BOY": "男孩",
    "GIRL": "女孩",
    "BAG": "背包",
    "SAVE": "保存",
    "SAVE?": "保存？",
    "MENU": "菜单",
    "INFO": "信息",
    "NAME": "名字",
    "NICKNAME": "昵称",
    "LEVEL": "等级",
    "TYPE": "属性",
    "STATUS": "状态",
    "ATTACK": "攻击",
    "DEFENSE": "防御",
    "SPEED": "速度",
    "HP": "体力",
    "PP": "PP",
    "EXP": "经验",
    "NEXT": "下一个",
    "BACK": "返回",
    "CLOSE": "关闭",
    "TRADE": "交换",
    "BATTLE": "对战",
    "LINK": "联机",
    "PRESS START": "按 START",
    "PRESS A": "按 A",
    "A Button": "A键",
    "B Button": "B键",
    "B Button: Cancel": "B键：取消",
    "Control Pad": "十字键",
    "Communication standby…": "通讯待机……",
    "Communication standby…\nB Button: Cancel": "通讯待机……\nB键：取消",
    "An EGG can't be traded now.": "现在不能交换蛋。",
    " Want to do something?": "要做什么吗？",
    "Want to do something?": "要做什么吗？",
    "nature,\nobtained in a trade.": "性格，\n通过交换获得。",
    " , has\nleft, ending the chat.": "，已离开，\n聊天结束。",
    " Awaiting {FD:02}'s response…": "等待{FD:02}的回应……",
    "Awaiting {FD:02}'s response…": "等待{FD:02}的回应……",
    " Control\nPad, then press the A Button.": "用十字键选择，\n再按A键。",
    "Control\nPad, then press the A Button.": "用十字键选择，\n再按A键。",
    " {FD:02} checked the\nTRADING BOARD.{WAIT_CLEAR}": "{FD:02}查看了\n交换告示板。{WAIT_CLEAR}",
    "{FD:02} checked the\nTRADING BOARD.{WAIT_CLEAR}": "{FD:02}查看了\n交换告示板。{WAIT_CLEAR}",
}

PHRASE: list[tuple[str, str]] = [
    (r"(?i)Communication standby", "通讯待机"),
    (r"(?i)B Button:\s*Cancel", "B键：取消"),
    (r"(?i)A Button", "A键"),
    (r"(?i)B Button", "B键"),
    (r"(?i)Control Pad", "十字键"),
    (r"(?i)TRADING BOARD", "交换告示板"),
    (r"(?i)can't be traded", "不能交换"),
    (r"(?i)ending the chat", "聊天结束"),
    (r"(?i)has\nleft", "已离开"),
    (r"(?i)Awaiting", "等待"),
    (r"(?i)response", "回应"),
    (r"(?i)Want to do something", "要做什么吗"),
    (r"(?i)obtained in a trade", "通过交换获得"),
    (r"(?i)press the A Button", "按A键"),
    (r"(?i)checked the", "查看了"),
    (r"(?i)\bCancel\b", "取消"),
    (r"(?i)\bConfirm\b", "确认"),
    (r"(?i)\bTrade\b", "交换"),
    (r"(?i)\bBattle\b", "对战"),
    (r"(?i)\bLink\b", "联机"),
    (r"(?i)\bMale\b", "男性"),
    (r"(?i)\bFemale\b", "女性"),
    (r"(?i)\bEgg\b", "蛋"),
    (r"(?i)\bEGG\b", "蛋"),
]


def is_clock_row(off: int, en: str) -> bool:
    """Only skip day names / clock prompts — not the whole FC pool."""
    if DAY.match((en or "").strip()):
        return True
    if CLOCK_EN.search(en or ""):
        return True
    if off in (0x287A50, 0x101BB9F, 0x1020486, 0x1020666, 0x10206EF):
        return True
    return False


def translate_short(en: str) -> str | None:
    e = en.strip()
    if not e:
        return None
    if e in EXACT:
        return EXACT[e]
    # strip leading spaces key
    if en in EXACT:
        return EXACT[en]
    for k, v in EXACT.items():
        if k.strip() == e:
            return v
    out = en
    for pat, rep in PHRASE:
        out = re.sub(pat, rep, out)
    out = apply_glossary(out)
    out = scrub(out)
    if any("\u4e00" <= c <= "\u9fff" for c in out) and out != en:
        return out
    return None


def has_cjk(t: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in t)


def inplace(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    capacity = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if len(enc) > capacity:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > capacity:
            cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        if len(enc) > capacity:
            return "too_long"
    data[off : off + capacity] = enc + b"\x00" * (capacity - len(enc))
    return "ok"


def main() -> int:
    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    need = []
    for r in rows:
        off = int(r["offset"])
        en = r.get("en") or ""
        zh = scrub(r.get("zh") or "")
        if is_junk_en(en) or is_clock_row(off, en):
            continue
        # target: no CJK in zh (or empty but has english content we want — skip empty clock already)
        if zh and has_cjk(zh) and quality_ok(en, zh):
            continue
        if zh and has_cjk(zh):
            continue
        # empty zh with real english (non-clock) — also fill
        if not en.strip():
            continue
        if sum(c.isalpha() for c in en) < 2:
            continue
        # skip pure garbage alphabet dumps
        if re.search(r"zzilziiz|iiiiiiii", en):
            continue
        need.append(r)

    print(f"need={len(need)}", flush=True)
    ok = mt = fail = 0
    for i, r in enumerate(need):
        en = r.get("en") or ""
        zh = translate_short(en)
        if not zh or not has_cjk(zh):
            # MT for longer; for very short try engines too
            src = en.strip()[:900]
            if src:
                for eng in ("bing", "alibaba", "youdao"):
                    zh = translate_one(src, eng)
                    if zh and has_cjk(zh):
                        mt += 1
                        break
                    time.sleep(0.04)
        if zh:
            zh = scrub(apply_glossary(zh))
            # keep leading space style lightly
            if en[:1] == " " and not zh.startswith(" "):
                zh = " " + zh.lstrip()
        if zh and has_cjk(zh):
            r["zh"] = zh
            cache[en] = zh
            ok += 1
        else:
            fail += 1
        if (i + 1) % 40 == 0:
            print(f"  {i+1}/{len(need)} ok={ok} mt={mt} fail={fail}", flush=True)
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    LOCALE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    applied = long = 0
    for r in rows:
        off = int(r["offset"])
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        if is_clock_row(off, en) or is_junk_en(en) or not zh:
            continue
        if not has_cjk(zh):
            continue
        # relax quality for short UI
        if not quality_ok(en, zh) and len(en.strip()) > 24:
            continue
        st = inplace(data, golden, off, zh)
        if st == "ok":
            applied += 1
        elif st == "too_long":
            long += 1

    # Restore only clock day names / system prompts (never whole FC pool)
    from restore_clock_ui import CLOCK_OFFSETS, DAY, FC_POOL, restore_body  # noqa: E402

    a, b = FC_POOL
    for off in sorted(CLOCK_OFFSETS):
        restore_body(data, golden, off)
    off = a
    while off < b:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= b or eos - off > 40:
            off += 1
            continue
        from gen3_charmap import decode_bytes as _dec  # noqa: E402

        text = _dec(golden[off : eos + 1]).strip()
        if DAY.match(text):
            restore_body(data, golden, off)
        off = eos + 1
    for off in (0x287A50, 0x101BB9F, 0x1020486, 0x1020666, 0x10206EF):
        restore_body(data, golden, off)

    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print(f"done ok={ok} mt_used={mt} fail={fail} applied={applied} too_long={long}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
