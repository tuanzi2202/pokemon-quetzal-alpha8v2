#!/usr/bin/env python3
"""Canonical Simplified Chinese terminology shared by dialogue tooling."""

from __future__ import annotations

import re

from official_names_zh import OFFICIAL_NAMES
from force_trainer_class_zh import CLASS_ZH


# Longer phrases win.  These are source-language entities that must not be left
# to a generic translator because their official Chinese names are not literal.
EN_TERMS: dict[str, str] = {
    # Hoenn cities and towns
    "LITTLEROOT TOWN": "未白镇",
    "OLDALE TOWN": "古玫镇",
    "DEWFORD TOWN": "武斗镇",
    "LAVARIDGE TOWN": "釜炎镇",
    "FALLARBOR TOWN": "秋叶镇",
    "VERDANTURF TOWN": "绿茵镇",
    "PACIFIDLOG TOWN": "暮水镇",
    "PETALBURG CITY": "橙华市",
    "SLATEPORT CITY": "凯那市",
    "MAUVILLE CITY": "紫堇市",
    "RUSTBORO CITY": "卡那兹市",
    "FORTREE CITY": "茵郁市",
    "LILYCOVE CITY": "水静市",
    "MOSSDEEP CITY": "绿岭市",
    "SOOTOPOLIS CITY": "琉璃市",
    "EVER GRANDE CITY": "彩悠市",
    "LITTLEROOT": "未白镇",
    "OLDALE": "古玫镇",
    "DEWFORD": "武斗镇",
    "LAVARIDGE": "釜炎镇",
    "FALLARBOR": "秋叶镇",
    "VERDANTURF": "绿茵镇",
    "PACIFIDLOG": "暮水镇",
    "PETALBURG": "橙华市",
    "SLATEPORT": "凯那市",
    "MAUVILLE": "紫堇市",
    "RUSTBORO": "卡那兹市",
    "FORTREE": "茵郁市",
    "LILYCOVE": "水静市",
    "MOSSDEEP": "绿岭市",
    "SOOTOPOLIS": "琉璃市",
    "EVER GRANDE": "彩悠市",
    # Hoenn landmarks
    "PETALBURG WOODS": "橙华森林",
    "RUSTURF TUNNEL": "卡绿隧道",
    "GRANITE CAVE": "石之洞窟",
    "MT. CHIMNEY": "烟囱山",
    "FIERY PATH": "热焰小径",
    "JAGGED PASS": "凹凸山道",
    "METEOR FALLS": "流星瀑布",
    "MT. PYRE": "送神山",
    "SHOAL CAVE": "浅滩洞穴",
    "CAVE OF ORIGIN": "觉醒神殿",
    "SKY PILLAR": "天空之柱",
    "SEALED CHAMBER": "布告石室",
    "NEW MAUVILLE": "新紫堇",
    "ABANDONED SHIP": "弃船",
    "SOUTHERN ISLAND": "南方孤岛",
    "SAFARI ZONE": "狩猎地带",
    "BATTLE FRONTIER": "对战开拓区",
    "MIRAGE TOWER": "幻影之塔",
    "DESERT UNDERPASS": "沙漠地下道",
    "ARTISAN CAVE": "工匠之穴",
    "TRAINER HILL": "训练家之丘",
    "MARINE CAVE": "海之窟",
    "TERRA CAVE": "陆之窟",
    # Core game terminology
    "POKéMON TRAINERS": "宝可梦训练家",
    "POKéMON TRAINER": "宝可梦训练家",
    "POKEMON TRAINERS": "宝可梦训练家",
    "POKEMON TRAINER": "宝可梦训练家",
    "POKéMON LEAGUE": "宝可梦联盟",
    "POKEMON LEAGUE": "宝可梦联盟",
    "POKéMON CENTER": "宝可梦中心",
    "POKEMON CENTER": "宝可梦中心",
    "POKéMON MART": "友好商店",
    "POKEMON MART": "友好商店",
    "POKé BALLS": "精灵球",
    "POKé BALL": "精灵球",
    "POKE BALLS": "精灵球",
    "POKE BALL": "精灵球",
    "POKéDEX": "宝可梦图鉴",
    "POKEDEX": "宝可梦图鉴",
    "POKéNAV": "宝可领航",
    "POKENAV": "宝可领航",
    "POKéMON": "宝可梦",
    "POKEMON": "宝可梦",
    "TEAM MAGMA": "熔岩队",
    "TEAM AQUA": "海洋队",
    "MAGMA TEAM": "熔岩队",
    "AQUA TEAM": "海洋队",
    "GYM LEADERS": "道馆馆主",
    "GYM LEADER": "道馆馆主",
    "GYM BADGES": "道馆徽章",
    "GYM BADGE": "道馆徽章",
    "ELITE FOUR": "四天王",
    "BATTLE TOWER": "对战塔",
    "BATTLE DOME": "对战巨蛋",
    "BATTLE PALACE": "对战宫殿",
    "BATTLE ARENA": "对战竞技场",
    "BATTLE FACTORY": "对战工厂",
    "BATTLE PIKE": "对战水管",
    "BATTLE PYRAMID": "对战金字塔",
    "TRAINERS": "训练家",
    "TRAINER": "训练家",
    "BADGES": "徽章",
    "BADGE": "徽章",
    "GYM": "道馆",
    "DEVON CORPORATION": "得文公司",
    "DEVON CORP.": "得文公司",
    "DEVON": "得文公司",
    "SPACE CENTER": "宇宙中心",
    "POKéBLOCK": "宝可方块",
    "POKEBLOCK": "宝可方块",
    "BERRIES": "树果",
    "BERRY": "树果",
    "MOVE": "招式",
    "MOVES": "招式",
    "ABILITY": "特性",
    "ABILITIES": "特性",
    "ROUTE": "道路",
}

for _key, _value in OFFICIAL_NAMES.items():
    EN_TERMS.setdefault(_key, _value)
for _key, _value in CLASS_ZH.items():
    EN_TERMS.setdefault(_key, _value)

EN_TERMS_SORTED = sorted(EN_TERMS.items(), key=lambda pair: -len(pair[0]))

PERSON_NAMES: tuple[str, ...] = (
    "BRENDAN", "MAY", "BIRCH", "WALLY", "STEVEN", "WALLACE", "NORMAN",
    "ROXANNE", "BRAWLY", "WATTSON", "FLANNERY", "WINONA", "SIDNEY",
    "PHOEBE", "GLACIA", "DRAKE", "TATE", "LIZA", "MAXIE", "ARCHIE",
    "JUAN", "SCOTT", "COURTNEY", "SHELLY", "MATT", "TABITHA", "LUCY",
    "NOLAND", "GRETA", "TUCKER", "SPENSER", "BRANDON", "ANABEL",
    "GABBY", "TY", "STERN", "COZMO", "LANETTE", "ZINNIA", "BRINEY",
)

LOCATION_NAMES: tuple[str, ...] = (
    "PETALBURG WOODS", "RUSTURF TUNNEL", "GRANITE CAVE", "MT. CHIMNEY",
    "FIERY PATH", "JAGGED PASS", "METEOR FALLS", "MT. PYRE", "SHOAL CAVE",
    "CAVE OF ORIGIN", "SKY PILLAR", "SEALED CHAMBER", "NEW MAUVILLE",
    "ABANDONED SHIP", "SOUTHERN ISLAND", "SAFARI ZONE", "BATTLE FRONTIER",
    "MIRAGE TOWER", "DESERT UNDERPASS", "ARTISAN CAVE", "TRAINER HILL",
    "MARINE CAVE", "TERRA CAVE", "LITTLEROOT", "OLDALE", "DEWFORD",
    "LAVARIDGE", "FALLARBOR", "VERDANTURF", "PACIFIDLOG", "PETALBURG",
    "SLATEPORT", "MAUVILLE", "RUSTBORO", "FORTREE", "LILYCOVE",
    "MOSSDEEP", "SOOTOPOLIS", "EVER GRANDE",
)

# These replacements are activated only when the corresponding uppercase name
# occurs in the English source row, avoiding collisions with ordinary Chinese.
SOURCE_ENTITY_ALIASES: dict[str, tuple[str, ...]] = {
    "BRENDAN": ("布伦丹", "布兰登", "丹：", "丹:"),
    "MAY": ("阿美", "梅：", "梅:", "五月：", "五月:"),
    "BIRCH": ("伯奇",),
    "WALLY": ("沃利",),
    "STEVEN": ("史蒂文",),
    "WALLACE": ("华莱士",),
    "NORMAN": ("诺曼",),
    "ROXANNE": ("罗克珊", "萝珊"),
    "BRAWLY": ("布拉利", "布劳利"),
    "WATTSON": ("华生", "沃森"),
    "FLANNERY": ("弗兰纳里",),
    "WINONA": ("薇诺娜", "威诺娜"),
    "SIDNEY": ("西德尼",),
    "PHOEBE": ("菲比",),
    "GLACIA": ("葛拉西亚", "格拉西亚"),
    "DRAKE": ("德雷克",),
    "TATE": ("泰特",),
    "LIZA": ("莉莎", "丽莎"),
    "MAXIE": ("马克西",),
    "ARCHIE": ("阿奇", "阿尔奇"),
    "JUAN": ("胡安",),
    "SCOTT": ("斯科特", "史考特"),
    "COURTNEY": ("考特妮",),
    "SHELLY": ("谢莉",),
    "LUCY": ("露西",),
    "NOLAND": ("诺兰",),
    "GRETA": ("格里塔",),
    "TUCKER": ("塔克", "希尔斯"),
    "SPENSER": ("斯宾塞", "宇康"),
    "BRANDON": ("布兰登",),
    "ANABEL": ("安娜贝尔",),
    "GABBY": ("加比", "加贝"),
    "TY": ("泰伊",),
    "STERN": ("斯特恩",),
    "COZMO": ("科兹莫",),
    "LANETTE": ("拉内特",),
    "ZINNIA": ("日日美",),
    "BRINEY": ("布里尼", "布莱尼"),
}

SOURCE_LOCATION_ALIASES: dict[str, tuple[str, ...]] = {
    "LITTLEROOT": ("小根镇", "小根"),
    "OLDALE": ("古辰镇",),
    "DEWFORD": ("露珠镇", "杜弗德", "杜福德"),
    "LAVARIDGE": ("拉瓦里奇镇", "拉瓦里奇"),
    "FALLARBOR": ("坠落地点",),
    "VERDANTURF": ("绿原镇", "绿荫镇"),
    "PACIFIDLOG": ("太平洋",),
    "PETALBURG": ("佩塔尔堡", "彼得堡"),
    "SLATEPORT": ("斯拉特波特城", "斯拉特波特", "斯莱特港", "石港"),
    "MAUVILLE": ("摩尔维尔", "玛维尔", "莫维尔"),
    "RUSTBORO": ("卡绿镇", "锈市", "铁锈市", "拉斯伯勒市", "拉斯伯勒", "锈路堡"),
    "FORTREE": ("福特里",),
    "LILYCOVE": ("琉璃市市", "琉璃市", "莉莉科夫", "莉莉柯夫", "莉莉考夫", "莉莉宝船", "百合湾"),
    "MOSSDEEP": ("苔藓深城", "苔藓深", "莫斯蒂普", "莫斯迪普"),
    "SOOTOPOLIS": ("烟雾之城", "琉棋市", "苏托波里斯市", "苏托波利斯", "魂岩市"),
    "EVER GRANDE": ("曾经的大城市", "永远的大城市"),
    "RUSTURF TUNNEL": ("锈草隧道", "铁锈草隧道", "鲁斯特夫隧道"),
    "GRANITE CAVE": ("花岗岩洞穴", "石之洞窟洞穴"),
    "MT. CHIMNEY": ("烟囱山上", "烟囱"),
    "JAGGED PASS": ("锯齿通道", "参差小径"),
    "MT. PYRE": ("皮尔山", "皮尔先生", "太火葬用的"),
    "SHOAL CAVE": ("浅滩洞",),
    "SKY PILLAR": ("天空支柱", "天空柱子", "天柱"),
    "ABANDONED SHIP": ("被遗弃的船", "废弃船"),
    "SAFARI ZONE": ("野生动物园", "狩猎区"),
    "BATTLE FRONTIER": ("战斗前沿", "战斗前线", "战斗边界", "前线战役", "战线"),
    "MIRAGE TOWER": ("幻影塔", "海市蜃楼"),
    "TRAINER HILL": ("训练家山", "教练山"),
    "CAVE OF ORIGIN": ("起源的洞穴", "觉醒之祠", "觉醒祠堂"),
    "SEALED CHAMBER": ("封印之室",),
}


def source_mentions(source: str, key: str) -> bool:
    return re.search(rf"(?<![A-Z]){re.escape(key)}(?![A-Z])", source) is not None


def canonicalize_source_entities(source: str, text: str) -> str:
    value = text
    for key in PERSON_NAMES:
        if not source_mentions(source, key):
            continue
        expected = OFFICIAL_NAMES[key]
        if expected in value:
            continue
        for alias in SOURCE_ENTITY_ALIASES.get(key, ()):
            value = value.replace(alias, expected)
    for key in LOCATION_NAMES:
        if not source_mentions(source, key):
            continue
        expected = EN_TERMS[key]
        if expected in value:
            continue
        for alias in SOURCE_LOCATION_ALIASES.get(key, ()):
            value = value.replace(alias, expected)
    return value


def mentioned_locations(source: str) -> list[str]:
    found = [key for key in LOCATION_NAMES if source_mentions(source, key)]
    return [
        key for key in found
        if not any(key != other and key in other for other in found)
    ]


def location_present(key: str, text: str) -> bool:
    expected = EN_TERMS[key]
    if expected in text:
        return True
    if expected.endswith(("市", "镇")) and expected[:-1] in text:
        return True
    return False


# Known legacy/fan/machine translations found in the current locale.  Avoid
# overly broad replacements such as a bare single-character personal name.
BAD_ZH_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("水舰队团队", "海洋队"),
    ("水族战队", "海洋队"),
    ("水族队", "海洋队"),
    ("水舰队", "海洋队"),
    ("岩浆战队", "熔岩队"),
    ("岩浆团队", "熔岩队"),
    ("岩浆队", "熔岩队"),
    ("团队水", "海洋队"),
    ("团队岩浆", "熔岩队"),
    ("口袋妖怪", "宝可梦"),
    ("宠物小精灵", "宝可梦"),
    ("神奇宝贝", "宝可梦"),
    ("波卡姆", "宝可梦"),
    ("波克蒙", "宝可梦"),
    ("宝贝球", "精灵球"),
    ("刺球", "精灵球"),
    ("口袋球", "精灵球"),
    ("健身徽章", "道馆徽章"),
    ("健身房徽章", "道馆徽章"),
    ("健身房领导", "道馆馆主"),
    ("健身房领袖", "道馆馆主"),
    ("健身领袖", "道馆馆主"),
    ("体育馆馆主", "道馆馆主"),
    ("体育馆领导", "道馆馆主"),
    ("体育馆领袖", "道馆馆主"),
    ("体育主管", "道馆馆主"),
    ("健身房", "道馆"),
    ("体育馆", "道馆"),
    ("精英四人", "四天王"),
    ("精英四强", "四天王"),
    ("培训师", "训练家"),
    ("训练师", "训练家"),
    ("训练员", "训练家"),
    ("训练者", "训练家"),
    ("教练员", "训练家"),
    ("教练", "训练家"),
    ("运动鞋", "训练家"),
    ("浆果", "树果"),
    ("惠普", "HP"),
    ("日月光半导体", "得文公司"),
    ("德文郡", "得文公司"),
    ("德文公司", "得文公司"),
    ("马克西", "赤焰松"),
    ("阿奇", "水梧桐"),
    ("华莱士", "米可利"),
    ("诺曼", "千里"),
    ("弗兰纳里", "亚莎"),
    ("布伦丹", "小悠"),
    ("布兰登", "神代"),
    ("阿美", "小遥"),
    ("史蒂文", "大吾"),
    ("罗克珊", "杜娟"),
    ("布拉利", "藤树"),
    ("薇诺娜", "娜琪"),
    ("华生", "铁旋"),
    ("史考特", "亚希达"),
    ("斯科特", "亚希达"),
    ("胡安", "亚当"),
    ("露西", "小蓟"),
    ("希尔斯", "石南"),
    ("宇康", "郁金"),
    ("沙龙少女", "对战塔大君"),
    ("巨蛋高手", "巨蛋超级巨星"),
    ("宫殿大师", "宫殿守护者"),
    ("竞技大亨", "竞技场主将"),
    ("工厂首脑", "工厂头目"),
    ("水管女王", "水管皇后"),
    ("派克女王", "水管皇后"),
    ("金字塔之王", "金字塔法老"),
    ("伯奇教授", "小田卷博士"),
    ("伯奇博士", "小田卷博士"),
    ("布里尼先生", "哈奇老人"),
    ("布里尼", "哈奇老人"),
    ("皮柯", "小皮"),
    ("霍恩地区", "丰缘地区"),
    ("霍恩", "丰缘"),
    ("古辰镇", "古玫镇"),
    ("绿荫镇", "绿茵镇"),
    ("彩幽市", "彩悠市"),
    ("小根镇", "未白镇"),
    ("拉瓦里奇镇", "釜炎镇"),
    ("拉瓦里奇", "釜炎镇"),
    ("斯莱特波特", "凯那市"),
    ("斯莱特港市", "凯那市"),
    ("斯莱特港", "凯那市"),
    ("罗斯伯勒", "卡那兹市"),
    ("罗斯特伯勒", "卡那兹市"),
    ("锈色市", "卡那兹市"),
    ("莫斯迪普", "绿岭市"),
    ("莫维尔", "紫堇市"),
    ("福特里", "茵郁市"),
    ("利利科夫", "水静市"),
    ("利利柯夫", "水静市"),
    ("莉莉柯夫", "水静市"),
    ("佩塔尔堡", "橙华市"),
    ("彼得堡市", "橙华市"),
    ("彼得堡", "橙华市"),
    ("杜弗德", "武斗镇"),
    ("杜福德", "武斗镇"),
    ("天柱", "天空之柱"),
    ("起源的洞穴", "觉醒神殿"),
    ("觉醒祠堂", "觉醒神殿"),
    ("觉醒之祠", "觉醒神殿"),
    ("送神之山", "送神山"),
    ("封印之室", "布告石室"),
    ("变化洞窟", "变幻洞窟"),
    ("战斗前沿", "对战开拓区"),
    ("战斗穹顶", "对战巨蛋"),
    ("红色的宝物", "朱红色宝珠"),
    ("蓝球", "靛蓝色宝珠"),
    ("格鲁东", "固拉多"),
    ("古鲁顿", "固拉多"),
    ("pok<s:1>", "宝可梦"),
    ("Pok<s:1>", "宝可梦"),
)


def canonicalize_zh(text: str) -> str:
    """Normalize terminology, obvious translator debris, and unsupported glyphs."""
    value = text or ""
    for old, new in BAD_ZH_REPLACEMENTS:
        value = value.replace(old, new)

    value = re.sub(r"(?<!朱)红色宝珠", "朱红色宝珠", value)
    value = re.sub(r"(?<!靛)蓝色宝珠", "靛蓝色宝珠", value)

    value = re.sub(r"(\d+)号公路", r"\1号道路", value)
    value = re.sub(r"\b(?:POK[eé]MON|POK<s:1>)\b", "宝可梦", value, flags=re.I)
    value = re.sub(r"\[\s*(?:译文|参考译文|中文译文)\s*\]", "", value)
    value = re.sub(r"\[(?:[0-9A-Fa-f]{1,2}|qh|au:?)\]", "", value, flags=re.I)
    value = value.replace("{_}", "").replace("[()]", "")

    # The bundled font does not contain these variants.
    value = value.translate(str.maketrans({
        "—": "--",
        "–": "-",
        "’": "'",
        "．": ".",
        "【": "“",
        "】": "”",
        "《": "“",
        "》": "”",
        "瞭": "了",
    }))
    value = value.replace("[", "(").replace("]", ")")

    value = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", value)
    value = re.sub(r"\s+([，。！？；：、])", r"\1", value)
    value = re.sub(r"([（“])\s+", r"\1", value)
    value = re.sub(r"\s+([）”])", r"\1", value)
    value = re.sub(r"\s*(\{(?:WAIT_SCROLL|WAIT_CLEAR|F[CD9]:[0-9A-Fa-f]{2}|[0-9A-Fa-f]{2})\})\s*", r"\1", value)
    return value.strip()
