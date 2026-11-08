"""Validated RAM image formats. No hardware I/O."""
from dataclasses import dataclass, field
from pathlib import Path
import binascii, hashlib, json, re, struct

CACHE_ADDR=0x0f000000
UART_ADDR=0x0f001000
SCRATCH=0x03000000
MAX_IMAGE=32*1024*1024

def crc(data): return binascii.crc32(data)&0xffffffff
def sha(data): return hashlib.sha256(data).hexdigest()
def overlap(a,n,b,m): return a<b+m and b<a+n

def valid_ram(address,size):
    if size<=0 or address<0x100000 or address+size>0x1f000000:
        raise ValueError('ARM memory must be within verified DDR: 0x00100000-0x1effffff.')
    for reserved,length in [(CACHE_ADDR,0x1000),(UART_ADDR,0x1000),(SCRATCH,4)]:
        if overlap(address,size,reserved,length):
            raise ValueError('ARM memory overlaps a loader reserved region.')

@dataclass
class Image:
    name: str
    data: bytes
    ram: int
    entry: int=0
    bss: list=field(default_factory=list)
    kind: str='arm'
    details: str=''


def read_elf(path):
    path=Path(path)
    if path.stat().st_size>128*1024*1024: raise ValueError('ELF file is too large.')
    data=path.read_bytes()
    if len(data)<52 or data[:7]!=b'\x7fELF\x01\x01\x01':
        raise ValueError('An ARM 32-bit little-endian ELF is required. ELF64 and text files are not supported.')
    h=struct.unpack_from('<HHIIIIIHHHHHH',data,16)
    typ,machine,version,entry,phoff,_,_,ehsize,phsize,phnum,*_=h
    if (typ,machine,version)!=(2,40,1) or ehsize!=52 or phsize!=32 or not 1<=phnum<=128:
        raise ValueError('A linked ARM ELF executable is required.')
    if phoff<52 or phoff+phsize*phnum>len(data): raise ValueError('Invalid ELF program headers.')
    segments=[]
    for i in range(phnum):
        p=struct.unpack_from('<8I',data,phoff+i*32)
        typ,offset,virtual,physical,filesz,memsz,flags,align=p
        if typ in (2,3): raise ValueError('Dynamic linking and Linux userspace ELF files are not supported. Select a standalone executable.')
        if typ!=1 or memsz==0: continue
        if virtual!=physical or filesz>memsz or offset+filesz>len(data): raise ValueError('Invalid ELF segment layout or virtual-address relocation required.')
        valid_ram(physical,memsz)
        if align not in (0,1) and (align&(align-1) or (physical-offset)%align): raise ValueError('Invalid ELF segment alignment.')
        if any(overlap(physical,memsz,s[3],s[5]) for s in segments): raise ValueError('ELF memory segments overlap.')
        segments.append(p)
    if not segments or not any(p[3]<=entry<p[3]+p[4] and p[6]&1 for p in segments) or entry%4:
        raise ValueError('ELF entry must be an ARM-aligned address within an executable segment.')
    base=min(p[3] for p in segments)
    end=max(p[3]+p[4] for p in segments if p[4])
    if end-base>MAX_IMAGE: raise ValueError('ELF segment span exceeds 32 MiB.')
    valid_ram(base,end-base)
    raw=bytearray(end-base);bss=[]
    for _,offset,_,physical,filesz,memsz,_,_ in segments:
        raw[physical-base:physical-base+filesz]=data[offset:offset+filesz]
        if memsz>filesz: bss.append([physical+filesz,memsz-filesz])
    return Image(path.name,bytes(raw),base,entry,bss,'arm',f'ARM ELF · {len(raw):,} bytes - entry 0x{entry:08x}')


def read_bit(path):
    path=Path(path)
    if path.stat().st_size>8*1024*1024: raise ValueError('Bitstream size exceeds the XC7Z020 limit.')
    data=path.read_bytes()
    if len(data)<16: raise ValueError('Truncated bitstream file.')
    pos=2+int.from_bytes(data[:2],'big')
    if data[pos:pos+3]!=b'\x00\x01a': raise ValueError('Invalid Vivado .bit header.')
    pos+=2;fields={}
    for tag in b'abcde':
        if pos>=len(data) or data[pos]!=tag: raise ValueError('Invalid bitstream field.')
        pos+=1;width=4 if tag==101 else 2
        if pos+width>len(data): raise ValueError('Truncated bitstream field.')
        length=int.from_bytes(data[pos:pos+width],'big');pos+=width
        if pos+length>len(data): raise ValueError('Truncated bitstream data.')
        fields[tag]=data[pos:pos+length];pos+=length
    part=fields[98].rstrip(b'\0').decode('ascii',errors='strict').lower()
    if not re.fullmatch(r'(?:xc)?7z020clg400(?:-1)?',part):
        raise ValueError(f'Only MicroZed 7020 / clg400 is supported. File target: {part}.')
    raw=fields[101]
    if pos!=len(data) or len(raw)%4 or b'\xaa\x99\x55\x66' not in raw[:256]: raise ValueError('Invalid bitstream configuration data.')
    # Swap 32-bit words for the factory PCAP loader.
    converted=bytearray(len(raw))
    for i in range(4):converted[i::4]=raw[3-i::4]
    return Image(path.name,bytes(converted),0x04000000,kind='fpga',details=f'{part} · {len(raw):,} bytes PCAP')
