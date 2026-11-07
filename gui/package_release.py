from pathlib import Path
import zipfile,hashlib,shutil
import sys,PySide6
from importlib.metadata import distribution
root=Path(__file__).parent
release=root/'dist/MicroZed-USB-Loader'
for name in ('LICENSE','THIRD_PARTY_NOTICES.md'):
    shutil.copy2(root.parent/name,release/name)
# Qt uses the Windows ICU API. Do not ship unrelated Poppler/Conda ICU DLLs
# discovered on the build machine PATH (their exports are incompatible).
for name in ('icuuc.dll','icudt78.dll'):
    wrong=release/'_internal'/name
    if wrong.exists():wrong.unlink()
# Load one consistent modern MSVC runtime before Python/Qt imports.
for name in ('vcruntime140.dll','vcruntime140_1.dll','msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','msvcp140_codecvt_ids.dll','concrt140.dll'):
    source=Path(PySide6.__file__).parent/name
    target=release/'_internal'/name
    if source.exists() and (not target.exists() or source.read_bytes()!=target.read_bytes()):shutil.copy2(source,target)
licenses=release/'licenses';licenses.mkdir(exist_ok=True)
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists():shutil.copy2(python_license,licenses/'Python-LICENSE.txt')
for name in ['PySide6_Essentials','shiboken6','pyserial','pyinstaller']:
    dist=distribution(name)
    for f in dist.files or []:
        if any(s.lower().startswith(('license','copying')) for s in f.parts):
            p=Path(dist.locate_file(f))
            if p.is_file():
                target=licenses/name/str(f).replace('/','_').replace('\\','_')
                target.parent.mkdir(exist_ok=True);shutil.copy2(p,target)
(licenses/'NOTICE.txt').write_text('Includes Python, Qt/PySide6, shiboken6 and pyserial. Qt/PySide6 libraries remain dynamically replaceable in _internal. Qt project: https://www.qt.io/ ; PySide6 source: https://code.qt.io/pyside/pyside-setup.git/ . See bundled license texts.\n',encoding='utf-8')
paths=sorted(p for p in release.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
(release/'SHA256SUMS.txt').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(release).as_posix() for p in paths)+'\n')
archive=root/'dist/MicroZed-USB-Loader.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in release.rglob('*'):
        if p.is_file():z.write(p,p.relative_to(release.parent))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(archive,archive.stat().st_size)
