# Third-party components

The MIT license covers original loader code and example sources. It does not relicense third-party software or vendor-generated FPGA IP.

- The Silicon Labs CP210x driver retains its vendor license, included in `gui/assets/cp210x/SLAB_License_Agreement_VCP_Windows.txt`. It is bundled for use with Silicon Labs devices; vendor redistribution conditions apply.
- Python, Qt/PySide6, shiboken6, pyserial and PyInstaller retain their own licenses. The Windows package includes license texts under `licenses/`.
- Qt/PySide6 libraries are dynamically linked and remain replaceable in `_internal/`. Source: https://code.qt.io/pyside/pyside-setup.git/ .
- The FPGA example is generated with AMD Vivado IP. Its Tcl design recipe is provided; AMD tooling and IP retain their own terms.
