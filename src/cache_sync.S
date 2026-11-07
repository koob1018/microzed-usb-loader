/* Fixed-address helper for factory U-Boot: DDR writes do not invalidate I-cache.
 * Only supports the measured MMU-off, D-cache-off environment. Preserve args.
 * Keep this helper immutable at 0x0f000000 across application downloads.
 */
.syntax unified
.arm
.section .text.entry,"ax"
.global entry
entry:
    mrc p15, 0, r2, c1, c0, 0
    tst r2, #5
    movne r0, #1
    bxne lr
    mov r2, #0
    dsb sy
    mcr p15, 0, r2, c7, c5, 0
    mcr p15, 0, r2, c7, c5, 6
    dsb sy
    isb sy
    mov r0, #0
    bx lr
