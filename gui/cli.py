"""MicroZed USB Loader, command-line version.

Uses the same backend as the GUI (app.py) without Qt. Needs pyserial:
    python -m pip install pyserial==3.5

The board-side helper programs come from assets/ by default. With
--build-helpers they are compiled from src/ and persistent/ instead, which
needs arm-none-eabi-gcc and arm-none-eabi-objcopy on PATH.

Example:
  python cli.py --port /dev/cu.usbserial-0001 --bit design.bit --elf app.elf --ram
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import codecs
from datetime import datetime
from pathlib import Path

from backend import Board
from formats import read_bit, read_elf

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'gui' / 'assets'
DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'MicroZedLoader'  # same folder as the GUI
# Board text is printed as received, minus control characters that could upset the terminal.
CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')

# Board-side helpers the backend uploads, with the build flags from scripts/build_arm.ps1 and BUILD.md:
#   cache_sync    clears the CPU instruction cache before jumping into newly loaded code
#   uart_speed    switches the serial link to 921600 baud during transfers
#   backup_sender is retained for source review/building, but not used by this RAM-only loader
_C_FLAGS = ['-mcpu=cortex-a9', '-marm', '-mfloat-abi=soft', '-Os', '-ffreestanding', '-fno-builtin',
            '-fno-stack-protector', '-nostdlib', '-Wl,--build-id=none']
HELPERS = {
    'cache_sync': ['-mcpu=cortex-a9', '-marm', '-nostdlib', '-Wl,-Ttext,0x0f000000', '-Wl,-e,entry',
                   '-Wl,--build-id=none', 'src/cache_sync.S'],
    'uart_speed': _C_FLAGS + ['-Wl,-T,src/uart_speed.ld', 'src/uart_speed.c'],
    'backup_sender': _C_FLAGS + ['-Wl,-T,persistent/backup_sender.ld', 'persistent/backup_sender.c'],
}


# If you don't want to use the .bin files from assets/ build them here
def build_helpers(out):
    """Compile the helpers into folder `out` and return it."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    gcc, objcopy = shutil.which('arm-none-eabi-gcc'), shutil.which('arm-none-eabi-objcopy')
    if not gcc or not objcopy:
        raise SystemExit('Error: --build-helpers needs arm-none-eabi-gcc and arm-none-eabi-objcopy on PATH.')
    for name, args in HELPERS.items():
        elf = out / f'{name}.elf'
        for command in ([gcc, *args, '-o', str(elf)], [objcopy, '-O', 'binary', str(elf), str(out / f'{name}.bin')]):
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            if result.returncode:
                raise SystemExit(f'Error: building the {name} helper failed:\n{result.stderr}')
    return out


def show_output(board, log):
    """Keep the port open and print everything the board sends, until Ctrl+C."""
    print('\nShowing board output. Press Ctrl+C to stop.', flush=True)
    decoder=codecs.getincrementaldecoder('utf-8')(errors='replace')
    try:
        while True:
            data = board.s.read(max(board.s.in_waiting, 1))
            if data:
                log(decoder.decode(data))
    except KeyboardInterrupt:
        print('\nStopped showing board output.')


def run(port, mode, fpga, arm, helpers, monitor=False):
    """The same steps as the GUI's Worker.run, then optionally show board output."""
    if mode!='ram':raise ValueError('Flash writing is disabled. Only RAM loading is supported.')
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    logpath = DATA / 'logs' / f'{stamp}.log'
    logpath.parent.mkdir(parents=True, exist_ok=True)
    print(f'Log file: {logpath}')
    with logpath.open('w', encoding='utf-8') as logfile:
        step = None

        def log(text):
            nonlocal step
            logfile.write(text)
            logfile.flush()
            print(CONTROL_CHARS.sub('', text.replace('\r\n', '\n')), end='', flush=True)
            step = None

        def progress(_percent, text):
            # The backend reports every 1 KiB packet; print each step once.
            nonlocal step
            label = text.split(' · ')[0]
            if label != step:
                print(f'\n>> {label}', flush=True)
                step = label

        try:
            with Board(port, helpers, log, progress) as board:
                print(f'Connecting to {port}...', flush=True)
                if fpga or arm:
                    board.enter()
                    board.identify()
                    if fpga:
                        board.fpga(fpga)
                    message = board.arm(arm) if arm else 'FPGA configured and DONE verified. Flash is unchanged.'
                else:
                    message = 'Connected for monitoring; no boot commands sent.'
                print(f'\nDone: {message}', flush=True)
                if monitor:
                    show_output(board, log)
        except BaseException:
            logfile.write('\n' + traceback.format_exc())
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Load FPGA .bit and CPU .elf files onto a MicroZed 7020 over its USB-UART cable.',
        epilog='List serial ports with: python -m serial.tools.list_ports')
    parser.add_argument('--port', help='serial port, e.g. COM5, /dev/ttyUSB0 or /dev/cu.usbserial-0001')
    parser.add_argument('--list-ports', action='store_true', help='list available serial ports and exit')
    parser.add_argument('--bit', metavar='FILE', help='FPGA bitstream from Vivado')
    parser.add_argument('--elf', metavar='FILE', help='standalone ARM Cortex-A9 program (not a Linux program)')
    parser.add_argument('--ram', dest='mode', action='store_const', const='ram', default='ram',
                      help='load into RAM and run now; lost at power-off')
    parser.add_argument('--build-helpers', action='store_true',
                        help='compile the board-side helpers from src/ and persistent/ with arm-none-eabi-gcc '
                             'instead of using the prebuilt files in gui/assets')
    parser.add_argument('--monitor', action='store_true',
                        help='afterwards, keep the serial port open and show what the board prints, until Ctrl+C')
    args = parser.parse_args(argv)
    if args.list_ports:
        from serial.tools import list_ports
        ports=list(list_ports.comports())
        for port in ports:print(f'{port.device}: {port.description}')
        if not ports:print('No serial ports found. Check the USB-UART cable and driver. See DRIVERS.md.')
        return 0
    if not args.port:parser.error('give --port (or use --list-ports)')
    if not args.bit and not args.elf and not args.monitor:
        parser.error('give --bit, --elf, or --monitor')

    try:
        fpga = read_bit(args.bit) if args.bit else None
        arm = read_elf(args.elf) if args.elf else None
    except (OSError, ValueError) as exc:
        raise SystemExit(f'Error: {exc}')
    for kind, image in (('FPGA', fpga), ('CPU', arm)):
        if image:
            print(f'{kind} file: {image.name} ({image.details})')

    with tempfile.TemporaryDirectory() as tmp:
        helpers = build_helpers(Path(tmp)) if args.build_helpers else ASSETS
        if fpga or arm:
            for name in ('cache_sync.bin','uart_speed.bin'):
                if not (helpers/name).is_file():raise SystemExit(f'Missing helper: {name}. Use --build-helpers or restore gui/assets/.')
        print('Helpers: compiled from source' if args.build_helpers else f'Helpers: {helpers}')
        try:
            run(args.port, args.mode, fpga, arm, helpers, args.monitor)
        except KeyboardInterrupt:
            raise SystemExit('\nInterrupted. If the board stops responding, press RST before retrying.')
        except OSError as exc:
            raise SystemExit(f'\nSerial/I/O error: {exc}\nCheck the cable, port permissions and driver; close other serial applications. See DRIVERS.md.')
        except Exception as exc:
            raise SystemExit(f'\nError: {exc}')
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(errors='replace')
    sys.exit(main())
