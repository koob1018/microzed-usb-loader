from types import SimpleNamespace
import pytest
from backend import Board
from formats import UART_ADDR,valid_ram

@pytest.mark.parametrize('failure',[None,'switch','data'])
def test_transfer_always_restores_console(monkeypatch,failure):
    b=Board('TEST','.');events=[]
    monkeypatch.setattr(b,'prepare_transfer',lambda:events.append('prepare'))
    def switch():
        events.append('switch')
        if failure=='switch':raise RuntimeError('handshake')
    def raw(*args):
        events.append('data')
        if failure=='data':raise RuntimeError('transfer')
    monkeypatch.setattr(b,'switch_transfer',switch)
    monkeypatch.setattr(b,'_raw_upload',raw)
    monkeypatch.setattr(b,'restore_console',lambda:events.append('restore'))
    if failure:
        with pytest.raises(RuntimeError):b.upload(b'1234',0x4000000)
    else:b.upload(b'1234',0x4000000)
    assert events[0]=='prepare' and events[-1]=='restore'
    assert ('data' in events)==(failure!='switch')

def test_invalid_upload_does_not_switch(monkeypatch):
    b=Board('TEST','.')
    monkeypatch.setattr(b,'prepare_transfer',lambda:pytest.fail('unexpected transfer'))
    with pytest.raises(ValueError):b.upload(b'',0)

def test_disconnect_still_resets_host_speed(monkeypatch):
    b=Board('TEST','.')
    def broken(*args):raise OSError('Cable disconnected')
    b.s=SimpleNamespace(baudrate=921600,write=broken)
    with pytest.raises(RuntimeError,match='press RST'):b.restore_console()
    assert b.s.baudrate==115200

def test_helper_region_is_reserved():
    for address,size in ((UART_ADDR,4),(UART_ADDR-4,8),(UART_ADDR+4092,8)):
        with pytest.raises(ValueError):valid_ram(address,size)
    valid_ram(UART_ADDR+4096,4)


def test_helper_upload_failure_cancels_receiver(monkeypatch):
    b=Board('TEST','.');sent=[]
    b.s=SimpleNamespace(write=sent.append)
    def fail(*args):raise RuntimeError('helper transfer failed')
    monkeypatch.setattr(b,'_ymodem_upload',fail)
    monkeypatch.setattr(b,'collect',lambda *a:b'')
    with pytest.raises(RuntimeError,match='helper transfer failed'):b._raw_upload(b'1234',UART_ADDR)
    assert sent==[b'\x18'*5]
