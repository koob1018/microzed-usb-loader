from pathlib import Path
from types import SimpleNamespace
import pytest
import driver_setup as d

@pytest.mark.parametrize('code',[5,1223,1])
def test_install_failure_not_success(code):
    with pytest.raises(RuntimeError):d.install_message(code)

def test_install_results():
    assert 'Restart Windows' in d.install_message(3010)
    assert 'installed' in d.install_message(0)

@pytest.mark.parametrize('cancel',[False,True])
def test_windows_install_handoff(tmp_path,monkeypatch,cancel):
    import ctypes
    calls=[]
    class Function:
        def __init__(self,fn):self.fn=fn
        def __call__(self,*args):return self.fn(*args)
    def directory(buffer,size):buffer.value='C:\\Windows\\System32';return len(buffer.value)
    def execute(pointer):
        info=pointer._obj
        calls.append((info.lpVerb,info.lpFile,info.lpParameters,info.nShow))
        if cancel:ctypes.set_last_error(1223);return 0
        info.hProcess=123;return 1
    def exit_code(handle,pointer):pointer._obj.value=0;return 1
    kernel=SimpleNamespace(GetSystemDirectoryW=Function(directory),WaitForSingleObject=Function(lambda *a:0),GetExitCodeProcess=Function(exit_code),CloseHandle=Function(lambda h:1))
    shell=SimpleNamespace(ShellExecuteExW=Function(execute))
    monkeypatch.setattr(d.ctypes,'WinDLL',lambda name,**kw:kernel if name=='kernel32' else shell)
    monkeypatch.setattr(d,'verify_inf',lambda p:'Microsoft')
    path=tmp_path/'folder with spaces'/'silabser.inf'
    if cancel:
        with pytest.raises(RuntimeError,match='cancelled'):d.install(path)
    else:assert 'installed' in d.install(path)
    verb,exe,args,show=calls[0]
    assert verb=='runas' and exe.lower().endswith('system32\\pnputil.exe')
    assert '/add-driver' in args and '/install' in args and '/reboot' not in args and '/delete' not in args
    assert '"'+str(path.resolve())+'"' in args and show==0


def test_detection(monkeypatch):
    monkeypatch.setattr(d,'probe',lambda:['COM3'])
    assert not d.needs_install()
    monkeypatch.setattr(d,'probe',lambda:[])
    from contextlib import nullcontext
    monkeypatch.setattr(d.winreg,'OpenKey',lambda *a:nullcontext())
    monkeypatch.setattr(d.winreg,'QueryValueEx',lambda key,name:({'DeleteFlag':0,'Start':3,'ImagePath':__file__}[name],0))
    assert not d.needs_install()
    def missing(*a):raise FileNotFoundError()
    monkeypatch.setattr(d.winreg,'OpenKey',missing)
    assert d.needs_install()

def test_working_port_skips_install(monkeypatch):
    monkeypatch.setattr(d,'probe',lambda:['COM3'])
    monkeypatch.setattr(d,'install',lambda *a:pytest.fail('Should not install'))
    worker=d.DriverTask('unused.inf');results=[]
    worker.result.connect(lambda *a:results.append(a));worker.run()
    assert results[0][0] and 'No installation' in results[0][1]

@pytest.mark.parametrize('missing',[False,True])
def test_status_never_installs_automatically(monkeypatch,missing):
    import app
    from PySide6.QtWidgets import QApplication
    qt=QApplication.instance() or QApplication([])
    monkeypatch.setattr(app,'needs_install',lambda:missing)
    monkeypatch.setattr(app.Window,'setup_driver',lambda *a:pytest.fail('Automatic installation'))
    window=app.Window(auto_driver=False)
    window.ensure_driver()
    assert window.driver_button.text()==('Install driver' if missing else 'Driver installed')
    assert window.driver_button.isEnabled()==missing
    assert window.driver_button.y() <= window.ports.y()
    window.busy=True;window.ensure_driver()
    assert not window.driver_button.isEnabled()
    window.busy=False;window.close()

@pytest.mark.parametrize('failure',[False,True])
def test_worker_install_or_cancel(monkeypatch,failure):
    monkeypatch.setattr(d,'probe',lambda:[])
    calls=[]
    ole=SimpleNamespace(CoInitializeEx=lambda *a:0,CoUninitialize=lambda:calls.append('cleanup'))
    monkeypatch.setattr(d.ctypes,'WinDLL',lambda *a:ole)
    def install(path):
        if failure:raise RuntimeError('Installation cancelled')
        return 'Driver installed'
    monkeypatch.setattr(d,'install',install)
    worker=d.DriverTask('test.inf');results=[]
    worker.result.connect(lambda *a:results.append(a));worker.run()
    assert results[0][0] is not failure
    assert calls==['cleanup']

@pytest.mark.parametrize('deleted,start,path',[(1,3,__file__),(0,4,__file__),(0,3,'C:/missing-driver.sys')])
def test_removed_driver_service_is_not_installed(monkeypatch,deleted,start,path):
    from contextlib import nullcontext
    monkeypatch.setattr(d,'probe',lambda:[])
    monkeypatch.setattr(d.winreg,'OpenKey',lambda *a:nullcontext())
    monkeypatch.setattr(d.winreg,'QueryValueEx',lambda key,name:({'DeleteFlag':deleted,'Start':start,'ImagePath':path}[name],0))
    assert d.needs_install()
