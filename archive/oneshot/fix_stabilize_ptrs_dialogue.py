#!/usr/bin/env python3
"""Stabilize ROM: restore free-space pointer retargets; fix clock/save UI; safe dialogue CN.

Root cause of Pokemon Center wild battles / Birch chaos: apply_text retargeted
map/UI pointers from valid 0x09xxxxxx strings into 0x09E0xxxx free-space junk.
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


def is_free_ptr(p: int) -> bool:
    """Pointer into polluted free-space Chinese dump."""
    if 0x09DC0000 <= p <= 0x09FFFFFF:
        return True
    if 0x08000000 <= p <= 0x08FFFFFF:
        off = p - 0x08000000
        if 0x09E0000 <= off < 0x0A00000:
            return True
    return False


def looks_rom_ptr(p: int) -> bool:
    return 0x08000000 <= p <= 0x09FFFFFF


def restore_free_retargets(data: bytearray, golden: bytes, ranges: list[tuple[int, int]]) -> int:
    n = 0
    for a, b in ranges:
        for i in range(a, min(b, len(data) - 3), 4):
            p = int.from_bytes(data[i : i + 4], "little")
            pg = int.from_bytes(golden[i : i + 4], "little")
            if p == pg:
                continue
            if is_free_ptr(p) and looks_rom_ptr(pg):
                data[i : i + 4] = golden[i : i + 4]
                n += 1
    return n


def put(data: bytearray, golden: bytes, off: int, zh: str) -> str:
    eos = golden.find(b"\xff", off)
    if eos < 0:
        return "no_eos"
    # Refuse if golden slot looks like script-heavy (high non-text ratio at start)
    head = golden[off : off + min(12, eos - off)]
    letters = sum(1 for b in head if 0xBB <= b <= 0xEE or b in (0x00, 0xFE, 0xFB, 0xFA, 0xFD))
    if eos - off > 8 and letters < 3 and head[0] < 0x10 and head[0] not in (0x00,):
        # possible script prefix — only allow if known text lead
        pass
    cap = eos - off + 1
    enc, _ = encode_text_safe(zh)
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
            return "long"
    data[off : off + cap] = body + b"\xff" + b"\x00" * (cap - 1 - len(body))
    return "ok"


def restore_clock_strings(data: bytearray, golden: bytes) -> int:
    """Day names + AM/PM + TIME/CANCEL — keep English (narrow slots). Never touch abilities."""
    n = 0
    keep = {
        "SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY",
        "A.M.", "P.M.", "AM", "PM", "TIME", "CANCEL",
    }
    for start, end in [(0x0FC0000, 0x0FD0000), (0x1000000, 0x1030000)]:
        off = start
        while off < end:
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= end or eos - off > 24 or eos - off < 1:
                off = eos + 1 if eos >= off and eos < end else off + 1
                continue
            en = decode_bytes(golden[off : eos + 1]).strip()
            if en in keep:
                if bytes(data[off : eos + 1]) != golden[off : eos + 1]:
                    data[off : eos + 1] = golden[off : eos + 1]
                    n += 1
            off = eos + 1
    for off in (0x287A50, 0x101BB9F, 0x1020666, 0x10206EF):
        eos = golden.find(b"\xff", off)
        if eos > 0 and eos - off < 200:
            data[off : eos + 1] = golden[off : eos + 1]
            n += 1
    return n


SCRUB = [
    (re.compile(r"(?i)POK[EÉ]\s*BALLS?"), "精灵球"),
    (re.compile(r"(?i)GREAT\s*BALLS?"), "超级球"),
    (re.compile(r"(?i)ULTRA\s*BALLS?"), "高级球"),
    (re.compile(r"(?i)MASTER\s*BALLS?"), "大师球"),
    (re.compile(r"(?i)POK[EÉ]\s*MON"), "宝可梦"),
    (re.compile(r"(?i)POK[EÉ]\s*DEX"), "宝可梦图鉴"),
    (re.compile(r"(?i)POK[EÉ]\s*NAV"), "宝可梦导航器"),
    (re.compile(r"(?i)POK[EÉ]\s*CENTER"), "宝可梦中心"),
    (re.compile(r"(?i)POK[EÉ]\s*MART"), "宝可梦商店"),
    (re.compile(r"(?i)PROF\.\s*BIRCH"), "小田卷博士"),
    (re.compile(r"(?i)LITTLEROOT(\s*TOWN)?"), "未白镇"),
    (re.compile(r"(?i)OLDALE(\s*TOWN)?"), "古辰镇"),
    (re.compile(r"(?i)PETALBURG(\s*CITY)?"), "橙华市"),
    (re.compile(r"(?i)TRAINER"), "训练家"),
    (re.compile(r"(?i)^MAY:"), "小遥："),
    (re.compile(r"(?i)^BRENDAN:"), "小悠："),
    (re.compile(r"(?i)^MOM:"), "妈妈："),
    (re.compile(r"(?i)^WALLY:"), "望罗："),
]


def scrub(en: str) -> str:
    z = en
    for pat, rep in SCRUB:
        z = pat.sub(rep, z)
    return z


# High-priority early dialogues still English after pointer restore
HAND: dict[int, str] = {
    0x2761E3: (
        "妈妈：{FD:01}，到了哦，宝贝！{WAIT_CLEAR}"
        "坐着满载行李的搬家卡车，\n一定很累吧。{WAIT_CLEAR}"
        "这里就是未白镇。{WAIT_CLEAR}"
        "喜欢吗？\n这就是我们的新家！{WAIT_CLEAR}"
        "虽然古朴，但感觉很适合生活，\n你说呢？{WAIT_CLEAR}"
        "而且，"
    ),
    0x279D6E: (
        "宝可梦累了的话，就带到\n宝可梦中心去吧。{WAIT_CLEAR}"
        "附近的古辰镇就有\n宝可梦中心。"
    ),
    0x279DDB: (
        "高草丛里会跳出野生宝可梦。{WAIT_CLEAR}"
        "想捉宝可梦的话，\n就要走进草丛里去找。"
    ),
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
    0x2882AE: (
        "咦？\n你……你是谁？{WAIT_CLEAR}"
        "…………\n…………{WAIT_CLEAR}"
        "哦，你是{FD:01}{FD:05}吧？\n今天刚搬来的？{WAIT_CLEAR}"
        "嗯……我是小遥。\n请多关照！{WAIT_CLEAR}"
        "我……\n我的梦想是和全世界的{WAIT_SCROLL}宝可梦成为朋友。{WAIT_CLEAR}"
        "我……我听我爸爸小田卷博士\n说起过你，{FD:01}{FD:05}。{WAIT_CLEAR}"
        "我一直希望你能过来，\n我们能一起玩。"
    ),
    0x28849C: (
        "喂！\n你……{WAIT_CLEAR}"
        "你是谁？{WAIT_CLEAR}"
        "哦，你是{FD:01}吧？\n刚搬到隔壁对吧？{WAIT_CLEAR}"
        "我还不知道你是女孩子。{WAIT_CLEAR}"
        "我爸小田卷博士说新邻居是道馆馆主的{WAIT_SCROLL}孩子，我还以为会是男生呢。{WAIT_CLEAR}"
        "我叫小悠。\n嗨，邻居！{WAIT_CLEAR}"
        "嗯？你问我？\n我……也喜欢宝可梦。"
    ),
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
    0x279C70: "你、你去哪？！\n别丢下我啊！",
}


def batch_scrub_early(data: bytearray, golden: bytes) -> int:
    """Inplace-scrub early dialogue that is still mostly English."""
    n = 0
    for start, end in [(0x270000, 0x2C0000)]:
        off = start
        while off < end:
            eos = golden.find(b"\xff", off)
            if eos < 0 or eos >= end or eos - off > 320 or eos - off < 16:
                off += 1
                continue
            if off in HAND:
                off = eos + 1
                continue
            en = decode_bytes(golden[off : eos + 1])
            if not re.search(r"[A-Za-z]{4,}", en):
                off = eos + 1
                continue
            # Skip if looks like script+text blend (binary prefix before letters)
            raw = golden[off : off + 8]
            if raw[0] < 0x10 and raw[0] not in (0x00,) and not any(
                0xBB <= b <= 0xEE for b in raw
            ):
                # might be script — find MAY:/MOM: etc.
                if not re.match(
                    r"(?i)^(MAY|BRENDAN|MOM|WALLY|PROF|DAD|HI!|OH|HEY|THE |IF |YOU |A |MY )",
                    en.lstrip(),
                ):
                    off = eos + 1
                    continue
            slot = bytes(data[off : eos + 1])
            latin = sum(1 for b in slot if 0xBB <= b <= 0xEE)
            if latin < 25:
                off = eos + 1
                continue
            zh = scrub(en)
            cjk = sum(1 for c in zh if "\u4e00" <= c <= "\u9fff")
            # Only apply if scrub introduced meaningful CJK (not still pure EN)
            if cjk < 4:
                off = eos + 1
                continue
            # Still too English-heavy after scrub? skip (needs hand/MT)
            latin_left = len(re.findall(r"[A-Za-z]", zh))
            if latin_left > 80 and cjk < 15:
                off = eos + 1
                continue
            if put(data, golden, off, zh) == "ok":
                n += 1
            off = eos + 1
    return n


def fix_poke_qiu(data: bytearray) -> int:
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
        if data[j + 4 : j + 4 + len(qiu)] == qiu:
            old = 4 + len(qiu)
            if len(jing) <= old:
                data[j : j + old] = jing + b"\x00" * (old - len(jing))
                n += 1
        i = j + 1
    return n


def main() -> int:
    golden = GOLDEN.read_bytes()
    data = bytearray(OUT.read_bytes())

    print("=== restore free-space pointer retargets ===")
    ranges = [
        (0x000000, 0x270000),  # maps / scripts / UI ptrs
        (0xFC0000, 0x1030000),  # FC UI pool + upper
    ]
    n = restore_free_retargets(data, golden, ranges)
    print(f"  restored ptrs={n}")

    # Also restore ANY 4-byte diff in 0x100000-0x220000 where both look like 09-bank ptrs
    # (covers the 3-byte-looking diffs that are actually low 3 bytes of 09-ptrs)
    n2 = 0
    for i in range(0x100000, 0x220000, 4):
        p = int.from_bytes(data[i : i + 4], "little")
        pg = int.from_bytes(golden[i : i + 4], "little")
        if p != pg and (p >> 24) == 0x09 and (pg >> 24) == 0x09:
            data[i : i + 4] = golden[i : i + 4]
            n2 += 1
    print(f"  extra 09-bank dword restores in maps={n2}")

    print("=== clock / save time UI ===")
    nc = restore_clock_strings(data, golden)
    print(f"  clock strings restored={nc}")

    print("=== HAND dialogues ===")
    for off, zh in HAND.items():
        st = put(data, golden, off, zh)
        print(f"  {off:08X} {st}")

    # Re-apply battle menu
    def zh_bytes(s: str) -> bytes:
        enc, _ = encode_text_safe(s)
        return enc[:-1] if enc.endswith(b"\xff") else enc

    def put_menu(off: int, parts: list[bytes]) -> None:
        eos = golden.find(b"\xff", off)
        cap = eos - off + 1
        blob = b"".join(parts) + b"\xff"
        data[off : off + cap] = blob + b"\x00" * (cap - len(blob))

    put_menu(
        0xFFFB50,
        [
            zh_bytes("战斗"),
            bytes([0xFC, 0x13, 0x38]),
            zh_bytes("背包"),
            bytes([0xFE]),
            zh_bytes("宝可梦"),
            bytes([0xFC, 0x13, 0x38]),
            zh_bytes("逃跑"),
        ],
    )

    print("=== batch scrub early EN ===")
    nb = batch_scrub_early(data, golden)
    print(f"  scrubbed={nb}")

    print("=== poke球 ===")
    print(f"  fixed={fix_poke_qiu(data)}")

    # help inline
    data[0x279C0F:0x279C2B] = golden[0x279C0F:0x279C2B]
    put(data, golden, 0x279C1F, "\n救、救我！")

    # route101 script table must stay golden
    data[0x279E71:0x27A0D5] = golden[0x279E71:0x27A0D5]
    print("  route101 script tbl restored")

    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("E1E2E3E4E5E6E7E8F1F2F3F4F5F6F7F8")

    OUT.write_bytes(data)
    ROM.write_bytes(data)

    # verify ptrs
    bad = 0
    for i in range(0x100000, 0x220000, 4):
        p = int.from_bytes(data[i : i + 4], "little")
        pg = int.from_bytes(golden[i : i + 4], "little")
        if p != pg and is_free_ptr(p):
            bad += 1
    print(f"=== verify remaining free ptrs in maps={bad} ===")
    print("menu", data[0xFFFB50:0xFFFB6A].hex())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
