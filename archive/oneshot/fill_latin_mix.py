#!/usr/bin/env python3
"""Translate leftover Latin mixed into Chinese ZH (glossary + sentence fixes)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_locale_zh import is_junk_en, scrub_all  # noqa: E402
from fill_and_apply_remaining import (  # noqa: E402
    CACHE,
    GOLDEN,
    LOCALE,
    OUT,
    ROM,
    quality_ok,
)
from chs_encode import encode_text_safe  # noqa: E402
from official_names_zh import OFFICIAL_NAMES  # noqa: E402

B = r"(?<![A-Za-z])"
E = r"(?![A-Za-z])"

# Longer keys first. Official CN names + common leftovers.
GLOSSARY: list[tuple[str, str]] = [
    # glued / MT garbage
    (r"(?i)stepthisway", "这边请"),
    (r"(?i)havethis", "给你这个"),
    (r"(?i)linedup", "排好队了"),
    (r"(?i)jumpout", "跳出来了"),
    (r"(?i)veheard", "听说"),
    (r"(?i)I'veheard", "我听说"),
    (r"(?i)poksamudex", "宝可梦图鉴"),
    (r"(?i)poksamonleague", "宝可梦联盟"),
    (r"(?i)poksamleague", "宝可梦联盟"),
    (r"(?i)monleague", "宝可梦联盟"),
    (r"(?i)poksamo", "宝可梦"),
    (r"(?i)poksammon", "宝可梦"),
    (r"(?i)poksamon", "宝可梦"),
    (r"(?i)monwireless", "宝可梦无线"),
    (r"(?i)rrroooooaaar!", "吼——！"),
    (r"(?i)Gyaah\s*!", "呀啊！"),
    (r"(?i)Achah\s*!", "啊哈！"),
    (r"(?i)Waaaaah", "哇啊啊"),
    (r"(?i)Waaah", "哇啊"),
    (r"(?i)ouchies", "好痛"),
    (r"(?i)Pihyoh", "皮哟"),
    (r"(?i)Hohoho", "呵呵呵"),
    (r"(?i)Hmhm", "嗯嗯"),
    (r"(?i)LvlUp", "升级"),
    (r"(?i)NeglectsHP", "忽视体力"),
    (r"(?i)SP\.\s*ATK", "特攻"),
    (r"(?i)SP\.\s*DEF", "特防"),
    (r"(?i)SPECIAL", "特殊"),
    (r"(?i)S\.S\.\s*TIDAL", "破浪号"),
    (r"(?i)GameCube", "GameCube"),
    (r"(?i)Game Boy Advance", "GBA"),
    # places
    (rf"(?i){B}LITTLEROOT TOWN{E}", "未白镇"),
    (rf"(?i){B}OLDALE TOWN{E}", "古辰镇"),
    (rf"(?i){B}PETALBURG CITY{E}", "橙华市"),
    (rf"(?i){B}RUSTBORO CITY{E}", "卡绿镇"),
    (rf"(?i){B}DEWFORD TOWN{E}", "武斗镇"),
    (rf"(?i){B}SLATEPORT CITY{E}", "凯那市"),
    (rf"(?i){B}MAUVILLE CITY{E}", "紫堇市"),
    (rf"(?i){B}VERDANTURF TOWN{E}", "绿荫镇"),
    (rf"(?i){B}FALLARBOR TOWN{E}", "秋叶镇"),
    (rf"(?i){B}LAVARIDGE TOWN{E}", "釜炎镇"),
    (rf"(?i){B}FORTREE CITY{E}", "茵郁市"),
    (rf"(?i){B}LILYCOVE CITY{E}", "琉璃市"),
    (rf"(?i){B}MOSSDEEP CITY{E}", "绿岭市"),
    (rf"(?i){B}SOOTOPOLIS CITY{E}", "琉棋市"),
    (rf"(?i){B}PACIFIDLOG TOWN{E}", "暮水镇"),
    (rf"(?i){B}EVER GRANDE CITY{E}", "彩幽市"),
    (rf"(?i){B}BATTLE FRONTIER{E}", "对战开拓区"),
    (rf"(?i){B}BATTLE TENT{E}", "对战帐篷"),
    (rf"(?i){B}BATTLE TOWER{E}", "对战塔"),
    (rf"(?i){B}BATTLE DOME{E}", "对战巨蛋"),
    (rf"(?i){B}BATTLE PIKE{E}", "对战管道"),
    (rf"(?i){B}BATTLE PYRAMID{E}", "对战金字塔"),
    (rf"(?i){B}BATTLE PALACE{E}", "对战宫殿"),
    (rf"(?i){B}BATTLE ARENA{E}", "对战竞技场"),
    (rf"(?i){B}BATTLE FACTORY{E}", "对战工厂"),
    (rf"(?i){B}MT\.?\s*PYRE{E}", "送神山"),
    (rf"(?i){B}MT\.?\s*CHIMNEY{E}", "烟囱山"),
    (rf"(?i){B}RUSTURF TUNNEL{E}", "卡绿隧道"),
    (rf"(?i){B}GRANITE CAVE{E}", "石之洞窟"),
    (rf"(?i){B}PETALBURG{E}", "橙华市"),
    (rf"(?i){B}RUSTBORO{E}", "卡绿镇"),
    (rf"(?i){B}DEWFORD{E}", "武斗镇"),
    (rf"(?i){B}SLATEPORT{E}", "凯那市"),
    (rf"(?i){B}MAUVILLE{E}", "紫堇市"),
    (rf"(?i){B}VERDANTURF{E}", "绿荫镇"),
    (rf"(?i){B}FALLARBOR{E}", "秋叶镇"),
    (rf"(?i){B}LAVARIDGE{E}", "釜炎镇"),
    (rf"(?i){B}FORTREE{E}", "茵郁市"),
    (rf"(?i){B}LILYCOVE{E}", "琉璃市"),
    (rf"(?i){B}MOSSDEEP{E}", "绿岭市"),
    (rf"(?i){B}SOOTOPOLIS{E}", "琉棋市"),
    (rf"(?i){B}PACIFIDLOG{E}", "暮水镇"),
    (rf"(?i){B}LITTLEROOT{E}", "未白镇"),
    (rf"(?i){B}OLDALE{E}", "古辰镇"),
    (rf"(?i){B}HOENN{E}", "丰缘"),
    (rf"(?i){B}SAFARI ZONE{E}", "狩猎地带"),
    (rf"(?i){B}SAFARI{E}", "狩猎地带"),
    (rf"(?i){B}DEVON{E}", "得文"),
    (rf"(?i){B}TRICK HOUSE{E}", "戏法屋"),
    (rf"(?i){B}TRICK MASTER{E}", "戏法大师"),
    (rf"(?i){B}CONTEST HALL{E}", "华丽大赛会场"),
    (rf"(?i){B}RECORD CORNER{E}", "纪录角"),
    (rf"(?i){B}FAN CLUB{E}", "粉丝俱乐部"),
    (rf"(?i){B}DAY CARE{E}", "培育屋"),
    (rf"(?i){B}POKéMON CENTER{E}", "宝可梦中心"),
    (rf"(?i){B}POKEMON CENTER{E}", "宝可梦中心"),
    (rf"(?i){B}POKéMON MART{E}", "友好商店"),
    (rf"(?i){B}MART{E}", "商店"),
    # people
    (rf"(?i){B}BRENDAN{E}", "小悠"),
    (rf"(?i){B}MAY{E}", "小遥"),
    (rf"(?i){B}WALLY{E}", "满充"),
    (rf"(?i){B}STEVEN{E}", "大吾"),
    (rf"(?i){B}WALLACE{E}", "米可利"),
    (rf"(?i){B}ROXANNE{E}", "杜鹃"),
    (rf"(?i){B}BRAWLY{E}", "藤树"),
    (rf"(?i){B}WATTSON{E}", "铁旋"),
    (rf"(?i){B}FLANNERY{E}", "亚莎"),
    (rf"(?i){B}WINONA{E}", "娜琪"),
    (rf"(?i){B}NORMAN{E}", "千里"),
    (rf"(?i){B}TATE{E}", "小枫"),
    (rf"(?i){B}LIZA{E}", "小南"),
    (rf"(?i){B}JUAN{E}", "亚当"),
    (rf"(?i){B}ARCHIE{E}", "水梧桐"),
    (rf"(?i){B}MAXIE{E}", "赤焰松"),
    (rf"(?i){B}BRINEY{E}", "哈奇"),
    (rf"(?i){B}PEEKO{E}", "小皮"),
    (rf"(?i){B}RYDEL{E}", "兹伏安"),
    (rf"(?i){B}LANETTE{E}", "真由美"),
    (rf"(?i){B}COZMO{E}", "科兹莫"),
    (rf"(?i){B}SCOTT{E}", "斯科特"),
    (rf"(?i){B}KIRA{E}", "奇拉"),
    # pokemon
    (rf"(?i){B}ZIGZAGOON{E}", "蛇纹熊"),
    (rf"(?i){B}LOTAD{E}", "莲叶童子"),
    (rf"(?i){B}SEEDOT{E}", "橡实果"),
    (rf"(?i){B}CYNDAQUIL{E}", "火球鼠"),
    (rf"(?i){B}TOTODILE{E}", "小锯鳄"),
    (rf"(?i){B}CHIKORITA{E}", "菊草叶"),
    (rf"(?i){B}KIRLIA{E}", "奇鲁莉安"),
    (rf"(?i){B}AZUMARILL{E}", "玛力露丽"),
    (rf"(?i){B}AZURILL{E}", "露力丽"),
    (rf"(?i){B}GULPIN{E}", "溶食兽"),
    (rf"(?i){B}DODRIO{E}", "嘟嘟利"),
    (rf"(?i){B}CORSOLA{E}", "太阳珊瑚"),
    (rf"(?i){B}WAILMER{E}", "吼吼鲸"),
    (rf"(?i){B}KYOGRE{E}", "盖欧卡"),
    (rf"(?i){B}GROUDON{E}", "固拉多"),
    (rf"(?i){B}RAYQUAZA{E}", "烈空坐"),
    (rf"(?i){B}SNORLAX{E}", "卡比兽"),
    # types / moves / items
    (rf"(?i){B}ROCK SMASH{E}", "碎岩"),
    (rf"(?i){B}ROCK{E}", "岩石"),
    (rf"(?i){B}WATER{E}", "水"),
    (rf"(?i){B}RAIN{E}", "下雨"),
    (rf"(?i){B}SURF{E}", "冲浪"),
    (rf"(?i){B}MACH BIKE{E}", "变速自行车"),
    (rf"(?i){B}ACRO BIKE{E}", "越野自行车"),
    (rf"(?i){B}BIKE{E}", "自行车"),
    (rf"(?i){B}GOGGLES{E}", "护目镜"),
    (rf"(?i){B}BERRY{E}", "树果"),
    (rf"(?i){B}BADGE{E}", "徽章"),
    (rf"(?i){B}HEAL{E}", "回复"),
    (rf"(?i){B}LINK{E}", "联机"),
    (rf"(?i){B}MULTI{E}", "多人"),
    (rf"(?i){B}BATTLE{E}", "对战"),
    (rf"(?i){B}TRAINERS?{E}", "训练家"),
    (rf"(?i){B}LEAGUE{E}", "联盟"),
    (rf"(?i){B}FRONTIER{E}", "开拓区"),
    (rf"(?i){B}PYRAMID{E}", "金字塔"),
    (rf"(?i){B}DOME{E}", "巨蛋"),
    (rf"(?i){B}PIKE{E}", "管道"),
    (rf"(?i){B}CORNER{E}", "角落"),
    (rf"(?i){B}CLUB{E}", "俱乐部"),
    (rf"(?i){B}MASTER{E}", "大师"),
    (rf"(?i){B}CONTEST{E}", "华丽大赛"),
    (rf"(?i){B}TRICK{E}", "戏法"),
    (rf"(?i){B}GAME{E}", "游戏"),
    (rf"(?i){B}MODE{E}", "模式"),
    (rf"(?i){B}Dynamax{E}", "极巨化"),
    (rf"(?i){B}Mechadoll{E}", "机械人偶"),
    (rf"(?i){B}Emphasizes{E}", "侧重"),
    (rf"(?i){B}Neglects{E}", "忽视"),
    (rf"(?i){B}COTTAGE{E}", "小屋"),
    (rf"(?i){B}TIDAL{E}", "破浪号"),
    (rf"(?i){B}PYRE{E}", "送神山"),
    (rf"(?i){B}SMASH{E}", "碎岩"),
    (rf"(?i){B}hold{E}", "携带"),
    (rf"(?i){B}type{E}", "属性"),
    (rf"(?i){B}with{E}", "和"),
    (rf"(?i){B}that{E}", "那"),
    (rf"(?i){B}Here{E}", "这里"),
    (rf"(?i){B}hard{E}", "困难"),
    (rf"(?i){B}door{E}", "门"),
    (rf"(?i){B}START{E}", "START"),
    (rf"(?i){B}SAVE{E}", "保存"),
]

# Full-sentence overrides (zh key match substring -> replace whole or part)
SENTENCE_FIX: list[tuple[str, str]] = [
    (
        "it is, then!{WAIT_CLEAR}Anchors aweigh!\nPEEKO, we're setting sail, my darling!",
        "那就这样吧！{WAIT_CLEAR}起锚！\n小皮，我们出航啦，宝贝！",
    ),
    (
        "Oh, hi, {FD:01}{FD:05}!\nHave you gone to that place,{WAIT_SCROLL}the ",
        "哦，嗨，{FD:01}{FD:05}！\n你去过那个地方了吗，{WAIT_SCROLL}",
    ),
    (
        "Anchors aweigh!",
        "起锚！",
    ),
    (
        "we're setting sail, my darling!",
        "我们出航啦，宝贝！",
    ),
    (
        "it is, then!",
        "那就这样吧！",
    ),
]


def apply_glossary(zh: str) -> str:
    out = zh or ""
    # official names exact tokens
    for en, cn in sorted(OFFICIAL_NAMES.items(), key=lambda x: -len(x[0])):
        if en in ("N",):  # keep
            continue
        out = re.sub(rf"(?<![A-Za-z]){re.escape(en)}(?![A-Za-z])", cn, out, flags=re.IGNORECASE)
    for pat, rep in sorted(GLOSSARY, key=lambda x: -len(x[0])):
        out = re.sub(pat, rep, out)
    for a, b_ in SENTENCE_FIX:
        if a in out:
            out = out.replace(a, b_)
    out = scrub_all(out)
    # strip leftover pure English short glue if surrounded by CJK
    out = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?i:and|the|to|of|a|an|is|are|was|for|in|on)\s+(?=[\u4e00-\u9fff])", "", out)
    return out


def still_latin(zh: str) -> list[str]:
    plain = re.sub(r"\{[^}]+\}", "", zh)
    return [
        m
        for m in re.findall(r"[A-Za-z]{4,}", plain)
        if m.lower() not in {"lv", "hp", "pp", "exp", "tm", "hm", "gba", "ok", "start", "save", "wifi"}
    ]


def inplace(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    capacity = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if len(enc) > capacity:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > capacity:
            if "{WAIT_" in cut:
                cut = cut.rsplit("{WAIT_", 1)[0]
            else:
                cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        if len(enc) > capacity:
            return "too_long"
    data[off : off + capacity] = enc + b"\x00" * (capacity - len(enc))
    return "ok"


def main() -> int:
    mix_path = ROOT / "work" / "latin_mix.json"
    if not mix_path.exists():
        from export_latin_mix import main as exp

        exp()
    mix = json.loads(mix_path.read_text(encoding="utf-8"))
    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_off = {int(r["offset"]): r for r in rows}
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    fixed = left = 0
    remain_words: dict[str, int] = {}
    for item in mix:
        off = int(item["offset"])
        en = item.get("en") or ""
        zh0 = item.get("zh") or ""
        zh1 = apply_glossary(zh0)
        hits = still_latin(zh1)
        r = by_off.get(off)
        if not r:
            continue
        if is_junk_en(en):
            continue
        r["zh"] = zh1
        if en and quality_ok(en, zh1):
            cache[en] = zh1
        if hits:
            left += 1
            for h in hits:
                remain_words[h] = remain_words.get(h, 0) + 1
        else:
            fixed += 1

    # second pass: MT remaining unique problematic full lines via translators if available
    need_mt = []
    seen = set()
    for item in mix:
        off = int(item["offset"])
        r = by_off.get(off)
        if not r:
            continue
        zh = r.get("zh") or ""
        en = r.get("en") or ""
        hits = still_latin(zh)
        if not hits:
            continue
        # if zh still heavily latin, prefer translating from EN
        cjk = sum(1 for c in zh if "\u4e00" <= c <= "\u9fff")
        lat = sum(1 for c in zh if c.isascii() and c.isalpha())
        src = en if lat > cjk and en else zh
        if src in seen:
            continue
        seen.add(src)
        need_mt.append((off, src, en))

    print(f"glossary_cleared={fixed} still_mixed={left} unique_for_mt={len(need_mt)}")
    mt_ok = 0
    try:
        from fill_and_apply_remaining import translate_one

        for i, (off, src, en) in enumerate(need_mt):
            zh = None
            for eng in ("bing", "alibaba", "youdao"):
                zh = translate_one(src if len(src) < 900 else src[:900], eng)
                if zh:
                    break
            if not zh and en and en != src:
                for eng in ("bing", "alibaba"):
                    zh = translate_one(en[:900], eng)
                    if zh:
                        break
            if zh:
                zh = apply_glossary(zh)
                r = by_off[off]
                r["zh"] = zh
                if en:
                    cache[en] = zh
                mt_ok += 1
            if (i + 1) % 20 == 0:
                print(f"  mt {i+1}/{len(need_mt)} ok={mt_ok}", flush=True)
    except Exception as e:
        print("mt skip", e)

    # apply glossary again after MT
    for r in rows:
        if r.get("zh"):
            r["zh"] = apply_glossary(r["zh"])

    LOCALE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    n_ok = n_long = 0
    for r in rows:
        off = int(r["offset"])
        if 0x0FC0000 <= off < 0x0FD0000:
            continue
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        if not zh or is_junk_en(en) or not quality_ok(en, zh):
            continue
        st = inplace(data, golden, off, zh)
        if st == "ok":
            n_ok += 1
        elif st == "too_long":
            n_long += 1
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print(f"mt_ok={mt_ok} applied={n_ok} too_long={n_long}")
    top = sorted(remain_words.items(), key=lambda x: -x[1])[:30]
    print("remain_words_before_mt_top:")
    for w, n in top:
        print(f"  {n} {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
