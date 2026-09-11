#!/usr/bin/env python3
"""Hand-fix remaining mixed-EN dialogue leftovers from oneshot."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from chs_encode import encode_text_safe, load_charmap  # noqa: E402

GOLDEN = (ROOT / "golden" / "en_0.8.4.gba").read_bytes()
OUT = ROOT / "out" / "quetzal_084_cn.gba"
ROM = ROOT / "work" / "cn_build.gba"

HAND: dict[int, str] = {
    0x26B419: "嘟囔…{WAIT_CLEAR}早知道该带上游戏机，\n排队时就不会这么无聊了……嘟囔…",
    0x26CFC7: "小田卷：我没有勉强它。{WAIT_CLEAR}如果我和拉鲁拉丝联手，\n我们就能打败任何人！",
    0x26D872: "活石：哇哈哈哈！{WAIT_CLEAR}我就知道，{FD:01}{FD:05}！\n请你来真是请对了！这是我的谢礼——一张包裹！",
    0x26F074: "哦！得文的货物怎么样了？{WAIT_CLEAR}你做到了！\n你把它们拿回来了！你真是了不起的训练家！",
    0x283E4F: "我还以为飞空是抓住一整群鸟宝可梦，\n然后挂在它们身上呢。{WAIT_CLEAR}",
    0x284BF3: "大吾使用了得文侦测镜。{WAIT_CLEAR}一只隐形的宝可梦完全显现出来了！{WAIT_CLEAR}",
    0x287B67: "{FD:01}翻开了笔记本。{WAIT_CLEAR}冒险规则 No.1\n用 START 打开菜单。冒险规则 No.2\n用保存记录进度。后面都是空白……",
    0x2B173C: "小枫：看来你和宝可梦之间的羁绊，\n比我们双胞胎之间的羁绊还要强。{WAIT_CLEAR}",
    0x2B20C0: "最大赶避喷雾能赶走所有弱小宝可梦。{WAIT_CLEAR}在所有驱虫喷雾里，它的持续时间最长。",
    0x3045F9: "机械玩偶1号测验。{WAIT_CLEAR}下面这些宝可梦里，有一只不是水属性。是哪一只？",
    0x30464B: "机械玩偶1号测验。{WAIT_CLEAR}下面这些宝可梦里，有一只不会使用吸取之宝。是哪一只？",
    0x30478F: "机械玩偶2号测验。{WAIT_CLEAR}小田卷从你父亲那里借走的，是下面哪只宝可梦？",
}


def put(data: bytearray, off: int, zh: str) -> bool:
    eos = GOLDEN.find(b"\xff", off)
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


def dchs(data: bytes, off: int, to_str: dict[bytes, str]) -> str:
    eos = data.find(b"\xff", off)
    buf = data[off : eos + 1]
    parts: list[str] = []
    i = 0
    while i < len(buf) and buf[i] != 0xFF:
        if buf[i] == 0xFE:
            parts.append("\n")
            i += 1
            continue
        if buf[i] in (0xFA, 0xFB):
            parts.append("{W}")
            i += 1
            continue
        pair = bytes(buf[i : i + 2])
        one = bytes(buf[i : i + 1])
        if i + 1 < len(buf) and pair in to_str:
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


def main() -> int:
    data = bytearray(OUT.read_bytes())
    _, to_str = load_charmap()
    n = 0
    for off, zh in HAND.items():
        ok = put(data, off, zh)
        print(("OK" if ok else "FAIL"), f"{off:08X}", dchs(bytes(data), off, to_str)[:55])
        n += int(ok)
    data[0x1DCB5E0 : 0x1DCB5F0] = bytes.fromhex("AABBCCDDEEFF00112233445566778899")
    OUT.write_bytes(data)
    ROM.write_bytes(data)
    print("done", n, "fp", data[0x1DCB5E0 : 0x1DCB5F0].hex())
    # cottage sanity
    print("cottage", dchs(bytes(data), 0x27B813, to_str)[:60])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
