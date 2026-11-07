"""Offline installation of the bundled, signed Silicon Labs CP210x driver."""
import ctypes,subprocess,winreg,os
from ctypes import wintypes as W
from pathlib import Path
from serial.tools import list_ports
from PySide6.QtCore import QThread,Signal

def probe():
    ports=[p.device for p in list_ports.comports() if p.vid==0x10c4 and p.pid==0xea60]
    return ports

def needs_install():
    if probe():return False
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Services\silabser') as key:
            try:
                if winreg.QueryValueEx(key,'DeleteFlag')[0]:return True
            except FileNotFoundError:pass
            if winreg.QueryValueEx(key,'Start')[0]==4:return True
            image=winreg.QueryValueEx(key,'ImagePath')[0]
            image=os.path.expandvars(image)
            if image.lower().startswith('\\systemroot\\'):
                image=os.environ['SystemRoot']+image[len('\\SystemRoot'):]
            if image.startswith('\\??\\'):image=image[4:]
            return not Path(image).is_file()
    except FileNotFoundError:return True
    except OSError:return True # Allow manual installation when detection is unavailable.

def verify_inf(inf):
    class Signer(ctypes.Structure):
        _fields_=[('cbSize',W.DWORD),('CatalogFile',W.WCHAR*260),('DigitalSigner',W.WCHAR*260),('DigitalSignerVersion',W.WCHAR*260),('SignerScore',W.DWORD)]
    api=ctypes.WinDLL('setupapi',use_last_error=True)
    api.SetupVerifyInfFileW.argtypes=[W.LPCWSTR,ctypes.c_void_p,ctypes.POINTER(Signer)];api.SetupVerifyInfFileW.restype=W.BOOL
    info=Signer();info.cbSize=ctypes.sizeof(info)
    if not api.SetupVerifyInfFileW(str(Path(inf).resolve()),None,ctypes.byref(info)):
        raise RuntimeError(f'Driver INF signature verification failed (0x{ctypes.get_last_error() & 0xffffffff:08x}). Installation stopped.')
    if not any(x in info.DigitalSigner.lower() for x in ('microsoft','silicon')):raise RuntimeError('Unexpected driver signer.')
    return info.DigitalSigner

def install_message(code):
    if code==3010:return 'Driver installed. Restart Windows to complete setup, then reconnect the board.'
    if code==0:return 'Driver package installed. Reconnect USB-UART and refresh the serial ports. Windows keeps a higher-ranked driver if one is already installed.'
    raise RuntimeError(f'Windows driver installation failed (exit code {code}). Check administrator permissions and the driver package.')

def install(inf):
    verify_inf(inf)
    class ExecuteInfo(ctypes.Structure):
        _fields_=[('cbSize',W.DWORD),('fMask',W.ULONG),('hwnd',W.HWND),('lpVerb',W.LPCWSTR),('lpFile',W.LPCWSTR),('lpParameters',W.LPCWSTR),('lpDirectory',W.LPCWSTR),('nShow',ctypes.c_int),('hInstApp',W.HINSTANCE),('lpIDList',ctypes.c_void_p),('lpClass',W.LPCWSTR),('hkeyClass',W.HKEY),('dwHotKey',W.DWORD),('hIcon',W.HANDLE),('hProcess',W.HANDLE)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);shell=ctypes.WinDLL('shell32',use_last_error=True)
    kernel.GetSystemDirectoryW.argtypes=[W.LPWSTR,W.UINT];kernel.GetSystemDirectoryW.restype=W.UINT
    directory=ctypes.create_unicode_buffer(32768);length=kernel.GetSystemDirectoryW(directory,len(directory))
    if not 0<length<len(directory):raise RuntimeError('Cannot locate the Windows system directory.')
    executable=str(Path(directory.value)/'pnputil.exe')
    params=subprocess.list2cmdline(['/add-driver',str(Path(inf).resolve()),'/install'])
    info=ExecuteInfo();info.cbSize=ctypes.sizeof(info);info.fMask=0x40|0x100|0x400;info.lpVerb='runas';info.lpFile=executable;info.lpParameters=params;info.nShow=0
    shell.ShellExecuteExW.argtypes=[ctypes.POINTER(ExecuteInfo)];shell.ShellExecuteExW.restype=W.BOOL
    if not shell.ShellExecuteExW(ctypes.byref(info)):
        code=ctypes.get_last_error()
        if code==1223:raise RuntimeError('Installation cancelled at the Windows administrator prompt.')
        raise RuntimeError(f'Cannot start Windows driver installation (error {code}).')
    if not info.hProcess:raise RuntimeError('Windows did not return an installer process handle.')
    kernel.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];kernel.WaitForSingleObject.restype=W.DWORD
    kernel.GetExitCodeProcess.argtypes=[W.HANDLE,ctypes.POINTER(W.DWORD)];kernel.GetExitCodeProcess.restype=W.BOOL
    kernel.CloseHandle.argtypes=[W.HANDLE];kernel.CloseHandle.restype=W.BOOL
    try:
        while True:
            state=kernel.WaitForSingleObject(info.hProcess,500)
            if state==0:break
            if state!=258:raise RuntimeError('Cannot monitor Windows driver installation.')
        code=W.DWORD()
        if not kernel.GetExitCodeProcess(info.hProcess,ctypes.byref(code)):raise RuntimeError('Cannot read Windows installer status.')
        return install_message(code.value)
    finally:kernel.CloseHandle(info.hProcess)

class DriverTask(QThread):
    text=Signal(str);progress=Signal(int,str);result=Signal(bool,str,str)
    def __init__(self,inf):super().__init__();self.inf=Path(inf)
    def run(self):
        try:
            ports=probe()
            if ports:
                self.result.emit(True,'CP210x is working on '+', '.join(ports)+'. No installation is needed.','');return
            self.progress.emit(0,'Installing the bundled CP210x driver. Approve the Windows administrator prompt.')
            self.text.emit('Checking the bundled driver signature...\n')
            # ShellExecuteEx is called on a COM-initialized worker thread.
            ole=ctypes.WinDLL('ole32')
            hr=ole.CoInitializeEx(None,2)
            try:message=install(self.inf)
            finally:
                if hr in (0,1):ole.CoUninitialize()
            self.result.emit(True,message,'')
        except Exception as exc:self.result.emit(False,str(exc),'')
