#!/usr/bin/env python3
"""Fix leftover EN dialogues, POKé+球 partials, and ?? (0xAC) junk."""
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

# Hand fixes for reported / early-game leftovers
HAND: dict[int, str] = {
    # User example: Oh, I see, my dad gave you a Pokémon
    0x27A904: (
        "哦，嗨，{FD:01}{FD:05}！{WAIT_CLEAR}"
        "哦，原来爸爸送给你一只宝可梦了。{WAIT_CLEAR}"
        "既然都在这儿，就来打一架吧！{WAIT_CLEAR}"
        "我会教你，成为训练家意味着什么。"
    ),
    0x27AAF4: (
        "嘿，是{FD:01}！{WAIT_CLEAR}"
        "……哦对了，爸爸给了你一只宝可梦。{WAIT_CLEAR}"
        "既然碰上了，要比试一下吗？{WAIT_CLEAR}"
        "我来教你，训练家是怎么回事！"
    ),
    0x27EE9D: (
        "哦，原来如此！\n你们俩是分头行动的。{WAIT_SCROLL}"
        "嗯，那也好。{WAIT_CLEAR}"
        "对了，听说你的宝可梦导航器\n装上了对战寻呼系统。{WAIT_CLEAR}"
        "那我也把你登记进\n我的导航器吧。{WAIT_CLEAR}"
        "这样就算分开，\n我也能随时评价你的图鉴。"
    ),
    # Ball-related that were zeroed / partial
    0x281FB5: (
        "好消息！{WAIT_CLEAR}"
        "最近我们公司开发出了\n一种新型精灵球。{WAIT_CLEAR}"
        "不过库存还不够，\n现在还不能给你。"
    ),
    0x2B0C76: (
        "用念力举不起精灵球，\n太重了。但这团灰尘兔……{WAIT_CLEAR}"
        "好像轻飘飘的。"
    ),
    0x2B2868: "{FD:01}把精灵球\n留在了原地。",
    0x32263B: (
        "上次对战时，你是不是\n朝我们扔了精灵球？{WAIT_CLEAR}"
        "我们可不是野生宝可梦！"
    ),
    # Route 101 signs / tips
    0x279D6E: (
        "宝可梦累了的话，就带到\n宝可梦中心去吧。{WAIT_CLEAR}"
        "附近的古辰镇就有\n宝可梦中心。"
    ),
    0x279DDB: (
        "高草丛里会跳出野生宝可梦。{WAIT_CLEAR}"
        "想捉宝可梦的话，\n就要走进草丛里去找。"
    ),
    0x2765F6: (
        "使用电脑，就能存放道具\n和宝可梦。{WAIT_CLEAR}"
        "科学的力量真是了不起！"
    ),
    0x276CFC: (
        "你好！\n我在宝可梦商店工作。{WAIT_CLEAR}"
        "能跟我来一下吗？"
    ),
    0x276DEB: (
        "伤药随时都能用，\n在某些情况下比宝可梦中心{WAIT_SCROLL}还管用。"
    ),
    0x276E4F: (
        "啊啊啊！等等！\n请别进来！{WAIT_CLEAR}"
        "我刚发现稀有宝可梦的脚印！{WAIT_CLEAR}"
        "等我画完再进来，好吗？"
    ),
    # Mom arrival — text starts after 8-byte script prefix
    0x2761E3: (
        "妈妈：{FD:01}，到了哦，宝贝！{WAIT_CLEAR}"
        "坐着满载行李的搬家卡车，\n一定很累吧。{WAIT_CLEAR}"
        "这里就是未白镇。{WAIT_CLEAR}"
        "喜欢吗？\n这就是我们的新家！{WAIT_CLEAR}"
        "虽然古朴，但感觉很适合生活，\n你说呢？{WAIT_CLEAR}"
        "而且，"
    ),
    0x27BEB6: "{FD:01}把小遥\n登记到了宝可梦导航器。",
    0x27BED8: "小遥：对了，{FD:01}{FD:05}，\n你的宝可梦图鉴进展如何？",
    0x27BF51: (
        "小遥：咦，怎么了？{WAIT_CLEAR}"
        "你几乎没捉过、也没好好培养\n宝可梦吧？{WAIT_CLEAR}"
        "这对训练家来说可不像样！"
    ),
    0x27C065: (
        "小遥：看得出来，你已经很会\n指挥宝可梦了。{WAIT_CLEAR}"
        "不过别只会让它们对战，\n要像哈奇大人那样。{WAIT_CLEAR}"
        "和宝可梦做朋友\n也很重要哦。"
    ),
    0x27C12B: (
        "小悠：哦，嘿，{FD:01}！{WAIT_CLEAR}"
        "酷，你让得文给导航器装上了\n对战寻呼系统！{WAIT_CLEAR}"
        "我们互相登记到导航器里，\n好保持联系吧。"
    ),
    0x2BF038: "精灵球用完了。",
    0x27A8CC: "小遥：我看看……103号道路上\n能遇到的宝可梦有……",
    0x27AC99: "我的宝可梦累坏了……\n早知道该带伤药来的……",
}


def put(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    cap = eos - off + 1
    enc, miss = encode_text_safe(zh)
    if miss:
        print(f"  miss @{off:08X} {miss[:6]}")
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    if len(body) + 1 > cap:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > cap:
            cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        body = enc[:-1]
        if len(body) + 1 > cap:
            print(f"  FAIL {off:08X}")
            return "long"
        print(f"  TRIM {off:08X} {len(body)+1}/{cap}")
    else:
        print(f"  OK {off:08X} {len(body)+1}/{cap}")
    data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))
    return "ok"


def scrub_en_to_zh(en: str) -> str:
    """Conservative glossary scrub → still need full sentence ZH for mixed lines."""
    z = en
    reps = [
        (r"(?i)POK[EÉ]\s*BALLS?", "精灵球"),
        (r"(?i)GREAT\s*BALLS?", "超级球"),
        (r"(?i)ULTRA\s*BALLS?", "高级球"),
        (r"(?i)MASTER\s*BALLS?", "大师球"),
        (r"(?i)POK[EÉ]\s*MON", "宝可梦"),
        (r"(?i)POK[EÉ]\s*DEX", "宝可梦图鉴"),
        (r"(?i)POK[EÉ]\s*NAV", "宝可梦导航器"),
        (r"(?i)PROF\.\s*BIRCH", "小田卷博士"),
        (r"(?i)TRAINER", "训练家"),
        (r"(?i)LITTLEROOT", "未白镇"),
        (r"(?i)OLDALE", "古辰镇"),
        (r"(?i)PETALBURG", "橙华市"),
        (r"(?i)MAY:", "小遥："),
        (r"(?i)BRENDAN:", "小悠："),
        (r"(?i)MOM:", "妈妈："),
        (r"(?i)WALLY:", "小遥："),  # wrong - Wally is 小遥 in some CN? Actually 小悠 is Brendan, Wally is 小遥? 
        # Emerald: Wally = 小遥 in older Fan CN sometimes, official 小遥 is May. Wally = 望罗
    ]
    # Fix Wally
    reps[-1] = (r"(?i)WALLY:", "望罗：")
    for a, b in reps:
        z = re.sub(a, b, z)
    return z


def fix_poke_qiu_partials(data: bytearray, golden: bytes) -> int:
    """cac9c51b (POKé) immediately followed by 球 → 精灵球."""
    poke = bytes([0xCA, 0xC9, 0xC5, 0x1B])  # POKé
    qiu = encode_text_safe("球")[0]
    qiu = qiu[:-1] if qiu.endswith(b"\xff") else qiu
    jing = encode_text_safe("精灵球")[0]
    jing = jing[:-1] if jing.endswith(b"\xff") else jing
    n = 0
    # Also POKé + space + 球, POKéBALL partials
    patterns = [
        poke + qiu,  # POKé球
        poke + bytes([0x00]) + qiu,  # POKé 球
        poke + bytes([0x00, 0xBC, 0xBB, 0xC6, 0xC6]),  # still POKé BALL english
    ]
    # Walk dialogue-ish ranges
    for start, end in [(0x270000, 0x360000), (0xFB0000, 0x1000000)]:
        off = start
        while off < end - 8:
            if data[off : off + 4] != poke:
                off += 1
                continue
            # find string bounds
            s = off
            while s > start and golden[s - 1] != 0xFF and off - s < 120:
                s -= 1
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= end or eos - s > 400:
                off += 1
                continue
            en = decode_bytes(golden[s : eos + 1])
            if not re.search(r"(?i)pok.?e?\s*ball|pok.?e?\s*mon", en):
                # still fix raw POKé+球 in place if present
                window = bytes(data[off : off + 8])
                if qiu in window:
                    # inplace replace poke+qiu with jinglingqiu truncated to same span
                    # find qiu offset
                    rel = bytes(data[off : off + 12]).find(qiu)
                    if rel >= 0:
                        old_len = 4 + rel + len(qiu)  # rough
                        # better: replace from off spanning poke through qiu
                        span = rel + len(qiu)
                        old = bytes(data[off : off + 4 + span])
                        # Prefer rewriting whole string
                        zh = scrub_en_to_zh(en)
                        if any("\u4e00" <= c <= "\u9fff" for c in zh) and zh != en:
                            if put(data, golden, s, zh) == "ok":
                                n += 1
                                off = eos + 1
                                continue
                off += 1
                continue
            zh = scrub_en_to_zh(en)
            # If still mostly English, use fuller hand templates for ball lines
            latin = len(re.findall(r"[A-Za-z]", zh))
            cjk = sum(1 for c in zh if "\u4e00" <= c <= "\u9fff")
            if cjk == 0 or latin > cjk * 3:
                # force ball/mon word replace at least via rebuild
                zh = scrub_en_to_zh(en)
            if zh != en and cjk + sum(1 for c in zh if "\u4e00" <= c <= "\u9fff") > 0:
                # For lines that are still English-heavy, only apply if ball/pokémon words fixed
                # AND we have a HAND entry or early-game
                if s in HAND:
                    off = eos + 1
                    continue
                if latin > 40 and s >= 0x2B0000:
                    # late game: only fix if POKé+球 raw
                    raw = bytes(data[s : eos + 1])
                    if poke in raw and qiu in raw[raw.find(poke) : raw.find(poke) + 10]:
                        # rebuild from en with scrub — may leave English but fix poke球
                        if put(data, golden, s, zh) == "ok":
                            n += 1
                    off = eos + 1
                    continue
                if put(data, golden, s, zh) == "ok":
                    n += 1
            off = eos + 1
    print(f"poke/ball scrubbed strings≈{n}")
    return n


def fix_raw_poke_qiu(data: bytearray) -> int:
    """Byte-level: POKé + 球 → 精灵球 (same or shorter)."""
    poke = bytes([0xCA, 0xC9, 0xC5, 0x1B])
    qiu = encode_text_safe("球")[0]
    qiu = qiu[:-1] if qiu.endswith(b"\xff") else qiu
    jing = encode_text_safe("精灵球")[0]
    jing = jing[:-1] if jing.endswith(b"\xff") else jing
    n = 0
    i = 0
    while True:
        j = data.find(poke, i)
        if j < 0:
            break
        # POKé球
        if data[j + 4 : j + 4 + len(qiu)] == qiu:
            old_len = 4 + len(qiu)
            if len(jing) <= old_len:
                data[j : j + old_len] = jing + b"\x00" * (old_len - len(jing))
                n += 1
                i = j + old_len
                continue
        # POKé + 00 + 球
        if data[j + 4] == 0x00 and data[j + 5 : j + 5 + len(qiu)] == qiu:
            old_len = 5 + len(qiu)
            if len(jing) <= old_len:
                data[j : j + old_len] = jing + b"\x00" * (old_len - len(jing))
                n += 1
                i = j + old_len
                continue
        # POKé BALL still english (BC BB C6 C6 = BALL)
        if data[j + 4 : j + 9] == bytes([0x00, 0xBC, 0xBB, 0xC6, 0xC6]) or data[
            j + 4 : j + 8
        ] == bytes([0xBC, 0xBB, 0xC6, 0xC6]):
            start = j
            # include optional space and S
            end = j + 4
            if data[end] == 0x00:
                end += 1
            if data[end : end + 4] == bytes([0xBC, 0xBB, 0xC6, 0xC6]):
                end += 4
                if data[end] == 0xCD:  # S
                    end += 1
            old_len = end - start
            if len(jing) <= old_len:
                data[start:end] = jing + b"\x00" * (old_len - len(jing))
                n += 1
                i = end
                continue
        i = j + 1
    print(f"raw POKé+球/BALL fixes={n}")
    return n


def fix_ac_junk_in_translated(data: bytearray, golden: bytes) -> int:
    """Strings that are partially CN but contain 0xAC runs (shown as ??)."""
    n = 0
    for start, end in [(0x270000, 0x2B0000)]:
        off = start
        while off < end:
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= end or eos - off > 350 or eos - off < 12:
                off += 1
                continue
            slot = bytes(data[off : eos + 1])
            if slot.count(0xAC) < 2:
                off = eos + 1
                continue
            en = decode_bytes(golden[off : eos + 1])
            if not any(c.isalpha() for c in en):
                off = eos + 1
                continue
            # Prefer HAND
            if off in HAND:
                off = eos + 1
                continue
            # If already mostly Chinese except AC junk, rewrite from scrubbed EN
            # Detect: has CJK lead-ish and AC
            has_cjk = any(
                b in (0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E)
                for b in slot[:30]
            )
            if not has_cjk:
                off = eos + 1
                continue
            zh = scrub_en_to_zh(en)
            # Only auto-apply for early rival/mom style short-enough lines we can hand later
            # For now: strip AC by full rewrite if we have enough CJK in scrub... scrub alone may be EN
            # Better: restore golden then leave for HAND — no, user wants fix
            # Use simple dictionary translations for common patterns
            zh2 = auto_translate_common(en)
            if zh2 and put(data, golden, off, zh2) == "ok":
                n += 1
            off = eos + 1
    print(f"AC-junk rewritten={n}")
    return n


def auto_translate_common(en: str) -> str | None:
    """Very small pattern set for early mixed lines with ?? junk."""
    # Only return if we produce clear Chinese
    templates = [
        (
            r"(?i)Hey, it's \{FD:01\}!.*Dad gave you a POK",
            HAND[0x27AAF4],
        ),
        (
            r"(?i)Oh, hi, \{FD:01\}\{FD:05\}!.*dad gave you",
            HAND[0x27A904],
        ),
    ]
    for pat, zh in templates:
        if re.search(pat, en, re.S):
            return zh
    return None


def scan_still_english_early(data: bytearray, golden: bytes) -> list[tuple[int, str]]:
    """Find early strings still mostly English (for report + auto hand candidates)."""
    hits = []
    off = 0x276000
    while off < 0x27C000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0x27C000 or eos - off > 300 or eos - off < 20:
            off += 1
            continue
        en = decode_bytes(golden[off : eos + 1])
        if not re.search(r"[A-Za-z]{4,}", en):
            off = eos + 1
            continue
        slot = bytes(data[off : eos + 1])
        latin = sum(1 for b in slot if 0xBB <= b <= 0xEE)
        if latin >= 30:
            hits.append((off, en[:100].replace("\n", "/")))
        off = eos + 1
    return hits


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    print("=== HAND ===")
    for off, zh in HAND.items():
        put(data, golden, off, zh)

    print("=== raw POKé+球 ===")
    fix_raw_poke_qiu(data)

    print("=== AC junk ===")
    fix_ac_junk_in_translated(data, golden)

    # Extra early EN leftovers around rival battle / route 103
    EXTRA = {
        0x27A9D4: (
            "小遥：我想我明白爸爸为什么\n会这么看好你了。{WAIT_CLEAR}"
            "你才刚拿到宝可梦，\n就已经这么强了。{WAIT_CLEAR}"
            "你一定会成为厉害的训练家！"
        ),
        0x27AB9F: (
            "小悠：我好像懂了。\n我懂爸爸为什么会盯上你了。{WAIT_SCROLL}"
            "你才刚开始，就已经这么强。{WAIT_CLEAR}"
            "继续加油吧。"
        ),
    }
    # Only apply if still English
    print("=== EXTRA early ===")
    for off, zh in EXTRA.items():
        eos = golden.find(b"\xff", off)
        slot = bytes(data[off : eos + 1])
        latin = sum(1 for b in slot if 0xBB <= b <= 0xEE)
        if latin >= 20:
            put(data, golden, off, zh)
        else:
            print(f"  skip {off:08X} already cn-ish lat={latin}")

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("D1D2D3D4D5D6D7D8E1E2E3E4E5E6E7E8")

    OUT.write_bytes(data)
    ROM.write_bytes(data)

    print("=== verify ===")
    for off in (0x27A904, 0x27AAF4, 0x281FB5, 0x2B2868):
        eos = golden.find(b"\xff", off)
        slot = bytes(data[off : eos + 1])
        latin = sum(1 for b in slot if 0xBB <= b <= 0xEE)
        ac = slot.count(0xAC)
        print(f"  {off:08X} latin={latin} ac={ac} ff@{slot.find(0xff)} head={slot[:16].hex()}")

    # remaining POKé+球
    poke = bytes([0xCA, 0xC9, 0xC5, 0x1B])
    qiu = encode_text_safe("球")[0][:-1]
    left = 0
    i = 0
    while True:
        j = data.find(poke, i)
        if j < 0:
            break
        if data[j + 4 : j + 4 + len(qiu)] == qiu:
            left += 1
        i = j + 1
    print(f"remaining POKé+球={left}")

    hits = scan_still_english_early(data, golden)
    print(f"early still-EN count={len(hits)}")
    for off, en in hits[:20]:
        print(f"  {off:08X} {en}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
