"""Setup information only: no driver installation or system changes."""
DRIVER_URL = 'https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers'
DRIVER_HELP = '''<p>Connect the MicroZed USB-UART port with a data-capable USB cable.</p>
<p><b>Windows / macOS:</b> If the CP210x device does not appear, install the appropriate driver from
<a href="https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers">Silicon Labs official downloads</a>.
Follow the vendor instructions, reconnect the board, and click Refresh.</p>
<p><b>Linux:</b> The CP210x driver is commonly included in the kernel. If access is denied, check
your distribution's serial-device permissions (often the dialout group). Log in again after a group change.</p>
<p>Close other serial applications before connecting. This tool does not install drivers or request administrator privileges.</p>'''
