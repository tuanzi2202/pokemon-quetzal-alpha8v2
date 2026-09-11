#!/usr/bin/env python3
"""Sweep4: item-desc templates + map dialogue CN (locale fuzzy + hand dict)."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe, load_charmap  # noqa: E402
from fill_and_apply_remaining import quality_ok, scrub, CACHE  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"
LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"
MAP_TODO = ROOT / "work" / "map_en_todo.jsonl"

SKIP = [(0x279E71, 0x27A0D5), (0x2972B0, 0x297360), (0xFFFB50, 0xFFFC00)]


def in_skip(off: int) -> bool:
    return any(a <= off < b for a, b in SKIP)


def put(data: bytearray, golden: bytes, off: int, zh: str) -> bool:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return False
    cap = eos - off + 1
    text = zh
    while text:
        enc, _ = encode_text_safe(text)
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        body = enc[:-1]
        if len(body) + 1 <= cap:
            data[off : off + cap] = body + b"\xff" + bytes(cap - 1 - len(body))
            return True
        text = text[:-1]
    return False


def norm_key(s: str) -> str:
    s = s.replace("\r", "")
    s = re.sub(r"\{WAIT_(?:CLEAR|SCROLL)\}", "¶", s)
    s = re.sub(r"\{FD:[0-9A-Fa-f]{2}\}", "§", s)
    s = re.sub(r"\{FC:[0-9A-Fa-f]{2}\}", "", s)
    s = re.sub(r"\{[0-9A-Fa-f]{2}\}", "", s)
    s = s.replace("POKéMON", "POKEMON").replace("Pokémon", "POKEMON").replace("Pokémon", "POKEMON")
    s = s.replace("é", "e").replace("É", "E")
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


# ---- programmatic item templates ----
TYPE_ZH = {
    "Normal": "一般",
    "Fire": "火",
    "Water": "水",
    "Electric": "电",
    "Grass": "草",
    "Ice": "冰",
    "Fighting": "格斗",
    "Poison": "毒",
    "Ground": "地面",
    "Flying": "飞行",
    "Psychic": "超能力",
    "Bug": "虫",
    "Rock": "岩石",
    "Ghost": "幽灵",
    "Dragon": "龙",
    "Dark": "恶",
    "Steel": "钢",
    "Fairy": "妖精",
}

STAT_ZH = {
    "Attack": "攻击",
    "Defense": "防御",
    "Sp. Atk": "特攻",
    "Sp. Def": "特防",
    "Speed": "速度",
    "Atk": "攻击",
    "Def": "防御",
    "Spd": "速度",
    "HP": "HP",
}

CONTEST_ZH = {
    "Cool": "帅气",
    "Beauty": "美丽",
    "Cute": "可爱",
    "Smart": "聪明",
    "Tough": "强壮",
}


def translate_item_desc(en: str) -> str | None:
    en_s = en.strip()
    m = re.match(
        r"(?is)^A (?:fizzy soda drink|mineral water|nutritious milk|bitter root|very sweet drink|sweet chocolate|tasty snack)\nthat restores HP\nby (\d+) points\.$",
        en_s,
    )
    if m:
        kind = {
            "fizzy soda drink": "汽水",
            "mineral water": "矿泉水",
            "nutritious milk": "营养牛奶",
            "bitter root": "苦根",
            "very sweet drink": "非常甜的饮料",
            "sweet chocolate": "甜巧克力",
            "tasty snack": "美味零食",
        }
        low = en_s.lower()
        name = next(v for k, v in kind.items() if k in low)
        return f"能回复{m.group(1)}点HP的\n{name}。"

    m = re.match(r"(?is)^A bitter powder\nthat restores HP\nby (\d+) points\.$", en_s)
    if m:
        return f"能回复{m.group(1)}点HP的\n苦粉末。"
    if re.match(r"(?is)^A bitter powder\nthat heals all\nstatus problems\.$", en_s):
        return "能治愈所有异常\n状态的苦粉末。"
    if re.match(r"(?is)^A very bitter herb\nthat revives a\nfainted Pok[eé]mon\.$", en_s):
        return "能让濒死宝可梦\n复活的苦药草。"
    m = re.match(r"(?is)^A 100\{5B\} pure juice\nthat restores HP\nby (\d+) points\.$", en_s)
    if m:
        return f"能回复{m.group(1)}点HP的\n100%果汁。"
    if re.match(r"(?is)^A local specialty that\nheals all status problems\.$", en_s):
        return "能治愈所有异常状态\n的特产。"
    if re.match(r"(?is)^.*cures all the\nstatus problems of\none POK[EÉ]MON\.$", en_s):
        return "能治愈一只宝可梦的\n所有异常状态。"

    m = re.match(r"(?is)^Restores the PP\nof a selected\nmove by (\d+)\.$", en_s)
    if m:
        return f"让所选招式的PP\n回复{m.group(1)}。"
    if re.match(r"(?is)^Fully restores the\nPP of a selected\nmove\.$", en_s):
        return "让所选招式的PP\n完全回复。"
    m = re.match(r"(?is)^Restores the PP\nof all moves by (\d+)\.$", en_s)
    if m:
        return f"让所有招式的PP\n各回复{m.group(1)}。"

    if re.match(r"(?is)^Maximizes the IVs\nof one random stat\.$", en_s):
        return "将一项随机能力的\n个体值提到最高。"
    if re.match(r"(?is)^Maximizes the IVs\nof all stats\.$", en_s):
        return "将所有能力的\n个体值提到最高。"
    if re.match(r"(?is)^Switches a Pok[eé]-?\s*mon's ability\.$", en_s):
        return "改变宝可梦的特性。"

    m = re.match(
        r"(?is)^Can be smelled\. It\nups ([^,]+), but\nreduces ([^.]+)\.$",
        en_s,
    )
    if m:
        a = STAT_ZH.get(m.group(1).strip(), m.group(1).strip())
        b = STAT_ZH.get(m.group(2).strip(), m.group(2).strip())
        return f"有气味。提高{a}，\n但会降低{b}。"
    if re.match(r"(?is)^Can be smelled\. All\nstats grow at an\nequal rate\.$", en_s):
        return "有气味。各项能力\n均衡成长。"

    m = re.match(r"(?is)^Sharply raises stat\n([^ ]+(?:\. \w+)?)\nduring one battle\.$", en_s)
    if m:
        return f"在一场对战中\n大幅提高{STAT_ZH.get(m.group(1), m.group(1))}。"
    if re.match(r"(?is)^Sharply raises move\naccuracy during one\nbattle\.$", en_s):
        return "在一场对战中\n大幅提高命中率。"
    if re.match(r"(?is)^Raises the critical-hit\nratio during one battle\.$", en_s):
        return "在一场对战中\n提高击中要害率。"
    if re.match(r"(?is)^Prevents stat reduction\nwhen used in battle\.$", en_s):
        return "对战时使用可防止\n能力被降低。"
    if re.match(r"(?is)^Raises every stat during\none battle by one stage\.$", en_s):
        return "在一场对战中\n各项能力提高1级。"

    if re.match(r"(?is)^Use to escape instantly\nfrom a cave or a dungeon\.$", en_s):
        return "能立刻从洞穴或\n迷宫中脱出。"
    if re.match(r"(?is)^Works well if\nused in a\ndark place\.$", en_s):
        return "在黑暗的地方\n使用效果很好。"
    if re.match(r"(?is)^Works well if\nused on the\nfirst turn\.$", en_s):
        return "在第一回合使用\n效果很好。"

    # Hold items — berries / type boosts / EV items
    m = re.match(
        r"(?is)^A hold item that\nraises the power of\n(\w+)-type moves\.$",
        en_s,
    )
    if m:
        return f"携带后提高\n{TYPE_ZH.get(m.group(1), m.group(1))}属性招式威力。"
    m = re.match(
        r"(?is)^A hold item that\nboosts (\w+)-\s*type moves\.$",
        en_s,
    )
    if m:
        return f"携带后提高\n{TYPE_ZH.get(m.group(1), m.group(1))}属性招式威力。"
    m = re.match(
        r"(?is)^A hold item that\nslightly boosts\n(\w+)-type moves\.$",
        en_s,
    )
    if m:
        return f"携带后略微提高\n{TYPE_ZH.get(m.group(1), m.group(1))}属性招式威力。"

    m = re.match(r"(?is)^A hold item that\nraises (\w+) in\nContests\.$", en_s)
    if m:
        return f"携带后在华丽大赛中\n提高{CONTEST_ZH.get(m.group(1), m.group(1))}。"

    m = re.match(
        r"(?is)^A hold item that\npromotes(?: HP| Atk| Def| Spd)? gain,?\nbut reduces Speed\.$",
        en_s,
    )
    # more specific EV items:
    for en_pat, zh in [
        (
            r"(?is)^A hold item that\npromotes growth,\nbut reduces Speed\.$",
            "携带后促进成长，\n但会降低速度。",
        ),
        (
            r"(?is)^A hold item that\npromotes HP gain,\nbut reduces Speed\.$",
            "携带后促进HP努力值，\n但会降低速度。",
        ),
        (
            r"(?is)^A hold item that\npromotes Atk gain,\nbut reduces Speed\.$",
            "携带后促进攻击努力值，\n但会降低速度。",
        ),
        (
            r"(?is)^A hold item that\npromotes Def gain,\nbut reduces Speed\.$",
            "携带后促进防御努力值，\n但会降低速度。",
        ),
        (
            r"(?is)^Hold item that pro-\nmotes Sp\. Atk gain,\nbut reduces Speed\.$",
            "携带后促进特攻努力值，\n但会降低速度。",
        ),
        (
            r"(?is)^Hold item that pro-\nmotes Sp\. Def gain,\nbut reduces Speed\.$",
            "携带后促进特防努力值，\n但会降低速度。",
        ),
        (
            r"(?is)^A hold item that\npromotes Spd gain,\nbut reduces Speed\.$",
            "携带后促进速度努力值，\n但会降低速度。",
        ),
    ]:
        if re.match(en_pat, en_s):
            return zh

    berry_battle = [
        (r"(?is)^A hold item that\nheals paralysis\nin battle\.$", "携带后能在对战中\n治愈麻痹。"),
        (r"(?is)^A hold item that\nawaken(?:s)? Pok[eé]mon\nin battle\.$", "携带后能在对战中\n从睡眠中醒来。"),
        (r"(?is)^A hold item that\nheals poisoning\nin battle\.$", "携带后能在对战中\n治愈中毒。"),
        (r"(?is)^A hold item that\nheals a burn in\nbattle\.$", "携带后能在对战中\n治愈灼伤。"),
        (r"(?is)^A hold item that\ndefrosts Pok[eé]mon\nin battle\.$", "携带后能在对战中\n解除冰冻。"),
        (r"(?is)^A hold item that\nrestores 10 PP in\nbattle\.$", "携带后能在对战中\n回复10点PP。"),
        (r"(?is)^A hold item that\nrestores 10 HP in\nbattle\.$", "携带后能在对战中\n回复10点HP。"),
        (r"(?is)^A hold item that\nheals confusion\nin battle\.$", "携带后能在对战中\n治愈混乱。"),
        (r"(?is)^A hold item that\nheals any status\nproblem in battle\.$", "携带后能在对战中\n治愈所有异常状态。"),
        (r"(?is)^A hold item that\nrestores the user's\nHP a little\.$", "携带后能稍微\n回复自身HP。"),
        (r"(?is)^A hold item that\ngradually restores\nHP in battle\.$", "携带后能在对战中\n逐渐回复HP。"),
        (r"(?is)^A hold item that\nrestores HP upon\nstriking the foe\.$", "携带后攻击对手时\n回复HP。"),
        (r"(?is)^A hold item that\nimproves the\ncritical-hit rate\.$", "携带后提高\n击中要害率。"),
        (r"(?is)^A hold item that\nhelps repel wild\nPok[eé]mon\.$", "携带后有助于\n避开野生宝可梦。"),
        (r"(?is)^A hold item that\nassures fleeing\nfrom wild Pok[eé]mon\.$", "携带后必定能从\n野生宝可梦处逃走。"),
        (r"(?is)^A hold item that\noccasionally\nprevents fainting\.$", "携带后偶尔能\n防止濒死。"),
        (r"(?is)^A hold item that\nboosts Exp\. points\nearned in battle\.$", "携带后提高对战\n获得的经验值。"),
        (r"(?is)^A hold item that\ngets Exp\. points\nfrom battles\.$", "携带后即使未出战\n也能获得经验。"),
        (r"(?is)^A hold item that\noccasionally allows\nthe first strike\.$", "携带后偶尔能\n先制攻击。"),
        (r"(?is)^A hold item that\ncalms spirits and\nfosters friendship\.$", "携带后能安抚心情\n并增进亲密。"),
        (r"(?is)^A hold item that\nmay cause flinching\nwhen the foe is hit\.$", "携带后击中对手时\n可能使其畏缩。"),
        (r"(?is)^A hold item that\ncasts a glare to\nreduce accuracy\.$", "携带后能用强光\n降低对手命中。"),
        (r"(?is)^A hold item that\nrestores any\nlowered stat\.$", "携带后能回复\n被降低的能力。"),
        (r"(?is)^A held item that\nmakes the holder\nmove slower\.$", "携带后会让自己\n行动变慢。"),
        (r"(?is)^Doubles money in battle\nif the holder takes part\.$", "携带者参加对战时\n获得金钱翻倍。"),
        (r"(?is)^A hold item that\nslightly lowers the\nfoe's accuracy\.$", "携带后略微降低\n对手的命中率。"),
    ]
    for pat, zh in berry_battle:
        if re.match(pat, en_s):
            return zh

    # sweets
    if re.match(r"(?is)^Strawberry-shaped\nsweet loved by\nMilcery\.$", en_s):
        return "形状像草莓的甜糖，\n小仙奶很喜欢。"
    if re.match(r"(?is)^A berry-shaped\nsweet loved by\nMilcery\.$", en_s):
        return "形状像树果的甜糖，\n小仙奶很喜欢。"

    if re.match(r"(?is)^A fertilizer that\nups the life time\nof Berry trees\.$", en_s):
        return "延长树果树寿命的肥料。"
    if re.match(r"(?is)^A fertilizer that\nups the chance of\nBerry mutations\.$", en_s):
        return "提高树果突变几率的肥料。"
    if re.match(r"(?is)^A Berry to be used in cooking\.$", en_s):
        return "做料理时使用的树果。"
    if re.match(r"(?is)^A case that holds\nup to 9,999 Coins\.$", en_s):
        return "最多可装9999枚\n游戏硬币的盒子。"
    if re.match(r"(?is)^A shard from an ancient\nitem\. Can be sold cheaply\.$", en_s):
        return "古代道具的碎片。\n可以便宜卖掉。"
    if re.match(r"(?is)^A key that opens a door\ninside the Abandoned Ship\.$", en_s):
        return "能打开弃船内\n某扇门的钥匙。"
    if re.match(r"(?is)^A rare mushroom that\nwould sell at a high price\.$", en_s):
        return "能卖出高价的\n珍稀蘑菇。"
    if re.match(r"(?is)^A nugget of pure gold\.\nCan be sold at a high price\.$", en_s):
        return "纯金的金珠。\n可以卖出高价。"
    if re.match(r"(?is)^A beautiful bottle cap that\ngives off a silver gleam\.$", en_s):
        return "闪着银色光泽的\n漂亮瓶盖。"
    if re.match(r"(?is)^A beautiful bottle cap that\ngives off a golden gleam\.$", en_s):
        return "闪着金色光泽的\n漂亮瓶盖。"

    return None


# Hand translations for early/road NPCs (from map_en_todo)
HAND_MAP: dict[str, str] = {
    "See? This is PETALBURG CITY's GYM.": "看，这就是橙华市的道馆。",
    "This is the GYM's sign. Look for it\nwhenever you're looking for a GYM.": "这是道馆的招牌。\n找道馆时就认这个。",
    "PETALBURG CITY\n“Where people mingle with nature.”": "橙华市\n“人与自然交融之地。”",
    "I'm the EFFORT WOMAN! I'll go for it and\nsell you what you need!": "我是努力阿姨！\n我会加油把你要的卖给你！",
    "I'm the NATURE WOMAN! I'll go for it and\nsell you what you need!": "我是性格阿姨！\n我会加油把你要的卖给你！",
    "I'm the GIGA COOK! I'll go for it and\nsell you what you need!": "我是超级厨子！\n我会加油把你要的卖给你！",
    "{FD:01} received the EFFORT RIBBON.": "{FD:01}得到了努力奖章。",
    "{FD:01} put the EFFORT RIBBON\non {FD:02}.": "{FD:01}把努力奖章\n戴在了{FD:02}身上。",
    "Oh! Your {FD:02}, that EFFORT\nRIBBON looks good on it!": "哦！{FD:02}戴着努力奖章\n真好看！",
    "What is that over there?\nThat long line…": "那边是什么？\n好长的队伍……",
    "Hey, there! Quit pushing!\nThis is the line, can't you see?": "喂！别挤！\n看不见这是排队吗？",
    "Hey, you there!\nDon't butt in!": "喂，那边的！\n别插队！",
    "You can't run away!\nFight to the end!{FC:08}{40}": "逃不掉的！\n战斗到最后吧！{FC:08}{40}",
    "The mysterious strong winds\nhave dissipated!{FC:08}{40}": "神秘的强风\n已经平息了！{FC:08}{40}",
    "{FD:20} and {FD:21}\nwant to battle!{FC:08}{31}": "{FD:20}和{FD:21}\n要挑战！{FC:08}{31}",
}


def load_locale_fuzzy() -> tuple[dict[str, str], dict[str, str]]:
    exact: dict[str, str] = {}
    fuzzy: dict[str, str] = {}
    if not LOCALE.exists():
        return exact, fuzzy
    for line in LOCALE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        en = r.get("en") or ""
        zh = scrub(r.get("zh") or "")
        if not en or not quality_ok(en, zh):
            continue
        exact[en] = zh
        fuzzy[norm_key(en)] = zh
    return exact, fuzzy


def preserve_tokens(en: str, zh: str) -> bool:
    for tok in re.findall(r"\{(?:FD|FC):[0-9A-Fa-f]{2}\}|\{WAIT_(?:CLEAR|SCROLL)\}", en):
        if tok not in zh:
            return False
    return True


def apply_item_descs(data: bytearray, golden: bytes) -> int:
    n = 0
    off = 0xF8B000
    while off < 0xF9A000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0xF9A000 or eos - off > 160 or eos - off < 12:
            off += 1
            continue
        if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
            off = eos + 1
            continue
        en = decode_bytes(golden[off : eos + 1])
        zh = translate_item_desc(en)
        if zh and put(data, golden, off, zh):
            n += 1
        off = eos + 1
    return n


def apply_map(
    data: bytearray,
    golden: bytes,
    exact: dict[str, str],
    fuzzy: dict[str, str],
    cache: dict[str, str],
) -> tuple[int, int, int]:
    n_hand = n_loc = n_cache = 0
    todos = []
    if MAP_TODO.exists():
        for line in MAP_TODO.read_text(encoding="utf-8").splitlines():
            if line.strip():
                todos.append(json.loads(line))
    else:
        # rebuild quickly
        off = 0x260000
        while off < 0x360000:
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= 0x360000 or eos - off > 180 or eos - off < 16:
                off += 1
                continue
            if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
                off = eos + 1
                continue
            en = decode_bytes(golden[off : eos + 1])
            plain = re.sub(r"\{[^}]+\}", "", en)
            if sum(c.isalpha() for c in plain) >= 16 and len(re.findall(r"[A-Za-z]{3,}", plain)) >= 3:
                todos.append({"off": off, "en": en})
            off = eos + 1

    for item in todos:
        off = item["off"]
        en = item["en"]
        if in_skip(off):
            continue
        if bytes(data[off : golden.find(b"\xff", off) + 1]) != golden[off : golden.find(b"\xff", off) + 1]:
            continue
        zh = HAND_MAP.get(en)
        src = "hand"
        if not zh:
            zh = exact.get(en) or fuzzy.get(norm_key(en))
            src = "loc"
        if not zh:
            zh = scrub(cache.get(en, ""))
            src = "cache"
        if not zh or not quality_ok(en, zh) or not preserve_tokens(en, zh):
            continue
        if put(data, golden, off, zh):
            if src == "hand":
                n_hand += 1
            elif src == "loc":
                n_loc += 1
            else:
                n_cache += 1
    return n_hand, n_loc, n_cache


def decode_chs(data: bytes, to_str: dict[bytes, str]) -> str:
    parts: list[str] = []
    i = 0
    while i < len(data):
        if data[i] == 0xFF:
            break
        if data[i] == 0xFE:
            parts.append("\n")
            i += 1
            continue
        if i + 1 < len(data) and data[i : i + 2] in to_str:
            s2 = to_str[data[i : i + 2]]
            s1 = to_str.get(data[i : i + 1])
            if s1 and s1.isascii() and not s2.isascii():
                parts.append(s1)
                i += 1
                continue
            parts.append(s2)
            i += 2
            continue
        if data[i : i + 1] in to_str:
            parts.append(to_str[data[i : i + 1]])
            i += 1
            continue
        parts.append(f"[{data[i]:02X}]")
        i += 1
    return "".join(parts)


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    exact, fuzzy = load_locale_fuzzy()
    cache: dict[str, str] = {}
    if CACHE.exists():
        try:
            cache = {k: scrub(v) for k, v in json.loads(CACHE.read_text(encoding="utf-8")).items()}
        except Exception:
            cache = {}

    print(f"locale exact={len(exact)} fuzzy={len(fuzzy)} cache={len(cache)}")
    print("1) item descs…")
    n1 = apply_item_descs(data, golden)
    print(f"   {n1}")
    print("2) map dialogues…")
    h, l, c = apply_map(data, golden, exact, fuzzy, cache)
    print(f"   hand={h} locale={l} cache={c}")

    # hand extras for battle/menu
    for off, zh in HAND_MAP.items():
        pass
    for off_zh in [
        (0xFFBB33, "You can't run away!\nFight to the end!{FC:08}{40}"),
        (0xFFDD58, "The mysterious strong winds\nhave dissipated!{FC:08}{40}"),
        (0x100042C, "{FD:20} and {FD:21}\nwant to battle!{FC:08}{31}"),
    ]:
        off, en = off_zh
        zh = HAND_MAP.get(en)
        if zh and bytes(data[off : golden.find(b"\xff", off) + 1]) == golden[off : golden.find(b"\xff", off) + 1]:
            put(data, golden, off, zh)

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("8899AABBCCDDEEFF0011223344556677")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    _, to_str = load_charmap()
    for label, off in [("choco", 0xF8BB19), ("soda", 0xF8B80B), ("berry_para", 0xF9149A), ("gym", 0x269ADC)]:
        eos = golden.find(b"\xff", off)
        print(label, decode_chs(bytes(data[off : eos + 1]), to_str)[:80])

    # recount remaining item same-EN
    rem = 0
    off = 0xF8B000
    while off < 0xF9A000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0xF9A000 or eos - off > 160 or eos - off < 15:
            off += 1
            continue
        if bytes(data[off : eos + 1]) == golden[off : eos + 1]:
            en = decode_bytes(golden[off : eos + 1])
            if sum(c.isalpha() for c in en) >= 12 and en.count("{") <= 3:
                rem += 1
        off = eos + 1
    print("remaining item-desc same-EN ~", rem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
