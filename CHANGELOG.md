# Changelog

## v1.2.0

- Windows full package includes both GUI and console CLI executables sharing one runtime.
- Both Windows entry points work without a separate Python installation.
- Included helper sources support `--build-helpers` in the packaged CLI.
- Lightweight cross-platform CLI source package remains available separately.

## v1.1.0 — RAM-only loading and CLI

- Added the CLI contributed by Shiming Li, with integration changes and tests.
- CLI needs only pyserial; Qt is not imported. Supports Windows, Linux and macOS serial-port names.
- Added `--monitor` after loading and monitor-only sessions; Ctrl+C releases the port.
- Added `--build-helpers` to compile cache_sync, uart_speed and backup_sender from included sources using ARM GCC/objcopy.
- Removed all Flash save/restore transactions and environment-writing code from the backend. GUI is RAM-only; CLI rejects `--flash`.
- Removed bundled CP210x drivers and installation code. GUI provides Driver help with an official download link.
- Improved Ctrl+C cancellation during helper transfer. Existing board Flash contents are not changed by this update.

Earlier releases supported Flash and bundled drivers. Use v1.1.0 or later for the RAM-only workflow.
