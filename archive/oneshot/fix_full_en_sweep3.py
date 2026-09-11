#!/usr/bin/env python3
"""Comprehensive EN→CN apply: item descs (berries/food), map dialogues via locale/cache."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe, load_charmap  # noqa: E402
from fill_and_apply_remaining import quality_ok, scrub, CACHE  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"
LOCALE = ROOT / "locale" / "zh_CN" / "all_en_zh.jsonl"

SKIP = [
    (0x279E71, 0x27A0D5),
    (0x2972B0, 0x297360),
    (0xFFFB50, 0xFFFC00),
]

# ---- Berry / hold-item / heal description templates ----
DESC_TEMPLATES: list[tuple[re.Pattern[str], str]] = [
    # Food / drinks
    (
        re.compile(r"(?is)^A sweet chocolate\nthat restores HP\nby (\d+) points\.$"),
        "能回复{0}点HP的\n甜巧克力。",
    ),
    (
        re.compile(r"(?is)^A very sweet drink\nthat restores HP\nby (\d+) points\.$"),
        "能回复{0}点HP的\n非常甜的饮料。",
    ),
    (
        re.compile(r"(?is)^A mineral water\nthat restores HP\nby (\d+) points\.$"),
        "能回复{0}点HP的\n矿泉水。",
    ),
    (
        re.compile(r"(?is)^A fizzy soda drink\nthat restores HP\nby (\d+) points\.$"),
        "能回复{0}点HP的\n汽水。",
    ),
    (
        re.compile(r"(?is)^A nutritious milk\nthat restores HP\nby (\d+) points\.$"),
        "能回复{0}点HP的\n营养牛奶。",
    ),
    (
        re.compile(r"(?is)^A bitter root\nthat restores HP\nby (\d+) points\.$"),
        "能回复{0}点HP的\n苦根。",
    ),
    (
        re.compile(r"(?is)^A bitter powder\nthat heals all\nstatus problems\.$"),
        "能治愈所有异常\n状态的苦粉末。",
    ),
    (
        re.compile(r"(?is)^A very bitter herb\nthat revives a\nfainted Pok[eé]mon\.$"),
        "能让濒死宝可梦\n复活的苦药草。",
    ),
    (
        re.compile(r"(?is)^A tasty snack that\nrestores HP by\n(\d+) points\.$"),
        "能回复{0}点HP的\n美味零食。",
    ),
    (
        re.compile(r"(?is)^Heals a poisoned\nPok[eé]mon\.$"),
        "治愈中毒的宝可梦。",
    ),
    (
        re.compile(r"(?is)^Heals a burned\nPok[eé]mon\.$"),
        "治愈灼伤的宝可梦。",
    ),
    (
        re.compile(r"(?is)^Awakens a sleeping\nPok[eé]mon\.$"),
        "唤醒睡眠中的宝可梦。",
    ),
    (
        re.compile(r"(?is)^Defrosts a frozen\nPok[eé]mon\.$"),
        "解除冰冻的宝可梦。",
    ),
    (
        re.compile(r"(?is)^Heals a paralyzed\nPok[eé]mon\.$"),
        "治愈麻痹的宝可梦。",
    ),
    (
        re.compile(r"(?is)^Cures confusion\.$"),
        "治愈混乱状态。",
    ),
    (
        re.compile(r"(?is)^A medicine that\nrestores HP by\n(\d+) points\.$"),
        "能回复{0}点HP的\n伤药。",
    ),
    (
        re.compile(r"(?is)^A spray-type medicine\nfor treating wounds\.\nIt restores the HP of\none Pok[eé]mon by\n(\d+) points\.$"),
        "喷雾式伤药。\n能回复一只宝可梦\n{0}点HP。",
    ),
    (
        re.compile(r"(?is)^A medicine that\nfully restores the\nHP of a Pok[eé]mon\.$"),
        "能让宝可梦的HP\n完全回复的药。",
    ),
    (
        re.compile(r"(?is)^A medicine that\nrestores the PP of\nall the moves of a\nPok[eé]mon by (\d+)\.$"),
        "能让宝可梦所有招式\n的PP各回复{0}的药。",
    ),
    (
        re.compile(r"(?is)^A medicine that\nfully restores the\nPP of a single\nselected move\.$"),
        "能让一个招式的\nPP完全回复的药。",
    ),
    (
        re.compile(r"(?is)^A medicine that\nfully restores the\nPP of all of a\nPok[eé]mon's moves\.$"),
        "能让宝可梦所有招式\n的PP完全回复的药。",
    ),
    (
        re.compile(r"(?is)^A medicine that\nrevives a fainted\nPok[eé]mon\.$"),
        "能让濒死的宝可梦\n复活的药。",
    ),
    (
        re.compile(r"(?is)^A medicine that\nrevives a fainted\nPok[eé]mon and fully\nrestores its HP\.$"),
        "能让濒死宝可梦复活\n并完全回复HP的药。",
    ),
    # Berry hold effects (common Gen3 patterns)
    (
        re.compile(
            r"(?is)^A hold item that\nrestores HP if the\nholder is poisoned,\nparalyzed, or burned\.$"
        ),
        "携带后，中毒、麻痹\n或灼伤时回复HP。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nrestores HP if\nhit by a super-\neffective move\.$"),
        "携带后，被效果绝佳\n的招式击中时回复HP。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nraises Attack when\nHP is low\.$"),
        "携带后，HP变少时\n提高攻击。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nraises Defense when\nHP is low\.$"),
        "携带后，HP变少时\n提高防御。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nraises Speed when\nHP is low\.$"),
        "携带后，HP变少时\n提高速度。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nraises Sp\. Atk when\nHP is low\.$"),
        "携带后，HP变少时\n提高特攻。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nraises Sp\. Def when\nHP is low\.$"),
        "携带后，HP变少时\n提高特防。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nraises critical-hit\nratio when HP is low\.$"),
        "携带后，HP变少时\n提高击中要害率。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nsharply raises a\nstat when HP is low\.$"),
        "携带后，HP变少时\n大幅提高一项能力。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nrestores HP in a\npinch, but confuses\nif it dislikes the\ntaste\.$"),
        "携带后，危机时回复\nHP，但不喜欢味道时\n会混乱。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nrestores HP but\nmay confuse if\ndisliked\.$"),
        "携带后回复HP，但\n若不喜欢味道可能混乱。",
    ),
    (
        re.compile(r"(?is)^A Berry to be used in cooking\.$"),
        "做料理时使用的树果。",
    ),
    (
        re.compile(r"(?is)^A hold item that\ncures poison\.$"),
        "携带后能治愈中毒。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nawakes from sleep\.$"),
        "携带后能从睡眠中醒来。",
    ),
    (
        re.compile(r"(?is)^A hold item that\ncures a burn\.$"),
        "携带后能治愈灼伤。",
    ),
    (
        re.compile(r"(?is)^A hold item that\ndefrosts\.$"),
        "携带后能解除冰冻。",
    ),
    (
        re.compile(r"(?is)^A hold item that\ncures paralysis\.$"),
        "携带后能治愈麻痹。",
    ),
    (
        re.compile(r"(?is)^A hold item that\ncures confusion\.$"),
        "携带后能治愈混乱。",
    ),
    (
        re.compile(r"(?is)^A hold item that\ncures any status\nproblem\.$"),
        "携带后能治愈所有\n异常状态。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nrestores HP\.$"),
        "携带后能回复HP。",
    ),
    (
        re.compile(r"(?is)^A hold item that\nrestores PP\.$"),
        "携带后能回复PP。",
    ),
    (
        re.compile(r"(?is)^Works well if\nused in a\ndark place\.$"),
        "在黑暗的地方\n使用效果很好。",
    ),
    (
        re.compile(r"(?is)^Works well if\nused on the\nfirst turn\.$"),
        "在第一回合使用\n效果很好。",
    ),
    (
        re.compile(r"(?is)^.*cures all the\nstatus problems of\none POK[EÉ]MON\.$"),
        "能治愈一只宝可梦的\n所有异常状态。",
    ),
    (
        re.compile(r"(?is)^A fertilizer that\nups the life time\nof Berry trees\.$"),
        "延长树果树寿命的肥料。",
    ),
    (
        re.compile(r"(?is)^A fertilizer that\nups the chance of\nBerry mutations\.$"),
        "提高树果突变几率的肥料。",
    ),
]

# Exact EN→ZH for common short descs / names missed earlier
EXACT: dict[str, str] = {
    "Chocolate": "巧克力",
    "Sweet Heart": "甜心苹果",
    "Lava Cookie": "釜炎仙贝",
    "Old Gateau": "古早糕点",
    "Rage Candy Bar": "愤怒馒头",
    "Casteliacone": "飞云冰淇淋",
    "Lumiose Galette": "密阿雷格雷派饼",
    "Shalour Sable": "娑罗沙布蕾",
    "Big Malasada": "大马拉萨达",
    "Pewter Crunchies": "深灰米果",
    "Jubilife Muffin": "祝庆松饼",
    "Oran Berry": "橙橙果",
    "Sitrus Berry": "文柚果",
    "Leppa Berry": "苹野果",
    "Lum Berry": "木子果",
}


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
            data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))
            return True
        text = text[:-1]
    return False


def looks_dialogue(en: str) -> bool:
    plain = re.sub(r"\{[^}]+\}", "", en)
    if len(plain) < 12:
        return False
    letters = sum(c.isalpha() for c in plain)
    if letters < 10:
        return False
    # Reject control-soup / pointer garbage
    ctrl = len(re.findall(r"\{[0-9A-Fa-f]{2}\}", en))
    if ctrl > 6:
        return False
    words = re.findall(r"[A-Za-z]{3,}", plain)
    if len(words) < 2:
        return False
    # Prefer sentences with space
    if " " not in plain and "\n" not in en:
        return False
    return True


def load_locale() -> dict[str, str]:
    by: dict[str, str] = {}
    if not LOCALE.exists():
        return by
    for line in LOCALE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        en = r.get("en") or ""
        zh = scrub(r.get("zh") or "")
        if en and quality_ok(en, zh):
            by[en] = zh
    return by


def apply_templates(data: bytearray, golden: bytes) -> int:
    n = 0
    off = 0xF8B000
    while off < 0xF9A000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0xF9A000 or eos - off > 160 or eos - off < 10:
            off += 1
            continue
        en = decode_bytes(golden[off : eos + 1])
        zh = None
        if en in EXACT:
            zh = EXACT[en]
        else:
            for pat, tmpl in DESC_TEMPLATES:
                m = pat.match(en)
                if m:
                    zh = tmpl.format(*m.groups()) if m.groups() else tmpl
                    break
        if zh and put(data, golden, off, zh):
            n += 1
        off = eos + 1
    return n


def apply_exact_names(data: bytearray, golden: bytes) -> int:
    """Patch remaining English item names anywhere in name bank."""
    n = 0
    off = 0xF9B000
    while off < 0xFA2000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0xFA2000 or eos - off > 40 or eos - off < 3:
            off += 1
            continue
        en = decode_bytes(golden[off : eos + 1]).strip()
        # keep leading spaces layout for padded names
        raw = decode_bytes(golden[off : eos + 1])
        key = raw.strip()
        if key in EXACT:
            pad = len(raw) - len(raw.lstrip(" "))
            zh = (" " * pad) + EXACT[key] if pad else EXACT[key]
            if put(data, golden, off, zh):
                n += 1
        off = eos + 1
    return n


def apply_locale_dialogues(data: bytearray, golden: bytes, locale: dict[str, str], cache: dict[str, str]) -> int:
    n = 0
    for a, b in [(0x260000, 0x360000), (0xFF8000, 0x1000000), (0x1000000, 0x1030000)]:
        off = a
        while off < b:
            if in_skip(off):
                off += 1
                continue
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= b or eos - off > 180 or eos - off < 16:
                off += 1
                continue
            # only untouched or still-EN slots (same as golden)
            if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
                off = eos + 1
                continue
            en = decode_bytes(golden[off : eos + 1])
            if not looks_dialogue(en):
                off = eos + 1
                continue
            zh = locale.get(en) or scrub(cache.get(en, ""))
            if not quality_ok(en, zh):
                off = eos + 1
                continue
            fds = re.findall(r"\{FD:[0-9A-Fa-f]{2}\}", en)
            if any(t not in zh for t in fds):
                off = eos + 1
                continue
            # preserve WAIT tokens if present in EN
            for tok in ("{WAIT_CLEAR}", "{WAIT_SCROLL}"):
                if tok in en and tok not in zh:
                    # soft fail — skip unsafe
                    off = eos + 1
                    break
            else:
                if put(data, golden, off, zh):
                    n += 1
                off = eos + 1
                continue
            continue
    return n


def decode_chs(data: bytes, to_str: dict[bytes, str], max_len: int = 80) -> str:
    parts: list[str] = []
    i = 0
    while i < min(len(data), max_len):
        if data[i] == 0xFF:
            break
        if i + 1 < len(data) and data[i : i + 2] in to_str:
            parts.append(to_str[data[i : i + 2]])
            i += 2
            continue
        if data[i : i + 1] in to_str:
            parts.append(to_str[data[i : i + 1]])
            i += 1
            continue
        parts.append(f"[{data[i]:02X}]")
        i += 1
    return "".join(parts)


def count_remaining(data: bytearray, golden: bytes) -> dict[str, int]:
    out = {"map_dlg": 0, "item_desc": 0}
    for a, b, key in [(0x260000, 0x360000, "map_dlg"), (0xF8B000, 0xF9A000, "item_desc")]:
        off = a
        while off < b:
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= b or eos - off > 160 or eos - off < 12:
                off += 1
                continue
            if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
                off = eos + 1
                continue
            en = decode_bytes(golden[off : eos + 1])
            if looks_dialogue(en) if key == "map_dlg" else looks_dialogue(en) or len(en) > 15:
                if key == "item_desc":
                    plain = re.sub(r"\{[^}]+\}", "", en)
                    if sum(c.isalpha() for c in plain) >= 10 and " " in plain:
                        out[key] += 1
                else:
                    out[key] += 1
            off = eos + 1
    return out


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    locale = load_locale()
    cache: dict[str, str] = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    print(f"locale usable: {len(locale)} cache: {len(cache)}")
    print("1) item desc templates…")
    n1 = apply_templates(data, golden)
    print(f"   {n1}")
    print("2) exact item names…")
    n2 = apply_exact_names(data, golden)
    print(f"   {n2}")
    print("3) locale/cache dialogues…")
    n3 = apply_locale_dialogues(data, golden, locale, cache)
    print(f"   {n3}")

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("778899AABBCCDDEEFF00112233445566")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    _, to_str = load_charmap()
    off = 0xF8BB19
    eos = golden.find(b"\xff", off)
    print("choco CHS:", decode_chs(bytes(data[off : eos + 1]), to_str))
    rem = count_remaining(data, golden)
    print("remaining approx:", rem)
    print(f"total applied this run: {n1 + n2 + n3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
