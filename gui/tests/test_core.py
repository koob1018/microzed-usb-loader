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
