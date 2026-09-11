#!/usr/bin/env python3
"""Fix DAD Rustboro gym line + remaining mixed EN dialogues; push-ready."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe, load_charmap  # noqa: E402
from fill_and_apply_remaining import CACHE, quality_ok, scrub, translate_one  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"

HAND: dict[int, str] = {
    0x295324: (
        "爸爸:嗯?你不是要去\n卡那兹市的宝可梦道馆吗?{WAIT_CLEAR}"
        "和一个新手训练家对战\n对我来说毫无挑战。{WAIT_CLEAR}"
        "{FD:01},等你变得更强以后\n再来挑战我吧。{WAIT_CLEAR}"
        "当你能拿出四枚道馆徽章时,\n我再和你对战,好吗?"
    ),
    0x2956FA: (
        "爸爸:有了那枚徽章,\n你所有宝可梦的防御都会提高。{WAIT_CLEAR}"
        "学会秘传招式冲浪的宝可梦\n也能在水上移动了。"
    ),
    0x295014: (
        "爸爸:嗯。我也给你一个精灵球。\n加油吧!{WAIT_CLEAR}"
        "沃利得到了精灵球!"
    ),
    0x294F58: (
        "爸爸:{FD:01},你听到了吧?{WAIT_CLEAR}"
        "跟沃利一起去,确保他\n安全地捉到宝可梦。"
    ),
}

PLACE = [
    (r"PETALBURG", "橙华"),
    (r"RUSTBORO CITY", "卡那兹市"),
    (r"RUSTBORO", "卡那兹"),
    (r"SLATEPORT", "凯那"),
    (r"LILYCOVE", "琉璃市"),
    (r"DEWFORD", "武斗"),
    (r"VERDANTURF", "秋叶镇"),
    (r"MAUVILLE", "紫堇"),
    (r"OLDALE", "古辰"),
    (r"LITTLEROOT", "未白"),
    (r"TEAM AQUA", "水舰队"),
    (r"TEAM MAGMA", "熔岩队"),
    (r"POK[EÉ]MON", "宝可梦"),
    (r"TRAINERS?", "训练家"),
    (r"\bGYM\b", "道馆"),
    (r"\bDAD\b", "爸爸"),
    (r"\bWALLY\b", "沃利"),
    (r"BRENDAN", "小悠"),
    (r"\bMAY\b", "小遥"),
    (r"PROF\. BIRCH", "小田卷博士"),
    (r"STEVEN", "大吾"),
]


def place_scrub(zh: str) -> str:
    out = scrub(zh)
    for a, b in PLACE:
        out = re.sub(a, b, out, flags=re.IGNORECASE)
    out = re.sub(r"(?i)poke?qu\w*", "宝可梦", out)
    return out


def tokens_ok(en: str, zh: str) -> bool:
    return all(
        t in zh
        for t in re.findall(r"\{(?:FD|FC):[0-9A-Fa-f]{2}\}|\{WAIT_(?:CLEAR|SCROLL)\}", en)
    )


def reinject(en: str, zh: str) -> str:
    out = place_scrub(zh)
    for tok in re.findall(r"\{(?:FD|FC):[0-9A-Fa-f]{2}\}", en):
        if tok not in out:
            # try replace common MT damage to FD
            out = out.replace("?败", tok).replace("?()", tok)
            if tok not in out:
                out = tok + out
    for w in re.findall(r"\{WAIT_(?:CLEAR|SCROLL)\}", en):
        if w in out:
            continue
        m = re.search(r"[。！？…]", out)
        if m:
            i = m.end()
            out = out[:i] + w + out[i:]
        else:
            out += w
    return out


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
        if data[i] in (0xFA, 0xFB):
            parts.append("{WAIT_SCROLL}" if data[i] == 0xFA else "{WAIT_CLEAR}")
            i += 1
            continue
        if data[i] == 0xFD and i + 1 < len(data):
            parts.append(f"{{FD:{data[i+1]:02X}}}")
            i += 2
            continue
        pair = bytes(data[i : i + 2])
        one = bytes(data[i : i + 1])
        if i + 1 < len(data) and pair in to_str:
            s2 = to_str[pair]
            s1 = to_str.get(one)
            if s1 and s1.isascii() and not s2.isascii():
                parts.append(s1)
                i += 1
                continue
            parts.append(s2)
            i += 2
            continue
        if one in to_str:
            parts.append(to_str[one])
            i += 1
            continue
        parts.append("?")
        i += 1
    return "".join(parts)


def still_mostly_en(chs: str) -> bool:
    plain = re.sub(r"\{[^}]+\}", "", chs)
    letters = sum(c.isalpha() and c.isascii() for c in plain)
    cjk = sum(1 for c in plain if "\u4e00" <= c <= "\u9fff")
    words = [w.lower() for w in re.findall(r"[A-Za-z]{3,}", plain)]
    if letters < 10 or len(words) < 2:
        return False
    common = {
        "the",
        "you",
        "are",
        "and",
        "that",
        "this",
        "have",
        "will",
        "your",
        "going",
        "dad",
        "gym",
        "with",
        "from",
        "what",
        "when",
        "aren",
        "pokemon",
        "trainer",
        "battle",
        "listen",
        "think",
        "there",
        "these",
        "those",
        "just",
        "about",
        "after",
        "before",
        "uncle",
        "brendan",
        "steven",
        "wally",
        "press",
        "button",
        "machine",
        "fossils",
        "painting",
        "planet",
        "league",
        "elite",
        "catching",
        "handling",
        "registered",
    }
    if not any(w in common for w in words):
        if "宝可梦" in chs and letters >= 12:
            return True
        return False
    return letters > max(cjk, 6)


def collect(data: bytearray, golden: bytes, to_str: dict[bytes, str]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    off = 0x250000
    while off < 0x360000:
        eos = golden.find(b"\xff", off, min(off + 220, 0x360000))
        if eos < 0:
            nxt = golden.find(b"\xff", off, 0x360000)
            off = nxt + 1 if nxt >= 0 else 0x360000
            continue
        if eos - off < 24:
            off = eos + 1
            continue
        en = decode_bytes(golden[off : eos + 1])
        plain = re.sub(r"\{[^}]+\}", "", en)
        if sum(c.isalpha() for c in plain) < 18:
            off = eos + 1
            continue
        if len(re.findall(r"\{[0-9A-Fa-f]{2}\}", en)) > 6:
            off = eos + 1
            continue
        cur = decode_chs(bytes(data[off : eos + 1]), to_str)
        if still_mostly_en(cur):
            out.append((off, en))
        off = eos + 1
    return out


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    _, to_str = load_charmap()
    cache: dict[str, str] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    print("1) hand DAD lines", flush=True)
    for off, zh in HAND.items():
        ok = put(data, golden, off, zh)
        eos = golden.find(b"\xff", off)
        print(f"  {off:08X} {ok} {decode_chs(bytes(data[off:eos+1]), to_str)[:70]!r}")

    print("2) scan leftovers…", flush=True)
    cands = collect(data, golden, to_str)
    print(f"   candidates {len(cands)}", flush=True)
    applied = mt = 0
    for i, (off, en) in enumerate(cands):
        if off in HAND:
            continue
        zh = ""
        cached = place_scrub(cache.get(en, ""))
        if cached and quality_ok(en, cached) and tokens_ok(en, cached):
            zh = cached
        else:
            raw = translate_one(en, "bing")
            if raw:
                zh = reinject(en, place_scrub(raw))
                cache[en] = zh
                mt += 1
                time.sleep(0.05)
        if not zh or not quality_ok(en, zh) or not tokens_ok(en, zh):
            continue
        if put(data, golden, off, zh):
            applied += 1
            if applied <= 8 or applied % 40 == 0:
                print(f"  ok {applied} {off:08X} {en[:42]!r}", flush=True)
        if (i + 1) % 40 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            OUT.write_bytes(data)
            print(f"  progress {i+1}/{len(cands)} applied={applied}", flush=True)

    # re-apply hand (MT may have hit same offs before hand? hand was first)
    for off, zh in HAND.items():
        put(data, golden, off, zh)

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("445566778899AABBCCDDEEFF00112233")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    off = 0x295324
    print("VERIFY DAD", decode_chs(bytes(data[off : golden.find(b"\xff", off) + 1]), to_str))
    left = collect(data, golden, to_str)
    print(f"done applied={applied} mt={mt} remaining~{len(left)}")
    for o, e in left[:8]:
        print(f"  rem {o:08X} {e[:70]!r}")
    return 0


if __name__ == "__main__":
    # fix accidental walrus in print - rewrite clean
    raise SystemExit(main())
