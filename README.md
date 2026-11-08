# MicroZed USB Loader

Load FPGA `.bit` and standalone ARM CPU `.elf` files through the MicroZed USB-UART cable using the factory U-Boot. No JTAG adapter, Ethernet cable or microSD card is required for the verified setup.

**[Download the latest release](https://github.com/koob1018/microzed-usb-loader/releases/latest)**

Choose the Windows full package (GUI + CLI) or the lightweight cross-platform Python CLI. Both load programs into RAM for immediate execution; loaded programs are lost at power-off. Drivers are installed separately; see [driver setup](DRIVERS.md).

## Windows full package (GUI + CLI)

1. Extract **MicroZed-USB-Loader.zip** completely and run the executable. Keep `_internal` alongside it.
2. Connect USB-UART, select the serial port, and click **Connect**. If no port appears, use **Driver help**, then **Refresh**.
3. Drop or browse for a `.bit` and/or `.elf` file.
4. Click **Program FPGA**, **Program CPU** or **Program both**. All loads use RAM.
5. The connection remains open for serial output. Click **Disconnect** to release it.

Both Windows executables work without installing Python, pyserial, Vivado or Vitis. They share the `_internal` runtime directory. File selections start empty.

For the CLI, open PowerShell in the extracted folder:

```powershell
./microzed-cli.exe --list-ports
./microzed-cli.exe --port COM4 --elf examples/led_test.elf --monitor
./microzed-cli.exe --port COM4 --bit examples/usb_probe.bit --elf examples/fpga_cpu_test.elf
```

Use `--help` for options. `--build-helpers` is also available in the executable; it uses the included helper sources and requires ARM GCC and objcopy on PATH.

## Lightweight CLI (Windows / Linux / macOS)

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

Run from the extracted Windows full-package folder (replace `COM4` with your port):

```powershell
./microzed-cli.exe --port COM4 --elf examples/led_test.elf --monitor
```

Or from the lightweight CLI package / repository root:

```text
python gui/cli.py --port COM4 --elf build/led_test.elf --monitor
```

In the GUI, select `examples/led_test.elf` under **CPU**, connect the serial port, then click **Program CPU**. Leave the FPGA field empty. D3 should blink six times and remain on; the serial output should report `LED GPIO READBACK: PASS`. Press Ctrl+C to exit CLI monitoring.

Combined FPGA + CPU example, which checks an FPGA signature before blinking D3:

```powershell
./microzed-cli.exe --port COM4 --bit examples/usb_probe.bit --elf examples/fpga_cpu_test.elf --monitor
```

```text
python gui/cli.py --port COM4 --bit build/usb_probe.bit --elf build/hello.elf --monitor
```

Example C source: [LED test](src/led_test.c) and [combined FPGA/CPU test](src/hello.c). See [BUILD.md](BUILD.md) to rebuild them.

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

Thanks to Shiming Li for testing the tool and contributing the initial CLI with monitoring and source-built helpers.
