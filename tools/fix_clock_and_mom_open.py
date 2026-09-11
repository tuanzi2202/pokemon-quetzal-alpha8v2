#!/usr/bin/env python3
"""Restore wall-clock / FC UI pool corruption + force opening Mom speech Chinese.

apply_text mistook dwords in 0xFC0000-0xFD0000 for string pointers and retargeted
~590 of them into 0x09E0 free space (garbage). That trashes the wall-clock face.
There is no CJK in this pool — safe to restore wholesale from golden.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chs_encode import encode_text_safe  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"

# Full UI/string/pointer pool that apply_text polluted (clock + item text tables)
FC_POOL = (0x0FC0000, 0x0FD0000)

# Opening Mom lines (true string starts)
OPENING = {
    0x286E3D: (
        "搬家的宝可梦把行李\n都搬进来了，还帮忙打扫。{WAIT_SCROLL}"
        "真是太方便了！{WAIT_CLEAR}"
        "{FD:01}，你的房间在楼上。\n去看看吧，宝贝！{WAIT_CLEAR}"
        "爸爸买了个新时钟，\n纪念我们搬来这里。{WAIT_SCROLL}"
        "别忘了把钟调好！"
    ),
    0x287A82: (
        "妈妈：{FD:01}，喜欢你的\n新房间吗？{WAIT_CLEAR}"
        "很好！东西都收拾整齐了！{WAIT_CLEAR}"
        "楼下也全部搬进来了。{WAIT_CLEAR}"
        "宝可梦搬家公司真方便！{WAIT_CLEAR}"
        "对了，你也去看看桌上的\n东西是不是都在吧。"
    ),
    0x286F1B: "妈妈：怎么了，{FD:01}？{WAIT_CLEAR}不去看看自己的房间吗？",
    0x286F5E: "妈妈：{FD:01}。{WAIT_CLEAR}去把自己房间的钟调好吧，宝贝。",
    0x286F8D: "妈妈：啊！{FD:01}，{FD:01}！\n快！快过来！",
    0x286FB3: "妈妈：快看！是橙华道馆！\n说不定爸爸会出现哦！",
    0x286FE8: "妈妈：啊……结束了。{WAIT_CLEAR}我想爸爸有出镜，可我们错过了。\n真可惜。",
    # 0x287A50 clock-stopped UI: keep English (see restore_clock_ui.py)
    0x2870CF: "妈妈：你有没有去向\n小田卷博士打过招呼？",
    0x2870FF: "妈妈：还好吗，{FD:01}？\n你看起来有点累。{WAIT_CLEAR}我看你该休息一下了。",
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
    0x2870BA: "妈妈：再见啦，宝贝！",
    0x287153: "妈妈：小心点，宝贝！",
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
    # neighbor / rival first meeting
    0x2882AE: (
        "咦？\n你……你是谁？{WAIT_CLEAR}"
        "…………\n…………{WAIT_CLEAR}"
        "哦，你是{FD:01}{FD:05}吧？\n刚搬到隔壁的？"
    ),
    0x28849C: (
        "喂！\n你……{WAIT_CLEAR}"
        "你是谁？{WAIT_CLEAR}"
        "哦，你是{FD:01}吧？\n刚搬到隔壁对吧？"
    ),
    0x28808D: (
        "有其父必有其子。{WAIT_CLEAR}"
        "我丈夫和孩子一样\n都为宝可梦狂热。{WAIT_CLEAR}"
        "要是孩子也在就好了……"
    ),
    0x2881E9: (
        "我觉得人和宝可梦一起旅行\n真是太棒了。{WAIT_CLEAR}"
        "不过偶尔也该回家看看。"
    ),
}

# Day names: keep ENGLISH on purpose.
# Chinese 2-glyph labels (encode lead 0x10..) overflow the clock's narrow
# day slot and trash pixels on the face below. Do NOT inplace-patch DAYS.


def inplace(data: bytearray, golden: bytes, off: int, zh: str) -> None:
    eos = golden.find(b"\xff", off)
    capacity = eos - off + 1
    enc, missing = encode_text_safe(zh)
    if missing:
        print("missing glyphs", hex(off), missing)
    if len(enc) > capacity:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > capacity:
            cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        print(f"trimmed {off:08X} to {len(enc)}/{capacity}")
    if len(enc) > capacity:
        print(f"FAIL too long {off:08X}")
        return
    data[off : off + capacity] = enc + b"\x00" * (capacity - len(enc))
    for pv in (0x08000000 + off, 0x09000000 + (off & 0xFFFFFF)):
        needle = struct.pack("<I", pv)
        want = struct.pack("<I", 0x08000000 + off)
        idx = 0
        n = 0
        while True:
            j = data.find(needle, idx)
            if j < 0:
                break
            prev = data[j - 2 : j] if j >= 2 else b""
            if prev == b"\x0f\x00" or j % 4 == 0:
                data[j : j + 4] = want
                n += 1
            idx = j + 1
        if n:
            print(f"  retargeted {n} ptrs for {off:08X}")
    print(f"OK {off:08X} used={len(enc)}/{capacity}")


def inplace_no_ptr(data: bytearray, golden: bytes, off: int, zh: str) -> None:
    """Write string body only — leave pointer tables untouched."""
    eos = golden.find(b"\xff", off)
    capacity = eos - off + 1
    enc, missing = encode_text_safe(zh)
    if missing:
        print("missing glyphs", hex(off), missing)
        return
    if len(enc) > capacity:
        print(f"FAIL day too long {off:08X} {len(enc)}/{capacity}")
        return
    data[off : off + capacity] = enc + b"\x00" * (capacity - len(enc))
    print(f"OK day {off:08X} {zh} used={len(enc)}/{capacity}")


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    # Do NOT wholesale-restore FC pool (wipes ability/type CN). Clock-only via restore_clock_ui.
    for off, zh in OPENING.items():
        inplace(data, golden, off, zh)

    OUT.write_bytes(data)
    (ROOT / "work" / "cn_build.gba").write_bytes(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
