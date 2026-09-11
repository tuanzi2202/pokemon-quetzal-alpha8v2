#!/usr/bin/env python3
"""Hand-fixed opening Mom/May (and scrub MT garbage) then inplace-apply."""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chs_encode import encode_text_safe  # noqa: E402

CACHE = ROOT / "work" / "gtrans_cache.json"
LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"
ROM = ROOT / "work" / "cn_build.gba"
GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"

# offset -> full Chinese (controls preserved)
HAND: dict[int, str] = {
    # --- opening (clock / TV) ---
    0x287A82: (
        "妈妈：{FD:01}，喜欢你的\n新房间吗？{WAIT_CLEAR}"
        "很好！东西都收拾整齐了！{WAIT_CLEAR}"
        "楼下也全部搬进来了。{WAIT_CLEAR}"
        "宝可梦搬家公司真方便！{WAIT_CLEAR}"
        "对了，你也去看看桌上的\n东西是不是都在吧。"
    ),
    0x286F1B: (
        "妈妈：怎么了，{FD:01}？{WAIT_CLEAR}"
        "不去看看自己的房间吗？"
    ),
    0x286F5E: "妈妈：{FD:01}。{WAIT_CLEAR}去把自己房间的钟调好吧，宝贝。",
    0x286F8D: "妈妈：啊！{FD:01}，{FD:01}！\n快！快过来！",
    0x286FB3: "妈妈：快看！是橙华道馆！\n说不定爸爸会出现哦！",
    0x286FE8: (
        "妈妈：啊……结束了。{WAIT_CLEAR}"
        "我想爸爸有出镜，可我们错过了。\n真可惜。"
    ),
    0x286E3D: (
        "搬家的宝可梦把行李\n都搬进来了，还帮忙打扫。{WAIT_SCROLL}"
        "真是太方便了！{WAIT_CLEAR}"
        "{FD:01}，你的房间在楼上。\n去看看吧，宝贝！{WAIT_CLEAR}"
        "爸爸买了个新时钟，\n纪念我们搬来这里。{WAIT_SCROLL}"
        "别忘了把钟调好！"
    ),
    0x287A50: "时钟停了……{WAIT_CLEAR}最好设定好再开始！",
    0x28702C: (
        "对了。\n爸爸有个朋友住在镇上。{WAIT_CLEAR}"
        "他叫小田卷博士。{WAIT_CLEAR}"
        "就住在旁边，你该去打个招呼。"
    ),
    0x2871B5: (
        "别太勉强自己，宝贝。\n随时都可以回家。{WAIT_CLEAR}"
        "加油，宝贝！"
    ),
    0x287280: "已将妈妈登记到\n宝可梦导航器。",
    0x2872BD: "记者：……以上就是\n从橙华道馆前发回的报道。",
    0x287306: (
        "电视正在放电影。{WAIT_CLEAR}"
        "两个男人在巨大的钢琴键盘上跳舞。{WAIT_CLEAR}"
        "还是出门吧！"
    ),
    0x28735D: (
        "这是跑步鞋的说明书。{WAIT_CLEAR}"
        "“穿着跑步鞋时按B键就能奔跑。”{WAIT_CLEAR}"
        "“穿上跑步鞋，到野外尽情奔跑吧！”"
    ),
    0x287552: (
        "我该回橙华道馆了。{WAIT_CLEAR}"
        "妈妈，我不在的时候\n家里就拜托你了。"
    ),
    0x287666: (
        "现在为您插播紧急新闻！{WAIT_CLEAR}"
        "在丰缘各地，出现了\n目击传说宝可梦的报告……"
    ),
    0x2870CF: "妈妈：你有没有去向\n小田卷博士打过招呼？",
    0x2870FF: (
        "妈妈：还好吗，{FD:01}？\n你看起来有点累。{WAIT_CLEAR}"
        "我看你该休息一下了。"
    ),
    0x28716A: (
        "妈妈：哦？那枚徽章是爸爸给你的？{WAIT_CLEAR}"
        "那妈妈也给你一样东西吧！"
    ),
    0x287205: (
        "妈妈：那是什么，宝贝？宝可梦导航器？\n得文公司的人给你的？{WAIT_CLEAR}"
        "那，宝贝，要不要把妈妈\n也登记进去呢？{WAIT_CLEAR}"
        "…… …… ……"
    ),
    0x2875B0: (
        "妈妈：你那个爸爸啊……{WAIT_CLEAR}"
        "好不容易回家一趟，\n开口闭口却都是宝可梦。{WAIT_CLEAR}"
        "真该放松一下，多待一会儿。"
    ),
    0x287642: "妈妈：那是紧急新闻吗？",
    0x287748: (
        "妈妈：{FD:01}，你听到了吗？{WAIT_CLEAR}"
        "播报员说那只宝可梦\n是什么颜色的？"
    ),
    # --- may / later mom ---
    0x270958: "小遥：我培养的宝可梦可不会\n输给你的宝可梦，{FD:01}{FD:05}！",
    0x270A1F: (
        "小遥：我打算很快回未白镇了。{WAIT_CLEAR}"
        "我抓到了不少不错的宝可梦，\n图鉴也有进展了，所以{WAIT_SCROLL}"
        "我要回家给爸爸看看。"
    ),
    0x276308: "妈妈：等等，{FD:01}！",
    0x276317: (
        "妈妈：{FD:01}！{FD:01}！你有没有\n去向小田卷博士打过招呼？{WAIT_CLEAR}"
        "哇！好可爱的宝可梦！\n是小田卷博士给你的吧，真棒！{WAIT_CLEAR}"
        "真不愧是你爸爸的孩子。\n你和宝可梦很配呢！{WAIT_CLEAR}"
        "来，宝贝！要是出去冒险的话，\n就把这双"
    ),
    0x276476: (
        "妈妈：{FD:01}，这双鞋附带了\n使用说明。{WAIT_CLEAR}"
        "“穿着这双跑步鞋时按B键，\n就能跑得更快！”{WAIT_CLEAR}"
        "“穿上跑步鞋，\n到野外尽情奔跑吧！”"
    ),
    0x27664C: (
        "小田卷博士常在研究所里\n研究，然后又突然跑到野外{WAIT_SCROLL}"
        "继续调查……{WAIT_CLEAR}他到底什么时候\n才会待在家里呢？"
    ),
    0x276F9E: "小遥：{FD:01}{FD:05}！\n这边！{WAIT_SCROLL}我们快回家吧！",
    0x2870BA: "妈妈：再见啦，宝贝！",
    0x287153: "妈妈：小心点，宝贝！",
    0x34968B: (
        "妈妈：你爸爸和你……\n大家都为宝可梦着迷。{WAIT_CLEAR}"
        "宝可梦到底有什么魅力呢？{WAIT_CLEAR}"
        "我吗？\n我喜欢那些能帮我做{WAIT_SCROLL}家务的宝可梦。"
    ),
    0x349720: (
        "妈妈：嗨，{FD:01}！\n你爸爸总是把自己关在{WAIT_SCROLL}橙华道馆里。{WAIT_CLEAR}"
        "偶尔会回家一趟，\n但吃饱了又会回到道馆。{WAIT_CLEAR}"
        "输给你这件事，\n大概大大伤了他的自尊心吧！"
    ),
    0x349803: (
        "妈妈：{FD:01}……\n不用担心我和家里。{WAIT_CLEAR}"
        "那双跑步鞋，\n就穿到破掉为止吧，宝贝！"
    ),
    # --- Birch lab / starter path ---
    0x289A59: (
        "博士不喜欢坐在桌前工作。{WAIT_CLEAR}"
        "他更愿意亲自到野外去{WAIT_SCROLL}做调查。"
    ),
    0x289AE6: (
        "小田卷博士正在研究宝可梦的\n栖息地与分布。{WAIT_CLEAR}"
        "博士也很喜欢{FD:06}呢。"
    ),
    0x289B65: (
        "小田卷博士：那么，{FD:01}{FD:05}。{WAIT_CLEAR}"
        "你爸爸跟我说过好多你的事。{WAIT_CLEAR}"
        "他说你搬过来了，\n还没有宝可梦呢。{WAIT_CLEAR}"
        "那怎么行！{WAIT_CLEAR}"
        "来，这里有三只宝可梦！{WAIT_CLEAR}"
        "选一只做你的同伴吧！"
    ),
    0x289CC9: "小田卷博士：顺便给那只{FD:02}\n起个昵称怎么样？",
    0x289D0E: (
        "小田卷博士：顺便给那只{FD:02}\n起个昵称怎么样？{WAIT_CLEAR}"
    ),
    0x289D54: (
        "小田卷博士：如果你好好培养宝可梦、\n积累经验，我想你会成为{WAIT_SCROLL}"
        "非常出色的训练家。"
    ),
    0x289E33: (
        "小田卷博士：太好了！\n{FD:06}也会高兴的。{WAIT_CLEAR}"
        "让{FD:06}教你作为训练家\n意味着什么吧。"
    ),
    0x289E93: "小田卷博士：别这么说嘛。\n你该去见见我的孩子。",
    0x289ED2: (
        "小田卷博士：{FD:06}？\n大概回家了吧。{WAIT_CLEAR}"
        "也可能又在草丛里\n钻来钻去找宝可梦了。"
    ),
    0x289F80: (
        "小田卷博士：哦，嗨，{FD:01}{FD:05}！{WAIT_CLEAR}"
        "听说你第一次就赢了{FD:06}，\n真了不起！"
    ),
    0x28A090: "{FD:01}得到了宝可梦图鉴！",
    0x28A0A9: (
        "小田卷博士：宝可梦图鉴是高科技工具，\n会自动记录你遇见的{WAIT_SCROLL}"
        "每只宝可梦的资料。"
    ),
    0x28A1CD: (
        "小田卷博士：无数宝可梦\n在等着你！{WAIT_CLEAR}"
        "啊啊，我又开始手痒，\n想出去实地调查了！"
    ),
    0x28A235: (
        "小遥：哇，{FD:01}{FD:05}！\n你也拿到宝可梦图鉴了！{WAIT_CLEAR}"
        "太棒了！跟我一样！\n我的图鉴……嗯……"
    ),
    0x28A29E: (
        "小遥：能捉到很多宝可梦\n就很有趣！{WAIT_CLEAR}"
        "我要到处去找，\n因为我想……"
    ),
    0x28A351: "咦？你的背包满了。",
    0x28A366: "小遥：接下来该去哪里\n找宝可梦呢？",
    0x28A39D: (
        "小悠：哼……\n你也拿到宝可梦图鉴了啊。{WAIT_CLEAR}"
        "那好，这些给你。"
    ),
    0x28A3EC: (
        "小悠：你也知道，宝可梦越多\n就越有意思。{WAIT_CLEAR}"
        "我要去各地探索，\n找更多宝可梦。"
    ),
    0x28A4BB: "喂，你的背包满了。",
    0x2881E9: (
        "我觉得人和宝可梦一起旅行\n真是太棒了。{WAIT_CLEAR}"
        "不过偶尔也该回家看看。"
    ),
}


def scrub_mt(zh: str) -> str:
    if not zh:
        return zh
    reps = [
        (r"poksammon", "宝可梦"),
        (r"poksamdex", "宝可梦图鉴"),
        (r"POKsamMON", "宝可梦"),
        (r"POKéMON", "宝可梦"),
        (r"POKEMON", "宝可梦"),
        (r"Pokémon", "宝可梦"),
        (r"LITTLEROOT", "未白镇"),
        (r"Littleroot", "未白镇"),
        (r"PROF\. BIRCH", "小田卷博士"),
        (r"Prof\. Birch", "小田卷博士"),
        (r"RUNNING SHOES", "跑步鞋"),
        (r"PETALBURG", "橙华"),
        (r"\[\[10\]\]", "{WAIT_CLEAR}"),
        (r"\[\[0\]\]", "{WAIT_CLEAR}"),
        (r"\[\[1\]\]", "{WAIT_SCROLL}"),
        (r"pok<s:1>\s*mon", "宝可梦"),
        (r"MAY:", "小遥："),
        (r"MOM:", "妈妈："),
        (r"^梅：", "小遥："),
        (r"^妈：", "妈妈："),
    ]
    out = zh
    for a, b in reps:
        out = re.sub(a, b, out, flags=re.IGNORECASE)
    return out


def inplace_apply(data: bytearray, golden: bytes, off: int, zh: str) -> bool:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return False
    capacity = eos - off + 1
    enc, missing = encode_text_safe(zh)
    if len(enc) > capacity:
        # trim carefully at sentence end
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > capacity:
            cut = cut[:-1]
        enc, missing = encode_text_safe(cut)
        if len(enc) > capacity:
            print(f"TOO LONG {off:08X} need {len(enc)} cap {capacity} miss={missing}")
            return False
    blob = enc + (b"\x00" * (capacity - len(enc)))
    data[off : off + capacity] = blob
    # restore 0x08 pointer
    needle = struct.pack("<I", 0x08000000 + off)
    i = 0
    while True:
        j = golden.find(needle, i)
        if j < 0:
            break
        if j % 4 == 0:
            data[j : j + 4] = needle
        i = j + 1
    print(f"OK {off:08X} used={len(enc)}/{capacity}")
    return True


def main() -> int:
    cache: dict[str, str] = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))

    # Update locale + cache from HAND by offset
    rows_out = []
    en_by_off: dict[int, str] = {}
    for line in LOCALE.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        off = int(row["offset"])
        en = row.get("en") or ""
        en_by_off[off] = en
        if off in HAND:
            row["zh"] = HAND[off]
            if en:
                cache[en] = HAND[off]
        else:
            zh = scrub_mt(row.get("zh") or "")
            row["zh"] = zh
            if en and zh and zh != en:
                cache[en] = zh
        rows_out.append(row)

    LOCALE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows_out) + "\n",
        encoding="utf-8",
    )
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes() if OUT.exists() else ROM.read_bytes())
    n = 0
    for off, zh in HAND.items():
        if inplace_apply(data, golden, off, zh):
            n += 1
    # also scrub-inplace a few more early MAY/MOM that aren't in HAND if short enough
    for off, en in en_by_off.items():
        if off in HAND:
            continue
        if not (en.startswith("MOM:") or en.startswith("MAY:")):
            continue
        if not (0x270000 <= off < 0x28A000 or 0x349000 <= off < 0x34A000):
            continue
        zh = scrub_mt(cache.get(en) or "")
        if not zh or not any("\u4e00" <= c <= "\u9fff" for c in zh):
            continue
        if inplace_apply(data, golden, off, zh):
            n += 1

    ROM.write_bytes(data)
    OUT.write_bytes(data)
    print(f"inplace_applied={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
