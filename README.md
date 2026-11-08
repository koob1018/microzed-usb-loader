# MicroZed USB Loader

Load FPGA `.bit` and standalone ARM CPU `.elf` files through the MicroZed USB-UART cable using the factory U-Boot. No JTAG adapter, Ethernet cable or microSD card is required for the verified setup.

**[Download the latest release](https://github.com/koob1018/microzed-usb-loader/releases/latest)**

Choose the Windows GUI or the lightweight Python CLI. Both load programs into RAM for immediate execution; loaded programs are lost at power-off. Drivers are installed separately; see [driver setup](DRIVERS.md).

## Windows GUI

1. Extract **MicroZed-USB-Loader.zip** completely and run the executable. Keep `_internal` alongside it.
2. Connect USB-UART, select the serial port, and click **Connect**. If no port appears, use **Driver help**, then **Refresh**.
3. Drop or browse for a `.bit` and/or `.elf` file.
4. Click **Program FPGA**, **Program CPU** or **Program both**. All loads use RAM.
5. The connection remains open for serial output. Click **Disconnect** to release it.

The packaged GUI needs no Python, Vivado or Vitis installation. File selections start empty.

## Command line (Windows / Linux / macOS)

Download **MicroZed-USB-Loader-CLI.zip** or clone the repository, then run from its root. Python 3.10+ and **pyserial only** are required; Qt is not needed.

```text
python -m pip install -r gui/requirements-cli.txt
python gui/cli.py --list-ports
python gui/cli.py --port COM4 --elf build/led_test.elf --monitor
python gui/cli.py --port COM4 --bit build/usb_probe.bit
python gui/cli.py --port COM4 --bit build/usb_probe.bit --elf build/hello.elf --monitor
```

Use your actual port: for example `/dev/ttyUSB0` on Linux or `/dev/cu.usbserial-0001` on macOS. `--ram` is accepted for compatibility but optional.

Monitor without loading or sending boot commands:

```text
python gui/cli.py --port COM4 --monitor
```

Press **Ctrl+C** to stop monitoring and release the serial port. During an interrupted download the tool attempts to cancel reception and restore the console; if recovery is not confirmed, press **RST** before retrying. Do not connect the GUI and CLI to the same port simultaneously.

### Build helpers from source

To avoid precompiled helper binaries, install `arm-none-eabi-gcc` and `arm-none-eabi-objcopy` on PATH:

```text
python gui/cli.py --port COM4 --elf build/led_test.elf --build-helpers --monitor
```

This compiles `cache_sync`, `uart_speed` and `backup_sender` into a temporary directory and uses the freshly built RAM helpers for that session. `backup_sender` is retained as buildable source for review, but the RAM-only loader does not upload or use it. No vendor FPGA tools are required to compile these helpers. See [BUILD.md](BUILD.md).

## LED example

CPU-only: `build/led_test.elf` (GUI ZIP: `examples/led_test.elf`) blinks D3 six times and leaves it on, then returns to U-Boot. No FPGA file is needed.

Combined test: `build/usb_probe.bit` with `build/hello.elf` (GUI ZIP: `examples/fpga_cpu_test.elf`) checks an FPGA signature before blinking D3.

## How it works and compatibility

U-Boot receives data into DDR using YMODEM. A RAM helper switches transfers to 921600 and restores the 115200 console. U-Boot configures the FPGA through PCAP and starts CPU code at the ELF entry point. CRC32 verifies transfers.

- Hardware tested on MicroZed XC7Z020-1CLG400 with factory 2013 U-Boot, Windows 11 x64. Linux/macOS CLI support uses portable Python/pyserial; hardware validation on those hosts is not yet claimed.
- CPU files must be standalone ARM Cortex-A9 executables, not Linux programs. Existing PS clocks, DDR and MIO initialization must match the design. The loader does not apply an XSA, ps7_init.tcl or FSBL.
- Helpers reserve `0x0f000000–0x0f001fff`; overlapping CPU images are rejected.
- If a running program does not return, start loading and press RST while the tool waits for U-Boot. This tool does not provide breakpoint debugging.
- CPU programs execute with board-level privileges, so load only code you trust.

See [driver setup](DRIVERS.md), [validation](VALIDATION.md) and [changes](CHANGELOG.md).

## Develop the GUI

```text
python -m venv gui/.venv
gui/.venv/Scripts/python.exe -m pip install -r gui/requirements.txt
gui/.venv/Scripts/python.exe -m pytest gui/tests -q
gui/.venv/Scripts/python.exe gui/app.py
```

On Windows, run `gui/build.ps1` to package the GUI. Original code is MIT licensed; see [third-party notices](THIRD_PARTY_NOTICES.md).

## Acknowledgements

Thanks to Shiming Li for testing the tool, contributing the initial CLI with monitoring and source-built helpers, and suggesting the RAM-only workflow and separate driver installation.
