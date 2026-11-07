import sys,struct,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'gui'))
from formats import *
from backend import Board

def elf_file(tmp_path,address=0x100000,entry=None,filesz=4,memsz=16):
    d=bytearray(0x104);d[:16]=b'\x7fELF\x01\x01\x01'+b'\0'*9
    struct.pack_into('<HHIIIIIHHHHHH',d,16,2,40,1,address if entry is None else entry,52,0,0x5000200,52,32,1,0,0,0)
    struct.pack_into('<8I',d,52,1,0x100,address,address,filesz,memsz,5,4)
    d[0x100:]=b'\x1e\xff\x2f\xe1';p=tmp_path/'sample.elf';p.write_bytes(d);return p

def test_real_elf_matches_independent_objcopy():
    img=read_elf(ROOT/'build/hello.elf')
    assert img.data==(ROOT/'build/hello.bin').read_bytes()
    assert img.entry==0x10000000

def test_bit_matches_hardware_verified_payload():
    img=read_bit(ROOT/'build/usb_probe.bit')
    assert img.data==(ROOT/'build/usb_probe.pcap.bin').read_bytes()

def test_elf_preserves_zero_fill_description(tmp_path):
    img=read_elf(elf_file(tmp_path));assert img.bss==[[0x100004,12]];assert len(img.data)==4

@pytest.mark.parametrize('address,entry,filesz,memsz',[(0xf000000,None,4,16),(0x1f000000,None,4,16),(0x3000000,None,4,16),(0x100000,0x200000,4,16),(0x100000,None,17,16)])
def test_reject_dangerous_elf(tmp_path,address,entry,filesz,memsz):
    with pytest.raises(ValueError):read_elf(elf_file(tmp_path,address,entry,filesz,memsz))

def test_bit_reject_other_device(tmp_path):
    data=(ROOT/'build/usb_probe.bit').read_bytes().replace(b'7z020clg400',b'7z010clg400')
    p=tmp_path/'wrong.bit';p.write_bytes(data)
    with pytest.raises(ValueError):read_bit(p)

def test_elf_gap_cannot_overwrite_cache_helper(tmp_path):
    p=elf_file(tmp_path,address=0x0efffff0,filesz=4,memsz=4)
    data=bytearray(p.read_bytes());data.extend(b'abcd')
    struct.pack_into('<H',data,44,2)
    struct.pack_into('<8I',data,84,1,0x104,0x0f001000,0x0f001000,4,4,5,4)
    p.write_bytes(data)
    with pytest.raises(ValueError,match='reserved region'):read_elf(p)

def test_legacy_import_and_partial_update():
    old=(ROOT/'gui/tests/fixtures/legacy-payload.bin').read_bytes();env=parse_env((ROOT/'gui/tests/fixtures/synthetic-environment.bin').read_bytes())
    fpga,apps=read_bundle(old);assert len(apps)==2
    cache=(ROOT/'gui/assets/cache_sync.bin').read_bytes()
    blob,encoded,meta,used=make_bundle(fpga,apps,cache,env)
    retained,oldapps=read_bundle(blob)
    assert retained.data==fpga.data and [x.data for x in oldapps]==[x.data for x in apps]
    newapp=Image('new.elf',b'1234',0x100000,0x100000)
    blob,encoded,_,_=make_bundle(fpga,[newapp],cache,env)
    retained,newapps=read_bundle(blob);assert retained.data==fpga.data;assert len(newapps)==1;assert newapps[0].data==b'1234'
    assert parse_env(encoded)['bootcmd']=='run gui_boot'
    assert parse_env(encoded)['qspiboot']==env['qspiboot']
    assert used<PAYLOAD_SIZE

def test_oversize_and_corrupt_flash_refused():
    env=parse_env((ROOT/'gui/tests/fixtures/synthetic-environment.bin').read_bytes());cache=(ROOT/'gui/assets/cache_sync.bin').read_bytes()
    with pytest.raises(ValueError):make_bundle(None,[Image('large',b'1'*PAYLOAD_SIZE,0x100000,0x100000)],cache,env)
    bad=bytearray((ROOT/'gui/tests/fixtures/legacy-payload.bin').read_bytes());bad[0x1000]^=1
    with pytest.raises(ValueError):read_bundle(bytes(bad))
    with pytest.raises(ValueError):read_bundle(b'?'*PAYLOAD_SIZE)

def test_environment_corruption_refused():
    raw=bytearray((ROOT/'gui/tests/fixtures/synthetic-environment.bin').read_bytes());raw[-1]^=1
    with pytest.raises(ValueError):parse_env(bytes(raw))

class FakeBoard(Board):
    def __init__(self,fail=False):super().__init__('FAKE',ROOT/'gui/assets');self.writes=[];self.fail=fail
    def bounded_write(self,address,offset,data):
        if self.fail and offset==FLASH_START:raise RuntimeError('power loss')
        self.writes.append((offset,data))
    def protected_profile(self):pass
    def cmd(self,text,timeout=120):return b''

def test_flash_commit_order_and_interruption():
    old=(ROOT/'gui/tests/fixtures/legacy-payload.bin').read_bytes()+(ROOT/'gui/tests/fixtures/synthetic-environment.bin').read_bytes()
    env=parse_env(old[PAYLOAD_SIZE:]);newenv=encode_env(env|{'bootcmd':'run gui_boot'})
    board=FakeBoard();board.flash_transaction(old,b'\xff'*PAYLOAD_SIZE,newenv)
    assert [x[0] for x in board.writes]==[ENV_OFFSET,FLASH_START,ENV_OFFSET]
    assert parse_env(board.writes[0][1])['bootcmd']=='run qspiboot'
    assert board.writes[-1][1]==newenv
    board=FakeBoard(True)
    with pytest.raises(RuntimeError):board.flash_transaction(old,b'\xff'*PAYLOAD_SIZE,newenv)
    assert len(board.writes)==1 and parse_env(board.writes[0][1])['bootcmd']=='run qspiboot'

def test_write_guard():
    with pytest.raises(ValueError):Board('FAKE',ROOT/'gui/assets').bounded_write(0x6000000,0,b'0'*0x50000)



def test_backup_manifest_with_connected_serial(tmp_path,monkeypatch):
    from types import SimpleNamespace
    port=SimpleNamespace(port='TEST',read=lambda n:b'')
    board=Board(port,ROOT/'gui/assets')
    region=(ROOT/'gui/tests/fixtures/legacy-payload.bin').read_bytes()+(ROOT/'gui/tests/fixtures/synthetic-environment.bin').read_bytes()
    monkeypatch.setattr(board,'flash_read',lambda *a:crc(region))
    monkeypatch.setattr(board,'read_bytes',lambda n:region)
    assert board.region_snapshot(tmp_path/'backup')==region
    assert json.loads((tmp_path/'backup/backup.json').read_text())['port']=='TEST'
