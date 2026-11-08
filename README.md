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

## CLI reference

Both packages accept the same options; only the launch command and bundled example paths differ.

| Package | Launch command | Example files |
| --- | --- | --- |
| Windows full package | `./microzed-cli.exe` | `examples/` |
| Lightweight CLI / repository | `python gui/cli.py` | `build/` |

Run commands from the extracted package folder (repository root for source users). On systems where Python is named `python3`, use `python3` instead of `python`.

### Syntax and options

```text
./microzed-cli.exe --help
./microzed-cli.exe --list-ports
./microzed-cli.exe --port PORT [--bit FILE] [--elf FILE] [--ram] [--build-helpers] [--monitor]

python gui/cli.py --help
python gui/cli.py --list-ports
python gui/cli.py --port PORT [--bit FILE] [--elf FILE] [--ram] [--build-helpers] [--monitor]
```

Square brackets mean optional arguments; do not type the brackets. Replace `PORT` and `FILE` with actual values. A connection requires `--port` and at least one of `--bit`, `--elf` or `--monitor`. Help and port listing do not require a port.

| Option | Purpose |
| --- | --- |
| `-h`, `--help` | Show usage and exit. |
| `--list-ports` | List available serial ports and exit. |
| `--port PORT` | Select the serial port, such as `COM4`, `/dev/ttyUSB0` or `/dev/cu.usbserial-0001`. |
| `--bit FILE` | Load an FPGA `.bit` file. Can be used alone or with `--elf`. |
| `--elf FILE` | Load and start a standalone ARM CPU `.elf` file. Can be used alone or with `--bit`. |
| `--ram` | Explicitly select RAM loading. Optional: this is already the default. |
| `--monitor` | Keep showing serial output after loading until Ctrl+C. Used alone with `--port`, it only monitors and sends no boot commands. |
| `--build-helpers` | Compile the tool's helper programs from included source instead of using bundled binaries. Requires ARM GCC and objcopy on PATH. |

### Windows full-package examples

```powershell
# Show help or list ports
./microzed-cli.exe --help
./microzed-cli.exe --list-ports

# FPGA only
./microzed-cli.exe --port COM4 --bit examples/usb_probe.bit

# CPU only
./microzed-cli.exe --port COM4 --elf examples/led_test.elf

# FPGA and CPU together
./microzed-cli.exe --port COM4 --bit examples/usb_probe.bit --elf examples/fpga_cpu_test.elf

# Load, then keep showing board output
./microzed-cli.exe --port COM4 --elf examples/led_test.elf --monitor

# Monitor only, without loading
./microzed-cli.exe --port COM4 --monitor

# Rebuild helpers, then load and monitor
./microzed-cli.exe --port COM4 --elf examples/led_test.elf --build-helpers --monitor

# Your own file: quote paths containing spaces
./microzed-cli.exe --port COM4 --elf "C:/My Project/app.elf" --ram
```

### Lightweight CLI examples

```sh
# Show help or list ports
python gui/cli.py --help
python gui/cli.py --list-ports

# FPGA only
python gui/cli.py --port COM4 --bit build/usb_probe.bit

# CPU only
python gui/cli.py --port COM4 --elf build/led_test.elf

# FPGA and CPU together
python gui/cli.py --port COM4 --bit build/usb_probe.bit --elf build/hello.elf

# Load, then keep showing board output
python gui/cli.py --port COM4 --elf build/led_test.elf --monitor

# Monitor only, without loading
python gui/cli.py --port COM4 --monitor

# Rebuild helpers, then load and monitor
python gui/cli.py --port COM4 --elf build/led_test.elf --build-helpers --monitor

# Your own file: quote paths containing spaces
python gui/cli.py --port COM4 --elf "C:/My Project/app.elf" --ram

# Linux and macOS port examples: replace with your actual device
python3 gui/cli.py --port /dev/ttyUSB0 --elf build/led_test.elf --monitor
python3 gui/cli.py --port /dev/cu.usbserial-0001 --elf build/led_test.elf --monitor
```

`--monitor` and `--build-helpers` can also be added to FPGA-only or combined loads. Press **Ctrl+C** to stop monitoring and release the serial port. During an interrupted download the tool attempts to cancel reception and restore the console; if recovery is not confirmed, press **RST** before retrying. Do not connect the GUI and CLI to the same port simultaneously.

### Build helpers from source

Most users can use the bundled helper binaries and omit `--build-helpers`. This optional flag is for users who want to review and compile the tool's internal helper programs themselves; it does not compile your FPGA design or CPU application.

Install `arm-none-eabi-gcc` and `arm-none-eabi-objcopy` and add their directory to PATH, then use either package's `--build-helpers` example above.

This compiles `cache_sync`, `uart_speed` and `backup_sender` into a temporary directory and uses the freshly built RAM helpers for that session. `backup_sender` is retained as buildable source for review, but the loader does not upload or use it. No vendor FPGA tools are required to compile these helpers. See [BUILD.md](BUILD.md).

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
