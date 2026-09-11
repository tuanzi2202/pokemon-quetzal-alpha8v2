#!/usr/bin/env python3
"""Force-fix remaining latin_mix rows from EN with glossary + sound map."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_locale_zh import is_junk_en  # noqa: E402
from fill_and_apply_remaining import (  # noqa: E402
    CACHE,
    GOLDEN,
    LOCALE,
    OUT,
    ROM,
    quality_ok,
    translate_one,
)
from fill_latin_mix import apply_glossary, inplace, still_latin  # noqa: E402
from fill_latin_mix_pass2 import scrub2  # noqa: E402

SOUNDS = {
    "Oops!": "哎呀！",
    "Bufoh!": "布呼！",
    "Gwah!": "咕哇！",
    "Arrrgh!": "啊啊啊！",
    "Arrrgh !": "啊啊啊！",
    "Yeahah!": "耶哈！",
    "Ahahah!": "啊哈哈！",
    "Ahahah !": "啊哈哈！",
    "Gwahahah!": "咕哇哈哈！",
    "Gwahahah": "咕哇哈哈",
    "Kaaah!": "卡啊！",
    "Kwah!": "夸啊！",
    "Aiyeeh!": "哎呀！",
    "BRAVO!": "太棒了！",
}

MORE = [
    (r"(?i)Flute", "笛子"),
    (r"(?i)BALLS?", "精灵球"),
    (r"(?i)JAGGED PASS", "凹凸山道"),
    (r"(?i)GRANITE CAVE", "石之洞窟"),
    (r"(?i)GRANITE", "石之洞窟"),
    (r"(?i)KISS CUSHION", "亲吻坐垫"),
    (r"(?i)PALACE MAVEN", "宫殿大师"),
    (r"(?i)BATTLE PALACE", "对战宫殿"),
    (r"(?i)ALACE", "宫殿"),
    (r"(?i)firebrand", "火辣家伙"),
    (r"(?i)MIRACLE SEED", "奇迹种子"),
    (r"(?i)MIRACLE", "奇迹"),
    (r"(?i)ZIGG", "蛇纹熊"),
    (r"(?i)NORMAL", "一般"),
    (r"(?i)DRAGON", "龙"),
    (r"(?i)Fire", "火"),
    (r"(?i)Ice", "冰"),
    (r"(?i)Steel", "钢"),
    (r"(?i)Iron", "铁"),
    (r"(?i)Legendary", "传说"),
    (r"(?i)Lazy", "懒惰"),
    (r"(?i)Aurora", "极光"),
    (r"(?i)Glacier", "冰川"),
    (r"(?i)PEAK", "山峰"),
    (r"(?i)King", "国王"),
    (r"(?i)Tourney", "锦标赛"),
    (r"(?i)forplaying", "谢谢游玩"),
    (r"(?i)zippier", "更灵活"),
    (r"(?i)Chadoll", "机械人偶"),
    (r"(?i)AQUAS?", "水舰队"),
    (r"(?i)MYSTERY", "神秘"),
    (r"(?i)JUMP", "跳跃"),
    (r"(?i)TEALA", "席拉"),
    (r"(?i)DIRECT", "直连"),
    (r"(?i)YouTube", "YouTube"),
    (r"(?i)Discord", "Discord"),
    (r"(?i)Polkam", "波尔卡"),
    (r"(?i)ribbon", "奖章"),
    (r"(?i)Dear audience", "亲爱的观众"),
    (r"(?i)cuties", "小家伙们"),
    (r"(?i)sacred", "神圣"),
    (r"(?i)simply", "简直"),
    (r"(?i)wearing", "戴着"),
    (r"(?i)ribbons", "奖章"),
    (r"(?i)agree", "同意"),
    (r"(?i)hello", "你好"),
    (r"(?i)know", "知道"),
    (r"(?i)share", "分享"),
    (r"(?i)Please", "请"),
    (r"(?i)NEWS", "新闻"),
    (r"(?i)Find those", "找到那些"),
    (r"(?i)become stronger", "变得更强"),
    (r"(?i)Besides", "此外"),
    (r"(?i)convenient", "方便"),
    (r"(?i)serious", "认真"),
    (r"(?i)puts", "投入"),
    (r"(?i)said", "据说"),
    (r"(?i)checked", "确认了"),
    (r"(?i)enemy", "对手"),
    (r"(?i)apparently", "显然"),
    (r"(?i)used", "使用了"),
    (r"(?i)beaten", "被打败了"),
    (r"(?i)think", "觉得"),
    (r"(?i)there", "那里"),
    (r"(?i)other", "其他"),
    (r"(?i)items", "道具"),
    (r"(?i)where", "在哪里"),
    (r"(?i)mono", "单打"),
    (r"(?i)xpand", "扩展"),
    (r"(?i)Advance", ""),
    (r"(?i)GameCube", "任天堂主机"),
]


def force_clean(zh: str) -> str:
    out = scrub2(zh)
    for a, b in SOUNDS.items():
        out = out.replace(a, b)
    for pat, rep in MORE:
        out = re.sub(pat, rep, out)
    out = apply_glossary(out)
    # remove remaining latin words length>=4 except allowed
    def repl(m):
        w = m.group(0)
        if w.upper() in {"SELECT", "START", "SAVE", "GBA", "HP", "PP", "TM", "HM", "LV"}:
            return w
        if w in {"YouTube", "Discord"}:
            return w
        return ""

    out = re.sub(r"[A-Za-z]{4,}", repl, out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r" +([，。！？])", r"\1", out)
    return out.strip()


def main() -> int:
    mix = json.loads((ROOT / "work" / "latin_mix.json").read_text(encoding="utf-8"))
    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_off = {int(r["offset"]): r for r in rows}
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    ok = fail = 0
    for i, item in enumerate(mix):
        off = int(item["offset"])
        r = by_off.get(off)
        if not r:
            continue
        en = r.get("en") or item.get("en") or ""
        zh = r.get("zh") or ""
        if is_junk_en(en):
            continue
        # Prefer re-MT from EN when zh still messy
        hits = still_latin(force_clean(zh))
        new_zh = None
        if hits and en and sum(c.isalpha() for c in en) >= 12:
            for eng in ("bing", "alibaba", "youdao"):
                new_zh = translate_one(en[:900], eng)
                if new_zh:
                    break
                time.sleep(0.05)
        if not new_zh:
            new_zh = zh
        new_zh = force_clean(new_zh)
        # if wiped too much, keep previous scrub2
        if sum(1 for c in new_zh if "\u4e00" <= c <= "\u9fff") < 2 and zh:
            new_zh = force_clean(zh)
        r["zh"] = new_zh
        if en and quality_ok(en, new_zh):
            cache[en] = new_zh
            ok += 1
        else:
            fail += 1
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(mix)}", flush=True)

    LOCALE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
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
        en, zh = r.get("en") or "", r.get("zh") or ""
        if zh and not is_junk_en(en) and quality_ok(en, zh):
            if inplace(data, golden, off, zh) == "ok":
                n += 1
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print(f"done ok={ok} fail={fail} applied={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
