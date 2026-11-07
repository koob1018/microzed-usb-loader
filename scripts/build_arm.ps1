param([string]$AmdRoot = 'D:/software/AMD/2025.2')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$toolchain = Join-Path $AmdRoot 'gnu/aarch32/nt/gcc-arm-none-eabi/bin'
New-Item -ItemType Directory -Path (Join-Path $projectRoot 'build') -Force | Out-Null
& (Join-Path $toolchain 'arm-none-eabi-gcc.exe') -mcpu=cortex-a9 -marm -mfloat-abi=soft -mno-unaligned-access -Os -ffreestanding -fno-builtin -fno-stack-protector -nostdlib "-Wl,-T,$projectRoot/src/ram.ld" '-Wl,--build-id=none' -o "$projectRoot/build/hello.elf" "$projectRoot/src/hello.c"
if ($LASTEXITCODE -ne 0) { throw 'ARM build failed' }
& (Join-Path $toolchain 'arm-none-eabi-objcopy.exe') -O binary "$projectRoot/build/hello.elf" "$projectRoot/build/hello.bin"
if ($LASTEXITCODE -ne 0) { throw 'Binary export failed' }
& (Join-Path $toolchain 'arm-none-eabi-gcc.exe') -mcpu=cortex-a9 -marm -nostdlib '-Wl,-Ttext,0x0f000000' '-Wl,-e,entry' '-Wl,--build-id=none' -o "$projectRoot/build/cache_sync.elf" "$projectRoot/src/cache_sync.S"
if ($LASTEXITCODE -ne 0) { throw 'Cache helper build failed' }
& (Join-Path $toolchain 'arm-none-eabi-objcopy.exe') -O binary "$projectRoot/build/cache_sync.elf" "$projectRoot/build/cache_sync.bin"
if ($LASTEXITCODE -ne 0) { throw 'Cache helper export failed' }

& (Join-Path $toolchain 'arm-none-eabi-gcc.exe') -mcpu=cortex-a9 -marm -mfloat-abi=soft -Os -ffreestanding -fno-builtin -fno-stack-protector -nostdlib "-Wl,-T,$projectRoot/src/uart_speed.ld" '-Wl,--build-id=none' -o "$projectRoot/build/uart_speed.elf" "$projectRoot/src/uart_speed.c"
if ($LASTEXITCODE -ne 0) { throw 'Transfer helper compilation failed' }
& (Join-Path $toolchain 'arm-none-eabi-objcopy.exe') -O binary "$projectRoot/build/uart_speed.elf" "$projectRoot/gui/assets/uart_speed.bin"
if ($LASTEXITCODE -ne 0) { throw 'Transfer helper export failed' }
