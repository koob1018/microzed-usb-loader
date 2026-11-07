MicroZed USB Loader

QUICK START
1. Extract the entire ZIP and run MicroZed-USB-Loader.exe. Keep _internal beside it.
2. Connect the MicroZed 7020 USB-UART port and select its CP210x serial port, then click Connect.
   Driver status is checked at startup. If needed, click Install driver above the serial port.
   Python, Vivado and Vitis are not required to run this application.
   Disconnect releases the port. Downloads keep the connection open.
   File paths are not saved; each launch starts with empty file selections.
3. Drop .bit and/or .elf files, browse for them, or paste their paths.
4. Choose Save to Flash (default) or Run from RAM, then Program FPGA, Program CPU, or Program both.

TEMPORARY LOADING
Files are transferred to DDR over USB-UART. Transfer speed switches automatically
and returns to the normal console setting before configuration or CPU execution.
No speed selection is needed. FPGA configuration uses PCAP;
CPU execution starts at the ELF entry point. When loading both, FPGA is configured before CPU execution.
The loader parses ELF segments, clears BSS, and converts .bit files automatically.
Temporary contents are lost when power is removed. No manual .bin conversion is needed.

FLASH MODE
Saved files run on the next boot. Updating one component preserves the other.
The loader automatically backs up the writable area and verifies Flash readback.
The factory U-Boot and Linux regions are preserved.
The file area is limited to 576 KiB, including metadata and helper code.
Oversized designs are rejected; use temporary loading or reduce the design size.
Keep USB connected and power on during writes.
Automatic backups and operation logs are stored under:
%LOCALAPPDATA%\MicroZedLoader
This application does not offer a backup restoration or open-log-folder action.

COMPATIBILITY
MicroZed XC7Z020-1CLG400 with initialized DDR and UART1.
Flash mode requires the verified 2013 factory U-Boot/Linux layout and a valid
Flash environment. Other firmware layouts are rejected.
CPU ELF files must be compatible ARM Cortex-A9 standalone executables, not Linux programs.
The loader uses existing U-Boot PS initialization. It does not execute XSA,
ps7_init.tcl or a custom FSBL. The RAM transfer helper reserves
0x0f001000-0x0f001fff; CPU executables overlapping it are rejected. PS clocks, MIO and DDR settings must be compatible.
A verified transfer does not prove that an arbitrary application works correctly.
Continuous applications may require pressing RST before another download:
start the operation, then press RST while the loader waits for U-Boot.
USB-UART does not provide breakpoint debugging.
Board-generated serial text and user file names are displayed as received.

EXAMPLES
examples/led_test.elf blinks D3 without requiring an FPGA file.
examples/usb_probe.bit + examples/fpga_cpu_test.elf validate the FPGA signature and
blink D3 six times, then leave it on. D3 is connected to PS MIO47.

DEVELOPMENT
Python 3.12. Dependencies are listed in requirements.txt. Run python app.py.
build.ps1 creates the Windows folder distribution and ZIP.
tests runs without a connected board and uses synthetic Flash fixtures.
See the repository VALIDATION.md for hardware acceptance results.

UI VALIDATION
Empty or invalid targets disable their programming buttons. FPGA-only operations
do not require a CPU file, and CPU-only operations do not require an FPGA file.
Program both requires both valid files. Clear removes a selection.
Widget tests run offscreen; native Windows layout is inspected separately.

USB DRIVER SETUP
The official Silicon Labs CP210x 11.3.0 driver is included for offline installation.
At startup and on Refresh, the button above the serial port shows Driver installed
or Install driver. Installation starts only when you click Install driver.
Approve the Windows administrator prompt. Cancellation is supported; you can retry.
The package signature is verified before installation. No automatic reboot,
driver removal, or forced downgrade is used. Reconnect USB and refresh if needed.
Original vendor files and license are in _internal/assets/cp210x/.
Official site: https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers
