#!/usr/bin/env python3
"""Fast continue: remaining item descs + leftover dialogues via Bing MT."""
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
from fix_full_en_sweep4 import translate_item_desc  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"
SKIP = [(0x279E71, 0x27A0D5), (0x2972B0, 0x297360), (0xFFFB50, 0xFFFC00)]

PLACE = [
    (r"PETALBURG CITY", "橙华市"),
    (r"PETALBURG", "橙华"),
    (r"SLATEPORT", "凯那"),
    (r"MAUVILLE", "紫堇"),
    (r"RUSTBORO", "卡那兹"),
    (r"DEWFORD", "武斗"),
    (r"OLDALE", "古辰"),
    (r"LITTLEROOT", "未白"),
    (r"TEAM AQUA", "水舰队"),
    (r"TEAM MAGMA", "熔岩队"),
    (r"POK[EÉ]MON", "宝可梦"),
    (r"TRAINERS?", "训练家"),
]

EXTRA = [
    (
        re.compile(r"(?is)^A key that opens a door\ninside the Abandoned Ship\.$"),
        "能打开弃船内\n某扇门的钥匙。",
    ),
    (
        re.compile(r"(?is)^Boosts Defense on Electric\nTerrain, but only one time\.$"),
        "在电气场地上提高防御，\n但仅触发一次。",
    ),
    (
        re.compile(r"(?is)^Boosts Sp\. Def\. on Psychic\nTerrain, but only one time\.$"),
        "在精神场地上提高特防，\n但仅触发一次。",
    ),
    (
        re.compile(r"(?is)^Boosts Sp\. Def\. on Misty\nTerrain, but only one time\.$"),
        "在薄雾场地上提高特防，\n但仅触发一次。",
    ),
    (
        re.compile(r"(?is)^Boosts Attack on Grassy\nTerrain, but only one time\.$"),
        "在青草场地上提高攻击，\n但仅触发一次。",
    ),
]


def in_skip(off: int) -> bool:
    return any(a <= off < b for a, b in SKIP)


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


def place_scrub(zh: str) -> str:
    out = scrub(zh)
    for a, b in PLACE:
        out = re.sub(a, b, out, flags=re.IGNORECASE)
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
            out += tok
    for w in re.findall(r"\{WAIT_(?:CLEAR|SCROLL)\}", en):
        if w in out:
            continue
        m = re.search(r"[。！？…]", out)
        out = (out[: m.end()] + w + out[m.end()]) if m else out + w
    return out


def looks_dialogue(en: str) -> bool:
    plain = re.sub(r"\{[^}]+\}", "", en)
    if sum(c.isalpha() for c in plain) < 16:
        return False
    if len(re.findall(r"\{[0-9A-Fa-f]{2}\}", en)) > 4:
        return False
    if len(re.findall(r"[A-Za-z]{3,}", plain)) < 3:
        return False
    if " " not in plain and "\n" not in en:
        return False
    return True


def translate_desc(en: str) -> str | None:
    zh = translate_item_desc(en)
    if zh:
        return zh
    for pat, tmpl in EXTRA:
        if pat.match(en.strip()):
            return tmpl
    return None


def collect_fast(
    data: bytearray, golden: bytes, a: int, b: int, min_len: int, max_len: int, kind: str
) -> list[tuple[int, str]]:
    """Walk string table by jumping to next FF; skip huge gaps quickly."""
    out: list[tuple[int, str]] = []
    off = a
    while off < b:
        if in_skip(off):
            off = next((x[1] for x in SKIP if x[0] <= off < x[1]), off + 1)
            continue
        eos = golden.find(b"\xff", off, min(off + max_len + 1, b))
        if eos < 0:
            # jump forward to next FF in bank
            nxt = golden.find(b"\xff", off, b)
            off = (nxt + 1) if nxt >= 0 else b
            continue
        length = eos - off
        if length < min_len:
            off = eos + 1
            continue
        if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
            off = eos + 1
            continue
        en = decode_bytes(golden[off : eos + 1])
        ok = False
        if kind == "item":
            ok = sum(c.isalpha() for c in en) >= 12 and en.count("{") <= 4
        else:
            ok = looks_dialogue(en)
        if ok:
            out.append((off, en))
        off = eos + 1
    return out


def apply_list(
    data: bytearray,
    golden: bytes,
    cands: list[tuple[int, str]],
    cache: dict[str, str],
    label: str,
    use_tmpl: bool,
) -> tuple[int, int]:
    tmpl = mt = applied = 0
    for i, (off, en) in enumerate(cands):
        zh = translate_desc(en) if use_tmpl else None
        if zh:
            if put(data, golden, off, zh):
                tmpl += 1
                applied += 1
            continue
        cached = place_scrub(cache.get(en, ""))
        if cached and quality_ok(en, cached):
            zh = reinject(en, cached) if not tokens_ok(en, cached) else cached
        else:
            raw = translate_one(en, "bing")
            if not raw:
                continue
            zh = reinject(en, place_scrub(raw))
            cache[en] = zh
            mt += 1
            time.sleep(0.07)
        if not zh or not quality_ok(en, zh) or not tokens_ok(en, zh):
            continue
        if put(data, golden, off, zh):
            applied += 1
            if applied <= 6 or applied % 25 == 0:
                print(f"  [{label}] applied={applied} {off:08X} {en[:40]!r}", flush=True)
        if (i + 1) % 35 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            OUT.write_bytes(data)
            print(f"  [{label}] {i+1}/{len(cands)} applied={applied} mt={mt}", flush=True)
    return tmpl, mt


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
        if i + 1 < len(data) and data[i : i + 2] in to_str:
            s2 = to_str[data[i : i + 2]]
            s1 = to_str.get(data[i : i + 1])
            if s1 and s1.isascii() and not s2.isascii():
                parts.append(s1)
                i += 1
                continue
            parts.append(s2)
            i += 2
            continue
        if data[i : i + 1] in to_str:
            parts.append(to_str[data[i : i + 1]])
            i += 1
            continue
        parts.append(f"[{data[i]:02X}]")
        i += 1
    return "".join(parts)


def main() -> int:
    print("loading…", flush=True)
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    cache: dict[str, str] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    print("scan items…", flush=True)
    items = collect_fast(data, golden, 0xF8B000, 0xF9A000, 15, 160, "item")
    print(f"item candidates: {len(items)}", flush=True)
    t1, m1 = apply_list(data, golden, items, cache, "item", True)
    print(f"item tmpl={t1} mt={m1}", flush=True)

    print("scan map…", flush=True)
    maps = collect_fast(data, golden, 0x260000, 0x360000, 16, 180, "map")
    print(f"map candidates: {len(maps)}", flush=True)
    t2, m2 = apply_list(data, golden, maps, cache, "map", False)
    print(f"map tmpl={t2} mt={m2}", flush=True)

    print("scan early map 0x25…", flush=True)
    maps0 = collect_fast(data, golden, 0x250000, 0x260000, 16, 180, "map")
    print(f"early map candidates: {len(maps0)}", flush=True)
    t0, m0 = apply_list(data, golden, maps0, cache, "early", False)

    print("scan battle/menu…", flush=True)
    ui = collect_fast(data, golden, 0xFF8000, 0x1030000, 20, 160, "map")
    print(f"ui candidates: {len(ui)}", flush=True)
    t3, m3 = apply_list(data, golden, ui, cache, "ui", False)

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("CCDDEEFF00112233445566778899AABB")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    items2 = collect_fast(data, golden, 0xF8B000, 0xF9A000, 15, 160, "item")
    maps2 = collect_fast(data, golden, 0x250000, 0x360000, 16, 180, "map")
    print(f"REMAINING item={len(items2)} map={len(maps2)}", flush=True)
    _, to_str = load_charmap()
    for lab, off in [("choco", 0xF8BB19), ("gym", 0x269ADC), ("soda", 0xF8B80B)]:
        eos = golden.find(b"\xff", off)
        print(lab, decode_chs(bytes(data[off : eos + 1]), to_str)[:70], flush=True)
    for o, e in items2[:3]:
        print("rem item", f"{o:08X}", e[:70], flush=True)
    for o, e in maps2[:3]:
        print("rem map", f"{o:08X}", e[:70], flush=True)
    print(f"early mt={m0} ui mt={m3}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
