# Two entry points, one shared Python runtime and dependency directory.
from pathlib import Path
root = Path(SPECPATH)
helpers = [(str(root / 'assets'), 'assets'),
           (str(root.parent / 'src'), 'src'),
           (str(root.parent / 'persistent'), 'persistent')]
gui = Analysis([str(root / 'app.py')], pathex=[str(root)], datas=helpers)
cli = Analysis([str(root / 'cli.py')], pathex=[str(root)], datas=[])
gui_exe = EXE(PYZ(gui.pure), gui.scripts, [], exclude_binaries=True,
              name='MicroZed-USB-Loader', console=False)
cli_exe = EXE(PYZ(cli.pure), cli.scripts, [], exclude_binaries=True,
              name='microzed-cli', console=True)
COLLECT(gui_exe, cli_exe, gui.binaries, cli.binaries, gui.datas, cli.datas,
        name='MicroZed-USB-Loader')
