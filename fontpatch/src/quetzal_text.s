.include "./include/text.h"
.include "./include/gba/defines.h"
.include "./include/constants/global.h"

; DEBUG_SOLID_GLYPH=1: Chinese path fills a solid block then CopyGlyph (proves path).
; Set 0 to use real Wokann 1bpp fonts again.
.definelabel DEBUG_SOLID_GLYPH, 0
; DEBUG_SKIP_JP_CHECK=1: never treat printer+0x21 as japanese (Wokann offset may be wrong).
.definelabel DEBUG_SKIP_JP_CHECK, 1

.func A8StyleChinese
    ldrb r3,[r0]
    add r0,1
    str r0,[r6]

    push {r2-r6}
    ldrb r1,[r0]
    mov r0,r3
    ldrb r2,[r6,5]
    .if DEBUG_SKIP_JP_CHECK
    mov r3,0
    .else
    mov r3,r6
    add r3,0x21
    ldrb r3,[r3]
    .endif
    bl ChineseCodeCheck
    cmp r1,1
    beq @@CheckSuccess

 @@CheckFailure:
    ; Vanilla CharRead keeps the raw byte in r2, then r0 = r2 - 0xF8.
    ; Without restoring r2, Latin/FC control glyphs draw blank (only Chinese path worked).
    pop {r2-r6}
    mov r2,r3
    mov r0,r3
    sub r0,0xF8
    ldr r1,=(Quetzal_RenderText_AfterRead|1)
    bx r1
    .pool

 @@CheckSuccess:
    cmp r0,0x3E
    ble @@DoNotJumpDouble
    push {r0}
    ldr r0,[r6]
    add r0,1
    str r0,[r6]
    pop {r0}
 @@DoNotJumpDouble:
    .if DEBUG_SOLID_GLYPH
    ; Prove Chinese+CopyGlyph: solid 12x15 glyph, ignore font decode.
    ldr r1,=gCurGlyph
    mov r2,0
    mvn r3,r2
 @@SolidFill:
    str r3,[r1,r2]
    add r2,4
    cmp r2,0x80
    blt @@SolidFill
    mov r2,0x80
    add r2,r1
    mov r3,12
    strb r3,[r2]
    mov r3,15
    strb r3,[r2,1]
    pop {r2-r6}
    ldr r0,=(Quetzal_RenderText_CopyGlyph|1)
    bx r0
    .pool
    .else
    mov r1,r2
    ldr r2,=gCurGlyph
    bl DecompressGlyph_Chinese
    pop {r2-r6}
    ldr r0,=(Quetzal_RenderText_CopyGlyph|1)
    bx r0
    .pool
    .endif
.endfunc

.func ChineseCodeCheck
    push {lr}
    cmp r3,1
    beq @@NotChinese
    cmp r2,FONT_BRAILLE
    beq @@NotChinese
    cmp r0,0x36
    blt @@IfChineseChar
    cmp r0,0x3E
    bgt @@NotChinese
    b @@HasChinese
 @@IfChineseChar:
    cmp r0,1
    blt @@NotChinese
    cmp r0,0x1E
    bgt @@NotChinese
    cmp r0,6
    beq @@NotChinese
    cmp r0,0x1B
    beq @@NotChinese
    cmp r1,0xF7
    bge @@NotChinese
    lsl r0,r0,8
    add r0,r0,r1
 @@HasChinese:
    mov r1,1
    b @@Ret
 @@NotChinese:
    mov r1,0
 @@Ret:
    pop {pc}
.endfunc

.func DecompressGlyph_Chinese
    push {r4-r6,lr}
    mov r4,r0
    mov r6,r2
    mov r0,r1
    bl GetChineseFontWidthFunc
    mov r2,r0
    mov r5,0x80
    add r5,r6
    strb r2,[r5]
    add r2,3
    add r5,1
    strb r2,[r5]
    mov r0,r4
    cmp r0,0x3E
    bgt @@CaluChineseChar
    mov r2,0x36
    sub r2,r0,r2
    mov r3,0
    b @@SelectGlyph
 @@CaluChineseChar:
    lsr r3,r0,0x8
    lsl r2,r4,0x18
    lsr r2,r2,0x18
    cmp r3,0x6
    blt @@SubChs_1h_5h
    cmp r3,0x1b
    blt @@SubChs_7h_1Ah
    sub r3,0x1
 @@SubChs_7h_1Ah:
    sub r3,0x1
 @@SubChs_1h_5h:
    sub r3,0x1
    mov r0,0xF7
    mul r3,r0
    add r2,r2,r3
    mov r3,1
 @@SelectGlyph:
    cmp r1,0
    beq @@SelectBigGlyph
    b @@SelectSmallGlyph
 @@SelectBigGlyph:
    mov r0,0x10
    mul r2,r0
    mov r0,11
    mov r1,1
    cmp r3,0
    beq @@BigGlyphPunctuation
    b @@BigGlyphChar
 @@SelectSmallGlyph:
    mov r0,0xB
    mul r2,r0
    mov r0,9
    mov r1,2
    cmp r3,0
    beq @@SmallGlyphPunctuation
    b @@SmallGlyphChar
 @@BigGlyphPunctuation:
    ldr r5,=PokePunctuationChsNormal
    b @@GetGlyphAddress
 @@SmallGlyphPunctuation:
    ldr r5,=PokePunctuationChsSmall
    b @@GetGlyphAddress
 @@BigGlyphChar:
    ldr r5,=PokeFontChsNormal
    b @@GetGlyphAddress
 @@SmallGlyphChar:
    ldr r5,=PokeFontChsSmall
 @@GetGlyphAddress:
    mov r3,r1
    mov r1,r2
    mov r2,r0
    mov r0,r5
    bl Convert1bppTo2bpp
    mov r5,r0
    mov r0,r5
    mov r1,r6
    ldr r3,=(DecompressGlyphTile|1)
    bl @@call_r3
    add r5,0x10
    add r6,0x20
    mov r0,r5
    mov r1,r6
    ldr r3,=(DecompressGlyphTile|1)
    bl @@call_r3
    add r5,0x10
    add r6,0x20
    mov r0,r5
    mov r1,r6
    ldr r3,=(DecompressGlyphTile|1)
    bl @@call_r3
    add r5,0x10
    add r6,0x20
    mov r0,r5
    mov r1,r6
    ldr r3,=(DecompressGlyphTile|1)
    bl @@call_r3
    pop {r4-r6,pc}
 @@call_r3:
    bx r3
    .pool
.endfunc

.func Convert1bppTo2bpp
    push {r2-r7}
    mov r7,r2
    add r6,r0,r1
    ldr r5,=ChsGlyphScratch
    mov r0,0
    mov r2,0
 @@LoopInitClean:
    str r0,[r5,r2]
    add r2,4
    cmp r2,0xC0
    blt @@LoopInitClean
    mov r0,0
 @@LoopEmptyLine:
    cmp r0,r3
    bge @@DrawGlyphTile
    add r5,r5,2
    add r0,r0,1
    b @@LoopEmptyLine
 @@DrawGlyphTile:
    mov r2,0
    mov r4,0
    mov r3,0
 @@LoopDrawGlyphTile:
 @@SubLoopAddByte:
    lsl r4,r4,8
    ldrb r0,[r6]
    add r6,r6,1
    orr r4,r0
    mov r0,r4
    add r2,8
    cmp r2,r7
    blt @@SubLoopAddByte
    sub r2,r2,r7
    lsr r0,r2
    mov r1,16
    sub r1,r1,r7
    lsl r0,r1
    strh r0,[r5]
    add r5,r5,2
    mov r1,1
    lsl r1,r2
    sub r1,r1,1
    and r4,r1
    add r3,r3,1
    cmp r3,r7
    blt @@LoopDrawGlyphTile
    ldr r7,=ChsGlyphScratch
    ldr r6,=(ChsGlyphScratch+0x40)
    mov r5,0
 @@Loop16x162bpp:
    mov r4,8*2-1
    mov r3,8*4
    mov r2,0
    mov r1,0
 @@SubLoop16x162bppLinePiexl:
    sub r3,r3,1
    ldrh r0,[r7]
    push {r1}
    mov r1,1
    lsl r1,r4
    and r0,r1
    lsr r0,r4
    pop {r1}
    cmp r0,0
    beq @@SkipDraw
    lsl r0,r3
    orr r1,r0
    lsr r0,r0,2
    orr r1,r0
    lsl r0,r0,1
    orr r2,r0
    push {r1,r2}
    mov r2,1
    lsl r2,r3
    ldr r1,[r6]
    and r1,r2
    cmp r1,0
    beq @@NotOverlap
    ldr r1,[r6]
    eor r1,r2
    str r1,[r6]
 @@NotOverlap:
    pop {r1,r2}
 @@SkipDraw:
    sub r4,r4,1
    sub r3,r3,1
    cmp r3,2
    bge @@SubLoop16x162bppLinePiexl
    str r1,[r6,4]
    ldr r1,[r6]
    orr r2,r1
    str r2,[r6]
    add r5,r5,1
    add r6,r6,4
    add r7,r7,2
    cmp r5,16
    blt @@Loop16x162bpp
    ldr r4,=(ChsGlyphScratch+0x40)
    ldr r5,=(ChsGlyphScratch+0x80)
    mov r1,0
 @@LoopCut:
    mov r2,0
 @@SubLoopCutHalf:
    ldrh r0,[r4,2]
    strh r0,[r5]
    ldrh r0,[r4]
    strh r0,[r5,0x10]
    add r4,r4,4
    add r5,r5,2
    add r2,r2,1
    cmp r2,8
    blt @@SubLoopCutHalf
    add r5,0x10
    add r1,1
    cmp r1,2
    blt @@LoopCut
    ldr r0,=(ChsGlyphScratch+0x80)
    mov r1,0
    pop {r2-r7}
    bx lr
    .pool
.endfunc

.func GetChineseFontWidthFunc
    push {lr}
    cmp r0,FONT_SMALL
    beq @@S
    cmp r0,FONT_SMALL_NARROW
    beq @@S
    cmp r0,FONT_NARROW
    beq @@S
    mov r0,0xC
    mov r1,0
    pop {pc}
 @@S:
    mov r0,0xA
    mov r1,1
    pop {pc}
.endfunc
