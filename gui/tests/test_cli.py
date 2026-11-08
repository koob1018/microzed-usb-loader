from pathlib import Path
from types import SimpleNamespace
import pytest
import cli
from backend import Board
import app as gui

ROOT=Path(__file__).resolve().parents[2]

@pytest.mark.parametrize('target',['fpga','cpu','both'])
@pytest.mark.parametrize('monitor',[False,True])
@pytest.mark.parametrize('build',[False,True])
def test_cli_options(monkeypatch,target,monitor,build):
    calls=[];compiled=[]
    monkeypatch.setattr(cli,'run',lambda *a:calls.append(a))
    monkeypatch.setattr(cli,'build_helpers',lambda p:compiled.append(p) or cli.ASSETS)
    args=['--port','TEST']
    if target in ('fpga','both'):args+=['--bit',str(ROOT/'build/usb_probe.bit')]
    if target in ('cpu','both'):args+=['--elf',str(ROOT/'build/led_test.elf')]
    if monitor:args+=['--monitor']
    if build:args+=['--build-helpers']
    assert cli.main(args)==0
    port,mode,fpga,cpu,helpers,watch=calls[0]
    assert mode=='ram' and port=='TEST' and watch==monitor
    assert bool(fpga)==(target in ('fpga','both')) and bool(cpu)==(target in ('cpu','both'))
    assert bool(compiled)==build

@pytest.mark.parametrize('args',[[],['--port','TEST'],['--port','TEST','--flash'],['--port','TEST','--elf','missing.elf']])
def test_invalid_cli_never_opens_serial(monkeypatch,args):
    monkeypatch.setattr(cli,'run',lambda *a:pytest.fail('serial opened'))
    with pytest.raises(SystemExit):cli.main(args)

def test_monitor_only_does_not_boot(monkeypatch,tmp_path):
    events=[]
    class FakeBoard:
        def __init__(self,*a):pass
        def __enter__(self):events.append('open');return self
        def __exit__(self,*a):events.append('close')
        def enter(self):pytest.fail('monitor must not send boot commands')
    monkeypatch.setattr(cli,'Board',FakeBoard);monkeypatch.setattr(cli,'DATA',tmp_path)
    monkeypatch.setattr(cli,'show_output',lambda *a:events.append('monitor'))
    cli.run('TEST','ram',None,None,cli.ASSETS,True)
    assert events==['open','monitor','close']

@pytest.mark.parametrize('target',['fpga','cpu','both'])
@pytest.mark.parametrize('failure',[False,True])
def test_execution_and_port_cleanup(monkeypatch,tmp_path,target,failure):
    events=[]
    class FakeBoard:
        def __init__(self,*a):pass
        def __enter__(self):events.append('open');return self
        def __exit__(self,*a):events.append('close')
        def enter(self):events.append('enter')
        def identify(self):pass
        def fpga(self,image):
            events.append('fpga')
            if failure:raise OSError('disconnected')
        def arm(self,image):
            events.append('cpu')
            if failure:raise OSError('disconnected')
            return 'success'
    monkeypatch.setattr(cli,'Board',FakeBoard);monkeypatch.setattr(cli,'DATA',tmp_path)
    args=('TEST','ram',object() if target!='cpu' else None,object() if target!='fpga' else None,cli.ASSETS)
    if failure:
        with pytest.raises(OSError):cli.run(*args)
    else:cli.run(*args)
    assert events[0]=='open' and events[-1]=='close'
    if not failure:assert events[2:-1]==(['fpga'] if target=='fpga' else ['cpu'] if target=='cpu' else ['fpga','cpu'])

def test_monitor_utf8_and_interrupt():
    chunks=iter([b'\xe4\xbd',b'\xa0\n'])
    def read(n):
        try:return next(chunks)
        except StopIteration:raise KeyboardInterrupt
    output=[]
    cli.show_output(SimpleNamespace(s=SimpleNamespace(in_waiting=1,read=read)),output.append)
    assert ''.join(output)=='你\n'

def test_compiler_missing(monkeypatch,tmp_path):
    monkeypatch.setattr(cli.shutil,'which',lambda n:None)
    with pytest.raises(SystemExit,match='needs arm-none-eabi'):cli.build_helpers(tmp_path)

def test_compiler_failure(monkeypatch,tmp_path):
    monkeypatch.setattr(cli.shutil,'which',lambda n:n)
    monkeypatch.setattr(cli.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=1,stderr='compile error'))
    with pytest.raises(SystemExit,match='cache_sync helper failed'):cli.build_helpers(tmp_path)

@pytest.mark.parametrize('command',['sf write 1 2 3','sf update 1 2 3','sf erase 0 10000','saveenv','env save','echo test; sf update 1 2 3'])
def test_persistent_commands_rejected(command):
    board=Board('TEST','.')
    with pytest.raises(ValueError,match='disabled'):board.cmd(command)

def test_removed_flash_api():
    for method in ('save','restore','bounded_write','flash_transaction','region_snapshot'):
        assert not hasattr(Board,method)

def test_worker_rejects_flash_before_connect(monkeypatch,tmp_path):
    monkeypatch.setattr(gui,'DATA',tmp_path)
    monkeypatch.setattr(gui,'Board',lambda *a:pytest.fail('serial opened'))
    worker=gui.Worker('TEST','flash',object(),None);results=[]
    worker.result.connect(lambda *a:results.append(a));worker.run()
    assert not results[0][0] and 'disabled' in results[0][1]

def test_ctrl_c_cancels_helper_upload(monkeypatch):
    board=Board('TEST','.');sent=[];board.s=SimpleNamespace(write=sent.append)
    def stop(*a):raise KeyboardInterrupt
    monkeypatch.setattr(board,'_ymodem_upload',stop);monkeypatch.setattr(board,'collect',lambda *a:b'')
    with pytest.raises(KeyboardInterrupt):board._raw_upload(b'1234',0xf001000)
    assert sent==[b'\x18'*5]
