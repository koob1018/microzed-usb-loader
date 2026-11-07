$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & ./.venv/Scripts/python.exe -m PyInstaller --noconfirm --windowed --onedir --name MicroZed-USB-Loader --add-data 'assets;assets' app.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
    $releaseDir = Join-Path $PSScriptRoot 'dist/MicroZed-USB-Loader'
    Copy-Item -LiteralPath 'README.txt' -Destination $releaseDir
    Copy-Item -LiteralPath 'EXAMPLES.txt' -Destination $releaseDir
    New-Item -ItemType Directory -Force -Path (Join-Path $releaseDir 'examples') | Out-Null
    Copy-Item -LiteralPath '../build/usb_probe.bit' -Destination (Join-Path $releaseDir 'examples/usb_probe.bit')
    Copy-Item -LiteralPath '../build/led_test.elf' -Destination (Join-Path $releaseDir 'examples/led_test.elf')
    Copy-Item -LiteralPath '../build/hello.elf' -Destination (Join-Path $releaseDir 'examples/fpga_cpu_test.elf')
    & ./.venv/Scripts/python.exe package_release.py
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
} finally { Pop-Location }
