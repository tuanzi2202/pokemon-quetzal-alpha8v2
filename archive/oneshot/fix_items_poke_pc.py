#!/usr/bin/env python3
"""Fix item names + descriptions; scrub Poké/POKé leftovers; keep scripts intact."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"

# Fixed-width item name slots (leading 00 padding like golden)
ITEM_NAMES: dict[int, str] = {
    0xF9B251: "精灵球",
    0xF9B266: "超级球",
    0xF9B27B: "高级球",
    0xF9B28F: "大师球",
    0xF9B2A4: "纪念球",
    0xF9B2B9: "治愈球",
    0xF9B2CA: "捕网球",
    0xF9B2DD: "巢穴球",
    0xF9B2F2: "潜水球",
    0xF9B306: "黑暗球",
    0xF9B31A: "计时球",
    0xF9B32F: "先机球",
    0xF9B343: "重复球",
    0xF9B358: "豪华球",
    0xF9B36C: "等级球",
    0xF9B37F: "诱饵球",
    0xF9B392: "月亮球",
    0xF9B3A6: "友友球",
    0xF9B3BC: "甜蜜球",
    0xF9B3CE: "速度球",
    0xF9B3E2: "沉重球",
    0xF9B3F7: "梦境球",
    0xF9B40B: "狩猎球",
    0xF9B420: "竞速球",
    0xF9B433: "光耀球",
    0xF9B449: "究极球",
    0xF9B45B: "贵重球",
    0xF9B471: "伤药",
    0xF9B47F: "好伤药",
    0xF9B499: "厉害伤药",
    0xF9B4AD: "全满药",
    0xF9B4BF: "全复药",
    0xF9B4D5: "复活药",
    0xF9B4E3: "万能药",
    0xF9B4FB: "美味之水",
    0xF9B510: "劲爽汽水",
    0xF9B521: "果汁牛奶",  # lemonade approx - 柠檬汁饮料
    0xF9B535: "哞哞鲜奶",
    0xF9B54C: "力量粉",
    0xF9B562: "力量根",
    0xF9B574: "万能粉",
    0xF9B588: "复活草",
    0xF9B59D: "解毒药",
    0xF9B5AD: "解麻药",
    0xF9B5C6: "灼伤药",
    0xF9B5D6: "解冻药",
    0xF9B5E9: "解眠药",
    0xF9B5FE: "万灵药",
    0xF9B612: "PP单项小补剂",
    0xF9B622: "PP单项全补剂",
    0xF9B63A: "PP多项小补剂",
    0xF9B64B: "PP多项全补剂",
    0xF9B663: "树果汁",
    0xF9B678: "圣灰",
    0xF9B68B: "心形甜点",
    0xF9B6A0: "极巨蜂蜜",
}

# Fix lemonade name
ITEM_NAMES[0xF9B521] = "柠檬汁"

ITEM_DESCS: dict[int, str] = {
    0xF8B1D2: "用于捕捉野生\n宝可梦的道具。",
    0xF8B1F9: "性能不错的球，\n比精灵球更容易\n捉到宝可梦。",
    0xF8B230: "性能很好的球，\n比超级球更容易\n捉到宝可梦。",
    0xF8B26A: "性能最好的球，\n能必定捉到\n宝可梦。",
    0xF8B29D: "为纪念某事件\n而特制的稀有球。",
    0xF8B2CE: "捉到宝可梦后\n还能回复体力的球。",
    0xF8B2FC: "对水和虫属性\n宝可梦特别有效。",
    0xF8B333: "对弱小的宝可梦\n特别有效。",
    0xF8B35F: "对海底的宝可梦\n特别有效。",
    0xF8B3BB: "战斗回合越多，\n捕捉率越高。",
    0xF8B417: "对曾经捉到过的\n宝可梦更有效。",
    0xF8B44A: "捉到后会让宝可梦\n变得更亲密。",
    0xF8B478: "对等级低的\n宝可梦更有效。",
    0xF8B4A7: "对钓上来的\n宝可梦更有效。",
    0xF8B4D4: "对使用月之石\n进化的宝可梦有效。",
    0xF8B500: "捉到后会让宝可梦\n变得友好。",
    0xF8B532: "对异性宝可梦\n特别有效。",
    0xF8B560: "对速度很快的\n宝可梦有效。",
    0xF8B581: "对很重的\n宝可梦有效。",
    0xF8B5A3: "对睡着的\n宝可梦有效。",
    0xF8B5CF: "仅在狩猎地带\n使用的特殊球。",
    0xF8B604: "捕虫大赛中\n使用的特殊球。",
    0xF8B635: "专门用来捕捉\n光耀宝可梦的球。",
    0xF8B658: "专门用来捕捉\n究极异兽的球。",
    0xF8B67F: "为纪念某事件\n而特制的稀有球。",
    0xF8B6B0: "回复宝可梦\n20点HP。",
    0xF8B6DB: "回复宝可梦\n60点HP。",
    0xF8B706: "回复宝可梦\n120点HP。",
    0xF8B732: "完全回复\n宝可梦的HP。",
    0xF8B756: "完全回复宝可梦的\nHP和异常状态。",
    0xF8B785: "让倒下的宝可梦\n以一半HP复活。",
    0xF8B7B1: "让倒下的宝可梦\n以全部HP复活。",
}


def put_padded(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    """Write ZH into fixed slot; keep leading 00 padding like golden English."""
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    cap = eos - off + 1
    enc, miss = encode_text_safe(zh)
    if miss:
        print(f"  miss @{off:08X} {miss[:6]}")
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
        if len(body) + 1 > cap:
            print(f"  FAIL {off:08X}")
            return "long"
        print(f"  TRIM {off:08X}")
    # right-align into slot (match golden leading pads)
    pad = cap - 1 - len(body)
    data[off : off + cap] = (b"\x00" * pad) + body + b"\xff"
    return "ok"


def put(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    cap = eos - off + 1
    enc, _ = encode_text_safe(zh)
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
        if len(body) + 1 > cap:
            return "long"
    data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))
    return "ok"


SCRUB = [
    (re.compile(r"(?i)POK[EÉ]\s*BALLS?"), "精灵球"),
    (re.compile(r"(?i)GREAT\s*BALLS?"), "超级球"),
    (re.compile(r"(?i)ULTRA\s*BALLS?"), "高级球"),
    (re.compile(r"(?i)MASTER\s*BALLS?"), "大师球"),
    (re.compile(r"(?i)POK[EÉ]\s*MON"), "宝可梦"),
    (re.compile(r"(?i)Pokémon"), "宝可梦"),
    (re.compile(r"(?i)Pokemon"), "宝可梦"),
]


def scrub_en(en: str) -> str:
    z = en
    for pat, rep in SCRUB:
        z = pat.sub(rep, z)
    return z


def scrub_item_descs_range(data: bytearray, golden: bytes, start: int, end: int) -> int:
    """Any still-English desc containing Ball/Pokémon → scrub+inplace if enough CJK."""
    n = 0
    off = start
    while off < end:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= end or eos - off > 220 or eos - off < 12:
            off += 1
            continue
        if off in ITEM_DESCS:
            off = eos + 1
            continue
        en = decode_bytes(golden[off : eos + 1])
        if not re.search(r"(?i)ball|pok[eé]|pokémon|pokemon", en):
            off = eos + 1
            continue
        if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
            # already modified; still fix if raw POKé remains
            if b"\xca\xc9\xc5\x1b" not in bytes(data[off : eos + 1]) and b"\xca\xe3\xdf\x1b" not in bytes(
                data[off : eos + 1]
            ):
                off = eos + 1
                continue
        zh = scrub_en(en)
        cjk = sum(1 for c in zh if "\u4e00" <= c <= "\u9fff")
        if cjk < 2:
            off = eos + 1
            continue
        if put(data, golden, off, zh) == "ok":
            n += 1
        off = eos + 1
    return n


def fix_raw_poke_ball(data: bytearray) -> int:
    """Byte-level POKé/Poké + BALL → 精灵球; POKé+球 → 精灵球."""
    variants = [
        bytes([0xCA, 0xC9, 0xC5, 0x1B]),  # POKé
        bytes([0xCA, 0xE3, 0xDF, 0x1B]),  # Poké (title)
    ]
    ball_u = bytes([0xBC, 0xBB, 0xC6, 0xC6])  # BALL
    ball_t = bytes([0xBC, 0xD5, 0xE0, 0xE0])  # Ball
    qiu = encode_text_safe("球")[0]
    qiu = qiu[:-1] if qiu.endswith(b"\xff") else qiu
    jing = encode_text_safe("精灵球")[0]
    jing = jing[:-1] if jing.endswith(b"\xff") else jing
    n = 0
    for poke in variants:
        i = 0
        while True:
            j = data.find(poke, i)
            if j < 0:
                break
            # POKé + optional space + BALL/Ball
            for ball in (ball_u, ball_t):
                for gap in (0, 1):  # no space or 00 space
                    start = j
                    end = j + len(poke) + gap
                    if gap and data[j + len(poke)] != 0x00:
                        continue
                    if data[end : end + len(ball)] != ball:
                        continue
                    end2 = end + len(ball)
                    if end2 < len(data) and data[end2] == 0xCD:  # S
                        end2 += 1
                    old = end2 - start
                    if len(jing) <= old:
                        data[start:end2] = jing + b"\x00" * (old - len(jing))
                        n += 1
                    break
            # POKé + 球
            if data[j + len(poke) : j + len(poke) + len(qiu)] == qiu:
                old = len(poke) + len(qiu)
                if len(jing) <= old:
                    data[j : j + old] = jing + b"\x00" * (old - len(jing))
                    n += 1
            i = j + 1
    # Also POKéMON → 宝可梦 raw
    mon_u = bytes([0xC7, 0xC9, 0xC8])  # MON after POKé
    # skip - too risky mid words
    return n


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    print("=== item names ===")
    ok = 0
    for off, zh in ITEM_NAMES.items():
        st = put_padded(data, golden, off, zh)
        if st == "ok":
            ok += 1
        else:
            print(f"  {off:08X} {st}")
    print(f"  names ok={ok}/{len(ITEM_NAMES)}")

    print("=== item descs HAND ===")
    okd = 0
    for off, zh in ITEM_DESCS.items():
        st = put(data, golden, off, zh)
        if st == "ok":
            okd += 1
            print(f"  OK {off:08X}")
        else:
            print(f"  {off:08X} {st}")
    print(f"  descs ok={okd}/{len(ITEM_DESCS)}")

    print("=== scrub descs F8B-F9B ===")
    n = scrub_item_descs_range(data, golden, 0xF8B000, 0xF9B200)
    print(f"  scrubbed={n}")

    print("=== raw POKé/Poké Ball ===")
    print(f"  fixed={fix_raw_poke_ball(data)}")

    # secondary name bank F9F6xx (alt lang) - scrub Ball names if still EN/ES
    print("=== alt name bank F9F6 ===")
    alt = {
        0xF9F6FD: "精灵球",
        0xF9F712: "超级球",
        0xF9F73B: "大师球",
    }
    for off, zh in alt.items():
        eos = golden.find(b"\xff", off)
        if eos > 0:
            put_padded(data, golden, off, zh)
            print(f"  {off:08X}")

    # keep scripts
    data[0x279E71:0x27A0D5] = golden[0x279E71:0x27A0D5]

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("B1B2B3B4B5B6B7B8C1C2C3C4C5C6C7C8")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    # verify
    for off in (0xF9B251, 0xF8B1D2, 0xF8B26A):
        eos = golden.find(b"\xff", off)
        print(f"verify {off:08X}", data[off : eos + 1].hex())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
