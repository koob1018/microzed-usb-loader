ENTRY(entry)
SECTIONS
{
  . = 0x0f001000;
  .text : { KEEP(*(.text.entry)) *(.text*) *(.rodata*) }
  .data : { *(.data*) }
  .bss : { *(.bss*) *(COMMON) }
  ASSERT(. <= 0x0f002000, "UART helper exceeds reserved memory")
}
