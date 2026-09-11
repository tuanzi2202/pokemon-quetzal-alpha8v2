#!/usr/bin/env python3
"""Fix battle menu + Birch rescue dialogues; scrub broken POKéMON mid-replacements."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from gen3_charmap import decode_bytes, encode_plain  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"

# Battle command menu (must keep FC spacing codes)
BATTLE_MENU = {
    0xFFFB50: "战斗{FC:13}{38}背包\n宝可梦{FC:13}{38}逃跑",
    0xFFFB6A: "球{FC:13}{38}{55}{56}{57}{58}{59}\n靠近{FC:13}{38}逃跑",  # safari
}

BIRCH = {
    # Post-rescue on Route 101 (freeze point)
    0x279CA3: (
        "小田卷博士：呼……{WAIT_CLEAR}"
        "我在深草里调查野生宝可梦时被袭击了。{WAIT_CLEAR}"
        "你救了我，非常感谢！{WAIT_CLEAR}"
        "哦？{WAIT_CLEAR}"
        "你好，你是{FD:01}{FD:05}！{WAIT_CLEAR}"
        "这里不方便细聊，稍后请到我的宝可梦研究所来，好吗？"
    ),
    0x279C2B: (
        "喂！那边的人！\n拜托！救救我！{WAIT_CLEAR}"
        "我的背包里！\n有精灵球！"
    ),
    0x279C1F: "救、救我！",
    0x27680A: "你救了小田卷博士！\n我太高兴了！",
    0x2768C9: (
        "小田卷博士：哎呀哎呀，{FD:01}{FD:05}！\n刚才干得漂亮！{WAIT_CLEAR}"
        "第一次见到你时就觉得你不简单，{WAIT_SCROLL}"
        "但没想到能到这个地步。{WAIT_CLEAR}"
        "对了，我给你的宝可梦图鉴还在吧？{WAIT_CLEAR}"
        "我有东西要给你看。\n去研究所吧。"
    ),
}


def inplace(data: bytearray, golden: bytes, off: int, zh: str) -> bool:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return False
    capacity = eos - off + 1
    enc, missing = encode_text_safe(zh)
    if missing:
        print(f"  missing glyphs @{off:08X}: {missing[:6]}")
    if len(enc) > capacity:
        cut = zh
        while cut and len(encode_text_safe(cut)[0]) > capacity:
            cut = cut[:-1]
        enc, _ = encode_text_safe(cut)
        print(f"  TRIM {off:08X} used={len(enc)}/{capacity}")
        if len(enc) > capacity:
            print(f"  FAIL {off:08X}")
            return False
    else:
        print(f"  OK {off:08X} used={len(enc)}/{capacity}")
    # Keep EOS at golden slot end: shorter CN must not wipe the terminator position
    # with only NULs (and must not leave a mid-slot FF without trailing pad to capacity).
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    if len(body) + 1 > capacity:
        print(f"  FAIL {off:08X} body too long")
        return False
    data[off : off + capacity] = body + b"\x00" * (capacity - 1 - len(body)) + b"\xff"
    return True


def restore_then_fix_partial_pokemon(data: bytearray, golden: bytes) -> int:
    """Find strings where CN still contains literal 'POK' + junk from bad scrub; restore+rescrub."""
    # Detect: CN has POKé (cac9c51b) still, or 'POK' letters followed by CJK lead
    poke = bytes([0xCA, 0xC9, 0xC5, 0x1B])  # POKé
    n = 0
    # Focus early game + lab dialogues
    for start, end in [(0x270000, 0x2A0000), (0xFFB000, 0x1000000)]:
        off = start
        while off < end:
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= end or eos - off > 400:
                off += 1
                continue
            chunk_cn = bytes(data[off : eos + 1])
            chunk_en = golden[off : eos + 1]
            if poke in chunk_cn and chunk_cn != chunk_en:
                # partially translated — rewrite from EN with proper scrub
                en_text = decode_bytes(chunk_en)
                zh = en_text
                zh = re.sub(r"(?i)POK[EÉ]\s*MON", "宝可梦", zh)
                zh = re.sub(r"(?i)POK[EÉ]\s*DEX", "宝可梦图鉴", zh)
                zh = re.sub(r"(?i)POK[EÉ]\s*NAV", "宝可梦导航器", zh)
                zh = re.sub(r"(?i)POK[EÉ]\s*BALLS?", "精灵球", zh)
                zh = re.sub(r"(?i)PROF\.\s*BIRCH", "小田卷博士", zh)
                zh = re.sub(r"(?i)BIRCH", "小田卷", zh)
                if any("\u4e00" <= c <= "\u9fff" for c in zh) and zh != en_text:
                    if inplace(data, golden, off, zh):
                        n += 1
            off = eos + 1
    print(f"partial POKe scrubbed={n}")
    return n


def restore_blanked_mids(data: bytearray, golden: bytes) -> int:
    """Restore strings that were wiped to NULs (bad mid-string patches)."""
    n = 0
    for off in range(0x270000, 0x2A0000):
        if data[off] != 0:
            continue
        # potential wipe: many zeros then we need string start at prev FF+1
        pass
    # targeted known blanks
    for mid in (0x287037, 0x28837E):
        # find true start
        s = mid
        while s > 0 and golden[s - 1] != 0xFF and mid - s < 80:
            s -= 1
        eos = golden.find(b"\xff", mid)
        # restore whole string from start
        eos2 = golden.find(b"\xff", s)
        if eos2 > s:
            data[s : eos2 + 1] = golden[s : eos2 + 1]
            n += 1
            print(f"  restored blanked @{s:08X}")
    return n


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    print("=== battle menu ===")
    for off, zh in BATTLE_MENU.items():
        inplace(data, golden, off, zh)
        eos = golden.find(b"\xff", off)
        print("   ->", decode_bytes(bytes(data[off : eos + 1])))

    print("=== birch ===")
    for off, zh in BIRCH.items():
        inplace(data, golden, off, zh)

    print("=== restore blanks ===")
    restore_blanked_mids(data, golden)

    print("=== partial pokemon ===")
    restore_then_fix_partial_pokemon(data, golden)

    # fingerprint bump
    data[0x1DCB5E0 + 12] = (data[0x1DCB5E0 + 12] + 1) & 0xFF

    OUT.write_bytes(data)
    ROM.write_bytes(data)

    # verify
    for off, name in [
        (0xFFFB50, "menu"),
        (0x279CA3, "birch_whew"),
        (0x279C1F, "help"),
    ]:
        eos = golden.find(b"\xff", off)
        print(name, decode_bytes(bytes(data[off : eos + 1]))[:80])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
