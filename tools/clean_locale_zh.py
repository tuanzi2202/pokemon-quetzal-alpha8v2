#!/usr/bin/env python3
"""Clean locale/cache: Pokémon→宝可梦, strip junk symbols, drop garbage rows from apply."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chs_encode import encode_text_safe  # noqa: E402
from fill_and_apply_remaining import (  # noqa: E402
    CACHE,
    GOLDEN,
    LOCALE,
    OUT,
    ROM,
    SKIP_RANGES,
    quality_ok,
)

# Longer / more specific first
POK_RULES = [
    (r"(?i)poksamonleague", "宝可梦联盟"),
    (r"(?i)poksammonleague", "宝可梦联盟"),
    (r"(?i)pok[eé]?mon\s*dex", "宝可梦图鉴"),
    (r"(?i)pok[eé]?mon\s*nav(?:igator)?", "宝可梦导航器"),
    (r"(?i)pok[eé]?mon\s*center", "宝可梦中心"),
    (r"(?i)pok[eé]?mon\s*league", "宝可梦联盟"),
    (r"(?i)pok[eé]?mon\s*storage", "宝可梦存储"),
    (r"(?i)poksammon", "宝可梦"),
    (r"(?i)poksamon", "宝可梦"),
    (r"(?i)poksamo", "宝可梦"),
    (r"(?i)poksamdex", "宝可梦图鉴"),
    (r"(?i)poksamn", "宝可梦"),
    (r"(?i)monleague", "宝可梦联盟"),
    (r"(?i)pokmonleague", "宝可梦联盟"),
    (r"(?i)pok[eé]?mon", "宝可梦"),
    (r"(?i)pok[eé]?dex", "宝可梦图鉴"),
    (r"(?i)pok[eé]?nav", "宝可梦导航器"),
    (r"(?i)pokMON", "宝可梦"),
    # Truncated dump prefix
    (r"(?i)(^|[\n{ ])mon center", r"\1宝可梦中心"),
    (r"(?i)(^|[\n{ ])mon trades?", r"\1宝可梦交换"),
    (r"(?i)(^|[\n{ ])mon can ", r"\1宝可梦可以"),
    (r"(^|[\n{])MON(?=[ :：，,!.。！？\n{])", r"\1宝可梦"),
    (r"(?i)MON[：:]jumpout!?", "宝可梦跳出来了！"),
    (r"(?i)jumpout!?", "跳出来了！"),
    (r"(?i)\bP\.?\s*MON\b", "宝可梦"),
]

JUNK_EN_RE = re.compile(
    r"^(?:"
    r"[0-9A]{12,}"  # 9999AAA…
    r"|8?R{8,}"
    r"|[A-Z]( [A-Z])+ a b c d e.*"
    r"|U VWXYZabc.*"
    r"|CD TwC.*"
    r"|QECx.*"
    r")$",
    re.DOTALL,
)


def is_junk_en(en: str) -> bool:
    e = (en or "").strip()
    if not e:
        return True
    if JUNK_EN_RE.match(e):
        return True
    if e.count("9") > 10 and e.count("A") > 8:
        return True
    if e.count("R") > 15:
        return True
    if "a b c d e f g" in e:
        return True
    # pure alphabet dump
    letters = re.sub(r"[^A-Za-z]", "", e)
    if len(letters) > 40 and len(set(letters.lower())) <= 30 and " " in e and not re.search(
        r"(?i)\b(the|you|battle|pokemon|want|please)\b", e
    ):
        if re.search(r"^[A-Z] [A-Z] [A-Z]", e) or "VWXYZ" in e:
            return True
    return False


def clean_symbols(zh: str) -> str:
    out = zh or ""
    # zero-width / BOM / replacement
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\ufffd", "\u00a0"):
        out = out.replace(ch, "")
    # MT garbage tokens: [[T0]] [[ T1]] [[t2]] [T0] 【T0】 [qh]
    out = re.sub(r"\[\[\s*[Tt]\d+\s*\]\]", "", out)
    out = re.sub(r"【\s*[Tt]\d+\s*】", "", out)
    out = re.sub(r"\[\s*[Tt]\d+\s*\]", "", out)
    out = re.sub(r"\[\[?\s*T\d+\s*\]\]?", "", out)
    out = re.sub(r"\[qh\]", "", out, flags=re.IGNORECASE)
    # collapse decorative ellipsis runs
    out = re.sub(r"(?:\.\.\.|…|……|\u2026){2,}", "……", out)
    out = re.sub(r"(?:·\s*){3,}", "……", out)
    # spaced ellipsis: "... ... ..." / ". . . . ."
    out = re.sub(r"(?:\.\.\.\s*){2,}", "……", out)
    out = re.sub(r"(?:\.\s+){2,}\.?", "……", out)
    out = re.sub(r"(?:…\s*){2,}", "……", out)
    # !!?? spam (keep up to 2)
    out = re.sub(r"!{3,}", "!!", out)
    out = re.sub(r"\?{3,}", "??", out)
    out = re.sub(r"！{3,}", "！！", out)
    out = re.sub(r"？{3,}", "？？", out)
    # odd quote leftovers
    out = out.replace("``", "「").replace("''", "」")
    # strip leftover ASCII control except newline
    out = "".join(ch for ch in out if ch == "\n" or ord(ch) >= 32 or ch in "\t")
    # tidy spaces around CJK
    out = re.sub(r" +([，。！？、：；」』])", r"\1", out)
    out = re.sub(r"([「『]) +", r"\1", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    # leftover English glue words often from bad MT
    out = re.sub(r"(?i)\banyway\b[,，]?", "总之", out)
    return out


def scrub_all(zh: str) -> str:
    out = zh or ""
    for pat, rep in POK_RULES:
        out = re.sub(pat, rep, out)
    out = clean_symbols(out)
    # (?<![A-Za-z])..(?![A-Za-z]) — \b fails between CJK and Latin
    B = r"(?<![A-Za-z])"
    E = r"(?![A-Za-z])"
    extras = [
        (rf"(?i){B}TRAINER{E}", "训练家"),
        (rf"(?i){B}POKe?\s*BALL{E}", "精灵球"),
        (rf"(?i){B}GREAT BALL{E}", "超级球"),
        (rf"(?i){B}ULTRA BALL{E}", "高级球"),
        (rf"(?i){B}MASTER BALL{E}", "大师球"),
        (rf"(?i){B}BATTLE POINTS?{E}", "对战点数"),
        (rf"(?i){B}WIRELESS COMMUNICATION\s*SYSTEM{E}", "无线通讯系统"),
        (rf"(?i){B}WONDER CARDS?{E}", "神秘卡片"),
        (rf"(?i){B}WONDER NEWS{E}", "神秘新闻"),
        (rf"(?i){B}BERRY BLENDER{E}", "树果混合器"),
        (rf"(?i){B}BERRY CRUSH{E}", "树果粉碎"),
        (rf"(?i){B}CONTROL PAD{E}", "十字键"),
        (rf"(?i){B}MULTI BATTLE ROOM{E}", "多人对战房间"),
        (rf"(?i){B}BATTLE SALON{E}", "对战沙龙"),
        (rf"(?i){B}BATTLE TOWER{E}", "对战塔"),
        (rf"(?i){B}BULK UP{E}", "健美"),
        (rf"(?i){B}SLATEPORT{E}", "凯那市"),
        (rf"(?i){B}LILYCOVE{E}", "水静市"),
        (rf"(?i){B}DEWFORD{E}", "武斗镇"),
        (rf"(?i){B}MOSSDEEP{E}", "绿岭市"),
        (rf"(?i){B}SOOTOPOLIS{E}", "琉璃市"),
        (rf"(?i){B}FORTREE{E}", "茵郁市"),
        (rf"(?i){B}PETALBURG{E}", "橙华市"),
        (rf"(?i){B}RUSTBORO{E}", "卡那兹市"),
        (rf"(?i){B}OLDALE{E}", "古辰镇"),
        (rf"(?i){B}LITTLEROOT{E}", "未白镇"),
        (rf"(?i){B}LAVARIDGE{E}", "釜炎镇"),
        (rf"(?i){B}COVE LILY{E}", "琉璃"),
        (rf"(?i){B}GYM LEADER{E}", "道馆馆主"),
        (rf"(?i){B}GYM{E}", "道馆"),
        (rf"(?i){B}LEAGUE{E}", "联盟"),
        (rf"(?i){B}STEVEN{E}", "大吾"),
        (rf"(?i){B}WALLACE{E}", "米可利"),
        (rf"(?i){B}ARCHIE{E}", "水梧桐"),
        (rf"(?i){B}MAXIE{E}", "赤焰松"),
        (rf"(?i){B}FLANNERY{E}", "亚莎"),
        (rf"(?i){B}WAILMER{E}", "吼吼鲸"),
        (rf"(?i){B}AZURILL{E}", "露力丽"),
        (rf"(?i){B}SNORLAX{E}", "卡比兽"),
        (rf"(?i){B}KYOGRE{E}", "盖欧卡"),
        (rf"(?i){B}GROUDON{E}", "固拉多"),
        (rf"(?i){B}RAYQUAZA{E}", "烈空坐"),
        (rf"(?i){B}MT\.?\s*PYRE{E}", "送神山"),
        (rf"(?i){B}ORBS{E}", "宝珠"),
        (rf"(?i){B}TEAM AQUA{E}", "海洋队"),
        (rf"(?i){B}TEAM MAGMA{E}", "熔岩队"),
        (rf"(?i){B}AQUA{E}", "海洋队"),
        (rf"(?i){B}MAGMA{E}", "熔岩队"),
        (rf"(?i){B}CENTER{E}", "中心"),
        (rf"(?i){B}LEADER{E}", "馆主"),
        (rf"(?i){B}NAV{E}", "导航器"),
        (rf"(?i){B}TM(\d+){E}", r"招式学习器\1"),
        (r"\.{4,}", "……"),
        (rf"(?i){B}I'veheard{E}", "我听说"),
        (rf"(?i){B}veheard{E}", "听说"),
        (rf"(?i){B}door{E}\s*closed\.?", "门关着。"),
        (rf"(?i){B}closed\.?{E}", "关着。"),
        # laughter / cries left in Latin
        (rf"(?i)Fwohoho(?:\s*fwohohohoho)?", "喔呵呵呵呵"),
        (rf"(?i)Fuhahaha!?", "唔哈哈哈哈！"),
        (rf"(?i)Hahaha!?", "哈哈哈！"),
        (rf"(?i)Fwafwafwafwafwa", "呼哇呼哇"),
        (rf"(?i)Fwatchoo\s*!", "阿嚏！"),
        (r"\[\[[^\]]*\]\]", ""),
        (r"T\d+\s*", ""),
    ]
    for pat, rep in extras:
        out = re.sub(pat, rep, out)
    return out


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


def in_skip(off: int) -> bool:
    return any(a <= off < b for a, b in SKIP_RANGES)


def main() -> int:
    rows = [json.loads(l) for l in LOCALE.read_text(encoding="utf-8").splitlines() if l.strip()]
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    n_scrub = n_junk = n_pok = 0
    kept: list[dict] = []
    for r in rows:
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        if is_junk_en(en):
            n_junk += 1
            # keep row but mark zh empty so apply restores golden
            r["zh"] = ""
            r["junk"] = True
            kept.append(r)
            continue
        before = zh
        zh2 = scrub_all(zh)
        if "宝可梦" in zh2 and re.search(r"(?i)pok|MON", before):
            n_pok += 1
        if zh2 != before:
            n_scrub += 1
        r["zh"] = zh2
        r.pop("junk", None)
        kept.append(r)
        if en and zh2 and quality_ok(en, zh2):
            cache[en] = zh2

    # also scrub cache values
    for k, v in list(cache.items()):
        if is_junk_en(k):
            cache.pop(k, None)
            continue
        cache[k] = scrub_all(v)

    LOCALE.write_text(
        "\n".join(
            json.dumps(
                {
                    "offset": r["offset"],
                    "en": r.get("en") or "",
                    "zh": "" if r.get("junk") else (r.get("zh") or ""),
                },
                ensure_ascii=False,
            )
            for r in kept
        )
        + "\n",
        encoding="utf-8",
    )
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    # apply to ROM: good zh inplace; junk → restore golden
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes() if OUT.exists() else ROM.read_bytes())
    n_ok = n_restored = n_bad = n_long = 0
    for r in kept:
        off = int(r["offset"])
        if in_skip(off):
            continue
        en = r.get("en") or ""
        zh = r.get("zh") or ""
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos - off > 800:
            continue
        capacity = eos - off + 1
        if r.get("junk") or is_junk_en(en) or not zh:
            if r.get("junk") or is_junk_en(en):
                data[off : off + capacity] = golden[off : off + capacity]
                n_restored += 1
            else:
                n_bad += 1
            continue
        zh = scrub_all(zh)
        if not quality_ok(en, zh):
            n_bad += 1
            continue
        st = inplace(data, golden, off, zh)
        if st == "ok":
            n_ok += 1
        elif st == "too_long":
            n_long += 1

    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print(
        f"scrubbed={n_scrub} pok_hits~={n_pok} junk_rows={n_junk} "
        f"applied={n_ok} restored_junk={n_restored} bad={n_bad} long={n_long}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
