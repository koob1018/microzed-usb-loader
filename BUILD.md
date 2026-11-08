# Rebuilding helpers and examples

The GUI can be rebuilt using the prebuilt files under `build/` and `gui/assets/`. Vivado and an ARM compiler are needed only when changing firmware/helpers.

Run from the repository root. Set the toolchain path to your AMD installation:

```powershell
$toolchain = 'D:/software/AMD/2025.2/Vitis/gnu/aarch32/nt/gcc-arm-none-eabi/bin'
$gcc = Join-Path $toolchain 'arm-none-eabi-gcc.exe'
$objcopy = Join-Path $toolchain 'arm-none-eabi-objcopy.exe'
./scripts/build_arm.ps1 -AmdRoot 'D:/software/AMD/2025.2/Vitis'
& $gcc -mcpu=cortex-a9 -marm -mfloat-abi=soft -Os -ffreestanding -fno-builtin -fno-stack-protector -nostdlib '-Wl,-T,src/ram.ld' '-Wl,--build-id=none' -o build/led_test.elf src/led_test.c
Copy-Item build/cache_sync.bin gui/assets/cache_sync.bin
& $gcc -mcpu=cortex-a9 -marm -mfloat-abi=soft -Os -ffreestanding -fno-builtin -fno-stack-protector -nostdlib '-Wl,-T,persistent/backup_sender.ld' '-Wl,--build-id=none' -o build/backup_sender.elf persistent/backup_sender.c
& $objcopy -O binary build/backup_sender.elf gui/assets/backup_sender.bin
vivado -mode batch -source scripts/build_pl.tcl
```

`gui/build.ps1` uses `gui/loader.spec` to package the GUI and console CLI executables with one shared runtime, helper sources, examples and notices into `gui/dist/MicroZed-USB-Loader.zip`.


The CLI can compile all three helpers with `--build-helpers`. ARM GCC and objcopy must be on PATH. The backup reader is not used by RAM-only loading.
