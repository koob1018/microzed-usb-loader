# Serial driver setup

No driver files or installers are bundled. The application never requests administrator privileges or changes drivers. An existing working driver does not need to be reinstalled.

Connect the MicroZed **USB-UART** port with a data-capable cable. Close other serial programs before connecting.

## Windows

If the CP210x device has no COM port, install the appropriate Windows driver from [Silicon Labs official downloads](https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers), following their instructions. Reconnect USB and click **Refresh**. Ports typically look like `COM4`.

## macOS

If no serial device appears, use the macOS package and instructions on the same official Silicon Labs page. Select a device such as `/dev/cu.usbserial-0001` from the actual port list; names vary by driver version.

## Linux

The CP210x driver is commonly included in the kernel. Devices typically appear as `/dev/ttyUSB0`. If access is denied, check the device's owning group and your distribution's serial permissions. On distributions using the `dialout` group, the administrator can add your user to that group; log out and back in afterward. Do not make the serial device world-writable.

List ports on any supported Python platform:

```text
python gui/cli.py --list-ports
```

If the list is empty, check the data cable, USB port, board power and OS device detection. If the port is busy, close the GUI or other terminal program first.
