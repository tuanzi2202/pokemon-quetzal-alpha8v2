.ifndef TEXT_H
.definelabel TEXT_H,0

.definelabel gCurGlyph,                 0x03003090
.definelabel DecompressGlyphTile,       0x08004C08
.definelabel CopyGlyphToWindow,         0x08004D98

; REAL RenderText used by FontNormal/etc (BL 0x800588C) — NOT the dead copy at 0x21CBB8.
.definelabel Quetzal_RenderText,            0x0800588C
.definelabel Quetzal_RenderText_CharRead,   0x0800596C
.definelabel Quetzal_RenderText_AfterRead,  0x08005978
.definelabel Quetzal_RenderText_CopyGlyph,  0x08005D34

; Dead relocated copy (never BL'd by font funcs) — keep labels for docs only
.definelabel Quetzal_RenderText_DEAD,           0x0821CBB8
.definelabel Quetzal_RenderText_CharRead_DEAD,  0x0821CC68

.definelabel FONT_SMALL,            0
.definelabel FONT_NORMAL,           1
.definelabel FONT_SHORT,            2
.definelabel FONT_SHORT_COPY_1,     3
.definelabel FONT_SHORT_COPY_2,     4
.definelabel FONT_SHORT_COPY_3,     5
.definelabel FONT_BRAILLE,          6
.definelabel FONT_NARROW,           7
.definelabel FONT_SMALL_NARROW,     8
.definelabel FONT_BOLD,             9

.definelabel HackCodeAddresses,         0x08EB9878
.definelabel HackFontAddresses,         0x09D9B5A8
.definelabel ChsGlyphScratch,           0x0203FF40

.endif
