"""Validated file formats and bounded, versioned Flash bundles. No hardware I/O."""
from dataclasses import dataclass, field
from pathlib import Path
import binascii, hashlib, json, re, struct

FLASH_START=0x50000
PAYLOAD_SIZE=0x90000
ENV_OFFSET=0xe0000
ENV_SIZE=0x20000
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


def parse_env(blob):
    if len(blob)!=ENV_SIZE or crc(blob[4:])!=struct.unpack_from('<I',blob)[0]: raise ValueError('Invalid Flash environment CRC.')
    body=blob[4:];end=body.find(b'\0\0')
    if end<0: raise ValueError('Environment terminator is missing.')
    result={}
    for line in body[:end].split(b'\0'):
        k,v=line.decode('ascii').split('=',1)
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',k): raise ValueError('Invalid environment variable name.')
        result[k]=v
    return result

def encode_env(env):
    for k,v in env.items():
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',k) or any(c in v for c in '\0\r\n'):raise ValueError('Environment contains invalid characters.')
    data=b'\0'.join(f'{k}={v}'.encode('ascii') for k,v in sorted(env.items()))+b'\0\0'
    if len(data)>ENV_SIZE-4: raise ValueError('Boot configuration is too large.')
    data=data.ljust(ENV_SIZE-4,b'\0')
    return struct.pack('<I',crc(data))+data


def read_bundle(payload):
    if len(payload)!=PAYLOAD_SIZE: raise ValueError('Invalid Flash region length.')
    if payload==b'\xff'*len(payload):return None,[]
    try:meta=json.loads(payload[:0x1000].split(b'\n',1)[0])
    except Exception as e:raise ValueError('The Flash file area contains unknown data. Overwrite refused.') from e
    if meta.get('magic')=='MICROZED_COURSE_QSPI_V1':
        items=meta['items'];fpga=items.get('fpga');apps=[items[k]|{'name':k,'entry':items[k]['ram'],'bss':[]} for k in ('led','nn') if k in items]
    elif meta.get('magic')=='MICROZED_GUI_V2':fpga=meta.get('fpga');apps=meta['apps']
    else:raise ValueError('Unsupported Flash layout version.')
    occupied=[]
    def unpack(m,kind):
        offset=m['flash']-FLASH_START;n=m['bytes']
        if offset<0x1000 or n<=0 or offset+n>len(payload):raise ValueError('Flash metadata is out of bounds.')
        if any(overlap(offset,n,a,b) for a,b in occupied):raise ValueError('Flash data blocks overlap.')
        occupied.append((offset,n));raw=payload[offset:offset+n]
        if sha(raw)!=m['sha256'] or crc(raw)!=int(m['crc32'],16):raise ValueError('Flash file checksum failed. Corrupted data cannot be preserved.')
        ram=m['ram'];entry=m.get('entry',ram);bss=m.get('bss',[])
        if kind=='arm':
            valid_ram(ram,n)
            if not ram<=entry<ram+n or entry%4:raise ValueError('Invalid Flash ARM entry point.')
            for address,size in bss:valid_ram(address,size)
        elif ram!=0x04000000:raise ValueError('Invalid Flash FPGA buffer.')
        return Image(m.get('name',Path(m.get('source',kind)).name),raw,ram,entry,bss,kind)
    return unpack(fpga,'fpga') if fpga else None,[unpack(m,'arm') for m in apps]


def make_bundle(fpga,apps,cache,env):
    payload=bytearray(b'\xff'*PAYLOAD_SIZE);cursor=0x1000
    def pack(img):
        nonlocal cursor
        cursor=(cursor+255)&~255
        if cursor+len(img.data)>PAYLOAD_SIZE:raise ValueError('Selected and preserved files exceed the 576 KiB Flash file area. Use temporary loading or a smaller design.')
        payload[cursor:cursor+len(img.data)]=img.data
        m={'name':img.name,'flash':FLASH_START+cursor,'bytes':len(img.data),'ram':img.ram,'entry':img.entry,'bss':img.bss,'sha256':sha(img.data),'crc32':f'{crc(img.data):08x}'}
        cursor+=len(img.data);return m
    meta={'magic':'MICROZED_GUI_V2','cache':pack(Image('cache_sync',cache,CACHE_ADDR,CACHE_ADDR)),'fpga':pack(fpga) if fpga else None,'apps':[pack(a) for a in apps]}
    header=json.dumps(meta,separators=(',',':'),ensure_ascii=True).encode()+b'\n'
    if len(header)>0x1000:raise ValueError('Flash file metadata is too large.')
    payload[:len(header)]=header
    newenv={k:v for k,v in env.items() if not k.startswith(('gui_','course_')) and k not in ('courseboot','filesize','fileaddr')}
    if 'qspiboot' not in newenv:raise ValueError('Factory Linux boot entry is missing.')
    newenv.update(bootdelay='5',bootcmd='run gui_boot',factoryboot='run qspiboot')
    def load(m):return f"sf read {m['ram']:x} {m['flash']:x} {m['bytes']:x} && crc32 {m['ram']:x} {m['bytes']:x} {SCRATCH:x} && itest.l *{SCRATCH:x} == {m['crc32']}"
    newenv['gui_prepare']='sf probe 0 0 0 && '+load(meta['cache'])
    steps=['run gui_prepare']
    if fpga:
        m=meta['fpga'];newenv['gui_fpga']=load(m)+f" && mw.l f8007080 30800100 1 && fpga load 0 4000000 {m['bytes']:x}"
        steps.append('run gui_fpga')
    for i,m in enumerate(meta['apps']):
        command=load(m)
        for address,size in m['bss']:command+=f' && mw.b {address:x} 0 {size:x}'
        command+=f" && go {CACHE_ADDR:x} && go {m['entry']:x}"
        if len(command)>1800:raise ValueError('Too many ELF segments: boot command exceeds the U-Boot limit.')
        newenv[f'gui_app{i}']=command;steps.append(f'run gui_app{i}')
    newenv['gui_boot']='if '+' && '.join(steps)+'; then echo GUI_AUTORUN_RETURNED_OK; else echo GUI_AUTORUN_FAILED; fi'
    return bytes(payload),encode_env(newenv),meta,cursor
