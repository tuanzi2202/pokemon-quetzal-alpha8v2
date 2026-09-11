#!/usr/bin/env python3
"""Translate Title-Case battle species / moves / abilities tables (inplace as EN).

Also fills FC-pool UPPERCASE ability/type/UI strings inplace (no pointer reloc).
Does NOT wholesale-restore FC pool (that wiped Chinese earlier).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from fill_and_apply_remaining import GOLDEN, LOCALE, OUT, ROM, scrub  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GLOSS = ROOT / "glossary"
SPECIES_START = 0x40E308  # ??????????
MOVES_START = 0x417D6A  # Pound
MOVES_END = 0x41B5C8  # after Nihil Light
ABIL_START = 0x426FE0  # Stench
FC_POOL = (0x0FC0000, 0x0FD0000)

# Day names stay English (narrow clock slots)
KEEP_EN_EXACT = {
    "SUNDAY",
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "A.M.",
    "P.M.",
    "AM",
    "PM",
}

# FC / UI short map (prefer forms that fit tiny inplace slots)
FC_EXACT: dict[str, str] = {
    "I CHOOSE YOU": "就选你了",
    "GOTCHA": "抓到了",
    "TRADE": "交换",
    "SAPPHIRE": "蓝宝石",
    "EVOLVE": "进化",
    "ENCYCLOPEDIA": "百科",
    "NATURE": "性格",
    "CENTER": "中心",
    "EGG": "蛋",
    "LINK": "联机",
    "SP. ABILITY": "特性",
    "TRAINER": "训练家",
    "VERSION": "版本",
    "POKéNAV": "导航器",
    "POKéMON": "宝可梦",
    "POKéDEX": "图鉴",
    "POKENAV": "导航器",
    "POKEMON": "宝可梦",
    "POKEDEX": "图鉴",
    "NAV": "导航",
    "MON": "宝",
    "GET": "得",
    "DEX": "鉴",
    "RUBY": "红宝石",
    "LEVEL": "等级",
    "RED": "红",
    "GREEN": "绿",
    "BAG": "背包",
    "FLAME": "火焰",
    "GOLD": "金",
    "LEAF": "叶",
    "SILVER": "银",
    "EMERALD": "绿宝石",
    "DARK": "恶",
    "COLOR": "颜色",
    "ALT. COLOR": "异色",
    "ROCK": "岩石",
    "BEAUTIFUL": "美丽",
    "BEAUTY": "美丽",
    "FIGHTING": "格斗",
    "SMART": "聪明",
    "SMARTNESS": "聪明",
    "COOL": "帅气",
    "COOLNESS": "帅气",
    "CUTE": "可爱",
    "CUTENESS": "可爱",
    "GRASS": "草",
    "GHOST": "幽灵",
    "ICE": "冰",
    "GROUND": "地面",
    "TYPE": "属性",
    "TOUGH": "强壮",
    "TOUGHNESS": "强壮",
    "ELECTRIC": "电",
    "POISON": "毒",
    "DRAGON": "龙",
    "NORMAL": "一般",
    "STEEL": "钢",
    "SHINE": "闪光",
    "FLYING": "飞行",
    "FIRE": "火",
    "WATER": "水",
    "BUG": "虫",
    "PSYCHIC": "超能",
    "PATTERN": "花纹",
    "ATTACK": "攻击",
    "BATTLE": "对战",
    "FIGHT": "战斗",
    "POWER": "力量",
    "MOVE": "招式",
    "YES": "是",
    "NO": "否",
    "CANCEL": "取消",
    "HP": "血",
    "PP": "PP",
    # Easy Chat / battle chatter (common)
    "MATCH UP": "对阵",
    "DECIDE": "决定",
    "LET ME WIN": "让我赢",
    "WINS": "胜利",
    "WIN": "赢",
    "WON": "赢了",
    "IF I WIN": "若我赢",
    "WHEN I WIN": "赢的时候",
    "CAN'T WIN": "赢不了",
    "CAN WIN": "能赢",
    "NO MATCH": "不对等",
    "SPIRIT": "精神",
    "DECIDED": "决定了",
    "TRUMP CARD": "王牌",
    "TAKE THAT": "接招",
    "COME ON": "来吧",
    "SURRENDER": "投降",
    "GUTSY": "胆量",
    "TALENT": "才能",
    "STRATEGY": "策略",
    "SMITE": "痛击",
    "MATCH": "对决",
    "VICTORY": "胜利",
    "OFFENSIVE": "进攻",
    "SENSE": "感觉",
    "VERSUS": "对战",
    "FIGHTS": "战斗",
    "CHALLENGE": "挑战",
    "STRONG": "强",
    "TOO STRONG": "太强了",
    "GO EASY": "手下留情",
    "FOE": "对手",
    "GENIUS": "天才",
    "LEGEND": "传说",
    "ESCAPE": "逃跑",
    "AIM": "瞄准",
    "RESUSCITATE": "复活",
    "POINTS": "点数",
    "SERIOUS": "认真",
    "GIVE UP": "放弃",
    "LOSS": "败北",
    "IF I LOSE": "若我输",
    "LOST": "输了",
    "LOSE": "输",
    "GUARD": "防御",
    "PARTNER": "搭档",
    "REJECT": "拒绝",
    "ACCEPT": "接受",
    "INVINCIBLE": "无敌",
    "RECEIVED": "收到",
    "EASY": "简单",
    "WEAK": "弱",
    "TOO WEAK": "太弱",
    "PUSHOVER": "轻松",
    "LEADER": "首领",
    "RULE": "规则",
}


def load_maps() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    moves = {
        r["name_en"].strip(): r["name_zh"].strip()
        for r in json.loads((GLOSS / "move_list.json").read_text(encoding="utf-8"))
        if r.get("name_en") and r.get("name_zh")
    }
    abils = {
        r["name_en"].strip(): r["name_zh"].strip()
        for r in json.loads((GLOSS / "ability_list.json").read_text(encoding="utf-8"))
        if r.get("name_en") and r.get("name_zh")
    }
    species = {
        r["name_en"].strip(): r["name_zh"].strip()
        for r in json.loads((GLOSS / "simple_pokedex.json").read_text(encoding="utf-8"))
        if r.get("name_en") and r.get("name_zh")
    }
    # aliases / Quetzal naming
    aliases = {
        "Double Slap": "DoubleSlap",
        "Vise Grip": "Vice Grip",
        "ViceGrip": "Vice Grip",
        "Thunder Punch": "ThunderPunch",
        "Poison Powder": "PoisonPowder",
        "Thunder Shock": "ThunderShock",
        "Bubble Beam": "BubbleBeam",
        "Sonic Boom": "SonicBoom",
        "Self-Destruct": "SelfDestruct",
        "Selfdestruct": "SelfDestruct",
        "Hi Jump Kick": "High Jump Kick",
        "High Jump Kick": "High Jump Kick",
        "Feint Attack": "Faint Attack",
        "Faint Attack": "Faint Attack",
        "Smelling Salts": "SmellingSalt",
        "Ancient Power": "AncientPower",
        "Extreme Speed": "ExtremeSpeed",
        "Dragon Breath": "DragonBreath",
        "Dynamic Punch": "DynamicPunch",
        "Lock-On": "Lock-On",
        "Will-O-Wisp": "Will-O-Wisp",
        "Mud-Slap": "Mud-Slap",
        "Wake-Up Slap": "Wake-Up Slap",
        "Baby-Doll Eyes": "Baby-Doll Eyes",
        "Ho-Oh": "Ho-Oh",
        "Porygon-Z": "Porygon-Z",
        "Jangmo-o": "Jangmo-o",
        "Hakamo-o": "Hakamo-o",
        "Kommo-o": "Kommo-o",
        "Type: Null": "Type: Null",
        "Mr. Mime": "Mr. Mime",
        "Mime Jr.": "Mime Jr.",
        "Nidoran♀": "Nidoran♀",
        "Nidoran♂": "Nidoran♂",
        "Farfetch'd": "Farfetch'd",
        "Sirfetch'd": "Sirfetch'd",
    }
    # build case-insensitive move lookup
    move_ci = {k.lower(): v for k, v in moves.items()}
    for a, b in aliases.items():
        if b in moves:
            move_ci[a.lower()] = moves[b]
        if a in moves:
            move_ci[a.lower()] = moves[a]
    # also map without spaces/hyphens
    extra = {}
    for k, v in list(move_ci.items()):
        extra[re.sub(r"[^a-z0-9]", "", k)] = v
    move_ci.update(extra)

    abil_ci = {k.lower(): v for k, v in abils.items()}
    for k, v in list(abil_ci.items()):
        abil_ci[re.sub(r"[^a-z0-9]", "", k)] = v

    sp_ci = {k.lower(): v for k, v in species.items()}
    return move_ci, abil_ci, sp_ci


def lookup(name: str, table: dict[str, str]) -> str | None:
    n = name.strip()
    if not n or n in {"-", "?", "??????????"}:
        return None
    if n.lower() in table:
        return table[n.lower()]
    key = re.sub(r"[^a-z0-9]", "", n.lower())
    if key in table:
        return table[key]
    # regional prefixes
    for pref, zhpref in (
        ("Alolan ", "阿罗拉"),
        ("Galarian ", "伽勒尔"),
        ("Hisuian ", "洗翠"),
        ("Paldean ", "帕底亚"),
        ("Mega ", "超级"),
        ("Primal ", "原始"),
        ("Gigantamax ", "超极巨"),
        ("Shadow ", "暗影"),
    ):
        if n.startswith(pref):
            base = lookup(n[len(pref) :], table)
            if base:
                return zhpref + base
    return None


def walk_strings(rom: bytes, start: int, end: int) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    off = start
    while off < end:
        eos = rom.find(b"\xff", off)
        if eos < 0 or eos >= end or eos - off > 48:
            off += 1
            continue
        text = decode_bytes(rom[off : eos + 1])
        out.append((off, text))
        off = eos + 1
    return out


def inplace_padded(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    capacity = eos - off + 1
    enc, missing = encode_text_safe(zh)
    if len(enc) > capacity:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > capacity:
            cut = cut[:-1]
        enc, missing = encode_text_safe(cut)
        if len(enc) > capacity:
            return "too_long"
    # right-align with leading spaces (0x00) like original EN
    pad = capacity - len(enc)
    data[off : off + capacity] = (b"\x00" * pad) + enc
    return "ok" if not missing else "ok_missing"


def translate_table(
    data: bytearray,
    golden: bytes,
    start: int,
    end: int,
    table: dict[str, str],
    label: str,
) -> tuple[int, int, int]:
    rows = walk_strings(golden, start, end)
    ok = miss = fail = 0
    for off, raw in rows:
        name = raw.strip()
        if not name or set(name) <= {"-", "?", " "}:
            continue
        zh = lookup(name, table)
        if not zh:
            miss += 1
            continue
        st = inplace_padded(data, golden, off, zh)
        if st.startswith("ok"):
            ok += 1
        else:
            fail += 1
    print(f"{label}: ok={ok} miss={miss} fail={fail} rows={len(rows)}")
    return ok, miss, fail


def fill_fc_pool(data: bytearray, golden: bytes, abil_ci: dict[str, str], move_ci: dict[str, str]) -> int:
    """Inplace-only FC string bodies; skip day names."""
    a, b = FC_POOL
    rows = walk_strings(golden, a, b)
    n = 0
    for off, raw in rows:
        en = raw.strip()
        # normalize POKé / POKe variants for lookup
        en_key = en.replace("é", "e").replace("É", "E")
        if not en or en.upper() in KEEP_EN_EXACT:
            continue
        zh = None
        for key in (en, en.upper(), en_key, en_key.upper(), en.title()):
            if key in FC_EXACT:
                zh = FC_EXACT[key]
                break
            if key.upper() in FC_EXACT:
                zh = FC_EXACT[key.upper()]
                break
        if not zh:
            zh = lookup(en, abil_ci) or lookup(en, move_ci)
            if not zh:
                titled = en.title() if en.isupper() else en
                zh = lookup(titled, abil_ci) or lookup(titled, move_ci)
        if not zh:
            continue
        st = inplace_padded(data, golden, off, zh)
        if st == "too_long" and len(zh) > 1:
            st = inplace_padded(data, golden, off, zh[: max(1, len(zh) // 2)])
        if st == "too_long" and len(zh) > 1:
            st = inplace_padded(data, golden, off, zh[:1])
        if st.startswith("ok"):
            n += 1
    print(f"FC_pool inplace={n}/{len(rows)}")
    return n


def scrub_dialogue_locale() -> int:
    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    n = 0
    repl = [
        (re.compile(r"(?i)\bPOKé?\s*MON\b"), "宝可梦"),
        (re.compile(r"(?i)\bPOKé?\s*DEX\b"), "宝可梦图鉴"),
        (re.compile(r"(?i)\bPOKé?\s*NAV\b"), "宝可梦导航器"),
        (re.compile(r"(?<![A-Za-z])MON(?=[ :，,!.。！？\n{]|$)"), "宝可梦"),
        (re.compile(r"(?<![A-Za-z])DEX(?=[ :，,!.。！？\n{]|$)"), "图鉴"),
        (re.compile(r"(?<![A-Za-z])EGG(?=[ :，,!.。！？\n{]|$)"), "蛋"),
        (re.compile(r"(?<![A-Za-z])ROD(?=[ :，,!.。！？\n{]|$)"), "钓竿"),
        (re.compile(r"(?i)\bKYOGRE\b"), "盖欧卡"),
        (re.compile(r"(?i)\bGROUDON\b"), "固拉多"),
        (re.compile(r"(?i)\bRAYQUAZA\b"), "烈空坐"),
    ]
    for r in rows:
        zh = r.get("zh") or ""
        if not zh:
            continue
        z2 = scrub(zh)
        for pat, rep in repl:
            z2 = pat.sub(rep, z2)
        if z2 != zh:
            r["zh"] = z2
            n += 1
    LOCALE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print(f"locale scrubbed={n}")
    return n


def apply_locale_dialogue(data: bytearray, golden: bytes) -> int:
    """Re-apply locale ZH only where ROM body is still English or has Latin bleed."""
    from fill_and_apply_remaining import quality_ok  # noqa: E402

    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    n = 0
    for r in rows:
        off = int(r["offset"])
        if FC_POOL[0] <= off < FC_POOL[1]:
            continue
        if 0x40E000 <= off < 0x42A000:
            continue
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        if not zh or not any("\u4e00" <= c <= "\u9fff" for c in zh):
            continue
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos - off > 500:
            continue
        capacity = eos - off + 1
        rom_same = bytes(data[off : eos + 1]) == golden[off : eos + 1]
        cur = decode_bytes(bytes(data[off : eos + 1]))
        plain = re.sub(r"\{[^}]+\}", "", cur)
        latin_bleed = bool(re.search(r"[A-Za-z]{3,}", plain))
        if not rom_same and not latin_bleed:
            continue
        if not quality_ok(en, zh) and len(en) > 40:
            continue
        enc, _ = encode_text_safe(zh)
        if len(enc) > capacity:
            cut = zh
            while cut and len(encode_text_safe(cut)[0]) > capacity:
                cut = cut[:-1]
            enc, _ = encode_text_safe(cut)
            if len(enc) > capacity:
                continue
        data[off : off + capacity] = enc + b"\x00" * (capacity - len(enc))
        n += 1
    print(f"locale dialogue applied={n}")
    return n


def main() -> int:
    move_ci, abil_ci, sp_ci = load_maps()
    print(f"maps moves={len(move_ci)} abil={len(abil_ci)} species={len(sp_ci)}")

    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    scrub_dialogue_locale()

    translate_table(data, golden, SPECIES_START, MOVES_START, sp_ci, "species_title")
    translate_table(data, golden, MOVES_START, MOVES_END, move_ci, "moves_title")
    # abilities: walk until we leave plausible names (~400)
    translate_table(data, golden, ABIL_START, ABIL_START + 0x3000, abil_ci, "abil_title")
    fill_fc_pool(data, golden, abil_ci, move_ci)
    apply_locale_dialogue(data, golden)

    # Restore ONLY clock day-name + system strings (not whole FC pool)
    from restore_clock_ui import CLOCK_OFFSETS, CLOCK_EN, DAY, restore_body  # noqa: E402

    for off in sorted(CLOCK_OFFSETS):
        restore_body(data, golden, off)
    # day names inside FC
    for off, raw in walk_strings(golden, *FC_POOL):
        if DAY.match(raw.strip()) or CLOCK_EN.search(raw):
            restore_body(data, golden, off)

    # Mom opening: inplace body only (no pointer retarget)
    from fix_clock_and_mom_open import OPENING  # noqa: E402

    for off, zh in OPENING.items():
        if off == 0x287A50:
            continue
        inplace_padded(data, golden, off, zh)

    OUT.write_bytes(data)
    ROM.write_bytes(data)

    # verify samples
    for off, lab in [
        (0x40EFCE, "Treecko"),
        (0x417D6A, "Pound"),
        (0x417F93, "Tackle"),
        (0x426FE0, "Stench"),
        (0x0FC3053, "LEVEL"),
        (0x0FC31D1, "STENCH"),
        (0x0FC303E, "MON"),
    ]:
        eos = data.find(b"\xff", off)
        print(f"  {lab}: {decode_bytes(bytes(data[off:eos+1]))!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
