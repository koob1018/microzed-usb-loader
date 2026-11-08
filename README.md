# MicroZed USB Loader

Load FPGA `.bit` and standalone ARM CPU `.elf` files onto a MicroZed through its USB-UART cable, using the factory U-Boot. No JTAG adapter, Ethernet or microSD card is needed for the tested setup. Load FPGA and CPU separately or together, then view serial output.

Programs run in RAM and are lost at power-off.

## Download

**[Get the latest release](https://github.com/koob1018/microzed-usb-loader/releases/latest)**

| Package | Includes | Requirements |
| --- | --- | --- |
| **MicroZed-USB-Loader.zip** | Windows GUI + standalone CLI, examples and helper sources | Windows; no Python installation needed |
| **MicroZed-USB-Loader-CLI.zip** | Lightweight cross-platform CLI, examples and helper sources | Python 3.10+ and pyserial; no Qt |

Connect the board's **USB-UART** port with a data-capable cable. If no serial port appears, see [driver setup](DRIVERS.md). Drivers are installed separately. Vivado/Vitis are not needed to run the loader; use your design tools to generate your own `.bit` and `.elf` files.

## Quick start

### Windows GUI

1. Extract the full package and run **MicroZed-USB-Loader.exe**. Keep `_internal` beside both executables.
2. Select the serial port and click **Connect**. Use **Driver help** or **Refresh** if needed.
3. Drop or browse for a `.bit` and/or `.elf` file.
4. Click **Program FPGA**, **Program CPU** or **Program both**.
5. Serial output remains visible. Click **Disconnect** to release the port.

For a first test, select `examples/led_test.elf` under **CPU**, leave FPGA empty and click **Program CPU**. D3 should blink six times and remain on.

### Command line

Run from the extracted package folder. Both editions have identical options; only the launcher and example paths differ.

**Windows full package — PowerShell:**

```powershell
./microzed-cli.exe --list-ports
./microzed-cli.exe --port COM4 --elf examples/led_test.elf --monitor
```

**Lightweight package / repository root:**

```sh
python -m pip install -r gui/requirements-cli.txt
python gui/cli.py --list-ports
python gui/cli.py --port COM4 --elf build/led_test.elf --monitor
```

Replace `COM4` with your port: e.g. `/dev/ttyUSB0` on Linux or `/dev/cu.usbserial-0001` on macOS. Use `python3` if that is your Python command. Press **Ctrl+C** to exit monitoring. GUI and CLI cannot use the same port simultaneously.

## CLI reference

```text
./microzed-cli.exe [-h | --list-ports]
./microzed-cli.exe --port PORT [--bit FILE] [--elf FILE] [--monitor] [--build-helpers] [--ram]

python gui/cli.py [-h | --list-ports]
python gui/cli.py --port PORT [--bit FILE] [--elf FILE] [--monitor] [--build-helpers] [--ram]
```

Brackets denote optional arguments; do not type them. For a connection, provide `--port` and at least one of `--bit`, `--elf` or `--monitor`.

| Option | Function |
| --- | --- |
| `-h`, `--help` | Show help and exit. |
| `--list-ports` | List serial ports and exit; no connection required. |
| `--port PORT` | Select the serial port. |
| `--bit FILE` | Load an FPGA bitstream. |
| `--elf FILE` | Load and start a standalone ARM CPU program. |
| `--monitor` | Keep displaying board output until Ctrl+C; also works without loading. Monitor-only sends no boot commands. |
| `--build-helpers` | Compile internal helper programs from included source; requires ARM GCC and objcopy on PATH. |
| `--ram` | Explicit RAM loading; optional because it is already the default. |

Append any of these argument combinations to **either** launcher above. Replace filenames and port as needed; quote paths containing spaces.

| Task | Arguments |
| --- | --- |
| FPGA only | `--port COM4 --bit design.bit` |
| CPU only | `--port COM4 --elf app.elf` |
| FPGA + CPU | `--port COM4 --bit design.bit --elf app.elf` |
| Load and monitor | `--port COM4 --elf app.elf --monitor` |
| Monitor only | `--port COM4 --monitor` |
| Rebuild helpers and load | `--port COM4 --elf app.elf --build-helpers --monitor` |
| Path containing spaces | `--port COM4 --elf "C:/My Project/app.elf"` |

`--monitor` and `--build-helpers` also work with FPGA-only and combined loads.

### Optional: compile helpers yourself

Normally, the loader uses its bundled helper binaries. `--build-helpers` instead compiles the internal helper source locally; it does **not** compile your FPGA design or CPU application. Install `arm-none-eabi-gcc` and `arm-none-eabi-objcopy` and add their directory to PATH.

The helpers handle CPU cache synchronization (`cache_sync`) and serial-speed switching (`uart_speed`). All three supplied helpers are compiled into a temporary directory; `backup_sender` is retained for source review but is not used during loading. See [BUILD.md](BUILD.md).

## Included examples

| Test | Windows full package | Lightweight package / repository | Expected result |
| --- | --- | --- | --- |
| CPU-only LED | `examples/led_test.elf` | `build/led_test.elf` | D3 blinks six times, stays on; `LED GPIO READBACK: PASS`. No FPGA file needed. |
| FPGA + CPU | `examples/usb_probe.bit` + `examples/fpga_cpu_test.elf` | `build/usb_probe.bit` + `build/hello.elf` | CPU verifies the FPGA signature, then performs the LED test. |

**`fpga_cpu_test.elf` and `hello.elf` are the same program under different package filenames.** Both CPU examples return to U-Boot when finished. The combined test should report `FPGA SIGNATURE: PASS` as well as the LED result.

CPU-only commands are shown in Quick start. For the combined test:

```powershell
# Windows full package
./microzed-cli.exe --port COM4 --bit examples/usb_probe.bit --elf examples/fpga_cpu_test.elf --monitor
```

```sh
# Lightweight package / repository
python gui/cli.py --port COM4 --bit build/usb_probe.bit --elf build/hello.elf --monitor
```

C source: [LED test](src/led_test.c), [combined test](src/hello.c). Rebuild instructions: [BUILD.md](BUILD.md).

## How it works and compatibility

U-Boot receives data into DDR using YMODEM, configures the FPGA through PCAP and starts CPU code at the ELF entry point. RAM helpers switch transfers to 921600 baud, restore the 115200 console and synchronize CPU caches. CRC32 verifies transfers.

- **Tested hardware:** MicroZed XC7Z020-1CLG400, factory 2013 U-Boot, Windows 11 x64. Linux/macOS hardware testing has not been performed. See [validation results](VALIDATION.md).
- **Your design:** CPU files must be standalone ARM Cortex-A9 executables, not Linux applications. Designs must match the existing PS clocks, DDR and MIO initialization; the loader does not apply an XSA, FSBL or `ps7_init.tcl`.
- **Memory:** Helpers reserve `0x0f000000–0x0f001fff`; overlapping CPU images are rejected.
- **Recovery:** If a program does not return, start loading and press **RST** while the tool waits for U-Boot. After an interrupted transfer, retry only once the console has recovered; otherwise press RST first.
- **Scope:** This is a loader, not a breakpoint debugger. CPU programs run with board-level privileges; use code you trust.

## Development

```powershell
python -m venv gui/.venv
./gui/.venv/Scripts/python.exe -m pip install -r gui/requirements.txt
./gui/.venv/Scripts/python.exe -m pytest gui/tests -q
./gui/.venv/Scripts/python.exe gui/app.py
./gui/build.ps1
```

The Windows build produces both executables with a shared runtime. See [BUILD.md](BUILD.md) and [change history](CHANGELOG.md). Original code is MIT licensed; bundled components retain their [own licenses](THIRD_PARTY_NOTICES.md).

## Acknowledgements

Thanks to Shiming Li for testing the tool and contributing the initial CLI with monitoring and source-built helpers.
