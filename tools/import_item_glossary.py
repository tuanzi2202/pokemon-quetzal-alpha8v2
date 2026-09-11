#!/usr/bin/env python3
"""Generate committed item glossaries from audited local sources.

This maintainer tool imports official Simplified Chinese names from PokeAPI,
adds explicit Quetzal-only names, and replaces incomplete ROM descriptions
with compact hand-written Chinese. The generated JSON is used offline by the
normal build.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe, load_charmap  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
CURRENT = ROOT / "out" / "quetzal_084_cn.gba"
NAME_OUT = ROOT / "glossary" / "item_names_zh.json"
DESC_OUT = ROOT / "glossary" / "item_descriptions_zh.json"
NAME_START, NAME_END = 0xF9B200, 0xF9F700
DESC_START, DESC_END = 0xF8B000, 0xF9B200

CUSTOM_ITEM_NAMES: dict[str, str] = {
    "Radiant Ball": "闪耀球", "IV Up": "个体提升", "IV Max": "个体全满",
    "Giga Candy": "超极巨糖果", "Orange Mail": "橙色邮件",
    "Harbor Mail": "港口邮件", "Glitter Mail": "闪亮邮件",
    "Mech Mail": "机械邮件", "Wood Mail": "木纹邮件",
    "Wave Mail": "波浪邮件", "Bead Mail": "珠子邮件",
    "Shadow Mail": "暗影邮件", "Tropic Mail": "热带邮件",
    "Dream Mail": "梦幻邮件", "Fab Mail": "华丽邮件",
    "Retro Mail": "怀旧邮件", "HM08": "秘传08", "Bicycle": "自行车",
    "Berry Pouch": "树果袋", "Pokéblock Case": "宝可方块盒",
    "{53}{54} Box Link": "盒子连接",
    "Powder Jar": "粉末罐", "Fame Checker": "名人检查器",
    "Teachy TV": "教学电视", "Mystic Ticket": "神秘船票",
    "Aurora Ticket": "极光船票", "Old Sea Map": "古航海图",
    "Magma Emblem": "熔岩队之证", "Bike Voucher": "自行车兑换券",
    "Tri-Pass": "三岛通证", "Rainbow Pass": "彩虹通行证",
    "Ruby": "红玉", "Sapphire": "蓝宝石", "Berserk Gene": "疯狂基因",
    "Pastry Bag": "糕点袋", "Stellar Tera Shard": "星晶太晶碎块",
    "Reset Tera Shard": "重置太晶碎块", "Fresh Start Mochi": "净空糍",
    "Jubilife Muffin": "祝庆玛芬", "Remedy": "好伤药",
    "Fine Remedy": "厉害伤药", "Superb Remedy": "超厉害伤药",
    "Aux Evasion": "闪避强化", "Aux Guard": "防守强化",
    "Aux Power": "力量强化", "Aux Powerguard": "全力强化",
    "Choice Dumpling": "选择粽", "Swap Snack": "换位零食",
    "Twice-Spiced Radish": "双倍腌菜", "Gender Pill": "性别药丸",
    "Max Candy": "满级糖果", "Pokéshi Doll": "宝可梦木雕",
    "Bond Scroll": "羁绊卷轴",
}
CUSTOM_ITEM_NAMES.update({
    "Clefablite": "皮可西石", "Victreebelite": "大食花石",
    "Starminite": "宝石海星石", "Dragoninite": "快龙石",
    "Meganiumite": "大竺葵石", "Feraligite": "大力鳄石",
    "Skarmorite": "盔甲鸟石", "Froslassite": "雪妖女石",
    "Emboarite": "炎武王石", "Excadrite": "龙头地鼠石",
    "Scolipite": "蜈蚣王石", "Scraftinite": "头巾混混石",
    "Eelektrossite": "麻麻鳗鱼王石", "Chandelurite": "水晶灯火灵石",
    "Chesnaughtite": "布里卡隆石", "Delphoxite": "妖火红狐石",
    "Greninjite": "甲贺忍蛙石", "Pyroarite": "火炎狮石",
    "Floettite": "花叶蒂石", "Malamarite": "乌贼王石",
    "Barbaracite": "龟足巨铠石", "Dragalgite": "毒藻龙石",
    "Hawluchanite": "摔角鹰人石", "Zygardite": "基格尔德石",
    "Drampanite": "老翁龙石", "Falinksite": "列阵兵石",
    "Raichunite X": "雷丘石X", "Raichunite Y": "雷丘石Y",
    "Chimechite": "风铃铃石", "Absolite Z": "阿勃梭鲁石Z",
    "Staraptite": "姆克鹰石", "Garchompite Z": "烈咬陆鲨石Z",
    "Lucarionite Z": "路卡利欧石Z", "Heatranite": "席多蓝恩石",
    "Darkranite": "达克莱伊石", "Golurkite": "泥偶巨人石",
    "Meowsticite": "超能妙喵石", "Crabominite": "好胜毛蟹石",
    "Golisopite": "具甲武者石", "Magearnite": "玛机雅娜石",
    "Zeraorite": "捷拉奥拉石", "Scovillainite": "狠辣椒石",
    "Glimmoranite": "晶光花石", "Tatsugirinite": "米立龙石",
    "Baxcalibrite": "戟脊龙石",
})

TYPE_ZH = {
    "normal": "一般", "fire": "火", "water": "水", "electric": "电",
    "grass": "草", "ice": "冰", "fighting": "格斗", "poison": "毒",
    "ground": "地面", "flying": "飞行", "psychic": "超能力", "bug": "虫",
    "rock": "岩石", "ghost": "幽灵", "dragon": "龙", "dark": "恶",
    "steel": "钢", "fairy": "妖精", "stellar": "星晶",
}
STAT_ZH = {
    "hp": "HP", "attack": "攻击", "defense": "防御",
    "sp. atk": "特攻", "sp. def": "特防", "speed": "速度",
}


def key(text: str) -> str:
    return "".join(ch.lower() for ch in unicodedata.normalize("NFKD", text) if ch.isalnum())


def font_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text).replace("・", "·")


def decode_chs(raw: bytes, table: dict[bytes, str]) -> str:
    parts: list[str] = []
    i = 0
    while i < len(raw):
        if raw[i] == 0xFF:
            break
        if raw[i] == 0xFE:
            parts.append("\n")
            i += 1
            continue
        if i + 1 < len(raw) and raw[i:i + 2] in table:
            two, one = table[raw[i:i + 2]], table.get(raw[i:i + 1])
            if one and one.isascii() and not two.isascii():
                parts.append(one)
                i += 1
            else:
                parts.append(two)
                i += 2
            continue
        parts.append(table.get(raw[i:i + 1], "?"))
        i += 1
    return "".join(parts).strip()


def normalize_en(text: str) -> str:
    text = re.sub(r"(?i)Pok[eé]-?\s*mon", "Pokemon", text.replace("\r", " "))
    text = re.sub(r"-\s+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def incomplete_zh(text: str) -> bool:
    check = re.sub(r"(?i)(HP|PP|IV|EV|EXP|TM|HM)", "", text)
    cjk = sum("\u3400" <= ch <= "\u9fff" for ch in text)
    return cjk < 4 or bool(re.search(r"[A-Za-z]{2,}", check)) or "?" in text or "�" in text


def compact_description(source: str, species: dict[str, str]) -> str | None:
    """Translate patterns that were English or damaged in the current ROM."""
    text = normalize_en(source)
    low = text.lower()
    status_rules = (
        ("heals a poisoned pokemon", "治愈宝可梦的中毒。"),
        ("heals a paralyzed pokemon", "治愈宝可梦的麻痹。"),
        ("heals pokemon of a burn", "治愈宝可梦的灼伤。"),
        ("defrosts a frozen pokemon", "解除宝可梦的冰冻。"),
        ("awakens a sleeping pokemon", "唤醒睡眠中的宝可梦。"),
    )
    for needle, zh in status_rules:
        if low.startswith(needle):
            return zh
    if "heals all the status problems of one pokemon" in low:
        return "治愈宝可梦的所有\n异常状态。"
    if "fully restores the pp of a pokemon's moves" in low:
        return "让宝可梦所有招式的\nPP完全回复。"
    if "fully revives and restores all fainted pokemon" in low:
        return "让所有濒死宝可梦\n复活并完全回复。"
    if "revives a fainted pokemon with all its hp" in low:
        return "让濒死宝可梦复活并\n回复全部HP。"

    m = re.search(
        r"(?:raises|raises the base|an item that raises the base) "
        r"(hp|attack|defense|sp\. atk\.?|sp\. def\.?|speed)"
        r"(?: stat)?(?: of one| of a)? pokemon", low,
    )
    if m:
        return f"提高宝可梦的{STAT_ZH[m.group(1).rstrip('.')]}\n基础点数。"
    if "turns the ability of a pokemon into a rare ability" in low:
        return "将宝可梦特性变为\n隐藏特性。"
    if "raises the level of a pokemon by one" in low:
        return "让宝可梦提升1级。"

    amounts = {
        "very small": "极少量", "small": "少量", "moderate": "中量",
        "large": "大量", "very large": "巨量",
    }
    m = re.search(r"gives a (very small|small|moderate|large|very large) amount of exp", low)
    if m:
        return f"给予宝可梦{amounts[m.group(1)]}\n经验值。"
    if "changes a pokemon's gigantamax power" in low:
        return "改变宝可梦的\n超极巨化能力。"

    flute_rules = (
        ("awakens sleeping pokemon", "唤醒睡眠宝可梦的\n玻璃笛。"),
        ("snaps pokemon out of confusion", "解除宝可梦混乱的\n玻璃笛。"),
        ("snaps pokemon out of attraction", "解除宝可梦着迷的\n玻璃笛。"),
        ("keeps away wild pokemon", "减少野生宝可梦\n出现的玻璃笛。"),
        ("lures wild pokemon", "增加野生宝可梦\n出现的玻璃笛。"),
    )
    if "glass flute" in low:
        for needle, zh in flute_rules:
            if needle in low:
                return zh
    m = re.search(r"repels weak wild pokemon for (\d+) steps", low)
    if m:
        return f"在{m.group(1)}步内驱除\n较弱的野生宝可梦。"
    m = re.search(r"makes pokemon more likely to appear for (\d+) steps", low)
    if m:
        return f"在{m.group(1)}步内更容易\n遇到野生宝可梦。"
    if "use to flee from any battle with a wild pokemon" in low:
        return "必定能从野生宝可梦\n对战中逃走。"
    if "sweet honey that attracts wild pokemon" in low:
        return "使用后会吸引\n野生宝可梦。"
    if "ornament that depicts a pokemon from alola" in low:
        return "描绘阿罗拉宝可梦的\n装饰品。"

    fossil_rules = (
        ("ancient marine pokemon's seashell", "古代海洋宝可梦的\n贝壳化石碎片。"),
        ("ancient marine pokemon's shell", "古代海洋宝可梦的\n甲壳化石碎片。"),
        ("genes of an ancient pokemon", "含有古代宝可梦\n基因的化石。"),
        ("seafloordwelling pokemon", "古代海底宝可梦的\n化石。"),
        ("prehistoric pokemon's large jaw", "史前宝可梦的\n颚部化石碎片。"),
        ("prehistoric pokemon's skin sail", "史前宝可梦的\n背鳍化石碎片。"),
        ("skysoaring pokemon", "古代飞行宝可梦的\n化石。"),
        ("seadwelling pokemon", "古代海洋宝可梦的\n化石。"),
        ("landroaming pokemon", "古代陆地宝可梦的\n化石。"),
    )
    for needle, zh in fossil_rules:
        if needle in low:
            return zh

    if "den to attract dynamax pokemon" in low:
        return "投入宝可梦巢穴会\n吸引极巨化宝可梦。"
    mail_species = {
        "zigzagoon": "蛇纹熊", "wingull": "长翅鸥", "pikachu": "皮卡丘",
        "magnemite": "小磁怪", "slakoth": "懒人獭", "wailmer": "吼吼鲸",
        "duskull": "夜巡灵", "bellossom": "美丽花", "gorgeous": "华丽",
    }
    m = re.search(r"a (\w+)-print mail to be held by a pokemon", low)
    if m:
        return f"印有{mail_species.get(m.group(1), m.group(1))}图案，供\n宝可梦携带的邮件。"
    if "mail featuring a sketch of the holding pokemon" in low:
        return "绘有携带者宝可梦\n图案的邮件。"
    if "gorgeous-print mail to be held by a pokemon" in low:
        return "供宝可梦携带的\n华丽图案邮件。"
    if "mail featuring the drawings of three pokemon" in low:
        return "绘有三只宝可梦\n图案的邮件。"

    if (
        "makes certain species of pokemon evolve" in low
        or "makes certain pokemon evolve" in low
        or "makes some pokemon evolve" in low
        or "evolves certain pokemon" in low
    ):
        return "能让特定宝可梦\n进化的道具。"
    if (
        "loved by a certain pokemon" in low
        or "treat loved by a certain pokemon" in low
        or "perfumes loved by a certain pokemon" in low
    ):
        return "特定宝可梦喜爱的\n进化道具。"
    if "shaped like an egg" in low and "pokemon evolve" in low:
        return "蛋形的宝可梦\n进化道具。"
    shapes = {
        "strawberry": "草莓", "berry": "树果", "heart": "爱心",
        "clover": "幸运草", "flower": "花朵", "star": "星星",
    }
    m = re.search(r"(strawberry|berry|heart|clover|flower|star)-shaped sweet loved by milcery", low)
    if m:
        return f"{shapes[m.group(1)]}形糖饰，\n小仙奶很喜欢。"
    if "flower nectar that changes the form of certain pokemon" in low:
        return "能改变特定宝可梦\n形态的花蜜。"

    m = re.search(r"changes genesect's techno blast to (\w+)-type", low)
    if m:
        return f"让盖诺赛克特的高科技光炮\n变为{TYPE_ZH[m.group(1)]}属性。"
    m = re.search(r"a disc with (\w+) type data\. it swaps silvally's type", low)
    if m:
        return f"装有{TYPE_ZH[m.group(1)]}属性数据，\n能改变银伴战兽的属性。"
    m = re.search(r"this stone enables (.+?) to mega evolve in battle", text, re.I)
    if m:
        mon = species.get(key(m.group(1)), m.group(1))
        return f"让{mon}在对战中\n进行超级进化。"
    m = re.search(r"upgrade (.+?)'s (.+?) into a z-move", text, re.I)
    if m:
        mon = species.get(key(m.group(1)), m.group(1))
        return f"将{mon}的专属招式\n变成Z招式。"

    if "helps repel wild pokemon" in low:
        return "携带后可减少\n野生宝可梦出现。"
    if "snaps pokemon out of move-binding effects" in low:
        return "解除宝可梦受到的\n绑紧类招式效果。"
    if "raises the def and sp. def of pokemon that can evolve" in low:
        return "提高可进化宝可梦的\n防御和特防。"
    if "halves a pokemon's weight" in low:
        return "携带后宝可梦的\n体重减半。"
    m = re.search(
        r"makes a pokemon friendly but lowers base (hp|attack|defense|sp\. atk|sp\. def|speed)",
        low,
    )
    if m:
        return f"提高亲密度，但会降低\n{STAT_ZH[m.group(1)]}基础点数。"
    if "allows a pokemon in a pinch to move first just once" in low:
        return "危急时可优先\n行动一次。"
    if "attack power varies among different pokemon" in low:
        return "威力会因宝可梦\n不同而变化。"
    if "raise the chance of shiny pokemon" in low:
        return "提高遇到异色\n宝可梦的概率。"
    if "returns a pokemon back to its original form" in low:
        return "让宝可梦恢复\n原本的形态。"
    if "splicer that fuses kyurem and a certain pokemon" in low:
        return "用来合体或分离酋雷姆\n与特定宝可梦。"
    if "bottle used to seal a certain pokemon" in low:
        return "很久以前用于封印\n某只宝可梦的瓶子。"
    if "fuse and split necrozma using a solgaleo" in low:
        return "用于合体或分离奈克洛兹玛\n与索尔迦雷欧。"
    if "fuse and split necrozma using a lunala" in low:
        return "用于合体或分离奈克洛兹玛\n与露奈雅拉。"
    if "holding their mega stone to mega evolve" in low:
        return "让携带进化石的宝可梦\n进行超级进化。"
    if "device grants access to the {53}{54} storage system" in low:
        return "用于连接宝可梦\n寄放系统的装置。"

    if "water to fish for wild pokemon" in low:
        return "在水边钓野生\n宝可梦的钓竿。"
    if "decent fishing rod for catching wild pokemon" in low:
        return "能钓到野生宝可梦的\n不错钓竿。"
    if "best fishing rod for catching wild pokemon" in low:
        return "能钓到野生宝可梦的\n顶级钓竿。"
    if "search out pokemon hiding in grass" in low:
        return "搜索藏在草丛中的\n宝可梦。"
    if "sweet-sounding flute that awakens pokemon" in low:
        return "能唤醒宝可梦的\n悦耳笛子。"
    if "signals any unseeable pokemon" in low:
        return "能探测隐形宝可梦的\n得文装置。"
    if "required for entering pokemon contests" in low:
        return "参加宝可梦华丽大赛\n所需的通行证。"
    if "parcel for prof. oak from a pokemon mart's clerk" in low:
        return "商店店员托付给\n大木博士的包裹。"
    if "cinnabar island gym's entrance" in low:
        return "红莲岛道馆入口的\n钥匙。"
    if "silph co's scope makes unseeable pokemon visible" in low:
        return "让看不见的宝可梦\n显形的西尔佛装置。"
    if "ups pokemon with certain abilities" in low:
        return "提高拥有特定特性的\n宝可梦能力。"

    m = re.search(r"these shards make a pokemon acquire (\w+) tera type", low)
    if m:
        return f"使宝可梦获得\n{TYPE_ZH[m.group(1)]}太晶属性。"
    if "remove a pokemon's tera type" in low:
        return "移除宝可梦的\n太晶属性。"
    if "resets all base points of a pokemon" in low:
        return "清空宝可梦的\n所有基础点数。"
    if "wooden toy carved in the image of a pokemon" in low:
        return "宝可梦造型的木雕。\n可以出售。"
    if "changes the gender of a pkm" in low:
        return "改变宝可梦性别的\n奇怪药丸。"
    if "raises the level of a pokemon to the max allowed" in low:
        return "把宝可梦等级提升到\n当前允许的上限。"
    return None


def load_name_csv(path: Path) -> dict[str, str]:
    by_id: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            by_id.setdefault(row["item_id"], {})[row["local_language_id"]] = row["name"]
    return {
        key(langs["9"]): font_text(langs["12"])
        for langs in by_id.values() if langs.get("9") and langs.get("12")
    }


def load_flavor_csv(path: Path) -> dict[str, str]:
    by_id: dict[str, dict[str, list[str]]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            by_id.setdefault(row["item_id"], {}).setdefault(row["language_id"], []).append(
                row["flavor_text"]
            )
    result: dict[str, str] = {}
    for langs in by_id.values():
        if not langs.get("12"):
            continue
        zh = font_text(langs["12"][-1]).replace("\n", "")
        for en in langs.get("9", []):
            result.setdefault(key(en), zh)
    return result


def scan_names(golden: bytes) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    off = NAME_START
    while off < NAME_END:
        eos = golden.find(b"\xff", off, NAME_END)
        if eos < 0:
            break
        if 1 <= eos - off <= 48:
            en = decode_bytes(golden[off:eos + 1]).strip()
            if (
                en
                and "\n" not in en
                and sum(ch.isalpha() for ch in en) >= 2
                and all(ch.isascii() or ch == "é" for ch in en)
            ):
                rows.append((off, eos + 1, en))
        off = eos + 1
    if len(rows) != 827:
        raise RuntimeError(f"expected 827 item names, found {len(rows)}")
    return rows


def scan_descriptions(golden: bytes) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    off = DESC_START
    while off < DESC_END:
        eos = golden.find(b"\xff", off, DESC_END)
        if eos < 0:
            break
        if 12 <= eos - off <= 160:
            en = decode_bytes(golden[off:eos + 1]).strip()
            if sum(ch.isalpha() for ch in en) >= 12 and en.count("{") <= 4:
                rows.append((off, eos + 1, en))
        off = eos + 1
    if len(rows) != 800:
        raise RuntimeError(f"expected 800 unique item descriptions, found {len(rows)}")
    return rows


def validate_fit(zh: str, capacity: int, label: str) -> None:
    encoded, missing = encode_text_safe(zh)
    if missing:
        points = ", ".join(f"U+{ord(ch):04X}" for ch in missing)
        raise ValueError(f"{label}: missing glyphs {points} in {zh!r}")
    if len(encoded) > capacity:
        raise ValueError(f"{label}: need {len(encoded)} bytes, capacity={capacity}: {zh!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pokeapi-dir", type=Path, required=True)
    args = parser.parse_args()
    names_csv = args.pokeapi_dir / "item_names.csv"
    flavor_csv = args.pokeapi_dir / "item_flavor_text.csv"
    if not names_csv.exists() or not flavor_csv.exists():
        parser.error("--pokeapi-dir must contain item_names.csv and item_flavor_text.csv")

    golden = GOLDEN.read_bytes()
    current = CURRENT.read_bytes() if CURRENT.exists() else None
    previous_descriptions: dict[tuple[int, str], dict[str, object]] = {}
    if DESC_OUT.exists():
        payload = json.loads(DESC_OUT.read_text(encoding="utf-8"))
        for row in payload.get("items", []):
            previous_descriptions[(int(row["offset"]), str(row["en"]))] = row
    if current is None and not previous_descriptions:
        raise FileNotFoundError(
            "need the committed item description glossary or out/quetzal_084_cn.gba"
        )
    _, decode_table = load_charmap()
    official_names = load_name_csv(names_csv)
    official_flavors = load_flavor_csv(flavor_csv)
    species = {
        key(row["name_en"]): row["name_zh"]
        for row in json.loads(
            (ROOT / "glossary" / "simple_pokedex.json").read_text(encoding="utf-8")
        )
        if row.get("name_en") and row.get("name_zh")
    }

    name_rows: list[dict[str, object]] = []
    name_sources: dict[str, int] = {}
    for off, end, en in scan_names(golden):
        source = "pokeapi"
        if en in CUSTOM_ITEM_NAMES:
            zh = CUSTOM_ITEM_NAMES[en]
            source = "quetzal"
        else:
            zh = official_names.get(key(en))
            if zh is None:
                raise KeyError(f"unmapped item name at {off:08X}: {en!r}")
        if re.fullmatch(r"TM\d+", en):
            zh, source = "招式" + en[2:], "rom-abbreviation"
        elif re.fullmatch(r"HM\d+", en):
            zh, source = "秘传" + en[2:], "rom-abbreviation"
        zh = font_text(zh)
        encoded, _ = encode_text_safe(zh)
        if len(encoded) > end - off and "进化石" in zh:
            zh, source = zh.replace("进化石", "石"), "rom-abbreviation"
        validate_fit(zh, end - off, f"{off:08X} {en}")
        name_rows.append({"offset": off, "en": en, "zh": zh, "source": source})
        name_sources[source] = name_sources.get(source, 0) + 1

    desc_rows: list[dict[str, object]] = []
    desc_sources: dict[str, int] = {}
    for off, end, en in scan_descriptions(golden):
        previous = previous_descriptions.get((off, en))
        if previous is not None:
            zh = str(previous["zh"])
            source = str(previous.get("source") or "existing-reviewed")
        elif current is not None:
            zh = decode_chs(current[off:end], decode_table)
            source = "existing-reviewed"
        else:
            raise KeyError(f"missing description baseline at {off:08X}: {en!r}")
        if incomplete_zh(zh):
            zh = compact_description(en, species)
            source = "compact-manual"
            if zh is None:
                official = official_flavors.get(key(en))
                if official is not None:
                    try:
                        validate_fit(official, end - off, f"{off:08X} official")
                    except ValueError:
                        official = None
                zh, source = official, "pokeapi"
            if zh is None:
                raise KeyError(f"unmapped incomplete description at {off:08X}: {en!r}")
        zh = font_text(zh)
        validate_fit(zh, end - off, f"{off:08X} description")
        if incomplete_zh(zh):
            raise ValueError(f"{off:08X}: generated description still incomplete: {zh!r}")
        desc_rows.append({"offset": off, "en": en, "zh": zh, "source": source})
        desc_sources[source] = desc_sources.get(source, 0) + 1

    provenance = {
        "rom": "Pokemon Quetzal 0.8.4 English",
        "name_range": [NAME_START, NAME_END],
        "description_range": [DESC_START, DESC_END],
        "pokeapi": "https://github.com/PokeAPI/pokeapi/tree/master/data/v2/csv",
    }
    NAME_OUT.write_text(
        json.dumps({"provenance": provenance, "items": name_rows}, ensure_ascii=False, indent=2)
        + "\n", encoding="utf-8",
    )
    DESC_OUT.write_text(
        json.dumps({"provenance": provenance, "items": desc_rows}, ensure_ascii=False, indent=2)
        + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "names": len(name_rows), "name_sources": name_sources,
        "descriptions": len(desc_rows), "description_sources": desc_sources,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
