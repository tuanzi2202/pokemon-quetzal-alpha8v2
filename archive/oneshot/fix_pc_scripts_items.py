#!/usr/bin/env python3
"""Fix Pokemon Center / script chaos + keep item CN.

Root causes still present after earlier passes:
1. Dialogue bank still has ~779 pointers retargeted to free-space (09DCxxxx).
2. Nurse script pointer tables around 0x2972xx were zeroed.
3. UI struct at 0x100Axxx had null slots overwritten by Chinese text spills.
"""
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


def u32(b: bytes | bytearray, o: int) -> int:
    return int.from_bytes(b[o : o + 4], "little")


def is_free(p: int) -> bool:
    return 0x09DC0000 <= p <= 0x09FFFFFF


def looks_rom(p: int) -> bool:
    return 0x08000000 <= p <= 0x09FFFFFF


def restore_free_retargets(data: bytearray, golden: bytes) -> int:
    n = 0
    for i in range(0, len(data) - 3, 4):
        if 0x1DC0000 <= i < 0x1F00000:
            continue
        p, pg = u32(data, i), u32(golden, i)
        if p != pg and is_free(p) and looks_rom(pg) and not is_free(pg):
            data[i : i + 4] = golden[i : i + 4]
            n += 1
    return n


def restore_zeroed_script_tables(data: bytearray, golden: bytes) -> int:
    """Where CN zeroed a run that in golden is a dense pointer/script table, restore."""
    n = 0
    # Critical early-game script/dialogue banks
    ranges = [
        (0x270000, 0x2A0000),
        (0x2A0000, 0x2E0000),
        (0x2E0000, 0x320000),
        (0x320000, 0x360000),
    ]
    for start, end in ranges:
        i = start
        while i < end - 4:
            # look for CN all-zero dword where golden looks like a ROM ptr
            if data[i : i + 4] == b"\x00\x00\x00\x00":
                pg = u32(golden, i)
                if looks_rom(pg) and not is_free(pg) and i % 4 == 0:
                    # expand to contiguous zeroed block that golden fills with non-zero
                    j = i
                    while j < end and data[j] == 0 and golden[j] != 0:
                        j += 1
                    # only restore if block has at least one ROM ptr and length>=8
                    if j - i >= 8:
                        ptrs = sum(
                            1
                            for k in range(i, j - 3, 4)
                            if looks_rom(u32(golden, k)) and not is_free(u32(golden, k))
                        )
                        if ptrs >= 1:
                            data[i:j] = golden[i:j]
                            n += j - i
                            i = j
                            continue
            i += 4 if i % 4 == 0 else 1
    return n


def restore_force_regions(data: bytearray, golden: bytes) -> None:
    """Hard restore known broken nurse / PC / early script tables."""
    for a, b in [
        (0x297200, 0x297400),  # Oldale-ish PC nurse scripts + menus
        (0x2972B0, 0x297360),  # pointer table specifically
        (0x279E71, 0x27A0D5),  # route101 scripts
    ]:
        data[a:b] = golden[a:b]


def fix_ui_null_spills(data: bytearray, golden: bytes) -> int:
    """Restore golden null dwords that were overwritten (text spill into structs)."""
    n = 0
    for start, end in [(0x1009000, 0x1012000), (0x0FC0000, 0x0FD0000), (0x0FA0000, 0x0FB0000)]:
        for i in range(start, min(end, len(data) - 3), 4):
            if golden[i : i + 4] == b"\x00\x00\x00\x00" and data[i : i + 4] != b"\x00\x00\x00\x00":
                # only if neighbors look like table (ptr or FF padding nearby)
                neigh = golden[max(0, i - 8) : i + 12]
                if b"\xff" in neigh or any(
                    looks_rom(u32(golden, i + k * 4)) for k in (-2, -1, 1, 2) if 0 <= i + k * 4 < len(golden) - 3
                ):
                    data[i : i + 4] = b"\x00\x00\x00\x00"
                    n += 1
    # Also restore short English labels that got spilled after those nulls
    for off in (0x100A02C, 0x100A060, 0x100A090, 0x100A0C8, 0x100A0F4):
        eos = golden.find(b"\xff", off)
        if 0 < eos - off < 20:
            data[off : eos + 1] = golden[off : eos + 1]
            # pad like golden after
            pad_end = min(eos + 1 + 4, len(golden))
            data[eos + 1 : pad_end] = golden[eos + 1 : pad_end]
            n += 1
    return n


# --- item CN (same as fix_items_poke_pc, condensed) ---
ITEM_NAMES = {
    0xF9B251: "精灵球",
    0xF9B266: "超级球",
    0xF9B27B: "高级球",
    0xF9B28F: "大师球",
    0xF9B2A4: "纪念球",
    0xF9B2B9: "治愈球",
    0xF9B2CA: "捕网球",
    0xF9B2DD: "巢穴球",
    0xF9B2F2: "潜水球",
    0xF9B306: "黑暗球",
    0xF9B31A: "计时球",
    0xF9B32F: "先机球",
    0xF9B343: "重复球",
    0xF9B358: "豪华球",
    0xF9B36C: "等级球",
    0xF9B37F: "诱饵球",
    0xF9B392: "月亮球",
    0xF9B3A6: "友友球",
    0xF9B3BC: "甜蜜球",
    0xF9B3CE: "速度球",
    0xF9B3E2: "沉重球",
    0xF9B3F7: "梦境球",
    0xF9B40B: "狩猎球",
    0xF9B420: "竞速球",
    0xF9B433: "光耀球",
    0xF9B449: "究极球",
    0xF9B45B: "贵重球",
    0xF9B471: "伤药",
    0xF9B47F: "好伤药",
    0xF9B499: "厉害伤药",
    0xF9B4AD: "全满药",
    0xF9B4BF: "全复药",
    0xF9B4D5: "复活药",
    0xF9B4E3: "万能药",
    0xF9B4FB: "美味之水",
    0xF9B510: "劲爽汽水",
    0xF9B521: "柠檬汁",
    0xF9B535: "哞哞鲜奶",
    0xF9B54C: "力量粉",
    0xF9B562: "力量根",
    0xF9B574: "万能粉",
    0xF9B588: "复活草",
    0xF9B59D: "解毒药",
    0xF9B5AD: "解麻药",
    0xF9B5C6: "灼伤药",
    0xF9B5D6: "解冻药",
    0xF9B5E9: "解眠药",
    0xF9B5FE: "万灵药",
}

ITEM_DESCS = {
    0xF8B1D2: "用于捕捉野生\n宝可梦的道具。",
    0xF8B1F9: "性能不错的球，\n比精灵球更容易\n捉到宝可梦。",
    0xF8B230: "性能很好的球，\n比超级球更容易\n捉到宝可梦。",
    0xF8B26A: "性能最好的球，\n能必定捉到\n宝可梦。",
    0xF8B29D: "为纪念某事件\n而特制的稀有球。",
    0xF8B2CE: "捉到宝可梦后\n还能回复体力的球。",
    0xF8B2FC: "对水和虫属性\n宝可梦特别有效。",
    0xF8B333: "对弱小的宝可梦\n特别有效。",
    0xF8B35F: "对海底的宝可梦\n特别有效。",
    0xF8B3BB: "战斗回合越多，\n捕捉率越高。",
    0xF8B417: "对曾经捉到过的\n宝可梦更有效。",
    0xF8B44A: "捉到后会让宝可梦\n变得更亲密。",
    0xF8B478: "对等级低的\n宝可梦更有效。",
    0xF8B4A7: "对钓上来的\n宝可梦更有效。",
    0xF8B4D4: "对使用月之石\n进化的宝可梦有效。",
    0xF8B500: "捉到后会让宝可梦\n变得友好。",
    0xF8B532: "对异性宝可梦\n特别有效。",
    0xF8B560: "对速度很快的\n宝可梦有效。",
    0xF8B581: "对很重的\n宝可梦有效。",
    0xF8B5A3: "对睡着的\n宝可梦有效。",
    0xF8B5CF: "仅在狩猎地带\n使用的特殊球。",
    0xF8B604: "捕虫大赛中\n使用的特殊球。",
    0xF8B635: "专门用来捕捉\n光耀宝可梦的球。",
    0xF8B658: "专门用来捕捉\n究极异兽的球。",
    0xF8B67F: "为纪念某事件\n而特制的稀有球。",
    0xF8B6B0: "回复宝可梦\n20点HP。",
    0xF8B6DB: "回复宝可梦\n60点HP。",
    0xF8B706: "回复宝可梦\n120点HP。",
    0xF8B732: "完全回复\n宝可梦的HP。",
    0xF8B756: "完全回复宝可梦的\nHP和异常状态。",
    0xF8B785: "让倒下的宝可梦\n以一半HP复活。",
    0xF8B7B1: "让倒下的宝可梦\n以全部HP复活。",
}

NURSE_ZH = {
    # After restoring golden PC block, overwrite pure text strings (not script tables)
    0x309C60: "欢迎光临！{WAIT_CLEAR}需要我为你做些什么？",
}


def put_padded(data: bytearray, golden: bytes, off: int, zh: str) -> bool:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return False
    cap = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    while len(body) + 1 > cap and zh:
        zh = zh[:-1]
        enc, _ = encode_text_safe(zh)
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        body = enc[:-1]
    if len(body) + 1 > cap:
        return False
    pad = cap - 1 - len(body)
    data[off : off + cap] = (b"\x00" * pad) + body + b"\xff"
    return True


def put(data: bytearray, golden: bytes, off: int, zh: str) -> bool:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return False
    cap = eos - off + 1
    enc, _ = encode_text_safe(zh)
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    while len(body) + 1 > cap and zh:
        zh = zh[:-1]
        enc, _ = encode_text_safe(zh)
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        body = enc[:-1]
    if len(body) + 1 > cap:
        return False
    data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))
    return True


def scrub_poke_tokens(data: bytearray, golden: bytes) -> int:
    """Replace remaining POKé/Poké BALL and POKéMON in text-looking slots."""
    n = 0
    poke_vars = [bytes([0xCA, 0xC9, 0xC5, 0x1B]), bytes([0xCA, 0xE3, 0xDF, 0x1B])]
    ball_u = bytes([0xBC, 0xBB, 0xC6, 0xC6])
    ball_t = bytes([0xBC, 0xD5, 0xE0, 0xE0])
    jing = encode_text_safe("精灵球")[0]
    jing = jing[:-1] if jing.endswith(b"\xff") else jing
    bao = encode_text_safe("宝可梦")[0]
    bao = bao[:-1] if bao.endswith(b"\xff") else bao
    mon = bytes([0xC7, 0xC9, 0xC8])  # MON

    # Prefer item/desc/UI banks first
    banks = [(0xF8B000, 0xFA0000), (0x260000, 0x360000), (0x400000, 0x450000)]
    for start, end in banks:
        for poke in poke_vars:
            i = start
            while True:
                j = data.find(poke, i, end)
                if j < 0:
                    break
                # POKé + space? + BALL
                for ball in (ball_u, ball_t):
                    for gap in (0, 1):
                        endb = j + len(poke) + gap
                        if gap and data[j + len(poke)] not in (0x00, 0xFE):
                            continue
                        if data[endb : endb + len(ball)] == ball:
                            end2 = endb + len(ball)
                            if end2 < len(data) and data[end2] == 0xCD:
                                end2 += 1
                            old = end2 - j
                            if len(jing) <= old:
                                data[j:end2] = jing + b"\x00" * (old - len(jing))
                                n += 1
                # POKéMON
                if data[j + len(poke) : j + len(poke) + 3] == mon:
                    old = len(poke) + 3
                    if len(bao) <= old:
                        data[j : j + old] = bao + b"\x00" * (old - len(bao))
                        n += 1
                i = j + 1
    return n


def reapply_items(data: bytearray, golden: bytes) -> None:
    for off, zh in ITEM_NAMES.items():
        put_padded(data, golden, off, zh)
    for off, zh in ITEM_DESCS.items():
        put(data, golden, off, zh)
    # scrub remaining EN item descs with Ball/Pokemon
    off = 0xF8B000
    while off < 0xF9B200:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0xF9B200 or eos - off > 220 or eos - off < 12:
            off += 1
            continue
        if off in ITEM_DESCS:
            off = eos + 1
            continue
        en = decode_bytes(golden[off : eos + 1])
        if not re.search(r"(?i)ball|pok[eé]|pokemon|pokémon", en):
            off = eos + 1
            continue
        zh = en
        zh = re.sub(r"(?i)POK[EÉ]\s*BALLS?", "精灵球", zh)
        zh = re.sub(r"(?i)GREAT\s*BALLS?", "超级球", zh)
        zh = re.sub(r"(?i)ULTRA\s*BALLS?", "高级球", zh)
        zh = re.sub(r"(?i)MASTER\s*BALLS?", "大师球", zh)
        zh = re.sub(r"(?i)Pokémon|Pokemon|POK[EÉ]MON", "宝可梦", zh)
        if sum(1 for c in zh if "\u4e00" <= c <= "\u9fff") >= 2:
            put(data, golden, off, zh)
        off = eos + 1


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    print("1) restore free-space pointer retargets")
    n1 = restore_free_retargets(data, golden)
    print(f"   restored {n1}")

    print("2) restore zeroed script/pointer tables")
    n2 = restore_zeroed_script_tables(data, golden)
    print(f"   bytes {n2}")

    print("3) force-restore PC/route101 regions")
    restore_force_regions(data, golden)

    print("4) fix UI null spills")
    n4 = fix_ui_null_spills(data, golden)
    print(f"   fixed {n4}")

    print("5) re-apply item CN")
    reapply_items(data, golden)

    print("6) scrub POKé BALL / POKéMON tokens")
    n6 = scrub_poke_tokens(data, golden)
    print(f"   scrubbed {n6}")

    print("7) nurse welcome CN (inplace if fits)")
    for off, zh in NURSE_ZH.items():
        ok = put(data, golden, off, zh)
        print(f"   {off:08X} {ok}")

    # keep clock EN labels
    for off in (0xFC70EF, 0xFC7B74):  # AM / CANCEL-ish — restore if known
        pass
    # restore day names / AM/PM/TIME/CANCEL from golden in FC pool (narrow)
    keep = {"SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "A.M.", "P.M.", "AM", "PM", "TIME", "CANCEL"}
    off = 0xFC0000
    while off < 0xFD0000:
        eos = golden.find(b"\xff", off)
        if eos < 0 or eos >= 0xFD0000 or eos - off > 24:
            off = eos + 1 if eos >= off and eos < 0xFD0000 else off + 1
            continue
        en = decode_bytes(golden[off : eos + 1]).strip()
        if en in keep:
            data[off : eos + 1] = golden[off : eos + 1]
        off = eos + 1

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("B1B2B3B4B5B6B7B8C1C2C3C4C5C6C7C8")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    # verify
    def check(i):
        p, pg = u32(data, i), u32(golden, i)
        print(f"  ptr@{i:08X} now={p:08X} gold={pg:08X} ok={p==pg}")

    print("verify:")
    check(0x28D99C)
    check(0x2972DC)
    print("  nurse table", data[0x2972BC:0x2972E0].hex())
    print("  item name", data[0xF9B251 : 0xF9B251 + 14].hex())
    print("  free-retargets left", end=" ")
    left = 0
    for i in range(0, len(data) - 3, 4):
        if 0x1DC0000 <= i < 0x1F00000:
            continue
        p, pg = u32(data, i), u32(golden, i)
        if p != pg and is_free(p) and looks_rom(pg) and not is_free(pg):
            left += 1
    print(left)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
