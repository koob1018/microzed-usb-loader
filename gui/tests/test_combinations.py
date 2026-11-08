from types import SimpleNamespace
import sys
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication,QEvent
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app as gui

@pytest.fixture(scope='session')
def qt():
    application=QApplication.instance() or QApplication([])
    yield application
    import gc
    gc.collect()
    QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
    application.processEvents()

@pytest.fixture
def window(qt,monkeypatch):
    monkeypatch.setattr(gui.list_ports,'comports',lambda:[])
    w=gui.Window();w.bit.path.clear();w.elf.path.clear();w.validate()
    yield w
    w.busy=False;w.close();w.timer.stop();w.worker=None;w.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)

@pytest.mark.parametrize('bit_state',['empty','valid','missing','invalid'])
@pytest.mark.parametrize('elf_state',['empty','valid','missing','invalid'])
@pytest.mark.parametrize('mode',['ram'])
@pytest.mark.parametrize('has_port',[False,True])
def test_selection_matrix(window,tmp_path,monkeypatch,bit_state,elf_state,mode,has_port):
    w=window;root=Path(__file__).resolve().parents[2]
    badbit=tmp_path/'bad.bit';badbit.write_bytes(b'not a bitstream')
    badelf=tmp_path/'bad.elf';badelf.write_bytes(b'not an ELF')
    choices=lambda state,valid,bad: {'empty':'','valid':str(valid),'missing':str(tmp_path/('missing'+bad.suffix)),'invalid':str(bad)}[state]
    w.bit.path.setText(choices(bit_state,root/'build/usb_probe.bit',badbit))
    w.elf.path.setText(choices(elf_state,root/'build/hello.elf',badelf))
    if has_port:w.ports.addItem('Test port','FAKE');w.connection=SimpleNamespace(port='FAKE',is_open=True,close=lambda:None)
    w.validate()
    validbit=bit_state=='valid';validelf=elf_state=='valid'
    assert [w.bit_button.isEnabled(),w.arm_button.isEnabled(),w.both_button.isEnabled()]==[has_port and validbit,has_port and validelf,has_port and validbit and validelf]
    # Exercise every dispatch path even if called directly with a disabled button.
    calls=[]
    class WorkerStub:
        def __init__(self,port,mode,fpga,arm):
            calls.append((port,mode,fpga,arm))
            class Signal:
                def connect(self,*args):pass
            self.text=Signal();self.progress=Signal();self.result=Signal();self.finished=Signal()
        def start(self):pass
    monkeypatch.setattr(gui,'Worker',WorkerStub)
    # Avoid writing real user preferences during the matrix.
    class Settings:
        def setValue(self,*args):pass
    w.settings=Settings()
    for target,allowed in [('fpga',validbit),('arm',validelf),('both',validbit and validelf)]:
        calls.clear();w.start(target)
        assert len(calls)==int(has_port and allowed)
        if calls:
            port,actualmode,fpga,arm=calls[0]
            assert port is w.connection and actualmode==mode
            assert (fpga is not None)==(target in ('fpga','both'))
            assert (arm is not None)==(target in ('arm','both'))
            assert not w.bit.isEnabled() and not w.elf.isEnabled()
            w.on_result(False,'Simulated disconnected board','test.log');w.on_finished()
            assert not w.busy and w.bit.isEnabled() and w.elf.isEnabled()
    calls.clear();w.launch();w.start('unknown');assert calls==[]
    w.busy=True;w.start('both');assert calls==[]

@pytest.mark.parametrize('mode',['ram'])
@pytest.mark.parametrize('target',['fpga','arm','both'])
@pytest.mark.parametrize('fail',[False,True])
def test_worker_routes_and_reports_errors(qt,tmp_path,monkeypatch,mode,target,fail):
    monkeypatch.setattr(gui,'DATA',tmp_path)
    calls=[]
    class Board:
        def __init__(self,*args):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def enter(self):
            if fail:raise OSError('Port disconnected')
        def identify(self):pass
        def fpga(self,image):calls.append(('fpga',image))
        def arm(self,image):calls.append(('arm',image));return 'CPU complete'
    monkeypatch.setattr(gui,'Board',Board)
    fpga=object() if target in ('fpga','both') else None
    arm=object() if target in ('arm','both') else None
    worker=gui.Worker('FAKE',mode,fpga,arm);results=[];worker.result.connect(lambda *args:results.append(args));worker.run()
    assert len(results)==1 and results[0][0]==(not fail)
    if fail:assert calls==[]
    else:assert calls==([('fpga',fpga)] if fpga else [])+([('arm',arm)] if arm else [])

def test_log_failure_reports_result(qt,tmp_path,monkeypatch):
    blocked=tmp_path/'blocked';blocked.write_text('file, not a directory')
    monkeypatch.setattr(gui,'DATA',blocked)
    worker=gui.Worker('FAKE','ram',object(),None);results=[]
    worker.result.connect(lambda *args:results.append(args));worker.run()
    assert len(results)==1 and results[0][0] is False

def test_clear_and_deleted_file(window,tmp_path,monkeypatch):
    w=window;w.ports.addItem('Test','FAKE');w.connection=SimpleNamespace(port='FAKE',is_open=True,close=lambda:None)
    root=Path(__file__).resolve().parents[2]
    p=tmp_path/'chosen.elf';p.write_bytes((root/'build/hello.elf').read_bytes())
    w.elf.path.setText(str(p));w.validate();assert w.arm_button.isEnabled()
    p.unlink();calls=[];monkeypatch.setattr(w,'launch',lambda *args:calls.append(args))
    w.start('arm');assert calls==[] and not w.arm_button.isEnabled()
    w.elf.clear.click();assert w.elf.path.text()=='' and not w.arm_button.isEnabled()

