#!/usr/bin/env python3
"""One-shot: fix cottage mix + remaining EN dialogues + reapply options/mode UI."""
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

HAND: dict[int, str] = {}  # filled after scan

PLACE = [
    (r"MR\.?\s*BRINEY", "哈奇老人"),
    (r"BRINEY", "哈奇"),
    (r"PEEKO", "小皮"),
    (r"PETALBURG WOODS", "橙华森林"),
    (r"PETALBURG", "橙华"),
    (r"RUSTBORO", "卡那兹"),
    (r"SLATEPORT", "凯那"),
    (r"LILYCOVE", "琉璃"),
    (r"DEWFORD", "武斗"),
    (r"VERDANTURF", "秋叶"),
    (r"MAUVILLE", "紫堇"),
    (r"OLDALE", "古辰"),
    (r"LITTLEROOT", "未白"),
    (r"TEAM AQUA", "水舰队"),
    (r"TEAM MAGMA", "熔岩队"),
    (r"DEVON CORPORATION", "得文公司"),
    (r"RYDEL'?S?\s*CYCLES?", "洛迪的自行车店"),
    (r"POK[EÉ]MON", "宝可梦"),
    (r"TRAINERS?", "训练家"),
    (r"\bGYM\b", "道馆"),
    (r"\bMAY\b", "小遥"),
    (r"BRENDAN", "小悠"),
    (r"STEVEN", "大吾"),
    (r"PROF\.?\s*BIRCH", "小田卷博士"),
]


def place_scrub(zh: str) -> str:
    out = scrub(zh)
    for a, b in PLACE:
        out = re.sub(a, b, out, flags=re.IGNORECASE)
    out = re.sub(r"(?i)poke?qu\w*", "宝可梦", out)
    out = re.sub(r"宝可梦\s*c梦", "宝可梦", out)
    out = re.sub(r"阿\[63\]可梦", "宝可梦", out)
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
            out = out.replace("?败", tok).replace("?()", tok).replace("?À?", tok)
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


def still_bad(chs: str, en: str) -> bool:
    """True if current text still needs full CN rewrite."""
    plain = re.sub(r"\{[^}]+\}", "", chs)
    letters = sum(c.isalpha() and c.isascii() for c in plain)
    cjk = sum(1 for c in plain if "\u4e00" <= c <= "\u9fff")
    words = [w.lower() for w in re.findall(r"[A-Za-z]{3,}", plain)]
    if letters < 6:
        return False
    # mixed EN+CJK dialogue
    if cjk >= 1 and letters >= 8 and len(words) >= 1:
        return True
    # mostly EN dialogue
    common = {
        "the", "and", "you", "are", "that", "this", "have", "will", "your",
        "going", "with", "from", "what", "when", "cottage", "seaside", "alive",
        "briney", "still", "there", "these", "about", "after", "before",
        "pokemon", "trainer", "battle", "listen", "think", "painting",
        "corporation", "cycles", "batteries", "hostage", "pretty", "flies",
    }
    if letters >= 12 and letters > max(cjk * 2, 8) and (
        any(w in common for w in words) or "宝可梦" in chs
    ):
        return True
    return False


def looks_dialogue(en: str) -> bool:
    plain = re.sub(r"\{[^}]+\}", "", en)
    if sum(c.isalpha() for c in plain) < 16:
        return False
    if len(re.findall(r"\{[0-9A-Fa-f]{2}\}", en)) > 5:
        return False
    if len(re.findall(r"[A-Za-z]{3,}", plain)) < 3:
        return False
    if " " not in plain and "\n" not in en:
        return False
    return True


def collect(data: bytearray, golden: bytes, to_str: dict[bytes, str]) -> list[tuple[int, str, str]]:
    out: list[tuple[int, str, str]] = []
    for a, b in [(0x250000, 0x360000), (0xFF8000, 0x1030000)]:
        off = a
        while off < b:
            eos = golden.find(b"\xff", off, min(off + 220, b))
            if eos < 0:
                nxt = golden.find(b"\xff", off, b)
                off = nxt + 1 if nxt >= 0 else b
                continue
            if eos - off < 18:
                off = eos + 1
                continue
            en = decode_bytes(golden[off : eos + 1])
            if not looks_dialogue(en):
                off = eos + 1
                continue
            cur = decode_chs(bytes(data[off : eos + 1]), to_str)
            if still_bad(cur, en):
                out.append((off, en, cur))
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

    # known cottage / briney lines from golden search
    hand_extra = {
        # filled dynamically if found
    }
    off = 0x250000
    while off < 0x360000:
        eos = golden.find(b"\xff", off, min(off + 240, 0x360000))
        if eos < 0:
            nxt = golden.find(b"\xff", off, 0x360000)
            off = nxt + 1 if nxt >= 0 else 0x360000
            continue
        en = decode_bytes(golden[off : eos + 1])
        el = en.lower()
        if "seaside cottage" in el or ("cottage" in el and "alive" in el) or (
            "briney" in el and "alive" in el
        ):
            print(f"FOUND cottage {off:08X} {en[:100]!r}")
            print(f"  cur {decode_chs(bytes(data[off:eos+1]), to_str)[:100]!r}")
        off = eos + 1

    print("scanning leftovers…", flush=True)
    cands = collect(data, golden, to_str)
    print(f"candidates {len(cands)}", flush=True)
    # prefer cottage-like first
    cands.sort(key=lambda x: (0 if "cottage" in x[1].lower() or "briney" in x[1].lower() or "alive" in x[1].lower() else 1, x[0]))

    applied = mt = 0
    for i, (off, en, cur) in enumerate(cands):
        zh = ""
        cached = place_scrub(cache.get(en, ""))
        if cached and quality_ok(en, cached) and tokens_ok(en, cached):
            # reject if cache still mostly latin
            if still_bad(cached, en):
                cached = ""
            else:
                zh = cached
        if not zh:
            raw = translate_one(en, "bing")
            if raw:
                zh = reinject(en, place_scrub(raw))
                cache[en] = zh
                mt += 1
                time.sleep(0.045)
        if not zh or not quality_ok(en, zh) or not tokens_ok(en, zh):
            continue
        if still_bad(zh, en) and sum(c.isalpha() and c.isascii() for c in zh) > 20:
            continue
        if put(data, golden, off, zh):
            applied += 1
            if applied <= 10 or "cottage" in en.lower() or "alive" in en.lower() or applied % 50 == 0:
                print(f"  ok {applied} {off:08X} {en[:48]!r} -> {zh[:40]!r}", flush=True)
        if (i + 1) % 40 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            OUT.write_bytes(data)
            print(f"  progress {i+1}/{len(cands)} applied={applied}", flush=True)

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("778899AABBCCDDEEFF00112233445566")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    left = collect(data, golden, to_str)
    print(f"done applied={applied} mt={mt} remaining={len(left)}", flush=True)
    for o, e, c in left[:12]:
        print(f"  rem {o:08X} EN={e[:60]!r}")
        print(f"       CN={c[:60]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
