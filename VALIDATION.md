# Validation — v1.1.0

Tested on Windows 11 x64, Python 3.12, and one MicroZed XC7Z020 with factory 2013 U-Boot.

- 97 automated tests passed: file validation, GUI selection combinations and focus, serial ownership, CLI arguments, monitoring, helper compilation failures, transfer interruption cleanup, and rejection of Flash operations.
- CLI CPU-only, FPGA-only and combined loads passed using both bundled helpers and helpers compiled from source (six hardware runs).
- GUI worker CPU-only, FPGA-only and combined loads passed (three hardware runs).
- CPU LED example reported GPIO readback PASS; FPGA configuration reported DONE; the combined example verified the FPGA signature.
- Monitor-only opened the port without boot commands. Monitoring after loading received a live board response. Ctrl+C stopped monitoring and released the port.
- Injected Ctrl+C during a high-speed transfer: cancellation, normal-speed console recovery and subsequent transfer passed.
- The complete 16 MiB Flash CRC was identical before and after acceptance testing. No Flash write or boot-environment save was performed.
- Packaged GUI starts with empty file paths, RAM-only controls and driver help linking to the official vendor; no installer is offered.
- CLI imports and hardware runs used a separate environment containing pyserial only, without Qt.

CLI wall-clock timings on this setup:

| Load | Bundled helpers | Compiled helpers |
| --- | ---: | ---: |
| CPU LED example | 9.2 s | 9.7 s |
| FPGA example | 19.8 s | 21.0 s |
| Both examples | 26.6 s | 26.8 s |

Times include connection, helper preparation, verification and program execution, not just data transfer. Source-built runs include compilation.

Linux and macOS hardware testing has not been performed. Results describe this board/setup, not universal compatibility. Automated tests use synthetic data; factory Flash dumps, course neural-network code, local logs and machine configuration are not distributed.
