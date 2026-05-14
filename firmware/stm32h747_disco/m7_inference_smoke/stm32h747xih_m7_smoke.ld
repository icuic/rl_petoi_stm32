ENTRY(main)

MEMORY
{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 1024K
  RAM_D1 (xrw): ORIGIN = 0x24000000, LENGTH = 512K
}

_estack = ORIGIN(RAM_D1) + LENGTH(RAM_D1);

SECTIONS
{
  .isr_vector :
  {
    KEEP(*(.isr_vector))
  } > FLASH

  .text :
  {
    *(.text*)
    *(.rodata*)
    KEEP(*(.init))
    KEEP(*(.fini))
    . = ALIGN(4);
    _etext = .;
  } > FLASH

  .ARM.extab :
  {
    *(.ARM.extab* .gnu.linkonce.armextab.*)
  } > FLASH

  .ARM.exidx :
  {
    __exidx_start = .;
    *(.ARM.exidx* .gnu.linkonce.armexidx.*)
    __exidx_end = .;
  } > FLASH

  _sidata = LOADADDR(.data);

  .data :
  {
    _sdata = .;
    *(.data*)
    . = ALIGN(4);
    _edata = .;
  } > RAM_D1 AT> FLASH

  .bss :
  {
    _sbss = .;
    *(.bss*)
    *(COMMON)
    . = ALIGN(4);
    _ebss = .;
  } > RAM_D1

  ._user_heap_stack (NOLOAD) :
  {
    . = ALIGN(8);
    . = . + 0x400;
    . = . + 0x1000;
    . = ALIGN(8);
  } > RAM_D1

  /DISCARD/ :
  {
    *(.note*)
    *(.comment*)
  }
}
