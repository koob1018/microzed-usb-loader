# MicroZed USB Loader

A Windows GUI for loading FPGA `.bit` files and ARM Cortex-A9 CPU `.elf` programs onto a MicroZed 7020 through its USB-UART cable. No JTAG adapter, Ethernet cable or microSD card is required for the verified setup.

**[Download the Windows application](https://github.com/koob1018/microzed-usb-loader/releases/latest)**

## Quick start

1. Download and extract **MicroZed-USB-Loader.zip**. Keep the executable and `_internal` folder together.
2. Connect the board's USB-UART port. If the driver is missing, click **Install driver** and approve the Windows administrator prompt.
3. Select the serial port and click **Connect**.
4. Drop or browse for a `.bit` and/or `.elf` file.
5. Choose **Run from RAM** for temporary loading or **Save to Flash** for automatic startup after power-on.
6. Click **Program FPGA**, **Program CPU**, or **Program both**.

File selections start empty. Transfer speed switches automatically; no baud-rate setting is needed. Vivado, Vitis and Python are not needed to run the packaged application.

## LED example

Select `examples/led_test.elf`, choose **Run from RAM**, then click **Program CPU**. D3 blinks six times and stays on. This example needs no FPGA file.

For a combined test, select `examples/usb_probe.bit` and `examples/fpga_cpu_test.elf`. The CPU checks an FPGA signature and blinks D3. See [example instructions](gui/EXAMPLES.txt).

## How it works

The loader uses existing U-Boot and transfers data into DDR using YMODEM. A RAM helper temporarily switches UART transfers to 921600, then restores the 115200 console. U-Boot configures the FPGA through PCAP and launches the CPU program at its ELF entry point. Every transfer is checked with CRC32.

Flash mode backs up the writable region, writes and verifies the payload, then updates the boot environment. Updating only one component preserves the other saved component.

## Compatibility and limits

- Tested on one MicroZed **XC7Z020-1CLG400**, with the verified 2013 factory U-Boot/Linux layout and CP210x USB-UART, on Windows 11 x64.
- Factory U-Boot and Linux remain protected. The application area is **576 KiB**, including metadata and helper code. Larger files can use RAM mode, subject to RAM/address limits.
- CPU executables must be compatible standalone ARM programs, not Linux applications. The loader does not apply an XSA, `ps7_init.tcl` or a new FSBL. PS clocks, DDR and MIO configuration must match the running setup.
- Helpers reserve `0x0f000000–0x0f001fff`. Overlapping CPU images are rejected.
- If a previous program does not return, start the operation and press **RST** while the tool waits for U-Boot. Keep power connected during Flash writes.
- This is a loader, not a breakpoint debugger. Arbitrary boards or firmware layouts are not supported.

## Build from source

Use Python 3.12 on Windows:

```powershell
python -m venv gui/.venv
gui/.venv/Scripts/python.exe -m pip install -r gui/requirements.txt
gui/.venv/Scripts/python.exe -m pytest gui/tests -q
gui/.venv/Scripts/python.exe gui/app.py
./gui/build.ps1
```

Prebuilt demonstration files and RAM helpers are included. Original C sources and linker scripts are under `src/` and `persistent/`; FPGA generation is in `scripts/build_pl.tcl`. Rebuilding these requires AMD tools. See [build instructions](BUILD.md).

## Validation

Hardware checks covered eight repeated transfers, CRC verification, interrupted-transfer recovery, FPGA DONE, CPU execution, serial connection retention, Flash readback and automatic startup. Test Flash contents were restored afterward.

The same 256 KiB payload took **36.5 s at the original speed and 16.3 s with automatic switching** (about 2.2x). A small FPGA + LED CPU example took **26.7 s** in RAM mode and **90.1 s** in Flash mode, including applicable verification/backup steps. Times vary with payload and setup. See [validation notes](VALIDATION.md).

## License

Original code is MIT licensed: use, modify and redistribute it with the copyright and license notice. Bundled third-party components retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
