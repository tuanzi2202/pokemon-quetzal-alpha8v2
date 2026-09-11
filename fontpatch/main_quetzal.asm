.gba
.open Origin_Rom,0x08000000

.include "./include/text.h"

.thumb
; Same divert as Alpha8v2 @ RenderText CharRead
.org Quetzal_RenderText_CharRead
    ldr r0,[r6]
    ldr r3,=(A8StyleChinese|1)
    bx r3
    nop
.pool

.org HackCodeAddresses
.thumb
.include "./src/quetzal_text.s"

; Wokann 1bpp fonts (match locale PMRSEFRLG encoding)
.org HackFontAddresses
.align 4
PokePunctuationChsNormal:
    .incbin "./graphics/fonts/gba_chs_punctuation_11x11.bin"
PokeFontChsNormal:
    .incbin "./graphics/fonts/gba_chs_font_11x11.bin"
.align 4
PokePunctuationChsSmall:
    .incbin "./graphics/fonts/gba_chs_punctuation_9x9.bin"
PokeFontChsSmall:
    .incbin "./graphics/fonts/gba_chs_font_9x9.bin"

.close
