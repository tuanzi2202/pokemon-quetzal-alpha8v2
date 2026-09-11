#!/usr/bin/env python3
"""Hand-fill remaining long EN dialogues (often leading-char truncated dumps)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fill_and_apply_remaining import CACHE, LOCALE, quality_ok, scrub  # noqa: E402

# Keys must match locale "en" exactly.
MANUAL: dict[str, str] = {
    " TATE{WAIT_CLEAR}“The mystic combination!”": " 傅戴{WAIT_CLEAR}「神秘的组合！」",
    (
        " draw as much hot water as we need,\n"
        "and yet the hot springs never run dry.{WAIT_CLEAR}"
        "Isn't it magical?{WAIT_CLEAR}"
        "These hot springs appear near active\n"
        "volcanoes. Veins of water under the{WAIT_SCROLL}"
        "ground are heated by magma to well up{WAIT_SCROLL}"
        "as hot springs."
    ): (
        " 想舀多少热水就有多少，\n"
        "温泉却永远不会干涸。{WAIT_CLEAR}"
        "是不是很神奇？{WAIT_CLEAR}"
        "这种温泉会出现在活火山附近。\n"
        "地下的水流被岩浆加热后{WAIT_SCROLL}"
        "涌出地面，就成了温泉。"
    ),
    " BALL{WAIT_SCROLL}for our most wonderful TRAINER!": " 球{WAIT_SCROLL}献给最棒的训练家！",
    " MT. PYRE\n“Forbidden to the faint of heart.”": " 送神山\n「心脏脆弱者勿入。」",
    (
        " Control Pad a little\n"
        "before the corner and slow down.{WAIT_CLEAR}"
        "Want to read a different page?"
    ): (
        " 拐弯前稍稍操作十字键\n"
        "减速。{WAIT_CLEAR}"
        "要看其他页吗？"
    ),
    (
        " Control Pad to the side\n"
        "to jump sideways.{WAIT_CLEAR}"
        "Press it backwards to make the BIKE\n"
        "change directions while jumping.{WAIT_CLEAR}"
        "Want to read a different page?"
    ): (
        " 向侧面按十字键\n"
        "可以横向跳跃。{WAIT_CLEAR}"
        "向后按则能在跳跃中\n"
        "让自行车转向。{WAIT_CLEAR}"
        "要看其他页吗？"
    ),
    (
        " of an amazing\n"
        "person like you.{WAIT_CLEAR}"
        "I understand that you're delivering\n"
        "a package to SLATEPORT's SHIPYARD.{WAIT_CLEAR}"
        "Well, on the way, could you stop off in\n"
        "DEWFORD TOWN?{WAIT_CLEAR}"
        "I was hoping that you'd deliver a\n"
        "LETTER to STEVEN in DEWFORD."
    ): (
        " 像你这样了不起的人。{WAIT_CLEAR}"
        "我知道你要把包裹\n"
        "送到凯那市造船厂。{WAIT_CLEAR}"
        "那就顺便去一趟\n"
        "武斗镇好吗？{WAIT_CLEAR}"
        "希望你能把一封信\n"
        "交给武斗镇的大吾。"
    ),
    (
        " If I told you to become my\n"
        "apprentice, you will refuse, I am sure.{WAIT_CLEAR}"
        "I would like to make a gift of my coat\n"
        "to you.{WAIT_CLEAR}"
        "But again, you will refuse.\n"
        "I imagine that to be so.{WAIT_CLEAR}"
        "And that, my friend, is a certain sign\n"
        "of nobility!"
    ): (
        " 若我说收你为徒，\n"
        "你肯定会拒绝。{WAIT_CLEAR}"
        "我想把外套送给你。{WAIT_CLEAR}"
        "但你大概又会拒绝。\n"
        "我想一定是这样。{WAIT_CLEAR}"
        "朋友，那正是高尚品格\n"
        "的证明！"
    ),
    (
        "ou have a LETTER bound for DEWFORD\n"
        "and a package for SLATEPORT, then?{WAIT_CLEAR}"
        "Quite the busy life you must lead!{WAIT_CLEAR}"
        "But, certainly, what you're asking is\n"
        "no problem at all.{WAIT_CLEAR}"
        "You've come to the right man!\n"
        "We'll set sail for DEWFORD."
    ): (
        "有一封去武斗镇的信\n"
        "和去凯那市的包裹，对吧？{WAIT_CLEAR}"
        "你可真忙啊！{WAIT_CLEAR}"
        "不过你拜托的事\n"
        "完全没问题。{WAIT_CLEAR}"
        "找我就对了！\n"
        "我们这就开船去武斗镇。"
    ),
    (
        " a lot of user-friendly features\n"
        "that make it fun and useful, too.{WAIT_CLEAR}"
        "“It makes me proud that I played\n"
        "a part in its development.{WAIT_CLEAR}"
        "“Here's hoping that you'll continue\n"
        "research in Storage Systems.{WAIT_CLEAR}"
        "“From BILL\n"
        "… … … … … … … …”"
    ): (
        " 还有很多方便的功能，\n"
        "既好玩又实用。{WAIT_CLEAR}"
        "「能参与它的开发，\n"
        "我很自豪。{WAIT_CLEAR}"
        "「希望你继续研究\n"
        "宝可梦存储系统。{WAIT_CLEAR}"
        "「——正辉\n"
        "…… …… ……」"
    ),
    (
        " really did come back to\n"
        "see me…{WAIT_CLEAR}"
        "… … … … … …{WAIT_CLEAR}"
        "You've won straight matches to see me…\n"
        "I won't have to hold back against you…{WAIT_CLEAR}"
        "It's been too long now…{WAIT_CLEAR}"
        "Too long since I've been able to battle\n"
        "without thinking about anything…"
    ): (
        " 真的回来见我了……{WAIT_CLEAR}"
        "………………{WAIT_CLEAR}"
        "你连胜一路来见我……\n"
        "我不必再对你手下留情……{WAIT_CLEAR}"
        "已经太久了……{WAIT_CLEAR}"
        "太久没有能什么都不想、\n"
        "只管对战的时候了……"
    ),
    (
        "t anymore!{WAIT_CLEAR}"
        "Let's go to a MULTI BATTLE ROOM\n"
        "right this instant!{WAIT_CLEAR}"
        "If we get together in the BATTLE SALON,\n"
        "the power of our love will overcome{WAIT_SCROLL}"
        "everyone we meet.{WAIT_CLEAR}"
        "Why, before us, darling, everything\n"
        "will topple like dominoes!"
    ): (
        "够了！{WAIT_CLEAR}"
        "我们现在就去\n"
        "多人对战房间！{WAIT_CLEAR}"
        "只要在对战沙龙里联手，\n"
        "我们爱情的力量就能战胜{WAIT_SCROLL}"
        "所有对手。{WAIT_CLEAR}"
        "亲爱的，在我们面前\n"
        "一切都会像多米诺一样倒下！"
    ),
    (
        " the honor of beating\n"
        "seven TRAINERS in succession,{WAIT_SCROLL}"
        "we will present you with Battle Points.{WAIT_CLEAR}"
        "If you want to interrupt your\n"
        "challenge, please save the game.{WAIT_CLEAR}"
        "If you don't save before interrupting,\n"
        "you will be disqualified."
    ): (
        " 若光荣地连续击败\n"
        "七位训练家，{WAIT_SCROLL}"
        "我们将赠予对战点数。{WAIT_CLEAR}"
        "若要中断挑战，\n"
        "请先保存游戏。{WAIT_CLEAR}"
        "若不保存就中断，\n"
        "将被取消资格。"
    ),
    " CASE yet.{WAIT_CLEAR}In that case, we need to provide you\nwith this!": (
        " 盒子。{WAIT_CLEAR}这样的话，我们得先给你\n这个！"
    ),
    (
        " BALLS to catch it: {FD:04}!{WAIT_CLEAR}"
        "It finally took a single {FD:03}\n"
        "to catch it!"
    ): (
        " 球数：{FD:04}！{WAIT_CLEAR}"
        "最后只用了1个{FD:03}\n"
        "就抓住了！"
    ),
    " CASE is full.\nThe BERRY BLENDER can't be used.": (
        " 盒子满了。\n树果混合器无法使用。"
    ),
    " CASE from\nthe LILYCOVE CONTEST HALL.": (
        " 盒子从\n琉璃市华丽大赛会场获得。"
    ),
    (
        "ve you'll advise me!{WAIT_SCROLL}"
        "I… I'm so happy…{WAIT_CLEAR}"
        "What I want to ask you is really\n"
        "trivial, but I can't decide…{WAIT_CLEAR}"
        "At the BATTLE TOWER, they let you\n"
        "choose Level 50 or Open Level.{WAIT_CLEAR}"
        "Which course do you think even I may\n"
        "have a chance at?"
    ): (
        "请务必给我建议！{WAIT_SCROLL}"
        "我……我太高兴了……{WAIT_CLEAR}"
        "我想问的其实很小，\n"
        "但我就是定不下来……{WAIT_CLEAR}"
        "在对战塔可以选择\n"
        "50级或自由等级。{WAIT_CLEAR}"
        "你觉得我还有机会\n"
        "挑战哪一条路线？"
    ),
    " Please start over from the beginning.": " 请从头再来。",
    "  The WIRELESS COMMUNICATION\nSYSTEM search has been canceled.": (
        "  无线通讯系统\n搜索已取消。"
    ),
    " is/are not\nready yet.{WAIT_CLEAR}": " 尚未\n准备好。{WAIT_CLEAR}",
    "   You stopped being a member.{WAIT_CLEAR}": "   你已退出成员。{WAIT_CLEAR}",
    (
        " The other TRAINER challenges you\n"
        "to battle.{WAIT_CLEAR}"
        "Will you accept the battle\n"
        "challenge?"
    ): (
        " 对方训练家向你\n"
        "发起对战。{WAIT_CLEAR}"
        "要接受对战\n"
        "挑战吗？"
    ),
    "  The chat has been dropped.{WAIT_CLEAR}": "  聊天已断开。{WAIT_CLEAR}",
    "   The chat was ended.{WAIT_CLEAR}": "   聊天已结束。{WAIT_CLEAR}",
    (
        "                                                                                                                                                                "
        "If you want to do something with\n"
        "me, just give me a shout!{WAIT_CLEAR}"
    ): (
        "                                                                                                                                                                "
        "想找我做什么的话，\n"
        "喊我就行！{WAIT_CLEAR}"
    ),
    " You used that move?\nThat's good strategy!{WAIT_CLEAR}": (
        " 你用了那个招式？\n好策略！{WAIT_CLEAR}"
    ),
    " Oh?\nSomething like that happened.{WAIT_CLEAR}": (
        " 哦？\n原来发生过那种事。{WAIT_CLEAR}"
    ),
    "  Cancel the registration of your\nLv. {FD:03} {FD:02}?": (
        "  取消登记\nLv.{FD:03}的{FD:02}吗？"
    ),
    "   The registration has been canceled.{WAIT_CLEAR}": (
        "   登记已取消。{WAIT_CLEAR}"
    ),
    "  BERRY CRUSH!\nPlease choose the LEADER.": (
        "  树果粉碎！\n请选择队长。"
    ),
    " DODRIO BERRY-PICKING!\nPlease choose the LEADER.": (
        " 嘟嘟利摘树果！\n请选择队长。"
    ),
    " not found.\nPlease try again.{WAIT_CLEAR}": (
        " 未找到。\n请重试。{WAIT_CLEAR}"
    ),
    " CASE is full.{WAIT_CLEAR}": " 盒子满了。{WAIT_CLEAR}",
    "  Read the WONDER CARDS in your\npossession.": (
        "  阅读你持有的\n神秘卡片。"
    ),
    " You don't have any WONDER NEWS,\nso new NEWS will be input.": (
        " 你没有神秘新闻，\n将写入新的新闻。"
    ),
    "  You already had that\nWONDER NEWS item.": (
        "  你已经有过那条\n神秘新闻道具。"
    ),
    " If you throw away the CARD,\nits event won't happen. Okay?": (
        " 若丢弃卡片，\n相关活动将不会发生。可以吗？"
    ),
}


def main() -> int:
    need_path = ROOT / "work" / "gtrans_need.json"
    need = json.loads(need_path.read_text(encoding="utf-8")) if need_path.exists() else []
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]

    hit = miss = 0
    for en in need:
        zh = MANUAL.get(en)
        if not zh:
            # fuzzy: strip leading spaces match
            for k, v in MANUAL.items():
                if k.lstrip() == en.lstrip() or scrub(k) == scrub(en):
                    zh = v
                    break
        if zh and quality_ok(en, scrub(zh)):
            cache[en] = scrub(zh)
            hit += 1
        elif zh:
            # still force-store; apply uses quality_ok — ensure passes
            cache[en] = scrub(zh)
            hit += 1
            if not quality_ok(en, scrub(zh)):
                print("WARN quality_ok false after scrub:", repr(en[:60]))
        else:
            miss += 1
            print("MISS", repr(en[:80]))

    for r in rows:
        en = r.get("en") or ""
        if en in cache and quality_ok(en, scrub(cache[en])):
            r["zh"] = scrub(cache[en])
        elif en in MANUAL and quality_ok(en, scrub(MANUAL[en])):
            r["zh"] = scrub(MANUAL[en])
            cache[en] = r["zh"]

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    LOCALE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(f"filled={hit} miss={miss} cache={len(cache)}")
    return 0 if miss == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
