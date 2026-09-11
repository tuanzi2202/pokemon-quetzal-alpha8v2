#!/usr/bin/env python3
"""Translate EN JSONL -> zh_CN. Exact phrases only — no mid-string word salad."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PHRASES: list[tuple[str, str]] = [
    ("The Wireless Adapter is not\nconnected.", "没有连接无线适配器。"),
    ("NEW GAME", "新游戏"),
    ("CONTINUE", "继续游戏"),
    ("OPTION", "选项"),
    ("OPTIONS", "选项"),
    ("MYSTERY GIFT", "神秘礼物"),
    ("MYSTERY EVENTS", "神秘事件"),
    ("TEXT SPEED", "文字速度"),
    ("BATTLE STYLE", "对战动画"),
    ("BUTTON MODE", "按键模式"),
    ("FRAME", "窗口边框"),
    ("CANCEL", "取消"),
    ("CONFIRM", "确认"),
    ("POKéDEX", "图鉴"),
    ("POKeDEX", "图鉴"),
    ("POKéMON", "宝可梦"),
    ("POKeMON", "宝可梦"),
    ("POKéNAV", "导航"),
    ("POKeNAV", "导航"),
    ("POKEMON", "宝可梦"),
    ("BAG", "背包"),
    ("SAVE", "保存"),
    ("Multiplayer", "多人游戏"),
    ("MULTIPLAYER", "多人游戏"),
    ("YES", "是"),
    ("NO", "否"),
    ("FAST", "快"),
    ("SLOW", "慢"),
    ("MID", "中"),
    ("MEDIUM", "中"),
    ("SOUND", "声音"),
    ("STEREO", "立体声"),
    ("MONO", "单声道"),
    ("SHIFT", "替换"),
    ("SET", "固定"),
    ("TYPE", "属性"),
    ("NATURE", "性格"),
    ("STATUS", "状态"),
    ("MOVES", "招式"),
    ("MOVE", "招式"),
    ("ITEM", "道具"),
    ("ITEMS", "道具"),
    ("USE", "使用"),
    ("GIVE", "给予"),
    ("TOSS", "扔掉"),
    ("REGISTER", "登记"),
    ("SELECT", "选择"),
    ("START", "开始"),
    ("CONTROLS", "操作说明"),
    ("BADGES", "徽章"),
    ("TIME", "时间"),
    ("MALE", "男性"),
    ("FEMALE", "女性"),
    ("BOY", "男孩"),
    ("GIRL", "女孩"),
    ("NAME", "昵称"),
    ("PARTY", "同行"),
    ("BOX", "盒子"),
    ("MAP", "地图"),
    ("EXIT", "退出"),
    ("CLOSE", "关闭"),
    ("NEXT", "下一个"),
    ("BACK", "返回"),
    ("FIGHT", "战斗"),
    ("RUN", "逃跑"),
    ("CATCH", "捕捉"),
    ("SWITCH", "替换"),
    ("SUMMARY", "概况"),
    ("LEVEL", "等级"),
    ("PLAYER", "玩家"),
    ("ATTACK", "攻击"),
    ("DEFENSE", "防御"),
    ("SPEED", "速度"),
    ("SP. ATK", "特攻"),
    ("SP. DEF", "特防"),
    ("VERY EASY", "非常简单"),
    ("VERY HARD", "非常困难"),
    ("VERY LOW", "极低"),
    ("VERY HIGH", "极高"),
    ("EASIEST", "最简单"),
    ("EASY", "简单"),
    ("NORMAL", "普通"),
    ("HARD", "困难"),
    ("HARDEST", "最难"),
    ("CHEATS", "作弊"),
    ("RANDOM", "随机"),
    ("CUSTOM OPTIONS", "自定义选项"),
    ("DEFAULT OPTIONS", "默认选项"),
    ("CUSTOM", "自定义"),
    ("NORMAL MODE", "普通模式"),
    ("COOP MODE", "协作模式"),
    ("E-MODE", "E模式"),
    ("G-MODE", "G模式"),
    ("NEVER", "从不"),
    ("ALWAYS", "总是"),
    ("LOW", "低"),
    ("HIGH", "高"),
    ("Choose game mode.", "选择游戏模式。"),
    ("Choose game difficulty.", "选择游戏难度。"),
    ("Choose pokedex mode.", "选择图鉴模式。"),
    ("Choose custom or default options.", "选择自定义或默认选项。"),
    ("Choose one of these default options.", "请选择以下默认选项之一。"),
    ("Unlock cheats?", "解锁作弊？"),
    ("Choose shiny probability.", "选择闪光概率。"),
    ("Choose radiant probability.", "选择光耀概率。"),
    ("UNLOCK AREAS AFTER HALL OF FAME", "殿堂后解锁地区"),
    ("UNLOCK AREAS AT THE START", "开局解锁地区"),
    ("Level cap by badges?", "徽章等级上限？"),
    ("UNLOCK ALL MISC AFTER HALL OF FAME", "殿堂后解锁全部杂项"),
    ("UNLOCK ALL MISC AT THE START", "开局解锁全部杂项"),
    ("Unlock all miscellaneous?", "解锁全部杂项？"),
    ("UNLOCK AFTER HALL OF FAME", "殿堂后解锁"),
    ("UNLOCK AT THE START", "开局解锁"),
    ("UNLOCK AFTER 6TH BADGE", "第6枚徽章后解锁"),
    ("Unlock exp. share all?", "解锁经验分享全体？"),
    ("Unlock exp multiplier?", "解锁经验倍率？"),
    ("Unlock teleport?", "解锁传送？"),
    ("Unlock respawn items/berries?", "解锁道具/树果刷新？"),
    ("Unlock battle rematches?", "解锁再战？"),
    ("Unlock portable PC heals pokemon?", "解锁便携电脑治疗？"),
    ("Shiny odds: ", "闪光概率："),
    ("Radiant odds: ", "光耀概率："),
    ("Wait...", "请稍候…"),

    ("What will\n{FD:01} do?", "{FD:01}要\n做什么？"),
    ("Got away safely!", "成功逃走了！"),
    ("It's super effective!", "效果拔群！"),
    ("It's not very effective…", "效果不太好…"),
    ("A critical hit!", "击中要害！"),
    ("The save file has been updated.", "存档已更新。"),
    ("The save file is corrupted. The\nprevious save file will be loaded.", "存档已损坏。\n将读取上一次的存档。"),
    ("The save file has been erased\ndue to corruption or damage.", "存档因损坏已被清除。"),
    ("Updating save file using external\ndata. Please wait.", "正在用外部数据更新存档。\n请稍候。"),
]


def translate_line(en: str) -> str:
    if not en:
        return en
    for a, b in sorted(PHRASES, key=lambda x: -len(x[0])):
        if en == a:
            return b
    return en


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dump" / "menu_title.jsonl"
    dst_dir = ROOT / "locale" / "zh_CN"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name.replace(".jsonl", "_zh.jsonl")
    n = changed = 0
    with src.open(encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            row = json.loads(line)
            en = row.get("en", "")
            zh = translate_line(en)
            row["zh"] = zh
            if zh != en:
                changed += 1
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    print(f"translated {n} changed {changed} -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
