#!/usr/bin/env python3
"""Emergency fix: restore corrupted scripts/zeroed May intro; re-apply safe Chinese."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"


def put(data: bytearray, golden: bytes, off: int, zh: str) -> None:
    """Write Chinese into a pure text slot; keep FF at golden EOS."""
    eos = golden.find(b"\xff", off)
    if eos < 0:
        raise ValueError(f"no eos @{off:08X}")
    cap = eos - off + 1
    enc, miss = encode_text_safe(zh)
    if miss:
        print(f"  missing @{off:08X}: {miss[:8]}")
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    if len(body) + 1 > cap:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > cap:
            cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        body = enc[:-1]
        print(f"  TRIM {off:08X} {len(body)+1}/{cap}")
    else:
        print(f"  OK {off:08X} {len(body)+1}/{cap}")
    # Early FF then NUL pad — avoids the text engine reading hundreds of spaces.
    data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))


def restore(data: bytearray, golden: bytes, start: int, end: int, label: str) -> None:
    data[start:end] = golden[start:end]
    print(f"RESTORE {label} {start:08X}-{end:08X} ({end-start} bytes)")


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    # --- 1) Route 101 script/pointer table (apply_text retargeted ptrs → freeze) ---
    restore(data, golden, 0x279E71, 0x27A0D5, "route101_scripts_ptrs")

    # --- 2) Inline "H-help me!" block: restore script prefix, then Chinese text ---
    restore(data, golden, 0x279C0F, 0x279C2B, "birch_help_inline")
    # golden: ... 0B FE "H-help me!" FF  — keep FE, replace text after it
    # 0x279C1F is FE in golden; text body starts 0x279C20
    put(data, golden, 0x279C1F, "\n救、救我！")

    # --- 3) Birch rescue dialogues (pure text) ---
    BIRCH = {
        0x279C2B: (
            "喂！那边的人！\n拜托！救救我！{WAIT_CLEAR}"
            "我的背包里！\n有精灵球！"
        ),
        0x279C70: "你、你去哪？！\n别丢下我啊！",
        0x279CA3: (
            "小田卷博士：呼……{WAIT_CLEAR}"
            "我在深草里调查野生宝可梦时被袭击了。{WAIT_CLEAR}"
            "你救了我，非常感谢！{WAIT_CLEAR}"
            "哦？{WAIT_CLEAR}"
            "你好，你是{FD:01}{FD:05}！{WAIT_CLEAR}"
            "这里不方便细聊，稍后请到我的宝可梦研究所来，好吗？"
        ),
        0x27680A: "你救了小田卷博士！\n我太高兴了！",
        0x2768C9: (
            "小田卷博士：哎呀哎呀，{FD:01}{FD:05}！\n刚才干得漂亮！{WAIT_CLEAR}"
            "第一次见到你时就觉得你不简单，{WAIT_SCROLL}"
            "但没想到能到这个地步。{WAIT_CLEAR}"
            "对了，我给你的宝可梦图鉴还在吧？{WAIT_CLEAR}"
            "我有东西要给你看。\n去研究所吧。"
        ),
        0x276890: "小田卷博士的宝可梦研究所",
    }
    print("=== birch texts ===")
    for off, zh in BIRCH.items():
        put(data, golden, off, zh)

    # --- 4) May/Brendan first meeting (were zeroed / mid-restored to English) ---
    print("=== first meeting ===")
    put(
        data,
        golden,
        0x2882AE,
        (
            "咦？\n你……你是谁？{WAIT_CLEAR}"
            "…………\n…………{WAIT_CLEAR}"
            "哦，你是{FD:01}{FD:05}吧？\n今天刚搬来的？{WAIT_CLEAR}"
            "嗯……我是小遥。\n请多关照！{WAIT_CLEAR}"
            "我……\n我的梦想是和全世界的{WAIT_SCROLL}宝可梦成为朋友。{WAIT_CLEAR}"
            "我……我听我爸爸小田卷博士\n说起过你，{FD:01}{FD:05}。{WAIT_CLEAR}"
            "我一直希望你能过来，\n我们能一起玩。"
        ),
    )
    put(
        data,
        golden,
        0x28849C,
        (
            "喂！\n你……{WAIT_CLEAR}"
            "你是谁？{WAIT_CLEAR}"
            "哦，你是{FD:01}吧？\n刚搬到隔壁对吧？{WAIT_CLEAR}"
            "我还不知道你是女孩子。{WAIT_CLEAR}"
            "我爸小田卷博士说新邻居是道馆馆主的{WAIT_SCROLL}孩子，我还以为会是男生呢。{WAIT_CLEAR}"
            "我叫小悠。\n嗨，邻居！{WAIT_CLEAR}"
            "嗯？你问我？\n我……也喜欢宝可梦。"
        ),
    )
    # duplicate brendan intro bank
    put(
        data,
        golden,
        0x288B8D,
        (
            "喂！\n你……{WAIT_CLEAR}"
            "你是谁？{WAIT_CLEAR}"
            "哦，你是{FD:01}吧？\n刚搬到隔壁对吧？{WAIT_CLEAR}"
            "我还不知道你是女孩子。{WAIT_CLEAR}"
            "我爸小田卷博士说新邻居是道馆馆主的{WAIT_SCROLL}孩子，我还以为会是男生呢。{WAIT_CLEAR}"
            "我叫小悠。\n嗨，邻居！{WAIT_CLEAR}"
            "嗯？你问我？\n我……也喜欢宝可梦。"
        ),
    )

    # --- 5) Restore shop-script+MAY blob header, translate text only ---
    restore(data, golden, 0x270720, 0x270785, "may_shop_script_hdr")
    put(
        data,
        golden,
        0x270785,
        (
            "小遥：咦？\n{FD:01}{FD:05}，你也来买东西？{WAIT_CLEAR}"
            "我买了一堆人偶和海报。{WAIT_CLEAR}"
            "当然，我也抓了不少宝可梦，\n正在好好培养{WAIT_SCROLL}呢。"
        ),
    )

    # --- 6) Other zeroed early dialogues ---
    print("=== restore zeroed early ===")
    MORE = {
        0x28702C: (
            "对了。\n爸爸有个朋友住在镇上。{WAIT_CLEAR}"
            "他叫小田卷博士。{WAIT_CLEAR}"
            "就住在旁边，你该去打个招呼。"
        ),
        0x287666: (
            "现在为您插播紧急新闻！{WAIT_CLEAR}"
            "在丰缘各地，出现了\n目击传说宝可梦的报告……"
        ),
        0x2881E9: (
            "我觉得人和宝可梦一起旅行\n真是太棒了。{WAIT_CLEAR}"
            "不过偶尔也该回家看看。"
        ),
        0x28808D: (
            "有其父必有其子。{WAIT_CLEAR}"
            "我丈夫和孩子一样\n都为宝可梦狂热。{WAIT_CLEAR}"
            "要是孩子也在就好了……"
        ),
        0x289A59: (
            "博士不喜欢坐在桌前工作。{WAIT_CLEAR}"
            "他更愿意亲自到野外去{WAIT_SCROLL}做调查。"
        ),
        0x289B65: (
            "小田卷博士：那么，{FD:01}{FD:05}。{WAIT_CLEAR}"
            "你爸爸跟我说过好多你的事。{WAIT_CLEAR}"
            "他说你搬过来了，\n还没有宝可梦呢。{WAIT_CLEAR}"
            "那怎么行！{WAIT_CLEAR}"
            "来，这里有三只宝可梦！{WAIT_CLEAR}"
            "选一只做你的同伴吧！"
        ),
        0x289D54: (
            "小田卷博士：如果你好好培养宝可梦、\n积累经验，我想你会成为{WAIT_SCROLL}"
            "非常出色的训练家。"
        ),
        0x289F80: (
            "小田卷博士：哦，嗨，{FD:01}{FD:05}！{WAIT_CLEAR}"
            "听说你第一次就赢了{FD:06}，\n真了不起！"
        ),
        0x28A29E: (
            "小遥：能捉到很多宝可梦\n就很有趣！{WAIT_CLEAR}"
            "我要到处去找，\n因为我想……"
        ),
        0x28A3EC: (
            "小悠：你也知道，宝可梦越多\n就越有意思。{WAIT_CLEAR}"
            "我要去各地探索，\n找更多宝可梦。"
        ),
        0x2708B1: (
            "小遥：咦，为什么？{FD:01}{FD:05}，\n你还没有好好培养宝可梦吗？{WAIT_CLEAR}"
            "那样可不像话哦。"
        ),
        0x270919: "小遥：来吧，和我对战，\n让我看看你的宝可梦！",
        0x276F9E: "小遥：{FD:01}{FD:05}！\n这边！{WAIT_SCROLL}我们快回家吧！",
        0x279E59: "101号道路\n未白镇",
    }
    for off, zh in MORE.items():
        put(data, golden, off, zh)

    # --- 7) Battle menu (keep) ---
    print("=== battle menu ===")
    # raw 0x38 spacing via token — encode_text_safe may drop unknown {38};
    # inject manually like before
    def put_menu(off: int, parts: list[bytes]) -> None:
        eos = golden.find(b"\xff", off)
        cap = eos - off + 1
        blob = b"".join(parts) + b"\xff"
        if len(blob) > cap:
            raise SystemExit(f"menu overflow {off:08X}")
        data[off : off + cap] = blob + b"\x00" * (cap - len(blob))
        print(f"  menu {off:08X} {len(blob)}/{cap}")

    # 战斗 FC:13 0x38 背包 \n 宝可梦 FC:13 0x38 逃跑
    def zh_bytes(s: str) -> bytes:
        enc, _ = encode_text_safe(s)
        return enc[:-1] if enc.endswith(b"\xff") else enc

    put_menu(
        0xFFFB50,
        [
            zh_bytes("战斗"),
            bytes([0xFC, 0x13, 0x38]),
            zh_bytes("背包"),
            bytes([0xFE]),
            zh_bytes("宝可梦"),
            bytes([0xFC, 0x13, 0x38]),
            zh_bytes("逃跑"),
        ],
    )
    put_menu(
        0xFFFB6A,
        [
            zh_bytes("球"),
            bytes([0xFC, 0x13, 0x38, 0x55, 0x56, 0x57, 0x58, 0x59]),
            bytes([0xFE]),
            zh_bytes("靠近"),
            bytes([0xFC, 0x13, 0x38]),
            zh_bytes("逃跑"),
        ],
    )

    # fingerprint bump
    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("B1B2B3B4B5B6B7B8C1C2C3C4C5C6C7C8")

    OUT.write_bytes(data)
    ROM.write_bytes(data)

    # verify
    print("=== verify ===")
    for off, name in [
        (0x2882AE, "may_first"),
        (0x279C0F, "help_inline"),
        (0x279CA3, "whew"),
        (0x279E71, "script_tbl"),
        (0xFFFB50, "menu"),
    ]:
        eos = golden.find(b"\xff", off)
        if name == "script_tbl":
            same = data[0x279E71:0x27A0D5] == golden[0x279E71:0x27A0D5]
            print(name, "restored" if same else "DIFF")
            # spot-check previously bad ptr
            print("  ptr@279EF0", bytes(data[0x279EF0:0x279EF4]).hex(), "golden", golden[0x279EF0:0x279EF4].hex())
        elif name == "help_inline":
            print(name, bytes(data[off : off + 28]).hex())
            print("  g", golden[off : off + 28].hex())
        else:
            slot = bytes(data[off : eos + 1])
            print(name, "ff@", slot.find(b"\xff"), "head", slot[:24].hex())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
