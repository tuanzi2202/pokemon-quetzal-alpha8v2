#!/usr/bin/env python3
"""Fix user-reported: Mom/Birch, poksammon, T1 junk, species names; rebuild ROM."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chs_encode import encode_text_safe  # noqa: E402
from clean_locale_zh import scrub_all  # noqa: E402
from fill_and_apply_remaining import CACHE, GOLDEN, LOCALE, OUT, ROM, quality_ok  # noqa: E402
from fix_clock_and_mom_open import OPENING, inplace  # noqa: E402
from official_names_zh import OFFICIAL_NAMES  # noqa: E402

# Official Simplified Chinese species (Gen1–3 core + common Quetzal)
SPECIES: dict[str, str] = {
    "BULBASAUR": "妙蛙种子", "IVYSAUR": "妙蛙草", "VENUSAUR": "妙蛙花",
    "CHARMANDER": "小火龙", "CHARMELEON": "火恐龙", "CHARIZARD": "喷火龙",
    "SQUIRTLE": "杰尼龟", "WARTORTLE": "卡咪龟", "BLASTOISE": "水箭龟",
    "CATERPIE": "绿毛虫", "METAPOD": "铁甲蛹", "BUTTERFREE": "巴大蝶",
    "WEEDLE": "独角虫", "KAKUNA": "铁壳蛹", "BEEDRILL": "大针蜂",
    "PIDGEY": "波波", "PIDGEOTTO": "比比鸟", "PIDGEOT": "大比鸟",
    "RATTATA": "小拉达", "RATICATE": "拉达", "SPEAROW": "烈雀", "FEAROW": "大嘴雀",
    "EKANS": "阿柏蛇", "ARBOK": "阿柏怪", "PIKACHU": "皮卡丘", "RAICHU": "雷丘",
    "SANDSHREW": "穿山鼠", "SANDSLASH": "穿山王",
    "NIDORAN♀": "尼多兰", "NIDORINA": "尼多娜", "NIDOQUEEN": "尼多后",
    "NIDORAN♂": "尼多朗", "NIDORINO": "尼多力诺", "NIDOKING": "尼多王",
    "CLEFAIRY": "皮皮", "CLEFABLE": "皮可西", "VULPIX": "六尾", "NINETALES": "九尾",
    "JIGGLYPUFF": "胖丁", "WIGGLYTUFF": "胖可丁", "ZUBAT": "超音蝠", "GOLBAT": "大嘴蝠",
    "ODDISH": "走路草", "GLOOM": "臭臭花", "VILEPLUME": "霸王花",
    "PARAS": "派拉斯", "PARASECT": "派拉斯特", "VENONAT": "毛球", "VENOMOTH": "摩鲁蛾",
    "DIGLETT": "地鼠", "DUGTRIO": "三地鼠", "MEOWTH": "喵喵", "PERSIAN": "猫老大",
    "PSYDUCK": "可达鸭", "GOLDUCK": "哥达鸭", "MANKEY": "猴怪", "PRIMEAPE": "火暴猴",
    "GROWLITHE": "卡蒂狗", "ARCANINE": "风速狗", "POLIWAG": "蚊香蝌蚪",
    "POLIWHIRL": "蚊香君", "POLIWRATH": "蚊香泳士",
    "ABRA": "凯西", "KADABRA": "勇基拉", "ALAKAZAM": "胡地",
    "MACHOP": "腕力", "MACHOKE": "豪力", "MACHAMP": "怪力",
    "BELLSPROUT": "喇叭芽", "WEEPINBELL": "口呆花", "VICTREEBEL": "大食花",
    "TENTACOOL": "玛瑙水母", "TENTACRUEL": "毒刺水母",
    "GEODUDE": "小拳石", "GRAVELER": "隆隆石", "GOLEM": "隆隆岩",
    "PONYTA": "小火马", "RAPIDASH": "烈焰马", "SLOWPOKE": "呆呆兽", "SLOWBRO": "呆壳兽",
    "MAGNEMITE": "小磁怪", "MAGNETON": "三合一磁怪", "FARFETCHD": "大葱鸭",
    "DODUO": "嘟嘟", "DODRIO": "嘟嘟利", "SEEL": "小海狮", "DEWGONG": "白海狮",
    "GRIMER": "臭泥", "MUK": "臭臭泥", "SHELLDER": "大舌贝", "CLOYSTER": "刺甲贝",
    "GASTLY": "鬼斯", "HAUNTER": "鬼斯通", "GENGAR": "耿鬼", "ONIX": "大岩蛇",
    "DROWZEE": "催眠貘", "HYPNO": "引梦貘人", "KRABBY": "大钳蟹", "KINGLER": "巨钳蟹",
    "VOLTORB": "霹雳电球", "ELECTRODE": "顽皮雷弹", "EXEGGCUTE": "蛋蛋", "EXEGGUTOR": "椰蛋树",
    "CUBONE": "卡拉卡拉", "MAROWAK": "嘎啦嘎啦", "HITMONLEE": "飞腿郎", "HITMONCHAN": "快拳郎",
    "LICKITUNG": "大舌头", "KOFFING": "瓦斯弹", "WEEZING": "双弹瓦斯",
    "RHYHORN": "独角犀牛", "RHYDON": "钻角犀兽", "CHANSEY": "吉利蛋", "TANGELA": "蔓藤怪",
    "KANGASKHAN": "袋兽", "HORSEA": "墨海马", "SEADRA": "海刺龙",
    "GOLDEEN": "角金鱼", "SEAKING": "金鱼王", "STARYU": "海星星", "STARMIE": "宝石海星",
    "MR. MIME": "魔墙人偶", "SCYTHER": "飞天螳螂", "JYNX": "迷唇姐", "ELECTABUZZ": "电击兽",
    "MAGMAR": "鸭嘴火兽", "PINSIR": "凯罗斯", "TAUROS": "肯泰罗",
    "MAGIKARP": "鲤鱼王", "GYARADOS": "暴鲤龙", "LAPRAS": "拉普拉斯", "DITTO": "百变怪",
    "EEVEE": "伊布", "VAPOREON": "水伊布", "JOLTEON": "雷伊布", "FLAREON": "火伊布",
    "PORYGON": "多边兽", "OMANYTE": "菊石兽", "OMASTAR": "多刺菊石兽",
    "KABUTO": "化石盔", "KABUTOPS": "镰刀盔", "AERODACTYL": "化石翼龙", "SNORLAX": "卡比兽",
    "ARTICUNO": "急冻鸟", "ZAPDOS": "闪电鸟", "MOLTRES": "火焰鸟",
    "DRATINI": "迷你龙", "DRAGONAIR": "哈克龙", "DRAGONITE": "快龙",
    "MEWTWO": "超梦", "MEW": "梦幻",
    # Johto
    "CHIKORITA": "菊草叶", "BAYLEEF": "月桂叶", "MEGANIUM": "大竺葵",
    "CYNDAQUIL": "火球鼠", "QUILAVA": "火岩鼠", "TYPHLOSION": "火暴兽",
    "TOTODILE": "小锯鳄", "CROCONAW": "蓝鳄", "FERALIGATR": "大力鳄",
    "SENTRET": "尾立", "FURRET": "大尾立", "HOOTHOOT": "咕咕", "NOCTOWL": "猫头夜鹰",
    "LEDYBA": "芭瓢虫", "LEDIAN": "安瓢虫", "SPINARAK": "圆丝蛛", "ARIADOS": "阿利多斯",
    "CROBAT": "叉字蝠", "CHINCHOU": "灯笼鱼", "LANTURN": "电灯怪",
    "PICHU": "皮丘", "CLEFFA": "皮宝宝", "IGGLYBUFF": "宝宝丁", "TOGEPI": "波克比",
    "TOGETIC": "波克基古", "NATU": "天然雀", "XATU": "天然鸟",
    "MAREEP": "咩利羊", "FLAAFFY": "茸茸羊", "AMPHAROS": "电龙",
    "BELLOSSOM": "美丽花", "MARILL": "玛力露", "AZUMARILL": "玛力露丽",
    "SUDOWOODO": "树才怪", "POLITOED": "蚊香蛙皇", "HOPPIP": "毽子草",
    "SKIPLOOM": "毽子花", "JUMPLUFF": "毽子棉", "AIPOM": "长尾怪手",
    "SUNKERN": "向日种子", "SUNFLORA": "向日花怪", "YANMA": "阳阳玛",
    "WOOPER": "乌波", "QUAGSIRE": "沼王", "ESPEON": "太阳伊布", "UMBREON": "月亮伊布",
    "MURKROW": "黑暗鸦", "SLOWKING": "呆呆王", "MISDREAVUS": "梦妖", "UNOWN": "未知图腾",
    "WOBBUFFET": "果然翁", "GIRAFARIG": "麒麟奇", "PINECO": "榛果球", "FORRETRESS": "佛烈托斯",
    "DUNSPARCE": "土龙弟弟", "GLIGAR": "天蝎", "STEELIX": "大钢蛇",
    "SNUBBULL": "布鲁", "GRANBULL": "布鲁皇", "QWILFISH": "千针鱼", "SCIZOR": "巨钳螳螂",
    "SHUCKLE": "壶壶", "HERACROSS": "赫拉克罗斯", "SNEASEL": "狃拉",
    "TEDDIURSA": "熊宝宝", "URSARING": "圈圈熊", "SLUGMA": "熔岩虫", "MAGCARGO": "熔岩蜗牛",
    "SWINUB": "小山猪", "PILOSWINE": "长毛猪", "CORSOLA": "太阳珊瑚",
    "REMORAID": "铁炮鱼", "OCTILLERY": "章鱼桶", "DELIBIRD": "信使鸟", "MANTINE": "巨翅飞鱼",
    "SKARMORY": "盔甲鸟", "HOUNDOUR": "戴鲁比", "HOUNDOOM": "黑鲁加", "KINGDRA": "刺龙王",
    "PHANPY": "小小象", "DONPHAN": "顿甲", "PORYGON2": "多边兽Ⅱ", "STANTLER": "惊角鹿",
    "SMEARGLE": "图图犬", "TYROGUE": "无畏小子", "HITMONTOP": "战舞郎",
    "SMOOCHUM": "迷唇娃", "ELEKID": "电击怪", "MAGBY": "鸭嘴宝宝", "MILTANK": "大奶罐",
    "BLISSEY": "幸福蛋", "RAIKOU": "雷公", "ENTEI": "炎帝", "SUICUNE": "水君",
    "LARVITAR": "幼基拉斯", "PUPITAR": "沙基拉斯", "TYRANITAR": "班基拉斯",
    "LUGIA": "洛奇亚", "HO-OH": "凤王", "CELEBI": "时拉比",
    # Hoenn
    "TREECKO": "木守宫", "GROVYLE": "森林蜥蜴", "SCEPTILE": "蜥蜴王",
    "TORCHIC": "火稚鸡", "COMBUSKEN": "力壮鸡", "BLAZIKEN": "火焰鸡",
    "MUDKIP": "水跃鱼", "MARSHTOMP": "沼跃鱼", "SWAMPERT": "巨沼怪",
    "POOCHYENA": "土狼犬", "MIGHTYENA": "大狼犬", "ZIGZAGOON": "蛇纹熊", "LINOONE": "直冲熊",
    "WURMPLE": "刺尾虫", "SILCOON": "甲壳茧", "BEAUTIFLY": "狩猎凤蝶",
    "CASCOON": "盾甲茧", "DUSTOX": "毒粉蛾", "LOTAD": "莲叶童子", "LOMBRE": "莲帽小童",
    "LUDICOLO": "乐天河童", "SEEDOT": "橡实果", "NUZLEAF": "长鼻叶", "SHIFTRY": "狡猾天狗",
    "TAILLOW": "傲骨燕", "SWELLOW": "大王燕", "WINGULL": "长翅鸥", "PELIPPER": "大嘴鸥",
    "RALTS": "拉鲁拉丝", "KIRLIA": "奇鲁莉安", "GARDEVOIR": "沙奈朵",
    "SURSKIT": "溜溜糖球", "MASQUERAIN": "雨翅蛾", "SHROOMISH": "蘑蘑菇", "BRELOOM": "斗笠菇",
    "SLAKOTH": "懒人獭", "VIGOROTH": "过动猿", "SLAKING": "请假王",
    "NINCADA": "土居忍士", "NINJASK": "铁面忍者", "SHEDINJA": "脱壳忍者",
    "WHISMUR": "咕妞妞", "LOUDRED": "吼爆弹", "EXPLOUD": "爆音怪",
    "MAKUHITA": "幕下力士", "HARIYAMA": "铁掌力士", "AZURILL": "露力丽",
    "NOSEPASS": "朝北鼻", "SKITTY": "向尾喵", "DELCATTY": "优雅猫",
    "SABLEYE": "勾魂眼", "MAWILE": "大嘴娃", "ARON": "可可多拉", "LAIRON": "可多拉",
    "AGGRON": "波士可多拉", "MEDITITE": "玛沙那", "MEDICHAM": "恰雷姆",
    "ELECTRIKE": "落雷兽", "MANECTRIC": "雷电兽", "PLUSLE": "正电拍拍", "MINUN": "负电拍拍",
    "VOLBEAT": "电萤虫", "ILLUMISE": "甜甜萤", "ROSELIA": "毒蔷薇",
    "GULPIN": "溶食兽", "SWALOT": "吞食兽", "CARVANHA": "利牙鱼", "SHARPEDO": "巨牙鲨",
    "WAILMER": "吼吼鲸", "WAILORD": "吼鲸王", "NUMEL": "呆火驼", "CAMERUPT": "喷火驼",
    "TORKOAL": "煤炭龟", "SPOINK": "跳跳猪", "GRUMPIG": "噗噗猪", "SPINDA": "晃晃斑",
    "TRAPINCH": "大颚蚁", "VIBRAVA": "超音波幼虫", "FLYGON": "沙漠蜻蜓",
    "CACNEA": "刺球仙人掌", "CACTURNE": "梦歌仙人掌", "SWABLU": "青绵鸟", "ALTARIA": "七夕青鸟",
    "ZANGOOSE": "猫鼬斩", "SEVIPER": "饭匙蛇", "LUNATONE": "月石", "SOLROCK": "太阳岩",
    "BARBOACH": "泥泥鳅", "WHISCASH": "鲶鱼王", "CORPHISH": "龙虾小兵", "CRAWDAUNT": "铁螯龙虾",
    "BALTOY": "天秤偶", "CLAYDOL": "念力土偶", "LILEEP": "触手百合", "CRADILY": "摇篮百合",
    "ANORITH": "太古羽虫", "ARMALDO": "太古盔甲", "FEEBAS": "丑丑鱼", "MILOTIC": "美纳斯",
    "CASTFORM": "飘浮泡泡", "KECLEON": "变隐龙", "SHUPPET": "怨影娃娃", "BANETTE": "诅咒娃娃",
    "DUSKULL": "夜巡灵", "DUSCLOPS": "彷徨夜灵", "TROPIUS": "热带龙", "CHIMECHO": "风铃铃",
    "ABSOL": "阿勃梭鲁", "WYNAUT": "小果然", "SNORUNT": "雪童子", "GLALIE": "冰鬼护",
    "SPHEAL": "海豹球", "SEALEO": "海魔狮", "WALREIN": "帝牙海狮",
    "CLAMPERL": "珍珠贝", "HUNTAIL": "猎斑鱼", "GOREBYSS": "樱花鱼", "RELICANTH": "古空棘鱼",
    "LUVDISC": "爱心鱼", "BAGON": "宝贝龙", "SHELGON": "甲壳龙", "SALAMENCE": "暴飞龙",
    "BELDUM": "铁哑铃", "METANG": "金属怪", "METAGROSS": "巨金怪",
    "REGIROCK": "雷吉洛克", "REGICE": "雷吉艾斯", "REGISTEEL": "雷吉斯奇鲁",
    "LATIAS": "拉帝亚斯", "LATIOS": "拉帝欧斯", "KYOGRE": "盖欧卡", "GROUDON": "固拉多",
    "RAYQUAZA": "烈空坐", "JIRACHI": "基拉祈", "DEOXYS": "代欧奇希斯",
}

DIALOGUE_FORCE: dict[int, str] = {
    0x279C1F: "救、救我！",
    0xFFB1E2: "小田卷博士：别丢下我啊！{WAIT_CLEAR}",
    0x3446518: "帮我做{WAIT_SCROLL}家务的宝可梦。",
}

JUNK_RE = [
    (r"\[\[\s*[Tt]\d+\s*\]\]", ""),
    (r"【\s*[Tt]\d+\s*】", ""),
    (r"\[\s*[Tt]\d+\s*\]", ""),
    (r"(?<![A-Za-z0-9{])T[0-9](?![0-9A-Za-z}])", ""),
    (r"(?i)poksamumo[n]?", "宝可梦"),
    (r"(?i)poksamumon", "宝可梦"),
    (r"(?i)poksamen", "宝可梦"),
    (r"(?i)poksammon", "宝可梦"),
    (r"(?i)poksamon", "宝可梦"),
    (r"(?i)poksamo", "宝可梦"),
    (r"(?i)poksamn", "宝可梦"),
    (r"(?i)ksammon", "宝可梦"),
    (r"(?i)pok[eé]?mon", "宝可梦"),
    (r"(^|[\n{ ])MON(?=[ :：，,!.。！？\n{]|$)", r"\1宝可梦"),
    (r"\?{3,}", "？"),
    (r"\.{4,}", "……"),
    (r"(?:…\s*){3,}", "……"),
]


def clean_zh(zh: str) -> str:
    out = zh or ""
    for pat, rep in JUNK_RE:
        out = re.sub(pat, rep, out)
    out = scrub_all(out)
    return out


def inplace_simple(data: bytearray, golden: bytes, off: int, zh: str) -> bool:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return False
    capacity = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if len(enc) > capacity:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > capacity:
            cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        if len(enc) > capacity:
            return False
    data[off : off + capacity] = enc + b"\x00" * (capacity - len(enc))
    return True


def main() -> int:
    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    n_sp = n_dlg = n_cl = 0
    for r in rows:
        off = int(r["offset"])
        en = (r.get("en") or "").strip()
        zh = r.get("zh") or ""

        if off in DIALOGUE_FORCE:
            r["zh"] = DIALOGUE_FORCE[off]
            n_dlg += 1
            continue

        # exact species / official name
        key = en.upper()
        if key in SPECIES:
            r["zh"] = SPECIES[key]
            cache[r.get("en") or en] = r["zh"]
            n_sp += 1
            continue
        if en in OFFICIAL_NAMES:
            r["zh"] = OFFICIAL_NAMES[en]
            n_sp += 1
            continue
        # "TREECKO DOLL" etc
        for sp, cn in SPECIES.items():
            if en.upper().startswith(sp + " ") or en.upper() == sp:
                r["zh"] = re.sub(re.escape(sp), cn, en, flags=re.I)
                # if leftover latin doll/coins translate lightly
                r["zh"] = re.sub(r"(?i)DOLL", "玩偶", r["zh"])
                r["zh"] = re.sub(r"(?i)COINS?", "硬币", r["zh"])
                n_sp += 1
                break
        else:
            zh2 = clean_zh(zh)
            if zh2 != zh:
                r["zh"] = zh2
                n_cl += 1
                # also replace species tokens inside dialogue
                for sp, cn in SPECIES.items():
                    if re.search(rf"(?<![A-Za-z]){re.escape(sp)}(?![A-Za-z])", r["zh"], re.I):
                        r["zh"] = re.sub(rf"(?<![A-Za-z]){re.escape(sp)}(?![A-Za-z])", cn, r["zh"], flags=re.I)
                        n_sp += 1

    LOCALE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"species/name={n_sp} dialogue_force={n_dlg} cleaned={n_cl}")

    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    # apply all good zh
    applied = 0
    for r in rows:
        off = int(r["offset"])
        # FC pool: allow inplace apply (abilities/types/UI)
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        if not zh:
            continue
        # allow short species names even if quality_ok strict fails
        ok = quality_ok(en, zh) or (
            any("\u4e00" <= c <= "\u9fff" for c in zh) and len(en.strip()) <= 16
        )
        if not ok:
            continue
        if inplace_simple(data, golden, off, zh):
            applied += 1

    # Mom opening Chinese
    for off, zh in OPENING.items():
        if off == 0x287A50:
            continue
        inplace(data, golden, off, zh)

    # forced dialogues
    for off, zh in DIALOGUE_FORCE.items():
        inplace_simple(data, golden, off, zh)

    # Restore ONLY clock day names / system prompts (never whole FC pool)
    from restore_clock_ui import CLOCK_OFFSETS, DAY, restore_body  # noqa: E402

    for off in sorted(CLOCK_OFFSETS):
        restore_body(data, golden, off)
    off = 0x0FC0000
    while off < 0x0FD0000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0x0FD0000 or eos - off > 40:
            off += 1
            continue
        from gen3_charmap import decode_bytes as _dec  # noqa: E402

        text = _dec(golden[off : eos + 1]).strip()
        if DAY.match(text):
            restore_body(data, golden, off)
        off = eos + 1
    for off in (0x287A50, 0x101BB9F, 0x1020486, 0x1020666, 0x10206EF):
        restore_body(data, golden, off)

    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print(f"applied={applied} wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
