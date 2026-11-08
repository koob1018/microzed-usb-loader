MicroZed USB Loader — Windows full package (GUI + CLI)

Extract the entire ZIP. Run MicroZed-USB-Loader.exe with _internal beside it.
Connect USB-UART, select the serial port, then click Connect.
Drop/browse for .bit and/or .elf files, then Program FPGA, CPU or both.
Serial output continues after loading. Disconnect releases the port.

Programs run in RAM and are lost at power-off.
No driver is bundled or installed by this application. Use Driver help or DRIVERS.md.

Examples: see EXAMPLES.txt. CPU-only LED testing requires no FPGA file.
CPU ELF must be standalone ARM Cortex-A9 code compatible with existing DDR,
UART and clock initialization. XSA/FSBL/ps7_init are not applied by this tool.
If an application keeps running, start loading and press RST during U-Boot detection.
RAM helpers reserve 0x0f000000-0x0f001fff. USB-UART is not a breakpoint debugger.

Source, CLI, build instructions and known limits:
https://github.com/koob1018/microzed-usb-loader

CLI: open PowerShell in this folder and run:
  ./microzed-cli.exe --list-ports
  ./microzed-cli.exe --port COM4 --elf examples/led_test.elf --monitor
  ./microzed-cli.exe --help

Both executables share _internal. No Python installation is required.
--build-helpers uses the included source and needs ARM GCC/objcopy on PATH.
Do not connect the GUI and CLI to the same serial port simultaneously.
The separate lightweight Python CLI package requires Python and pyserial.
Original code: MIT. Other components retain their own licenses (see licenses/).
