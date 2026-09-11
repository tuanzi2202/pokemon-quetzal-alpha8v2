#!/usr/bin/env python3
"""Fix garbled money notices + player-info labels (FD/$ placeholders).

Root causes:
- Charmap maps B7 to ¥; writers used '$' → encode_text_safe turned it into '?' (0xAC).
- Narrow UI strings lost {FD:xx} expanders when Chinese overran the slot.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"

# Use ¥ (charmap B7) — same byte as English '$'
# Use ASCII : ! for UI that shares English control layout (fullwidth ：！ → 3E/3C junk).
HAND: dict[int, str] = {
    # Battle money / whiteout
    0xFF9730: "{FD:23}得到了${FD:00}!\n获胜奖金!{WAIT_CLEAR}",
    0xFF9783: "{FD:23}支付了奖金${FD:00}…{WAIT_CLEAR}…………{WAIT_CLEAR}{FD:23}失去了意识!{FC:09}",
    0xFF97DA: "{FD:23}惊慌失措,丢了${FD:00}…{WAIT_CLEAR}…………{WAIT_CLEAR}{FD:23}失去了意识!{FC:09}",
    0xFFA227: "{FD:23}捡到了\n${FD:00}!{WAIT_CLEAR}",
    # Start-menu / trainer-card style short labels
    0x101BC0B: "玩家",
    0x101BC12: "图鉴",
    0x101BC1A: "时间",
    0x101BC1F: "徽章",
    0x1020BBC: "金钱",
    0x1020BC4: "图鉴",
    0x1020BD7: "时间",
    0x1020BAF: "名字:",
    # Coop / players info panel (must keep FD expanders)
    0x102483A: "玩家信息",
    0x102487C: "玩家:{FD:02}",
    0x10248D3: "时间:{FD:02}:{FD:03}",
    0x10248E1: "金钱:{FD:02}{FD:04}",
    0x10248C8: "名字:{FD:02}",
    0x1024901: "玩家",
}


def put(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    cap = eos - off + 1
    enc, miss = encode_text_safe(zh)
    if miss:
        # Prefer failing loudly for money/UI — don't silently insert '?'
        print(f"  WARN miss @{off:08X} {miss} in {zh!r}")
    if not enc.endswith(b"\xff"):
        enc += b"\xff"
    body = enc[:-1]
    if len(body) + 1 > cap:
        # try progressively shorter variants
        return f"long need={len(body)+1} cap={cap}"
    data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))
    return "ok"


def put_right_fd(data: bytearray, golden: bytes, off: int, label_zh: str, fd_tail: str) -> str:
    """Label + spaces + FD tail, matching golden's right-aligned expander layout."""
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    cap = eos - off + 1
    lab, miss = encode_text_safe(label_zh)
    if lab.endswith(b"\xff"):
        lab = lab[:-1]
    tail, miss2 = encode_text_safe(fd_tail)
    if tail.endswith(b"\xff"):
        tail = tail[:-1]
    if miss or miss2:
        print(f"  WARN @{off:08X} miss={miss+miss2}")
    need = len(lab) + len(tail) + 1
    if need > cap:
        return f"long need={need} cap={cap}"
    pad = cap - 1 - len(lab) - len(tail)
    data[off : off + cap] = lab + (b"\x00" * pad) + tail + b"\xff"
    return "ok"


def fix_all_dollar_to_yen_byte(data: bytearray, golden: bytes) -> int:
    """Where golden has B7 ($) and CN has AC (?), restore B7 if still in a money-ish string."""
    n = 0
    i = 0
    while True:
        j = golden.find(b"\xb7", i)
        if j < 0:
            break
        if data[j] == 0xAC:  # '?'
            data[j] = 0xB7
            n += 1
        i = j + 1
    return n


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    # Longer battle strings may need shorter ZH — try HAND then fallbacks
    fallbacks = {
        0xFF9730: [
            "{FD:23}得到了${FD:00}!\n获胜奖金!{WAIT_CLEAR}",
            "{FD:23}得到${FD:00}!\n获胜!{WAIT_CLEAR}",
            "{FD:23}得到${FD:00}!{WAIT_CLEAR}",
        ],
        0xFF9783: [
            "{FD:23}支付奖金${FD:00}…{WAIT_CLEAR}…{WAIT_CLEAR}{FD:23}倒下了!{FC:09}",
            "{FD:23}交出${FD:00}…{WAIT_CLEAR}…{WAIT_CLEAR}{FD:23}倒下了!{FC:09}",
        ],
        0xFF97DA: [
            "{FD:23}丢了${FD:00}…{WAIT_CLEAR}…{WAIT_CLEAR}{FD:23}倒下了!{FC:09}",
        ],
        0xFFA227: [
            "{FD:23}捡到了\n${FD:00}!{WAIT_CLEAR}",
            "{FD:23}获得\n${FD:00}!{WAIT_CLEAR}",
        ],
    }

    print("=== hand patches ===")
    for off, zh in HAND.items():
        cands = fallbacks.get(off, [zh])
        st = "fail"
        for c in cands:
            st = put(data, golden, off, c)
            if st == "ok":
                print(f"  OK {off:08X}")
                break
        else:
            # special right-align FD layouts
            if off == 0x102487C:
                st = put_right_fd(data, golden, off, "玩家:", "{FD:02}")
                print(f"  {st} {off:08X} right-fd player")
            elif off == 0x10248C8:
                st = put_right_fd(data, golden, off, "名字:", "{FD:02}")
                print(f"  {st} {off:08X} right-fd name")
            else:
                print(f"  FAIL {off:08X} {st}")

    # Ensure player-info FD strings specifically
    print("=== force FD layouts ===")
    for off, lab, tail in [
        (0x102487C, "玩家:", "{FD:02}"),
        (0x10248C8, "名字:", "{FD:02}"),
        (0x10248D3, "时间:", "{FD:02}:{FD:03}"),
        (0x10248E1, "金钱:", "{FD:02}{FD:04}"),
    ]:
        st = put_right_fd(data, golden, off, lab, tail)
        # TIME/MONEY may not need right-pad if compact fits
        if st != "ok":
            st = put(data, golden, off, lab + tail)
        print(f"  {off:08X} {st}")

    print("=== restore ?←$ bytes ===")
    print(f"  restored B7 from AC: {fix_all_dollar_to_yen_byte(data, golden)}")

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("112233445566778899AABBCCDDEEFF00")
    OUT.write_bytes(data)
    ROM.write_bytes(data)

    print("=== verify ===")
    for off in (0xFF9730, 0xFFA227, 0x10248D3, 0x10248E1, 0x102487C, 0x1020BBC, 0x101BC0B, 0x101BC1A):
        eos = golden.find(b"\xff", off)
        print(f"{off:08X} {decode_bytes(data[off:eos+1])!r}")
        print(f"         hex={data[off:eos+1].hex()}")
        # must contain FD if golden did
        ghas = b"\xfd" in golden[off:eos]
        rhas = b"\xfd" in data[off:eos]
        if ghas and not rhas:
            print("         !! MISSING FD")
        if b"\xb7" in golden[off:eos] and b"\xb7" not in data[off:eos]:
            print("         !! MISSING ¥/$")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
