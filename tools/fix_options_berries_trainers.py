#!/usr/bin/env python3
"""Fix Options UI, berry names, and remaining EN trainer intros."""
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

# --- Options (ASCII punctuation; keep FC color prefixes) ---
OPTIONS: dict[int, str] = {
    0x10222F5: "选项",
    0x10222FC: "文字速度",
    0x1022307: "战斗动画",
    0x1022314: "对战方式",
    0x1022321: "声音",
    0x1022327: "窗口",
    0x102232D: "取消",
    0x1022334: "按键模式",
    # values with color prefix
    0x1022340: "{FC:01}{06}{FC:03}{07}慢",
    0x102234B: "{FC:01}{06}{FC:03}{07}中",
    0x1022355: "{FC:01}{06}{FC:03}{07}快",
    0x1022360: "{FC:01}{06}{FC:03}{07}开",
    0x1022369: "{FC:01}{06}{FC:03}{07}关",
    0x1022373: "{FC:01}{06}{FC:03}{07}换人",
    0x102237F: "{FC:01}{06}{FC:03}{07}定",  # SET — 3-byte slot after FC
    0x1022389: "{FC:01}{06}{FC:03}{07}单声",  # MONO — tight
    0x1022394: "{FC:01}{06}{FC:03}{07}立体声",
    0x10223A1: "{FC:01}{06}{FC:03}{07}样式",
    0x10223B3: "{FC:01}{06}{FC:03}{07}普通",
}

# Mirror option-value block (seen earlier around 1024Bxx)
OPTIONS_MIRROR_SCAN = (0x1024B00, 0x1024E00)

# Official-ish berry names (item table @ F9DAxx)
BERRIES: dict[str, str] = {
    "Cheri Berry": "樱子果",
    "Chesto Berry": "零余果",
    "Pecha Berry": "桃桃果",
    "Rawst Berry": "莓莓果",
    "Aspear Berry": "利木果",
    "Leppa Berry": "苹野果",
    "Oran Berry": "橙橙果",
    "Persim Berry": "柿仔果",
    "Lum Berry": "木子果",
    "Sitrus Berry": "文柚果",
    "Figy Berry": "无花果",
    "Wiki Berry": "墨墨果",
    "Mago Berry": "蕉香果",
    "Aguav Berry": "苦蕉果",
    "Iapapa Berry": "凤梨果",
    "Razz Berry": "莓莓果果",  # 红阳果
    "Bluk Berry": "蓝莓果",
    "Nanab Berry": "黄蕉果",
    "Wepear Berry": "西梨果",
    "Pinap Berry": "凤梨果",
    "Pomeg Berry": "石榴果",
    "Kelpsy Berry": "藻根果",
    "Qualot Berry": "比巴果",
    "Hondew Berry": "蜜腹果",
    "Grepa Berry": "萄葡果",
    "Tamato Berry": "茄番果",
    "Cornn Berry": "玉黍果",
    "Magost Berry": "岳竹果",
    "Rabuta Berry": "毛丹果",
    "Nomel Berry": "刺角果",
    "Spelon Berry": "龙火果",
    "Pamtre Berry": "沙鳞果",
    "Watmel Berry": "瓜西果",
    "Durin Berry": "榴莲果",
    "Belue Berry": "星桃果",
    "Liechi Berry": "枝荔果",
    "Ganlon Berry": "龙须果",
    "Salac Berry": "沙罗果",
    "Petaya Berry": "莲蒲果",
    "Apicot Berry": "杏仔果",
    "Lansat Berry": "兰萨果",
    "Starf Berry": "星桃果",
    "Enigma Berry": "谜芝果",
    "Micle Berry": "奇秘果",
    "Custap Berry": "释陀果",
    "Jaboca Berry": "嘉宝果",
    "Rowap Berry": "莲雾果",
    "Kee Berry": "妃子果",
    "Maranga Berry": "玛古果",
    "Resist Berry": "抵抗果",
    "Berry Sweet": "果实甜糖",
    "Chilan Berry": "奇拉果",
    "Occa Berry": "巧可果",
    "Passho Berry": "千香果",
    "Wacan Berry": "烛木果",
    "Rindo Berry": "罗子果",
    "Yache Berry": "番荔果",
    "Chople Berry": "灯浆果",
    "Kebia Berry": "枝荔果",
    "Shuca Berry": "释迦果",
    "Coba Berry": "棱瓜果",
    "Payapa Berry": "木瓜果",
    "Tanga Berry": "藤距果",
    "Charti Berry": "瓜南果",
    "Kasib Berry": "青梨果",
    "Haban Berry": "宽仁果",
    "Colbur Berry": "雾莲果",
    "Babiri Berry": "脆骨果",
    "Roseli Berry": "玫玫果",
}

# Fix wrong berry nicknames to official SC
BERRIES.update(
    {
        "Razz Berry": "红阳果",
        "Bluk Berry": "蓝莓果",
        "Nanab Berry": "黄蕉果",
        "Wepear Berry": "西梨果",
        "Pinap Berry": "凤梨果",
        "Starf Berry": "星蔓果",
    }
)

# Hand trainer intros (user example + common early)
TRAINER_HAND: dict[int, str] = {
    0x32BA63: "哈哈!四目相对了!\n就用我的虫系宝可梦对战吧!",
    0x32C512: "吉娜: 好,我们用\n宝可梦对战吧!",
}

# Pattern-based rewrites for remaining EN intros (keep FD/WAIT)
INTRO_RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?is)^Hahah!\s*Our eyes met!\s*\nI'll take you on with my BUG POK[EÉ]MON!?$"
        ),
        "哈哈!四目相对了!\n就用我的虫系宝可梦对战吧!",
    ),
    (
        re.compile(r"(?is)^Our eyes met!\s*\nThere's no getting away now!?$"),
        "四目相对了!\n这次别想逃!",
    ),
    (
        re.compile(r"(?is)^Hahah! Our eyes met!\s*\nI'll take you on with my (.+?)!?$"),
        r"哈哈!四目相对了!\n就用我的\1对战吧!",
    ),
    (
        re.compile(r"(?is)^I'll take you on with my (.+?)!?$"),
        r"就用我的\1对战吧!",
    ),
    (
        re.compile(r"(?is)^My (.+?) are tough!\s*\nLet's battle!?$"),
        r"我的\1很强!\n来对战吧!",
    ),
    (
        re.compile(r"(?is)^I'm growing bored of swimming…\s*\nHow about a battle[!?]?$"),
        "游泳游腻了…\n来场对战怎么样?!",
    ),
    (
        re.compile(r"(?is)^You want to battle(, right)?[!?]?$"),
        "想对战吗?!",
    ),
    (
        re.compile(r"(?is)^Let's battle!?$"),
        "来对战吧!",
    ),
    (
        re.compile(r"(?is)^How about a battle[!?]?$"),
        "来场对战怎么样?!",
    ),
    (
        re.compile(r"(?is)^I challenge you to a battle!?$"),
        "我向你挑战!",
    ),
]


def put(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    cap = eos - off + 1
    enc, miss = encode_text_safe(zh)
    if miss:
        print(f"  miss @{off:08X} {miss[:8]} in {zh[:40]!r}")
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    if len(body) + 1 > cap:
        # trim Chinese carefully but keep FD/FC/WAIT tokens
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > cap:
            # remove last non-brace char
            if cut.endswith("}"):
                break
            cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        body = enc[:-1]
        if len(body) + 1 > cap:
            return f"long need={len(body)+1} cap={cap}"
        print(f"  TRIM {off:08X}")
    data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))
    return "ok"


def put_padded_name(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    """Item names often have leading 00 pads like English."""
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    cap = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    if len(body) + 1 > cap:
        return "long"
    pad = cap - 1 - len(body)
    data[off : off + cap] = (b"\x00" * pad) + body + b"\xff"
    return "ok"


def scrub_pokemon_words(en: str) -> str:
    z = en
    z = re.sub(r"(?i)POK[EÉ]\s*MON", "宝可梦", z)
    z = re.sub(r"(?i)Pokémon", "宝可梦", z)
    z = re.sub(r"(?i)Pokemon", "宝可梦", z)
    z = re.sub(r"(?i)BUG\s*宝可梦", "虫系宝可梦", z)
    z = re.sub(r"(?i)WATER\s*宝可梦", "水系宝可梦", z)
    z = re.sub(r"(?i)FIRE\s*宝可梦", "火系宝可梦", z)
    z = re.sub(r"(?i)GRASS\s*宝可梦", "草系宝可梦", z)
    z = re.sub(r"(?i)ELECTRIC\s*宝可梦", "电系宝可梦", z)
    z = re.sub(r"(?i)TRAINER", "训练家", z)
    return z


def translate_intro(en: str) -> str | None:
    en2 = scrub_pokemon_words(en.strip())
    for pat, rep in INTRO_RULES:
        m = pat.match(en.strip()) or pat.match(en2)
        if m:
            if "\\" in rep or rep.startswith("r"):
                pass
            out = pat.sub(rep, en.strip())
            if out == en.strip():
                out = pat.sub(rep, en2)
            return scrub_pokemon_words(out)
    # generic: still mostly English battle challenge lines
    low = en.lower()
    if any(
        k in low
        for k in (
            "eyes met",
            "take you on",
            "let's battle",
            "how about a battle",
            "challenge you",
            "want to battle",
            "battle me",
            "i'll battle",
            "come on",
            "prepare to",
        )
    ):
        # light template translations
        z = scrub_pokemon_words(en)
        z = re.sub(r"(?i)Hahah!?|Hahaha!?|Wahaha!?", "哈哈!", z)
        z = re.sub(r"(?i)Our eyes met!", "四目相对了!", z)
        z = re.sub(r"(?i)I'll take you on with my ", "就用我的", z)
        z = re.sub(r"(?i)I'll take you on!?!", "我要和你对战!", z)
        z = re.sub(r"(?i)There's no getting away now!", "这次别想逃!", z)
        z = re.sub(r"(?i)Let's battle!?", "来对战吧!", z)
        z = re.sub(r"(?i)How about a battle!?", "来场对战怎么样?!", z)
        z = re.sub(r"(?i)I challenge you to a battle!?", "我向你挑战!", z)
        z = re.sub(r"(?i)You want to battle!?", "想对战吗?!", z)
        z = re.sub(r"(?i)Prepare to lose!?", "做好输掉的准备吧!", z)
        # if still mostly Latin, skip
        latin = sum(1 for c in z if ("a" <= c <= "z") or ("A" <= c <= "Z"))
        cjk = sum(1 for c in z if "\u4e00" <= c <= "\u9fff")
        if cjk >= 4 and latin <= 8:
            return z
        if cjk >= 6:
            return z
    return None


def mirror_options_by_en(data: bytearray, golden: bytes) -> int:
    """Find same EN option labels elsewhere and apply same ZH."""
    en_to_zh = {
        "OPTION": "选项",
        "TEXT SPEED": "文字速度",
        "BATTLE SCENE": "战斗动画",
        "BATTLE STYLE": "对战方式",
        "SOUND": "声音",
        "FRAME": "窗口",
        "CANCEL": "取消",
        "BUTTON MODE": "按键模式",
    }
    n = 0
    for start, end in [(0x101B9D0, 0x101BA10), (0x101EDB0, 0x101EDE0), (0x1022450, 0x1022480), (0x1024B00, 0x1024E80)]:
        off = start
        while off < end:
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= end + 20 or eos - off > 20:
                off += 1
                continue
            en = decode_bytes(golden[off : eos + 1]).strip()
            # strip FC prefixes for matching
            en_plain = re.sub(r"\{FC:[0-9A-F]{2}\}", "", en).strip()
            if en_plain in en_to_zh:
                zh = en_to_zh[en_plain]
                if put(data, golden, off, zh) == "ok":
                    n += 1
            elif en.startswith("{FC:01}{06}{FC:03}{07}"):
                val = en_plain
                mapv = {
                    "SLOW": "慢",
                    "MID": "中",
                    "FAST": "快",
                    "ON": "开",
                    "OFF": "关",
                    "SHIFT": "换人",
                    "SET": "定",
                    "MONO": "单声",
                    "STEREO": "立体声",
                    "TYPE": "样式",
                    "NORMAL": "普通",
                    "VERY SLOW": "很慢",
                }
                if val in mapv:
                    zh = "{FC:01}{06}{FC:03}{07}" + mapv[val]
                    if put(data, golden, off, zh) == "ok":
                        n += 1
            off = eos + 1
    return n


def apply_berries(data: bytearray, golden: bytes) -> int:
    n = 0
    # scan item name bank + alt berry name bank
    for start, end in [(0xF9DA00, 0xF9E400), (0x42DF80, 0x42E020), (0xF9C4F0, 0xF9C520)]:
        off = start
        while off < end:
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= end or eos - off > 24 or eos - off < 4:
                off += 1
                continue
            en = decode_bytes(golden[off : eos + 1]).strip()
            if en in BERRIES:
                if put_padded_name(data, golden, off, BERRIES[en]) == "ok":
                    n += 1
            off = eos + 1
    return n


def apply_trainer_intros(data: bytearray, golden: bytes) -> int:
    n = 0
    for off, zh in TRAINER_HAND.items():
        if put(data, golden, off, zh) == "ok":
            n += 1
            print(f"  HAND {off:08X}")

    # Scan dialogue bank for EN intros matching keywords
    patterns = [
        bytes([0xD9, 0xED, 0xD9, 0xE7, 0x00, 0xE1, 0xD9, 0xE8]),  # eyes met
        bytes([0xE8, 0xD5, 0xDF, 0xD9, 0x00, 0xED, 0xE3, 0xE9, 0x00, 0xE3, 0xE2]),  # take you on
        bytes([0xC6, 0xD9, 0xE8, 0xB4, 0xE7, 0x00, 0xD6, 0xD5, 0xE8, 0xE8, 0xE0, 0xD9]),  # Let's battle
        bytes([0xC2, 0xE3, 0xEB, 0x00, 0xD5, 0xD6, 0xE3, 0xE9, 0xE8, 0x00, 0xD5, 0x00, 0xD6, 0xD5, 0xE8, 0xE8, 0xE0, 0xD9]),
    ]
    seen: set[int] = set()
    for pat in patterns:
        i = 0x260000
        while i < 0x360000:
            j = golden.find(pat, i, 0x360000)
            if j < 0:
                break
            prev = golden.rfind(b"\xff", max(0x260000, j - 120), j)
            start = prev + 1 if prev >= 0 else j
            eos = golden.find(b"\xff", j)
            if eos > 0 and 8 < eos - start < 160 and start not in seen:
                seen.add(start)
                en = decode_bytes(golden[start : eos + 1])
                # only if still English-ish in CN
                cur = decode_bytes(data[start : eos + 1])
                latin = sum(1 for c in cur if ("a" <= c <= "z") or ("A" <= c <= "Z"))
                if latin < 10 and "宝可梦" in cur and "eyes" not in cur.lower():
                    i = j + 1
                    continue
                zh = translate_intro(en)
                if zh and zh != en:
                    st = put(data, golden, start, zh)
                    if st == "ok":
                        n += 1
                        print(f"  OK {start:08X} {en[:40]!r} -> {zh[:40]!r}")
            i = j + 1

    # Second pass: remaining mixed EN battle lines
    off = 0x260000
    while off < 0x360000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0x360000 or eos - off > 160 or eos - off < 20:
            off = eos + 1 if eos >= off and eos < 0x360000 else off + 1
            continue
        if off in seen:
            off = eos + 1
            continue
        en = decode_bytes(golden[off : eos + 1])
        if not re.search(r"(?i)eyes met|take you on|let's battle|how about a battle|are tough", en):
            off = eos + 1
            continue
        # skip lines that are mostly script vars / not battle intros
        if en.count("{FD:") >= 2 or en.startswith("…") or en.startswith("..."):
            off = eos + 1
            continue
        cur = decode_bytes(data[off : eos + 1])
        latin = sum(1 for c in cur if ("a" <= c <= "z") or ("A" <= c <= "Z"))
        if latin < 8:
            off = eos + 1
            continue
        zh = translate_intro(en)
        if zh and zh != en:
            st = put(data, golden, off, zh)
            if st == "ok":
                n += 1
                seen.add(off)
                print(f"  OK2 {off:08X} {en[:40]!r}")
        off = eos + 1
    return n


def scan_fix_remaining_en_items(data: bytearray, golden: bytes) -> int:
    """Translate remaining identical-English item names in F9B/F9D banks if short."""
    # common leftovers
    EXTRA = {
        "Potion": "伤药",
        "Super Potion": "好伤药",
        "Hyper Potion": "厉害伤药",
        "Max Potion": "全满药",
        "Full Restore": "全复药",
        "Revive": "活力碎片",
        "Max Revive": "活力块",
        "Antidote": "解毒药",
        "Paralyze Heal": "解麻药",
        "Awakening": "解眠药",
        "Burn Heal": "灼伤药",
        "Ice Heal": "解冻药",
        "Full Heal": "万灵药",
        "Escape Rope": "离洞绳",
        "Repel": "除虫喷雾",
        "Super Repel": "白银喷雾",
        "Max Repel": "黄金喷雾",
        "X Attack": "力量强化",
        "X Defend": "防御强化",
        "X Speed": "速度强化",
        "X Accuracy": "命中强化",
        "X Special": "特攻强化",
        "Guard Spec.": "能力防守",
        "Dire Hit": "要害攻击",
        "Poké Doll": "皮皮玩偶",
        "Fluffy Tail": "向尾喵的尾巴",
        "Rare Candy": "神奇糖果",
        "PP Up": "PP提升剂",
        "PP Max": "PP极限提升剂",
        "Protein": "攻击增强剂",
        "Iron": "防御增强剂",
        "Carbos": "速度增强剂",
        "Calcium": "特攻增强剂",
        "Zinc": "特防增强剂",
        "HP Up": "HP增强剂",
        "Ether": "PP单项小补剂",
        "Max Ether": "PP单项全补剂",
        "Elixir": "PP多项小补剂",
        "Max Elixir": "PP多项全补剂",
    }
    n = 0
    off = 0xF9B200
    while off < 0xF9E400:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0xF9E400 or eos - off > 28 or eos - off < 3:
            off += 1
            continue
        en = decode_bytes(golden[off : eos + 1]).strip()
        if en in EXTRA and bytes(data[off : eos + 1]) == golden[off : eos + 1]:
            if put_padded_name(data, golden, off, EXTRA[en]) == "ok":
                n += 1
        off = eos + 1
    return n


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    print("1) Options menu")
    for off, zh in OPTIONS.items():
        st = put(data, golden, off, zh)
        print(f"  {off:08X} {st}")
    print(f"  mirrors {mirror_options_by_en(data, golden)}")

    print("2) Berries")
    print(f"  berries {apply_berries(data, golden)}")

    print("3) Extra EN items")
    print(f"  items {scan_fix_remaining_en_items(data, golden)}")

    print("4) Trainer intros")
    print(f"  intros {apply_trainer_intros(data, golden)}")

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("2233445566778899AABBCCDDEEFF0011")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    print("=== verify ===")
    for off in (0x10222F5, 0x10222FC, 0x1022307, 0x102234B, 0x1022360, 0x1022369, 0xF9DAE0, 0x32BA63):
        eos = golden.find(b"\xff", off)
        print(f"{off:08X} {decode_bytes(data[off:eos+1])!r} hex={data[off:eos+1].hex()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
