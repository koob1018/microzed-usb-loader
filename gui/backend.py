"""Serial transport and narrowly bounded MicroZed Flash transactions."""
from pathlib import Path
import binascii,json,re,struct,time,threading
import serial
from contextlib import contextmanager
from formats import *

PROMPT=b'zynq-uboot>'
class Board:
    def __init__(self,port,assets,log=lambda s:None,progress=lambda n,s:None):
        self.port=port;self.assets=Path(assets);self.log=log;self.progress=progress;self.s=None;self.owns_serial=not hasattr(port,'read');self._uart_ready=False
    def __enter__(self):
        self.s=serial.Serial(self.port,115200,timeout=.05,write_timeout=10) if self.owns_serial else self.port
        if not self.s.is_open:raise RuntimeError('Serial port is disconnected.')
        return self
    def __exit__(self,*args):
        if self.s and self.owns_serial:self.s.close()
    def collect(self,seconds):
        data=bytearray();end=time.monotonic()+seconds
        while time.monotonic()<end:data.extend(self.s.read(max(self.s.in_waiting,1)))
        return bytes(data)
    def until(self,marker,timeout=120):
        data=bytearray();end=time.monotonic()+timeout
        while time.monotonic()<end:
            data.extend(self.s.read(max(self.s.in_waiting,1)))
            if marker in data:return bytes(data)
            if len(data)>2*1024*1024:raise RuntimeError('Serial output exceeds the allowed size.')
        raise TimeoutError(f'Board response timed out; expected {marker!r}. Press RST and retry.')
    def cmd(self,text,timeout=120):
        self.s.write(text.encode('ascii')+b'\r')
        data=self.until(PROMPT,timeout);self.log(data.decode(errors='replace'))
        if re.search(rb'\b(error|failed|unknown command)\b',data,re.I):raise RuntimeError('The board rejected a command. See serial output.')
        return data
    def enter(self):
        self._uart_ready=False
        self.s.reset_input_buffer();self.s.write(b'echo GUI_PROBE\r');data=self.collect(.6)
        if PROMPT in data:return
        if b'zynq>' in data:self.s.write(b'sync; reboot\r');data=b''
        self.log('Waiting for U-Boot. If an application is running, press the board RST button.')
        end=time.monotonic()+22;interrupted=False
        while time.monotonic()<end:
            data+=self.s.read(max(self.s.in_waiting,1))
            if not interrupted and b'Hit any key' in data:self.s.write(b' ');interrupted=True
            if PROMPT in data:return
        raise RuntimeError('U-Boot not detected. Keep USB connected, press RST and retry during boot.')
    def identify(self):
        if b'23727093' not in self.cmd('md.l f8000530 1'):raise RuntimeError('The device is not the verified XC7Z020. Operation stopped.')
    def expect(self,accepted,timeout=15):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            b=self.s.read(1)
            if b and b[0] in accepted:return b[0]
        raise TimeoutError('YMODEM response timed out. The board may need a reset.')
    def packet(self,number,payload):
        size=128 if len(payload)<=128 else 1024
        payload=payload.ljust(size,b'\x1a')
        frame=bytes([1 if size==128 else 2,number&255,255-(number&255)])+payload+binascii.crc_hqx(payload,0).to_bytes(2,'big')
        for _ in range(10):
            self.s.write(frame);self.s.flush();answer=self.expect({6,21,24},10)
            if answer==6:return
            if answer==24:raise RuntimeError('The board cancelled YMODEM reception.')
        raise RuntimeError('Too many YMODEM retries.')
    def prepare_transfer(self):
        if self._uart_ready:return
        self._raw_upload((self.assets/'uart_speed.bin').read_bytes(),UART_ADDR,'transfer helper')
        self.sync_code()
        self._uart_ready=True
    def switch_transfer(self):
        self.s.write(f'go {UART_ADDR:x} fast\r'.encode());self.s.flush()
        time.sleep(.1);self.s.baudrate=921600;self.s.reset_input_buffer()
        self.cmd('echo TRANSFER_READY',3)
    def restore_console(self):
        failure=None
        try:
            # Abort an unfinished YMODEM transfer before returning to the console.
            self.s.write(b'\x18'*5);self.collect(.1)
            self.s.write(f'go {UART_ADDR:x} slow\r'.encode());self.s.flush();time.sleep(.1)
        except Exception as exc:failure=exc
        try:self.s.baudrate=115200
        except Exception as exc:failure=exc
        try:
            if failure:raise failure
            self.s.reset_input_buffer();self.cmd('echo CONSOLE_READY',3)
        except Exception as exc:
            self._uart_ready=False
            raise RuntimeError('Console recovery was not confirmed. Reconnect USB and press RST before retrying.') from exc
    @contextmanager
    def transfer_mode(self):
        self.prepare_transfer()
        try:
            self.switch_transfer()
            yield
        finally:
            self.restore_console()
    def upload(self,data,address,label='image.bin'):
        if not data or address<0x100000 or address+len(data)>0x1f000000:raise ValueError('Download address range is out of bounds.')
        with self.transfer_mode():self._raw_upload(data,address,label)
    def _raw_upload(self,data,address,label='image.bin'):
        try:self._ymodem_upload(data,address,label)
        except Exception:
            # Helper uploads also need cancellation, before any speed switch exists.
            try:self.s.write(b'\x18'*5);self.collect(.1)
            except Exception:pass
            raise
    def _ymodem_upload(self,data,address,label='image.bin'):
        if not data or address<0x100000 or address+len(data)>0x1f000000:raise ValueError('Download address range is out of bounds.')
        self.s.reset_input_buffer();self.s.write(f'loady {address:x}\r'.encode());self.expect({67})
        header=b'image.bin\0'+str(len(data)).encode()+b'\0'
        self.packet(0,header.ljust(128,b'\0'));self.expect({67})
        for i,offset in enumerate(range(0,len(data),1024),1):
            self.packet(i,data[offset:offset+1024])
            self.progress(min(100,(offset+1024)*100//len(data)),f'Transferring {label} · {min(offset+1024,len(data)):,} / {len(data):,} bytes')
        self.s.write(b'\x04');answer=self.expect({6,21})
        if answer==21:self.s.write(b'\x04');self.expect({6})
        self.expect({67});self.packet(0,b'\0'*128)
        self.log(self.until(PROMPT).decode(errors='replace'))
        self.checksum(address,len(data),crc(data))
    def checksum(self,address,size,expected=None):
        output=self.cmd(f'crc32 {address:x} {size:x}')
        m=re.search(rb'==> ([0-9a-fA-F]{8})',output)
        if not m:raise RuntimeError('No CRC32 response received.')
        actual=int(m[1],16)
        if expected is not None and expected!=actual:raise RuntimeError('Checksum mismatch. Further operations stopped.')
        return actual
    def sync_code(self):
        self._raw_upload((self.assets/'cache_sync.bin').read_bytes(),CACHE_ADDR,'cache synchronization helper')
        result=self.cmd(f'go {CACHE_ADDR:x}')
        if not re.search(rb'rc = 0x0\s',result):raise RuntimeError('CPU state does not support a safe launch. Reset and retry.')
    def fpga(self,image):
        self.upload(image.data,image.ram,image.name)
        state=self.cmd('md.l f8007080 1');m=re.search(rb'f8007080:\s*([0-9a-fA-F]{8})',state)
        if not m:raise RuntimeError('Cannot read PCAP status.')
        self.cmd(f'mw.l f8007080 {int(m[1],16)&~0x10:x} 1')
        self.cmd(f'fpga load 0 {image.ram:x} {len(image.data):x}')
        # FPGA DONE bit must be asserted in devcfg interrupt status.
        state=self.cmd('md.l f800700c 1');m=re.search(rb'f800700c:\s*([0-9a-fA-F]{8})',state)
        if not m or not int(m[1],16)&4:raise RuntimeError('FPGA DONE was not detected. Configuration success is unconfirmed.')
        self.log('FPGA configured; DONE asserted.')
    def arm(self,image):
        self.upload(image.data,image.ram,image.name)
        for address,size in image.bss:self.cmd(f'mw.b {address:x} 0 {size:x}')
        self.sync_code();self._uart_ready=False;self.s.write(f'go {image.entry:x}\r'.encode())
        output=bytearray();end=time.monotonic()+12
        while time.monotonic()<end:
            chunk=self.s.read(max(self.s.in_waiting,1));output.extend(chunk)
            if chunk:self.log(chunk.decode(errors='replace'))
            if b'Hit any key' in output:
                self.s.write(b' ');self.log('The application triggered a reset. Automatic boot interrupted.')
                tail=self.until(PROMPT,20);self.log(tail.decode(errors='replace'));return 'Application started and then reset the board. Returned to U-Boot.'
            if PROMPT in output:
                m=re.search(rb'Application terminated, rc = 0x([0-9a-fA-F]+)',output)
                if not m or int(m[1],16):raise RuntimeError('CPU program returned an unsuccessful status. See serial output.')
                return 'CPU program executed and returned to U-Boot (exit code 0).'
            if b'ARM FAULT' in output or b'data abort' in output.lower():raise RuntimeError('CPU program fault. Check serial output and reset the board.')
        return 'CPU launch command sent; no return within 12 seconds. Verify applications that run continuously or produce no output separately.'
    def flash_read(self,offset,size,address=0x08000000):
        self.cmd(f'sf read {address:x} {offset:x} {size:x}')
        expected=self.checksum(address,size)
        return expected
    def read_bytes(self,size):
        """Read initialized DDR 0x08000000 with bounded CRC/ACK frames."""
        self._raw_upload((self.assets/'backup_sender.bin').read_bytes(),0x11000000,'backup reader');self.sync_code()
        self.s.write(f'go 11000000 {size:x}\r'.encode());self.until(b'MZ_BACKUP_READY\r\n',10)
        self.s.write(b'H');self.s.flush();time.sleep(.15);self.s.baudrate=921600;self.s.write(b'R')
        result=bytearray();retries=0
        def exact(n):
            b=bytearray();end=time.monotonic()+25
            while len(b)<n and time.monotonic()<end:b.extend(self.s.read(n-len(b)))
            if len(b)!=n:raise TimeoutError('Flash backup read timed out.')
            return bytes(b)
        try:
            while len(result)<size:
                if exact(4)!=b'MZBK':raise RuntimeError('Invalid backup frame.')
                off,n,expected=struct.unpack('<III',exact(12))
                if off!=len(result) or n!=min(65536,size-off):raise RuntimeError('Invalid backup frame range.')
                data=exact(n)
                if crc(data)!=expected:
                    retries+=1
                    if retries>10:raise RuntimeError('Repeated backup checksum failures.')
                    self.s.write(b'N');continue
                result.extend(data);self.s.write(b'A');self.progress(len(result)*100//size,'Backing up current Flash contents')
            self.s.flush();self.s.baudrate=115200;self.collect(1)
            self.cmd('echo BACKUP_COMPLETE')
            return bytes(result)
        finally:
            if self.s.baudrate!=115200:
                self.s.write(b'C');self.s.flush();time.sleep(3);self.s.baudrate=115200
    def protected_profile(self):
        self._uart_ready=False
        self.cmd('sf probe 0 0 0')
        # Exact known factory bootloader profile. Never guess erase ranges.
        self.cmd('sf read 7000000 0 50000');self.checksum(0x07000000,0x50000,0x422d20eb)
        self.cmd('sf read 7000000 100000 f00000');self.checksum(0x07000000,0xf00000,0x21b4f701)
    def region_snapshot(self,directory):
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
        expected=self.flash_read(FLASH_START,PAYLOAD_SIZE+ENV_SIZE)
        region=self.read_bytes(PAYLOAD_SIZE+ENV_SIZE)
        if crc(region)!=expected:raise RuntimeError('Full backup CRC mismatch.')
        # Independent re-read of the flash, not just the RAM buffer.
        if self.flash_read(FLASH_START,len(region))!=expected:raise RuntimeError('Independent Flash reread checksum mismatch.')
        path=directory/'region.bin';path.write_bytes(region)
        manifest={'format':'MICROZED_GUI_BACKUP_V1','offset':FLASH_START,'size':len(region),'sha256':sha(region),'crc32':f'{crc(region):08x}','port':getattr(self.port,'port',self.port)}
        (directory/'backup.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        self.log(f'Backup completed: {directory}')
        return region
    def bounded_write(self,address,offset,data):
        if (offset,len(data)) not in [(FLASH_START,PAYLOAD_SIZE),(ENV_OFFSET,ENV_SIZE)]:raise ValueError('Writing to protected regions is prohibited.')
        self.upload(data,address,'Flash data')
        self.cmd(f'sf update {address:x} {offset:x} {len(data):x}')
        self.cmd(f'sf read 6400000 {offset:x} {len(data):x}')
        self.checksum(0x06400000,len(data),crc(data))
    def flash_transaction(self,old_region,new_payload,new_env):
        old_env=parse_env(old_region[PAYLOAD_SIZE:])
        fallback=dict(old_env);fallback['bootcmd']='run qspiboot'
        fallback=encode_env(fallback)
        if old_region[:PAYLOAD_SIZE]==new_payload and old_region[PAYLOAD_SIZE:]==new_env:
            self.log('Flash already contains the selected data. No rewrite needed.');return
        # Commit factory fallback BEFORE reusing the only payload slot.
        # Power loss during payload update therefore boots untouched factory Linux.
        self.progress(0,'Saving the factory boot fallback')
        self.bounded_write(0x06200000,ENV_OFFSET,fallback)
        try:
            self.progress(0,'Writing and verifying the file area')
            self.bounded_write(0x06000000,FLASH_START,new_payload)
            self.progress(0,'Committing the new automatic boot configuration')
            self.bounded_write(0x06200000,ENV_OFFSET,new_env)
        except Exception:
            self.log('Write did not complete. U-Boot is preserved for recovery; automatic boot may have reverted to factory Linux. This operation was not successful.')
            raise
        self.protected_profile()
        # Match the running U-Boot environment to its newly committed copy.
        self.cmd('env import -c 6200000 20000')
    def save(self,fpga,arm,directory):
        self.protected_profile();region=self.region_snapshot(directory)
        old_fpga,apps=read_bundle(region[:PAYLOAD_SIZE])
        env=parse_env(region[PAYLOAD_SIZE:])
        chosen_fpga=fpga if fpga else old_fpga
        chosen_apps=[arm] if arm else apps
        payload,new_env,meta,used=make_bundle(chosen_fpga,chosen_apps,(self.assets/'cache_sync.bin').read_bytes(),env)
        self.log(f'Preserving/writing: FPGA={chosen_fpga.name if chosen_fpga else "none"}; CPU={", ".join(a.name for a in chosen_apps) or "none"}; Flash usage: {used:,}/{PAYLOAD_SIZE:,} bytes.')
        self.flash_transaction(region,payload,new_env)
        (Path(directory)/'new-layout.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
        (Path(directory)/'result.json').write_text(json.dumps({'status':'FLASH_VERIFIED','old_sha256':sha(region),'new_sha256':sha(payload+new_env)},indent=2))
        return 'Flash saved and readback verified. Runs automatically on the next boot. The new CPU program has not been started.'
    def restore(self,manifest_path,directory):
        path=Path(manifest_path);m=json.loads(path.read_text());region=(path.parent/'region.bin').read_bytes()
        if m.get('format')!='MICROZED_GUI_BACKUP_V1' or m.get('offset')!=FLASH_START or len(region)!=PAYLOAD_SIZE+ENV_SIZE or sha(region)!=m.get('sha256'):raise ValueError('Invalid backup format or checksum.')
        parse_env(region[PAYLOAD_SIZE:]);read_bundle(region[:PAYLOAD_SIZE])
        self.protected_profile();old=self.region_snapshot(directory)
        self.flash_transaction(old,region[:PAYLOAD_SIZE],region[PAYLOAD_SIZE:])
        return 'Selected backup and boot settings restored. U-Boot and Linux are unchanged.'
