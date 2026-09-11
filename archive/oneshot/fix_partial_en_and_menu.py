#!/usr/bin/env python3
"""Fix partial-EN dialogues (POKéMON-only scrub) + broken start-menu labels."""
from __future__ import annotations

import json
import re
import struct
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
FREE_START = 0x01D9B5A8 + 0x30000
FREE_END = 0x01D9B5A8 + 0x264A58
CURSOR = ROOT / "work" / "free_cursor.txt"

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
    (r"\bGYM\b", "道馆"),
    (r"BATTLE TENT", "对战帐篷"),
    (r"BATTLE FRONTIER", "对战开拓区"),
]

# Start-menu labels: restore from golden then reloc ZH (BAG/DEX were smashed)
MENU_LABELS: list[tuple[str, str]] = [
    ("POKéDEX", "图鉴"),
    ("POKéMON", "宝可梦"),
    ("POKéNAV", "导航"),
    ("BAG", "背包"),
    ("SAVE", "保存"),
    ("OPTION", "选项"),
    ("EXIT", "退出"),
]


def place_scrub(zh: str) -> str:
    out = scrub(zh)
    for a, b in PLACE:
        out = re.sub(a, b, out, flags=re.IGNORECASE)
    # kill pokequ-style leftovers
    out = re.sub(r"(?i)poke?qu\w*", "宝可梦", out)
    out = re.sub(r"(?i)pok[eé]?去", "图鉴", out)
    out = re.sub(r"(?i)POK[EÉ]去", "图鉴", out)
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
        if m:
            i = m.end()
            out = out[:i] + w + out[i:]
        else:
            out = out + w
    return out


def put_inplace(data: bytearray, golden: bytes, off: int, zh: str) -> bool:
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


def find_ptrs(rom: bytes, offset: int) -> list[int]:
    out: list[int] = []
    for base in (0x08000000, 0x09000000):
        ptr = base + (offset & 0x00FFFFFF) if base == 0x09000000 else base + offset
        if base == 0x08000000:
            ptr = 0x08000000 + offset
        needle = struct.pack("<I", ptr)
        idx = 0
        while True:
            i = rom.find(needle, idx)
            if i < 0:
                break
            if i % 4 == 0:
                out.append(i)
            idx = i + 1
            if len(out) > 80:
                break
    return sorted(set(out))


def reloc_label(data: bytearray, free_at: int, off: int, zh: str) -> tuple[bool, int]:
    enc, miss = encode_text_safe(zh)
    if miss or not enc.endswith(b"\xff"):
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
    need = len(enc)
    if free_at + need > FREE_END:
        return False, free_at
    ptrs = find_ptrs(bytes(data), off)
    if not ptrs:
        # try inplace if fits golden slot
        return put_inplace(data, bytes(data), off, zh), free_at  # wrong - need golden
    new_off = free_at
    data[new_off : new_off + need] = enc
    free_at = (free_at + need + 3) & ~3
    new_ptr = struct.pack("<I", 0x08000000 + new_off)
    wrote = 0
    for p in ptrs:
        cur = struct.unpack_from("<I", data, p)[0]
        if 0x08000000 <= cur <= 0x09FFFFFF:
            data[p : p + 4] = new_ptr
            wrote += 1
    return wrote > 0, free_at


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


def still_mostly_en(chs: str) -> bool:
    plain = re.sub(r"\{[^}]+\}", "", chs)
    plain = re.sub(r"\[[0-9A-Fa-f]{2}\]", "", plain)
    letters = sum(c.isalpha() and c.isascii() for c in plain)
    cjk = sum(1 for c in plain if "\u4e00" <= c <= "\u9fff")
    if letters < 12:
        return False
    return letters > max(cjk * 2, 8)


def fix_menu(data: bytearray, golden: bytes, free_at: int) -> tuple[int, int]:
    n = 0
    # restore smashed labels from golden then reloc
    off = 0x101B000
    while off < 0x1028000:
        eos = golden.find(b"\xff", off, min(off + 24, 0x1028000))
        if eos < 0:
            nxt = golden.find(b"\xff", off, 0x1028000)
            off = nxt + 1 if nxt >= 0 else 0x1028000
            continue
        en = decode_bytes(golden[off : eos + 1]).strip()
        zh = dict(MENU_LABELS).get(en)
        if not zh:
            off = eos + 1
            continue
        # if already good CN skip
        _, to_str = load_charmap()
        cur = decode_chs(bytes(data[off : data.find(b"\xff", off) + 1]), to_str)
        if zh in cur and "POK" not in cur.upper() and cur.strip() != "背":
            off = eos + 1
            continue
        # restore golden bytes at slot so ptrs still valid, then reloc
        data[off : eos + 1] = golden[off : eos + 1]
        ok, free_at = reloc_label(data, free_at, off, zh)
        if ok:
            n += 1
            print(f"  menu {off:08X} {en} -> {zh}")
        off = eos + 1
    return n, free_at


def fix_partial(data: bytearray, golden: bytes, cache: dict[str, str]) -> tuple[int, int]:
    _, to_str = load_charmap()
    cands: list[tuple[int, str]] = []
    for a, b in [(0x250000, 0x360000)]:
        off = a
        while off < b:
            eos = golden.find(b"\xff", off, min(off + 181, b))
            if eos < 0:
                nxt = golden.find(b"\xff", off, b)
                off = nxt + 1 if nxt >= 0 else b
                continue
            if eos - off < 24:
                off = eos + 1
                continue
            en = decode_bytes(golden[off : eos + 1])
            plain = re.sub(r"\{[^}]+\}", "", en)
            if sum(c.isalpha() for c in plain) < 20:
                off = eos + 1
                continue
            if len(re.findall(r"[A-Za-z]{3,}", plain)) < 4:
                off = eos + 1
                continue
            if " " not in plain and "\n" not in en:
                off = eos + 1
                continue
            cur = decode_chs(bytes(data[off : eos + 1]), to_str)
            # include same-as-golden OR partial leftover EN
            if bytes(data[off : eos + 1]) == golden[off : eos + 1] or still_mostly_en(cur):
                if still_mostly_en(cur) or bytes(data[off : eos + 1]) == golden[off : eos + 1]:
                    cands.append((off, en))
            off = eos + 1
    print(f"partial/same EN dialogues: {len(cands)}")
    applied = mt = 0
    for i, (off, en) in enumerate(cands):
        zh = ""
        cached = place_scrub(cache.get(en, ""))
        if cached and quality_ok(en, cached):
            zh = reinject(en, cached) if not tokens_ok(en, cached) else cached
        else:
            raw = translate_one(en, "bing")
            if raw:
                zh = reinject(en, place_scrub(raw))
                cache[en] = zh
                mt += 1
                time.sleep(0.06)
        if not zh or not quality_ok(en, zh) or not tokens_ok(en, zh):
            continue
        if put_inplace(data, golden, off, zh):
            applied += 1
            if applied <= 8 or applied % 40 == 0:
                print(f"  dlg {applied} {off:08X} {en[:40]!r}", flush=True)
        if (i + 1) % 40 == 0:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            OUT.write_bytes(data)
            print(f"  progress {i+1}/{len(cands)} applied={applied}", flush=True)
    return applied, mt


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
    free_at = int(CURSOR.read_text().strip(), 0) if CURSOR.exists() else FREE_START

    print("1) start menu labels… SKIP (already fixed)", flush=True)
    n_menu = 0
    # n_menu, free_at = fix_menu(data, golden, free_at)
    # print(f"   menu fixed={n_menu}", flush=True)

    print("2) partial/leftover EN dialogues…", flush=True)
    n_dlg, n_mt = fix_partial(data, golden, cache)
    print(f"   dlg applied={n_dlg} mt={n_mt}", flush=True)

    # hand Hiya
    hiya = (
        "嗨!你该不会是…\n新手训练家吧?{WAIT_CLEAR}"
        "你知道宝可梦训练家\n到了新城镇会先做什么吗?{WAIT_CLEAR}"
        "他们会先看看镇上\n有什么样的道馆。"
    )
    put_inplace(data, golden, 0x269A42, hiya)

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("FF00112233445566778899AABBCCDDEE")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    CURSOR.write_text(hex(free_at), encoding="utf-8")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    _, to_str = load_charmap()
    for lab, off in [("hiya", 0x269A42), ("bag", 0x1020BAA), ("dex", 0x1020BA2)]:
        # find actual BAG after fix via golden scan sample
        pass
    # verify menu by searching golden BAG sites
    for off in range(0x101B000, 0x1028000):
        eos = golden.find(b"\xff", off, min(off + 8, 0x1028000))
        if eos < 0:
            continue
        en = decode_bytes(golden[off : eos + 1]).strip()
        if en in ("BAG", "POKéDEX", "SAVE") and off in (0x1020BAA, 0x1020BA2, 0x1020BB7, 0x101F1EA):
            # follow ptr if relocated - just print slot
            print(en, hex(off), decode_chs(bytes(data[off : data.find(b"\xff", off) + 1]), to_str)[:20])
    # follow one ptr for BAG
    bag_off = None
    off = 0x101B000
    while off < 0x1028000:
        eos = golden.find(b"\xff", off, min(off + 8, 0x1028000))
        if eos is not None and eos > off and decode_bytes(golden[off : eos + 1]).strip() == "BAG":
            bag_off = off
            break
        off = (eos + 1) if eos and eos >= off else off + 1
    if bag_off is not None:
        # read first ptr target
        ptrs = find_ptrs(bytes(data), bag_off)
        print("BAG slot", hex(bag_off), "ptrs", len(ptrs), decode_chs(bytes(data[bag_off : data.find(b"\xff", bag_off) + 1]), to_str)[:20])
        if ptrs:
            dest = struct.unpack_from("<I", data, ptrs[0])[0] - 0x08000000
            print("BAG dest", hex(dest), decode_chs(bytes(data[dest : data.find(b"\xff", dest) + 1]), to_str)[:20])
    print("hiya", decode_chs(bytes(data[0x269A42 : golden.find(b"\xff", 0x269A42) + 1]), to_str)[:80])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
