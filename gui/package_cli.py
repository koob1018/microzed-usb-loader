"""Create the portable CLI source bundle; standard library only."""
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[1]
files=['README.md','BUILD.md','DRIVERS.md','LICENSE','THIRD_PARTY_NOTICES.md','CHANGELOG.md','VALIDATION.md',
       'gui/cli.py','gui/backend.py','gui/formats.py','gui/requirements-cli.txt',
       'gui/assets/cache_sync.bin','gui/assets/uart_speed.bin','gui/assets/backup_sender.bin',
       'src/cache_sync.S','src/uart_speed.c','src/uart_speed.ld','src/hello.c','src/led_test.c','src/ram.ld',
       'persistent/backup_sender.c','persistent/backup_sender.ld',
       'build/usb_probe.bit','build/led_test.elf','build/hello.elf','scripts/build_arm.ps1','scripts/build_pl.tcl']
out=root/'gui/dist/MicroZed-USB-Loader-CLI.zip';out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
    for name in files:archive.write(root/name,'MicroZed-USB-Loader-CLI/'+name)
with zipfile.ZipFile(out) as archive:assert archive.testzip() is None
print(out,out.stat().st_size)
