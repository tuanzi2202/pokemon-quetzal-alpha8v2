格查尔 0.8.4 中文字库说明
========================

字形二进制与补丁逻辑不在本目录重复存放，统一见：

  ../fontpatch/graphics/fonts/
    gba_chs_font_11x11.bin
    gba_chs_font_9x9.bin
    gba_chs_punctuation_11x11.bin
    gba_chs_punctuation_9x9.bin

  ../fontpatch/PMRSEFRLG_charmap.txt   — 卧看微尘码表（汉字双字节）
  ../fontpatch/include/text.h          — Quetzal 适配钩子地址
  ../fontpatch/build.bat               — 打入 work/cn_build.gba

编码规则（摘要）
----------------
- 西文：绿宝石 Gen3 单字节（与 gen3_charmap.py 一致）
- 汉字：hi 0x01–0x1E（跳过 0x06/0x1B），lo 0x00–0xF6
- 终止符 0xFF；换行 0xFE；控制符 FA/FB/FC/FD/F9 保留

缺字
----
apply_text.py / chs_encode.encode_text_safe：未收录字回退为「?」并统计 missing。
