#!/usr/bin/env python3
"""Post-pass: cottage hand fix, mode wizard CN, restore bad FC ptrs (clock), options."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe, load_charmap  # noqa: E402
from fill_and_apply_remaining import CACHE  # noqa: E402
from force_mode_zh import MODE_WIZARD, find_ptrs, FREE_END  # noqa: E402
from gen3_charmap import decode_bytes  # noqa: E402

GOLDEN = ROOT / "golden" / "en_0.8.4.gba"
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"
CURSOR = ROOT / "work" / "free_cursor.txt"
FREE_START = 0x01D9B5A8 + 0x30000

COTTAGE_OFF = 0x27B813
COTTAGE_ZH = (
    "那座海边小屋就是\n哈奇老人住的地方。{WAIT_CLEAR}"
    "他从前是了不起的水手,\n再大的风浪也不怕。"
)
COTTAGE_EN = (
    "That seaside cottage is where\nMR. BRINEY lives.{WAIT_CLEAR}"
    "He was once a mighty sailor who never\nfeared the sea, however stormy."
)


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
            parts.append("{W}")
            i += 1
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


def restore_fc_bad_ptrs(data: bytearray, golden: bytes) -> int:
    n = 0
    for off in range(0xFC0000, 0xFD0000, 4):
        gv = struct.unpack_from("<I", golden, off)[0]
        rv = struct.unpack_from("<I", data, off)[0]
        if gv == rv:
            continue
        # restore only suspicious retargets into free/high space that gold didn't use
        gold_ok = 0x08000000 <= gv <= 0x08FFFFFF or 0x02000000 <= gv <= 0x03FFFFFF or gv < 0x01000000
        rom_free = 0x09DC0000 <= rv <= 0x09FFFFFF or 0x01D00000 <= (rv - 0x08000000) <= 0x01FFFFFF
        if rv != gv and (
            (0x09000000 <= rv <= 0x09FFFFFF and not (0x09000000 <= gv <= 0x09FFFFFF))
            or (0x081D0000 <= rv <= 0x081FFFFF and gv < 0x081D0000)
        ):
            struct.pack_into("<I", data, off, gv)
            n += 1
        elif gold_ok and rom_free:
            struct.pack_into("<I", data, off, gv)
            n += 1
    return n


def apply_mode(data: bytearray, free_at: int) -> tuple[int, int]:
    n = 0
    for off, zh in MODE_WIZARD:
        enc, miss = encode_text_safe(zh)
        if miss:
            continue
        if not enc.endswith(b"\xff"):
            enc += b"\xff"
        ptrs = find_ptrs(bytes(data), off)
        if not ptrs:
            # try restore golden needle first
            continue
        need = len(enc)
        if free_at + need > FREE_END:
            break
        new_off = free_at
        data[new_off : new_off + need] = enc
        free_at = (free_at + need + 3) & ~3
        new_ptr = struct.pack("<I", 0x08000000 + new_off)
        wrote = 0
        for p in ptrs:
            if p % 4:
                continue
            cur = struct.unpack_from("<I", data, p)[0]
            if 0x08000000 <= cur <= 0x09FFFFFF:
                data[p : p + 4] = new_ptr
                wrote += 1
        if wrote:
            n += 1
            print(f"  mode {off:08X}->{new_off:08X} {zh}")
    return n, free_at


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())
    _, to_str = load_charmap()
    free_at = int(CURSOR.read_text().strip(), 0) if CURSOR.exists() else FREE_START

    print("1) cottage hand")
    put(data, golden, COTTAGE_OFF, COTTAGE_ZH)
    print("  ", decode_chs(bytes(data[COTTAGE_OFF : golden.find(b"\xff", COTTAGE_OFF) + 1]), to_str))

    # fix cache
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
        cache[COTTAGE_EN] = COTTAGE_ZH
        # scrub other lives->还活着 mistakes
        for k, v in list(cache.items()):
            if "lives" in k.lower() and "还活着" in v:
                cache[k] = v.replace("还活着", "住在那里")
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    print("2) restore bad FC ptrs (clock)")
    nfc = restore_fc_bad_ptrs(data, golden)
    print(f"   restored {nfc}")

    # restore clock day names / stopped from golden (narrow slots)
    for off in [
        0xFC6D5C,
        0xFC6D63,
        0xFC6D8C,
        0xFC6DCF,
        0x287A50,
        # keep reset messages CN is fine; day names EN
    ]:
        eos = golden.find(b"\xff", off)
        if eos > off:
            data[off : eos + 1] = golden[off : eos + 1]

    print("3) mode wizard")
    # restore EN needles for mode strings that are still English so find_ptrs works
    for off, zh in MODE_WIZARD:
        eos = golden.find(b"\xff", off)
        if eos < 0:
            continue
        # if current still mostly EN or short, restore golden body at site
        cur = decode_bytes(bytes(data[off : data.find(b"\xff", off) + 1]))
        if sum(c.isascii() and c.isalpha() for c in cur) >= 3:
            data[off : eos + 1] = golden[off : eos + 1]
    nm, free_at = apply_mode(data, free_at)
    print(f"   mode patched {nm}")

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("8899AABBCCDDEEFF0011223344556677")
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    CURSOR.write_text(hex(free_at), encoding="utf-8")

    print("VERIFY cottage", decode_chs(bytes(data[COTTAGE_OFF : golden.find(b"\xff", COTTAGE_OFF) + 1]), to_str))
    for off, lab in [(0x102585D, "diff"), (0x102588E, "mode"), (0x102580E, "veasy"), (0x287A50, "clock")]:
        eos = data.find(b"\xff", off)
        # follow ptr if relocated
        ptrs = find_ptrs(bytes(data), off)
        if ptrs:
            dest = struct.unpack_from("<I", data, ptrs[0])[0] - 0x08000000
            print(lab, decode_chs(bytes(data[dest : data.find(b"\xff", dest) + 1]), to_str)[:40])
        else:
            print(lab, decode_chs(bytes(data[off : eos + 1]), to_str)[:40])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
