#!/usr/bin/env python3
"""Full-pass CN: apply locale ZH + items/berries + safe dialogue fill for still-EN."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from fill_and_apply_remaining import (  # noqa: E402
    CACHE,
    LOCALE,
    quality_ok,
    scrub,
    looks_full_line,
    has_latin,
)
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"

# Do not touch script-critical restored regions
SKIP = [
    (0x279E71, 0x27A0D5),
    (0x2972B0, 0x297360),
    (0xFFFB50, 0xFFFC00),  # battle menu
]

ITEM_NAMES: dict[str, str] = {
    "Pewter Crunchies": "深灰市脆饼",
    "Rage Candy Bar": "秘传酱肘子",
    "Lava Cookie": "釜炎仙贝",
    "Old Gateau": "森之仙贝",
    "Casteliacone": "雪花冰",
    "Lumiose Galette": "密阿雷格雷派饼",
    "Shalour Sable": "娑罗沙布蕾",
    "Big Malasada": "大马拉萨达",
    "Sweet Heart": "心意甜甜",
    "Sweet Apple": "甜甜苹果",
    "Tart Apple": "酸酸苹果",
    "Strawberry Sweet": "草莓糖饰",
    "Love Sweet": "爱情糖饰",
    "Berry Sweet": "野莓糖饰",
    "Clover Sweet": "幸运草糖饰",
    "Flower Sweet": "花朵糖饰",
    "Star Sweet": "星星糖饰",
    "Ribbon Sweet": "蝴蝶结糖饰",
    "Exp. Candy XS": "经验糖果XS",
    "Exp. Candy S": "经验糖果S",
    "Exp. Candy M": "经验糖果M",
    "Exp. Candy L": "经验糖果L",
    "Exp. Candy XL": "经验糖果XL",
    "Giga Candy": "极巨糖果",
    "Max Candy": "极巨糖果Max",
    "Rare Candy": "神奇糖果",
    "Health Mochi": "HP粘糕",
    "Muscle Mochi": "攻击粘糕",
    "Resist Mochi": "防御粘糕",
    "Genius Mochi": "特攻粘糕",
    "Clever Mochi": "特防粘糕",
    "Swift Mochi": "速度粘糕",
    "Fresh Start Mochi": "重新粘糕",
    "Tea": "茶",
    "Honey": "甜甜蜜",
    "Nugget": "金珠",
    "Big Nugget": "巨大金珠",
    "Tiny Mushroom": "小蘑菇",
    "Big Mushroom": "大蘑菇",
    "Balm Mushroom": "芳香蘑菇",
    "Pearl": "珍珠",
    "Big Pearl": "大珍珠",
    "Pearl String": "珍珠串",
    "Stardust": "星屑",
    "Star Piece": "星星碎片",
    "Comet Shard": "彗星碎片",
    "Heart Scale": "心之鳞片",
    "Rare Bone": "贵重骨头",
    "Pretty Feather": "美丽之羽",
    "Bottle Cap": "银色王冠",
    "Gold Bottle Cap": "金色王冠",
    "Ability Capsule": "特性胶囊",
    "Ability Patch": "特性贴布",
    "Max Mushrooms": "极巨蘑菇",
    "Poké Toy": "宝可梦玩具",
    "Blue Flute": "蓝色玻璃哨",
    "Yellow Flute": "黄色玻璃哨",
    "Red Flute": "红色玻璃哨",
    "Black Flute": "黑色玻璃哨",
    "White Flute": "白色玻璃哨",
    "X Defense": "防御强化",
    "X Sp. Atk": "特攻强化",
    "X Sp. Def": "特防强化",
    "Lure": "诱饵",
    "Super Lure": "白银诱饵",
    "Max Lure": "黄金诱饵",
    "Helix Fossil": "贝壳化石",
    "Dome Fossil": "甲壳化石",
    "Old Amber": "秘密琥珀",
    "Root Fossil": "根状化石",
    "Claw Fossil": "爪子化石",
    "Armor Fossil": "盾甲化石",
    "Skull Fossil": "头盖化石",
    "Cover Fossil": "背盖化石",
    "Plume Fossil": "羽毛化石",
    "Jaw Fossil": "颚之化石",
    "Sail Fossil": "鳍之化石",
    "Red Shard": "红色碎片",
    "Blue Shard": "蓝色碎片",
    "Yellow Shard": "黄色碎片",
    "Green Shard": "绿色碎片",
    "Shoal Salt": "浅滩海盐",
    "Shoal Shell": "浅滩贝壳",
    "Orange Mail": "橙色邮件",
    "Harbor Mail": "港口邮件",
    "Glitter Mail": "闪耀邮件",
    "IV Up": "个体提升剂",
    "IV Max": "个体极限剂",
}

# Mint names
for en, zh in [
    ("Lonely Mint", "孤独薄荷"),
    ("Adamant Mint", "固执薄荷"),
    ("Naughty Mint", "顽皮薄荷"),
    ("Brave Mint", "勇敢薄荷"),
    ("Bold Mint", "大胆薄荷"),
    ("Impish Mint", "淘气薄荷"),
    ("Lax Mint", "乐天薄荷"),
    ("Relaxed Mint", "悠闲薄荷"),
    ("Modest Mint", "内敛薄荷"),
    ("Mild Mint", "慢吞吞薄荷"),
    ("Rash Mint", "马虎薄荷"),
    ("Quiet Mint", "冷静薄荷"),
    ("Calm Mint", "温和薄荷"),
    ("Gentle Mint", "温顺薄荷"),
    ("Careful Mint", "慎重薄荷"),
    ("Sassy Mint", "自大薄荷"),
    ("Timid Mint", "胆小薄荷"),
    ("Hasty Mint", "急躁薄荷"),
    ("Jolly Mint", "爽朗薄荷"),
    ("Naive Mint", "天真薄荷"),
    ("Serious Mint", "认真薄荷"),
]:
    ITEM_NAMES[en] = zh

BERRY_DESC_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?is)^A Berry to be used in cooking\.$"), "做料理时使用的树果。"),
    (re.compile(r"(?is)^A hold item that\nrestores HP but\nmay confuse\.$"), "携带后可回复HP，\n但有时会混乱。"),
    (re.compile(r"(?is)^A hold item that\nrestores HP upon\nstriking the foe\.$"), "携带后攻击对手时\n可回复HP。"),
    (re.compile(r"(?is)^When held, it ups\nthe Accuracy of a\nmove in a pinch\.$"), "携带后，危急时\n招式命中率会提高。"),
    (re.compile(r"(?is)^A fertilizer that\nups the life time\nof Berry trees\.$"), "延长树果树寿命的肥料。"),
    (re.compile(r"(?is)^A fertilizer that\nups the chance of\nBerry mutations\.$"), "提高树果突变几率的肥料。"),
    (re.compile(r"(?is)^A case for holding\nPokéblocks made with\na Berry Blender\.$"), "用来收纳树果混合器\n做出的宝可方块。"),
    (re.compile(r"(?is)^Stores Berry\nPowder made using\na Berry Crusher\.$"), "收纳树果粉碎机\n做出的树果粉末。"),
]

# Common berry hold-item short descs by English template
BERRY_DESCS_HAND: dict[int, str] = {}


def in_skip(off: int) -> bool:
    return any(a <= off < b for a, b in SKIP)


def put(data: bytearray, golden: bytes, off: int, zh: str, padded: bool = False) -> str:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    cap = eos - off + 1
    enc, miss = encode_text_safe(zh)
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    if len(body) + 1 > cap:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > cap:
            if cut.endswith("}"):
                break
            cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        body = enc[:-1]
        if len(body) + 1 > cap:
            return "long"
    if padded:
        pad = cap - 1 - len(body)
        data[off : off + cap] = (b"\x00" * pad) + body + b"\xff"
    else:
        data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))
    return "ok"


def apply_locale(data: bytearray, golden: bytes) -> tuple[int, int]:
    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    cache: dict[str, str] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    ok = skip = 0
    for r in rows:
        off = int(r["offset"])
        if in_skip(off):
            continue
        en = (r.get("en") or "").strip()
        zh = scrub((r.get("zh") or "").strip())
        if not looks_full_line(en):
            continue
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos - off > 400:
            continue
        # only rewrite if still golden English
        if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
            continue
        if not quality_ok(en, zh):
            # try cache
            zh = scrub(cache.get(en, ""))
            if not quality_ok(en, zh):
                skip += 1
                continue
        st = put(data, golden, off, zh)
        if st == "ok":
            ok += 1
        else:
            skip += 1
    return ok, skip


def apply_item_names(data: bytearray, golden: bytes) -> int:
    n = 0
    for start, end in [(0xF9B200, 0xF9E800), (0xF9E800, 0xFA0000)]:
        off = start
        while off < end:
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= end or eos - off > 28 or eos - off < 3:
                off += 1
                continue
            en = decode_bytes(golden[off : eos + 1]).strip()
            if en in ITEM_NAMES and bytes(data[off : eos + 1]) == golden[off : eos + 1]:
                if put(data, golden, off, ITEM_NAMES[en], padded=True) == "ok":
                    n += 1
            off = eos + 1
    return n


def apply_item_descs(data: bytearray, golden: bytes) -> int:
    n = 0
    # Ball/heal leftovers that were re-Englished somehow + berry-ish
    HAND = {
        0xF8B1D2: "用于捕捉野生\n宝可梦的道具。",
        0xF8B1F9: "性能不错的球，\n比精灵球更容易\n捉到宝可梦。",
        0xF8B230: "性能很好的球，\n比超级球更容易\n捉到宝可梦。",
        0xF8B26A: "性能最好的球，\n能必定捉到\n宝可梦。",
        0xF8B6B0: "回复宝可梦\n20点HP。",
        0xF8B6DB: "回复宝可梦\n60点HP。",
        0xF8B706: "回复宝可梦\n120点HP。",
        0xF93583: "用来收纳树果混合器\n做出的宝可方块。",
        0xF934F3: "收纳树果粉碎机\n做出的树果粉末。",
        0xF8D31F: "延长树果树寿命的肥料。",
        0xF8D3C2: "提高树果突变几率的肥料。",
        0xF8DDC2: "小仙奶喜欢的\n草莓形状甜甜。",
        0xF8DE13: "小仙奶喜欢的\n树果形状甜甜。",
    }
    for off, zh in HAND.items():
        if put(data, golden, off, zh) == "ok":
            n += 1

    off = 0xF8B000
    while off < 0xF9B200:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0xF9B200 or eos - off > 200 or eos - off < 15:
            off += 1
            continue
        if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
            off = eos + 1
            continue
        en = decode_bytes(golden[off : eos + 1])
        zh = None
        for pat, rep in BERRY_DESC_RULES:
            if pat.match(en):
                zh = rep
                break
        if zh is None:
            # generic food/heal templates
            if re.match(r"(?is)^A bitter powder\nthat restores HP\nby (\d+) points\.$", en):
                m = re.match(r"(?is)^A bitter powder\nthat restores HP\nby (\d+) points\.$", en)
                zh = f"能回复{m.group(1)}点HP的\n苦味粉末。" if m else None
            elif "Lava Cookie" in en or "cures all status" in en.lower():
                zh = "能治愈所有异常状态的小吃。"
            elif re.search(r"(?i)chocolate|cookie|gateau|malasada|galette|sable|casteliacone|candy bar", en):
                # soft template
                zh = re.sub(r"(?i)Pokémon|Pokemon|POK[EÉ]MON", "宝可梦", en)
                zh = re.sub(r"(?i)restores HP", "回复HP", zh)
                zh = re.sub(r"(?i)status problems?", "异常状态", zh)
                if sum(1 for c in zh if "\u4e00" <= c <= "\u9fff") < 2:
                    zh = None
        if zh and put(data, golden, off, zh) == "ok":
            n += 1
        off = eos + 1
    return n


def fill_short_road_dialogs(data: bytearray, golden: bytes) -> int:
    """Translate remaining pure-EN dialogues in early/mid road banks using cache+rules."""
    cache: dict[str, str] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Common road NPC phrasebook
    PHRASES: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"(?is)^Huh\?\nYou want it, but not right now\?$"), "嗯?\n你想要,但现在不要?"),
        (re.compile(r"(?is)^Oh, don't be so negative!\nYou can have this!$"), "别这么消极!\n这个给你!"),
        (re.compile(r"(?is)^Please choose the two POK[EÉ]MON\nthat are to appear in battle\.$"), "请选择两只要\n出战的宝可梦。"),
        (re.compile(r"(?is)^h is next\.\nAre you ready\?$"), "下一个。\n准备好了吗?"),
    ]

    n = 0
    for start, end in [(0x2A0000, 0x2C0000), (0x2C0000, 0x2E0000), (0x260000, 0x290000)]:
        off = start
        while off < end:
            if in_skip(off):
                off += 1
                continue
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= end or eos - off > 180 or eos - off < 16:
                off += 1
                continue
            if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
                off = eos + 1
                continue
            en = decode_bytes(golden[off : eos + 1])
            if not looks_full_line(en):
                off = eos + 1
                continue
            # skip scripty / control-heavy
            if en.count("{FD:") + en.count("{FC:") > 4:
                off = eos + 1
                continue
            if sum(1 for c in en if c.isalpha()) < 10:
                off = eos + 1
                continue

            zh = None
            for pat, rep in PHRASES:
                if pat.match(en):
                    zh = rep
                    break
            if zh is None:
                zh = scrub(cache.get(en, ""))
            if not quality_ok(en, zh):
                off = eos + 1
                continue
            # preserve FD tokens from EN if ZH dropped them
            for m in re.finditer(r"\{FD:[0-9A-Fa-f]{2}\}", en):
                if m.group(0) not in zh:
                    zh = None
                    break
            if not zh:
                off = eos + 1
                continue
            if put(data, golden, off, zh) == "ok":
                n += 1
            off = eos + 1
    return n


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    print("1) apply locale ZH onto still-EN strings")
    ok, skip = apply_locale(data, golden)
    print(f"   applied={ok} skipped={skip}")

    print("2) special item names")
    print(f"   names={apply_item_names(data, golden)}")

    print("3) item/berry descriptions")
    print(f"   descs={apply_item_descs(data, golden)}")

    print("4) road dialogues from cache/phrases")
    print(f"   dialogs={fill_short_road_dialogs(data, golden)}")

    # keep nurse/options previous fixes by re-running light essentials? skip
    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("445566778899AABBCCDDEEFF00112233")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    # report remaining
    rem = 0
    for a, b in [(0x2A0000, 0x2E0000), (0xF9B680, 0xF9C200), (0xF8B1D0, 0xF8B800)]:
        off = a
        while off < b:
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= b or eos - off > 120 or eos - off < 12:
                off += 1
                continue
            en = decode_bytes(golden[off : eos + 1])
            if sum(c.isalpha() for c in en) >= 10 and bytes(data[off : eos + 1]) == golden[off : eos + 1]:
                rem += 1
            off = eos + 1
    print(f"5) remaining same-EN sample bands count≈{rem}")
    for off in (0xF9B6DF, 0xF9B6CD, 0xF9C383, 0x2A0000, 0xF8B1D2):
        eos = golden.find(b"\xff", off)
        print(f"   {off:08X} {decode_bytes(data[off:eos+1])[:60]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
