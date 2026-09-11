#!/usr/bin/env python3
"""Second pass: wipe remaining Latin mix with expanded glossary + hand fixes."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_locale_zh import is_junk_en  # noqa: E402
from fill_and_apply_remaining import CACHE, GOLDEN, LOCALE, OUT, ROM, quality_ok  # noqa: E402
from fill_latin_mix import apply_glossary, inplace, still_latin  # noqa: E402

EXTRA = [
    (r"(?i)poksamumo", "宝可梦"),
    (r"(?i)poksamumon", "宝可梦"),
    (r"(?i)poksamen", "宝可梦"),
    (r"(?i)poksamumo?", "宝可梦"),
    (r"(?i)ksammon", "宝可梦"),
    (r"(?i)poksamen?", "宝可梦"),
    (r"(?i)pokvac", "宝可梦"),
    (r"(?i)dovisitagain", "请再来玩"),
    (r"(?i)asfollows", "如下"),
    (r"(?i)EmphasizesHP", "侧重体力"),
    (r"(?i)NeglectsSP", "忽视特攻"),
    (r"(?i)Awoooh", "嗷呜"),
    (r"(?i)ahoy", "啊嘿"),
    (r"(?i)Fufufufufu", "呵呵呵呵呵"),
    (r"(?i)Eheheh", "诶嘿嘿"),
    (r"(?i)Grrr+", "咕噜噜"),
    (r"(?i)Kwah", "夸啊"),
    (r"(?i)Ayayayay", "哎呀呀呀"),
    (r"(?i)woweee", "哇诶"),
    (r"(?i)o{5,}h", "哦——"),
    (r"(?i)qqqq+", ""),
    (r"(?i)https?://\S+", ""),
    (r"(?i)www\.\S+", ""),
    (r"(?<![A-Za-z])RUSTURF(?![A-Za-z])", "卡绿隧道"),
    (r"(?<![A-Za-z])RALTS(?![A-Za-z])", "拉鲁拉丝"),
    (r"(?<![A-Za-z])MARILL(?![A-Za-z])", "玛力露"),
    (r"(?<![A-Za-z])ZUBAT(?![A-Za-z])", "超音蝠"),
    (r"(?<![A-Za-z])PORYGON(?![A-Za-z])", "多边兽"),
    (r"(?<![A-Za-z])DUSCLOPS(?![A-Za-z])", "彷徨夜灵"),
    (r"(?<![A-Za-z])CLEFAIRY(?![A-Za-z])", "皮皮"),
    (r"(?<![A-Za-z])SMOOCHUM(?![A-Za-z])", "迷唇娃"),
    (r"(?<![A-Za-z])PEKACHU(?![A-Za-z])", "皮卡丘"),
    (r"(?<![A-Za-z])WALDA(?![A-Za-z])", "瓦尔达"),
    (r"(?<![A-Za-z])KIRI(?![A-Za-z])", "奇莉"),
    (r"(?<![A-Za-z])TUBER(?![A-Za-z])", "泳圈小朋友"),
    (r"(?<![A-Za-z])COOLTRAINER(?![A-Za-z])", "精英训练家"),
    (r"(?<![A-Za-z])REVIVE(?![A-Za-z])", "活力块"),
    (r"(?<![A-Za-z])RIBBON(?![A-Za-z])", "奖章"),
    (r"(?<![A-Za-z])SPLASH(?![A-Za-z])", "跃起"),
    (r"(?<![A-Za-z])SMART(?![A-Za-z])", "聪明"),
    (r"(?<![A-Za-z])DIVE(?![A-Za-z])", "潜水"),
    (r"(?<![A-Za-z])HEAT(?![A-Za-z])", "高温"),
    (r"(?<![A-Za-z])DYNAMO(?![A-Za-z])", "电力"),
    (r"(?<![A-Za-z])ACRO(?![A-Za-z])", "越野"),
    (r"(?<![A-Za-z])HARBOR(?![A-Za-z])", "港口"),
    (r"(?<![A-Za-z])MAIL(?![A-Za-z])", "邮件"),
    (r"(?<![A-Za-z])RESEARCHER(?![A-Za-z])", "研究员"),
    (r"(?<![A-Za-z])FREAK(?![A-Za-z])", "狂热者"),
    (r"(?<![A-Za-z])LEECH(?![A-Za-z])", "吸血"),
    (r"(?<![A-Za-z])OTOPOLIS(?![A-Za-z])", "琉棋市"),
    (r"(?<![A-Za-z])MACHO(?![A-Za-z])", "怪力"),
    (r"(?<![A-Za-z])WOODS(?![A-Za-z])", "森林"),
    (r"(?<![A-Za-z])FLASH(?![A-Za-z])", "闪光"),
    (r"(?<![A-Za-z])Nuzlocke(?![A-Za-z])", "努兹洛克"),
    (r"(?<![A-Za-z])Sevii(?![A-Za-z])", "七之岛"),
    (r"(?<![A-Za-z])SPACE(?![A-Za-z])", "空间"),
    (r"(?<![A-Za-z])MATCH(?![A-Za-z])", "对战"),
    (r"(?<![A-Za-z])SELECT(?![A-Za-z])", "SELECT"),
    (r"(?<![A-Za-z])INERS(?![A-Za-z])", "训练家"),
    (r"(?<![A-Za-z])ECORD(?![A-Za-z])", "纪录"),
    (r"(?<![A-Za-z])Power(?![A-Za-z])", "力量"),
    (r"(?i)\bAlso\b", "另外"),
    (r"(?i)\bmakes\b", "让"),
    (r"(?i)\bfaster\b", "更快"),
    (r"(?i)\bshould\b", "应该"),
    (r"(?i)\btake\b", "拿"),
    (r"(?i)\byour\b", "你的"),
    (r"(?i)\blittle\b", "一点"),
    (r"(?i)\bthis\b", "这"),
    (r"(?i)\bwill\b", "会"),
    (r"(?i)\bHave\b", "有"),
    (r"(?i)\bever\b", "曾经"),
    (r"(?i)\bfought\b", "战斗过"),
    (r"(?i)\bWhen\b", "当"),
    (r"(?i)\bstrength\b", "力量"),
    (r"(?i)\binto\b", "进入"),
    (r"(?i)\bthese\b", "这些"),
    (r"(?i)\bToday\b", "今天"),
    (r"(?i)\bdeep\b", "深"),
    (r"(?i)\babout\b", "关于"),
    (r"(?i)\bmove\b", "招式"),
    (r"(?i)\bbeaten\b", "被打败"),
    (r"(?i)\bThis\b", "这"),
    (r"(?i)\bmagical\b", "神奇的"),
    (r"(?i)\bseed\b", "种子"),
    (r"(?i)\bholds\b", "携带"),
    (r"(?i)\bitem\b", "道具"),
    (r"(?i)\bGrass\b", "草"),
    (r"(?i)\bmoves\b", "招式"),
    (r"(?i)\bcan use\b", "可以使用"),
    (r"(?i)\bthe DYNAMO BADGE\b", "电力徽章"),
    (r"(?i)Game Boy Advance", "GBA"),
    (r"(?i)GameCube", "任天堂GameCube"),
    (r"(?i)\bAdvance\b", "Advance"),
    (r"(?i)xpand", "扩展"),
    (r"(?i)\bmono\b", "单打"),
    (r"~~~+", "……"),
]


HAND = {
    # fill exact zh snippets if needed after glossary
}


def scrub2(zh: str) -> str:
    out = apply_glossary(zh)
    for pat, rep in EXTRA:
        out = re.sub(pat, rep, out)
    for a, b in HAND.items():
        out = out.replace(a, b)
    # drop leftover short english words between CJK
    out = re.sub(
        r"(?<=[\u4e00-\u9fff])\s*[A-Za-z]{1,3}\s*(?=[\u4e00-\u9fff])",
        "",
        out,
    )
    return out


def main() -> int:
    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    fixed = left = 0
    remain = []
    for r in rows:
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        if not zh or is_junk_en(en):
            continue
        zh2 = scrub2(zh)
        r["zh"] = zh2
        if en and quality_ok(en, zh2):
            cache[en] = zh2
        hits = still_latin(zh2)
        # allow SELECT/START/SAVE/GBA/GameCube
        hits = [h for h in hits if h.upper() not in {"SELECT", "START", "SAVE", "GBA"} and "GAMECUBE" not in h.upper()]
        if hits:
            left += 1
            remain.append((int(r["offset"]), hits[:4], zh2[:100]))
        else:
            if still_latin(zh):
                fixed += 1

    LOCALE.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n",
        encoding="utf-8",
    )
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    n = 0
    for r in rows:
        off = int(r["offset"])
        if 0x0FC0000 <= off < 0x0FD0000:
            continue
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        if not zh or is_junk_en(en) or not quality_ok(en, zh):
            continue
        if inplace(data, golden, off, zh) == "ok":
            n += 1
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print(f"pass2_fixed~={fixed} still={left} applied={n}")
    for o, h, z in remain[:25]:
        print(f"{o:08X} {h} {z!r}")
    Path(ROOT / "work" / "latin_remain.json").write_text(
        json.dumps([{"offset": o, "hits": h, "zh": z} for o, h, z in remain], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
