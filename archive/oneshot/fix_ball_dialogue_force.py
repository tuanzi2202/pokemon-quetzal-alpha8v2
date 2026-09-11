#!/usr/bin/env python3
"""Hand-fix full ball-related dialogues at correct string starts."""
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

# offset -> full Chinese (must fit golden capacity to FF)
FORCE = {
    0x276D39: (
        "这里是宝可梦商店。\n看蓝色屋顶就知道。{WAIT_CLEAR}"
        "我们卖各种各样的商品，包括用来捕捉宝可梦的精灵球。{WAIT_CLEAR}"
        "来，这个宣传品送给你。"
    ),
    0x279C2B: (
        "喂！那边的人！\n拜托！救救我！{WAIT_CLEAR}"
        "我的背包里！\n有精灵球！"
    ),
    0x27B8C9: (
        "要用精灵球捕捉的话，\n先削弱野生宝可梦。{WAIT_CLEAR}"
        "中毒、灼伤或睡着时，\n会更好抓。"
    ),
    0x27B95C: (
        "偷别人的宝可梦就是小偷。{WAIT_CLEAR}"
        "精灵球只能扔向\n野生宝可梦。"
    ),
    0x28200B: (
        "我们的新型精灵球将在\n卡那兹市的宝可梦商店发售。{WAIT_CLEAR}"
        "请一定试试看！\n谢谢，再见！"
    ),
    0x28B74B: "我要去买很多精灵球，\n抓好多宝可梦！",
    0x294FF9: (
        "满充：哇！\n宝可梦！{WAIT_CLEAR}"
        "爸爸：嗯。也给你一个精灵球。\n加油！{WAIT_CLEAR}"
        "满充得到了精灵球！"
    ),
    0xFB778E: "现在不能使用\n精灵球！{WAIT_CLEAR}",
}


def inplace(data: bytearray, golden: bytes, off: int, zh: str) -> None:
    eos = golden.find(b"\xff", off)
    capacity = eos - off + 1
    enc, missing = encode_text_safe(zh)
    if missing:
        print(f"WARN missing {off:08X}", missing[:8])
    if len(enc) > capacity:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > capacity:
            cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        print(f"TRIM {off:08X} {len(enc)}/{capacity}")
    else:
        print(f"OK {off:08X} {len(enc)}/{capacity}")
    data[off : off + capacity] = enc + b"\x00" * (capacity - len(enc))
    print(" =>", decode_bytes(bytes(data[off : eos + 1]))[:80])


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    for off, zh in FORCE.items():
        inplace(data, golden, off, zh)

    # fingerprint bump for forced internal re-copy
    data[0x1DCB5E0 + 13] = (data[0x1DCB5E0 + 13] + 1) & 0xFF

    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print("Tackle still", decode_bytes(bytes(data[0x417F99 : 0x417F99 + 17]) + b"\xff"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
