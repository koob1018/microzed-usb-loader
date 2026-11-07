/* Runs via U-Boot `go 0x10000000`; uses its initialized UART and stack. */
typedef unsigned int u32;
#define REG(a) (*(volatile u32 *)(a))
#define LED_BIT (1u << 15) /* MIO47 = GPIO bank 1, bit 15 */
static void led(int on) {
    /* Mask all bank-1 low-half pins except MIO47. */
    REG(0xe000a008) = 0x7fff0000u | (on ? LED_BIT : 0);
    __asm__ volatile("dsb sy" ::: "memory");
}
static void delay(void) {
    /* Visible delay, deliberately approximate: depends on boot CPU clock. */
    for (volatile u32 i = 0; i < 500000; ++i) __asm__ volatile("nop");
}
static void putchar_uart(char c) {
    volatile u32 *uart = (volatile u32 *)0xe0001000;
    while (uart[0x2c/4] & 0x10) {}
    uart[0x30/4] = (unsigned char)c;
}
static void puts_uart(const char *s) {
    while (*s) {
        putchar_uart(*s++);
    }
}
static void hex(u32 value) {
    const char *digits = "0123456789abcdef";
    puts_uart("0x");
    for (int i=7;i>=0;i--) putchar_uart(digits[(value>>(i*4))&15]);
}
__attribute__((section(".text.entry"))) int entry(void) {
    puts_uart("\r\nARM LED TEST: entered\r\n");
    REG(0xf8000008) = 0xdf0d; /* unlock SLCR */
    REG(0xf80007bc) &= ~0xffu; /* MIO47 GPIO output; preserve electrical settings */
    REG(0xf8000004) = 0x767b; /* lock SLCR */
    puts_uart("MIO47 configured\r\n");
    led(0);
    REG(0xe000a244) |= LED_BIT;
    REG(0xe000a248) |= LED_BIT;
    puts_uart("GPIO output enabled\r\n");
    puts_uart("\r\nMICROZED USB-ONLY ARM TEST: PASS\r\nPSS_IDCODE=");
    hex(*(volatile u32 *)0xf8000530);
    puts_uart("\r\nPL GPIO bank2="); hex(*(volatile u32 *)0xe000a068);
    puts_uart("\r\nPL GPIO bank3="); hex(*(volatile u32 *)0xe000a06c);
    if (REG(0xe000a068) != 0xeef85532u || REG(0xe000a06c) != 0xb3d58bbeu) {
        puts_uart("\r\nFPGA SIGNATURE: FAIL; LED remains off.\r\n");
        return 1;
    }
    puts_uart("\r\nFPGA SIGNATURE: PASS; blinking D3 six times.\r\n");
    for (int i = 0; i < 6; ++i) {
        led(1); delay();
        if (!(REG(0xe000a064) & LED_BIT)) {
            led(0); puts_uart("LED GPIO READBACK: FAIL\r\n"); return 2;
        }
        led(0); delay();
        if (REG(0xe000a064) & LED_BIT) {
            puts_uart("LED GPIO READBACK: FAIL\r\n"); return 3;
        }
    }
    led(1);
    puts_uart("LED GPIO READBACK: PASS; D3 stays on.\r\n");
    puts_uart("\r\nReturning to U-Boot.\r\n");
    return 0;
}
