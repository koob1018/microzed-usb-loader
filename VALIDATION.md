# Validation

Tested on Windows 11 x64 with one MicroZed XC7Z020 and the factory 2013 U-Boot/Linux layout.

- Automated tests cover GUI combinations/focus, serial ownership, driver detection, malformed inputs, reserved memory, Flash write bounds/order and speed-switch cleanup.
- Eight repeated 64 KiB random-data transfers passed CRC and normal-speed console checks.
- Interrupted YMODEM: receiver cancellation, console recovery and retry passed.
- Restore before the first speed switch: helper initialization guard passed.
- FPGA DONE asserted; CPU LED example executed and returned.
- Combined RAM load: 26.711 seconds. Combined Flash load: 90.090 seconds, including backup and verification. Automatic startup after software reset passed.
- Initial Flash restored and complete 16 MiB CRC matched its pre-test value; original automatic startup passed.
- Final helper guard/linker correction was followed by repeat-transfer, cancellation, FPGA and CPU checks. Flash acceptance preceded that correction.
- Packaged application starts with empty paths, detects the driver, and shows serial selection without a speed selector. ZIP integrity and file checksums verified.

The same 256 KiB transfer took 36.506 seconds at the original speed and 16.301 seconds with automatic switching, including helper preparation.

The latest acceptance run did not simulate physical USB removal during a Flash write. Results describe the tested board and setup, not universal compatibility.

Public tests use synthetic Flash fixtures. No factory Flash dump, course neural-network code, local serial logs or private machine configuration is included.
