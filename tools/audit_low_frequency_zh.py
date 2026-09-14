#!/usr/bin/env python3
"""Audit Easy Chat and other low-frequency localization surfaces."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text, encode_text_safe  # noqa: E402
from force_mode_zh import INPLACE_MODE_WIZARD  # noqa: E402
from force_randomizer_zh import INPLACE_FORCED  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"
EASY_CHAT = ROOT / "locale" / "zh_CN" / "easy_chat_zh.jsonl"
UNALIGNED = ROOT / "locale" / "zh_CN" / "low_frequency_unaligned_zh.jsonl"

GROUP_COUNTS = {
    "trainer": 27,
    "status": 109,
    "battle": 63,
    "greetings": 42,
    "people": 75,
    "voices": 63,
    "speech": 60,
    "endings": 69,
    "feelings": 69,
    "conditions": 69,
    "actions": 78,
    "lifestyle": 45,
    "hobbies": 54,
    "time": 45,
    "misc": 42,
    "adjectives": 36,
    "events": 29,
    "trendy_saying": 33,
}

# These labels and system messages are especially prone to plausible-looking
# machine translation, so exact wording is part of the regression contract.
EXPECTED = {
    2580963: "妈妈：{FD:01}，我们到了，宝贝！{WAIT_CLEAR}和行李一起坐搬家卡车，\n一定很累吧。{WAIT_CLEAR}这里就是未白镇。{WAIT_CLEAR}感觉怎么样？\n这就是我们的新家！{WAIT_CLEAR}虽然有些朴素，住起来\n应该很舒服，对吧？{WAIT_CLEAR}而且你也有自己的房间了，{FD:01}！\n我们进去吧。",
    2649661: "搬家工的宝可梦把搬家和\n打扫工作全包了。{WAIT_SCROLL}真方便啊！{WAIT_CLEAR}{FD:01}，你的房间在楼上。\n去看看吧！{WAIT_CLEAR}爸爸买了个新时钟，\n纪念我们搬到这里。{WAIT_SCROLL}别忘了调好时间！",
    2649997: "妈妈：啊！{FD:01}，{FD:01}！\n快！快过来！",
    2653239: "这是一台任天堂GameCube。{WAIT_CLEAR}连接着一台Game Boy Advance，\n可作为控制器使用。",
    2941788: "想在这里建立你的秘密基地吗？",
    2652752: "时钟停了……{WAIT_CLEAR}把时间调好，让它走起来吧！",
    2652842: "好！所有东西都收拾整齐了！{WAIT_CLEAR}楼下的搬家工作\n也全部完成了。{WAIT_CLEAR}搬家工宝可梦真方便！{WAIT_CLEAR}对了，你最好检查一下\n桌上的东西是否齐全。",
    16890783: "内置电池电量已耗尽。\n游戏仍可继续。{WAIT_CLEAR}但与时钟相关的事件\n将不再发生。",
    16890902: "图鉴",
    16890918: "A键",
    16890968: "十字键",
    16907395: "请选择4个词语",
    16907425: "组成你的个人简介。",
    16907477: "组成一句话。",
    16907802: "邮件正文",
    16907907: "当前流行语",
    16908221: "退出编辑吗？",
    16908737: "个人简介",
    16908855: "采访",
    16908865: "一句格言",
    16908877: "粉丝的问题",
    16909065: "谜题的答案是？",
    16909446: "备份存储器损坏，或\n内置电池电量已耗尽。\n仍可游戏，但无法保存。",
    16909926: "时钟已重设。\n正在保存数据，请稍候。",
    16910063: "现在可以使用游戏内时钟\n校准功能了。",
    16918289: "宝可梦",
    16918293: "训练家",
    16918301: "状态",
    16918308: "对战",
    16918315: "问候语",
    16918325: "人物",
    16918332: "拟声词",
    16918339: "口语",
    16918346: "句尾",
    16918354: "感受",
    16918363: "状况",
    16918374: "动作",
    16918382: "生活",
    16918392: "爱好",
    16918400: "时间",
    16918405: "杂项",
    16918411: "形容词",
    16918422: "事件",
    16918429: "招式1",
    16918436: "招式2",
    16918443: "流行语",
    16918461: "宝可梦2",
    16923247: "全部清除",
    16923266: "测验",
    16923282: "精灵球",
    16923303: "你已用掉该区域的遭遇机会！{FC:09}",
    3538965: "名字是{FD:01}{FD:05}，对吗？",
}

FORBIDDEN = (
    "好的说",
    "时髦的说",
    "组合四个单词",
    "组合六个单词",
    "组合九个单词",
    "去中心化交易所",
    "一个按钮",
    "风扇的问题",
    "德尔。所有",
    "我的联盟",
    "我的中心",
    "测试的答案",
    "混杂。",
    "移动1",
    "在党",
)

CONTROL_RE = re.compile(r"\{(?:WAIT_SCROLL|WAIT_CLEAR|F[CD9]:[0-9A-Fa-f]{2}|[0-9A-Fa-f]{2})\}")


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-issues", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []
    golden = GOLDEN.read_bytes()
    locale_rows = read_jsonl(LOCALE)
    locale = {int(row["offset"]): row for row in locale_rows}
    easy_rows = read_jsonl(EASY_CHAT)
    unaligned_rows = read_jsonl(UNALIGNED)

    actual_counts = Counter(str(row.get("group")) for row in easy_rows)
    if actual_counts != Counter(GROUP_COUNTS):
        failures.append(f"Easy Chat group counts differ: {dict(actual_counts)}")
    offsets = [int(row["offset"]) for row in easy_rows]
    if len(easy_rows) != 1008 or len(set(offsets)) != 1008:
        failures.append(f"Easy Chat requires 1008 unique rows, got {len(easy_rows)}/{len(set(offsets))}")
    for row in easy_rows:
        offset = int(row["offset"])
        slot = int(row["slot"])
        en = str(row.get("en") or "")
        zh = str(row.get("zh") or "")
        try:
            source = encode_text(en)
        except KeyError as exc:
            failures.append(f"Easy Chat source cannot encode at {offset:#x}: {exc}")
            continue
        if len(source) != slot or golden[offset:offset + slot] != source:
            failures.append(f"Easy Chat source drift at {offset:#x}: {en!r}")
        _encoded, missing = encode_text_safe(zh)
        if not zh or (zh == en and re.search(r"[A-Za-z]", en)):
            failures.append(f"Easy Chat untranslated at {offset:#x}: {en!r}")
        if missing:
            failures.append(f"Easy Chat missing glyph at {offset:#x}: {sorted(set(missing))}")

    for offset, expected in EXPECTED.items():
        row = locale.get(offset)
        if row is None:
            failures.append(f"locale row missing at {offset:#x}")
            continue
        actual = str(row.get("zh") or "")
        if actual != expected:
            failures.append(f"locale wording drift at {offset:#x}: {actual!r} != {expected!r}")

    editor_rows = [row for row in locale_rows if 16907395 <= int(row["offset"]) <= 16909293]
    for row in editor_rows:
        offset = int(row["offset"])
        en = str(row.get("en") or "")
        zh = str(row.get("zh") or "")
        _encoded, missing = encode_text_safe(zh)
        if not zh or zh == en:
            failures.append(f"Easy Chat editor untranslated at {offset:#x}: {en!r}")
        if CONTROL_RE.findall(en) != CONTROL_RE.findall(zh):
            failures.append(f"Easy Chat editor control mismatch at {offset:#x}")
        if missing:
            failures.append(f"Easy Chat editor missing glyph at {offset:#x}: {sorted(set(missing))}")

    for row in locale_rows:
        zh = str(row.get("zh") or "")
        for phrase in FORBIDDEN:
            if phrase in zh:
                failures.append(f"machine-translation remnant at {int(row['offset']):#x}: {phrase!r}")

    in_place_contract = (*INPLACE_MODE_WIZARD, *INPLACE_FORCED)
    for offset, en, zh in in_place_contract:
        source = encode_text(en)
        encoded, missing = encode_text_safe(zh)
        if golden[offset:offset + len(source)] != source:
            failures.append(f"in-place source drift at {offset:#x}: {en!r}")
        if len(encoded) > len(source):
            failures.append(f"in-place translation overflow at {offset:#x}: {len(encoded)} > {len(source)}")
        if missing:
            failures.append(f"in-place missing glyph at {offset:#x}: {sorted(set(missing))}")

    for row in unaligned_rows:
        offset = int(row["offset"])
        en = str(row["en"])
        zh = str(row["zh"])
        source = encode_text(en)
        _encoded, missing = encode_text_safe(zh)
        if golden[offset:offset + len(source)] != source:
            failures.append(f"unaligned source drift at {offset:#x}")
        if CONTROL_RE.findall(en) != CONTROL_RE.findall(zh):
            failures.append(f"unaligned control mismatch at {offset:#x}")
        if missing:
            failures.append(f"unaligned missing glyph at {offset:#x}: {sorted(set(missing))}")
        if row.get("in_place") and len(_encoded) > len(source):
            failures.append(f"unaligned in-place overflow at {offset:#x}")
        expected_ptr = (0x08000000 + offset).to_bytes(4, "little")
        for site in row["pointer_sites"]:
            site = int(site)
            if golden[site:site + 4] != expected_ptr:
                failures.append(f"unaligned pointer drift at {site:#x}")

    summary = {
        "easy_chat_rows": len(easy_rows),
        "easy_chat_groups": len(actual_counts),
        "editor_rows": len(editor_rows),
        "exact_contract_rows": len(EXPECTED),
        "in_place_contract_rows": len(in_place_contract),
        "unaligned_script_rows": len(unaligned_rows),
        "failures": len(failures),
    }
    print(json.dumps(summary, ensure_ascii=False))
    if failures:
        print("\n".join(failures[:100]))
    return 2 if args.fail_on_issues and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
