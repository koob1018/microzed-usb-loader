MicroZed USB Loader v1.1.0 — RAM only

Extract the entire ZIP. Run MicroZed-USB-Loader.exe with _internal beside it.
Connect USB-UART, select the serial port, then click Connect.
Drop/browse for .bit and/or .elf files, then Program FPGA, CPU or both.
Serial output continues after loading. Disconnect releases the port.

There is no Flash writing or automatic-startup setup in this version.
Loaded programs are lost at power-off. Existing Flash contents are unchanged.
No driver is bundled or installed by this application. Use Driver help or DRIVERS.md.

Examples: see EXAMPLES.txt. CPU-only LED testing requires no FPGA file.
CPU ELF must be standalone ARM Cortex-A9 code compatible with existing DDR,
UART and clock initialization. XSA/FSBL/ps7_init are not applied by this tool.
If an application keeps running, start loading and press RST during U-Boot detection.
RAM helpers reserve 0x0f000000-0x0f001fff. USB-UART is not a breakpoint debugger.

Source, CLI, build instructions and known limits:
https://github.com/koob1018/microzed-usb-loader

CLI requires Python and pyserial only. It supports --monitor and --build-helpers.
Original code: MIT. Other components retain their own licenses (see licenses/).
