"""MicroZed USB Loader — native Qt GUI."""
import sys,os,traceback,json,serial
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt,QThread,Signal,QTimer
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QComboBox,QCheckBox,QButtonGroup,QFileDialog,QPlainTextEdit,QProgressBar,QFrame,QMessageBox)
from serial.tools import list_ports
from formats import read_bit,read_elf,PAYLOAD_SIZE
from backend import Board
from driver_setup import DriverTask,needs_install

ASSETS=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'assets'
DATA=Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'MicroZedLoader'

class FileCard(QFrame):
    changed=Signal()
    dropped=Signal(list)
    def __init__(self,title,extension,parent=None):
        super().__init__(parent);self.extension=extension;self.setObjectName('card');self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        layout=QVBoxLayout(self);layout.setContentsMargins(20,12,20,12)
        header=QHBoxLayout();head=QLabel(title);head.setObjectName('cardTitle');header.addWidget(head);header.addStretch()
        badge=QLabel(extension.upper());badge.setObjectName('badge');header.addWidget(badge);layout.addLayout(header)
        self.hint=QLabel(f'Drop your {extension} file here, or browse to select it.');self.hint.setObjectName('muted');layout.addWidget(self.hint)
        row=QHBoxLayout();self.path=QLineEdit();self.path.setPlaceholderText(f'File path ({extension})');self.path.setAccessibleName(title+' file path');row.addWidget(self.path,1)
        self.browse=QPushButton('Browse...');self.browse.setAccessibleName(title+' browse');self.browse.clicked.connect(self.choose);row.addWidget(self.browse);layout.addLayout(row)
        self.clear=QPushButton('Clear');self.clear.setAccessibleName(title+' clear file');self.clear.clicked.connect(self.path.clear);row.addWidget(self.clear)
        self.path.setMinimumHeight(38);self.path.setAcceptDrops(False);self.browse.setMinimumHeight(38)
        self.info=QLabel('No file selected');self.info.setWordWrap(True);self.info.setObjectName('fileInfo');layout.addWidget(self.info)
        self.path.textChanged.connect(self.changed)
    def choose(self):
        path,_=QFileDialog.getOpenFileName(self,'Select '+self.extension+' file',self.path.text(),f'{self.extension} file (*{self.extension})',options=QFileDialog.Option.DontUseNativeDialog)
        if path:self.path.setText(path)
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and all(u.isLocalFile() for u in event.mimeData().urls()):event.acceptProposedAction()
    def dropEvent(self,event):
        self.dropped.emit([u.toLocalFile() for u in event.mimeData().urls()]);event.acceptProposedAction()

class Worker(QThread):
    text=Signal(str);progress=Signal(int,str);result=Signal(bool,str,str)
    def __init__(self,port,mode,fpga,arm):
        super().__init__();self.port=port;self.mode=mode;self.fpga=fpga;self.arm=arm
    def run(self):
        stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        directory=DATA/'backups'/stamp;logpath=DATA/'logs'/f'{stamp}.log'
        try:
            if self.fpga is None and self.arm is None:raise ValueError('Select at least one valid file.')
            if not self.port:raise ValueError('Select a serial port.')
            if self.mode not in ('ram','flash'):raise ValueError('Select a programming mode.')
            logpath.parent.mkdir(parents=True,exist_ok=True)
            with logpath.open('w',encoding='utf-8') as f:
                def log(text):f.write(text);f.flush();self.text.emit(text)
                try:
                    with Board(self.port,ASSETS,log,self.progress.emit) as board:
                        self.progress.emit(0,'Connecting to the board and detecting U-Boot');board.enter();board.identify()
                        if self.mode=='flash':message=board.save(self.fpga,self.arm,directory)
                        else:
                            if self.fpga:board.fpga(self.fpga)
                            message=board.arm(self.arm) if self.arm else 'FPGA configured and DONE verified. Flash is unchanged.'
                    self.result.emit(True,message,str(logpath))
                except Exception:
                    log('\n'+traceback.format_exc());raise
        except Exception as exc:
            self.result.emit(False,str(exc),str(logpath))

class Window(QMainWindow):
    def __init__(self,auto_driver=True):
        super().__init__();self.setWindowTitle('MicroZed USB Loader');self.resize(960,940);self.setMinimumSize(760,920);self.setAcceptDrops(True)
        self.worker=None;self.images={};self.busy=False;self.connection=None
        container=QWidget();self.setCentralWidget(container);layout=QVBoxLayout(container);layout.setContentsMargins(28,22,28,22);layout.setSpacing(12)
        title=QLabel('MicroZed USB Loader');title.setObjectName('title');layout.addWidget(title)
        row=QHBoxLayout();self.driver_button=QPushButton('Checking driver...');self.driver_button.setEnabled(False);self.driver_button.clicked.connect(self.setup_driver);row.addWidget(self.driver_button);row.addStretch();layout.addLayout(row)
        row=QHBoxLayout();row.addWidget(QLabel('Serial port'));self.ports=QComboBox();self.ports.setAccessibleName('Serial port selection');self.ports.setMinimumWidth(300);row.addWidget(self.ports,1)
        self.refresh=QPushButton('Refresh');self.refresh.clicked.connect(self.scan);row.addWidget(self.refresh)
        layout.addLayout(row)
        row=QHBoxLayout();self.connect_button=QPushButton('Connect');self.disconnect_button=QPushButton('Disconnect');self.connection_label=QLabel('Disconnected');self.connection_label.setObjectName('muted')
        self.connect_button.clicked.connect(self.connect_serial);self.disconnect_button.clicked.connect(self.disconnect_serial)
        row.addWidget(self.connect_button);row.addWidget(self.disconnect_button);row.addWidget(self.connection_label);row.addStretch();layout.addLayout(row)
        self.bit=FileCard('FPGA','.bit');self.elf=FileCard('CPU','.elf')
        for card in [self.bit,self.elf]:layout.addWidget(card);card.changed.connect(self.schedule_validate);card.dropped.connect(self.drop_paths)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.validate)
        row=QHBoxLayout();row.addWidget(QLabel('Mode'));row.addSpacing(16)
        self.flash_mode=QCheckBox('Save to Flash');self.ram_mode=QCheckBox('Run from RAM')
        self.mode_group=QButtonGroup(self);self.mode_group.setExclusive(True)
        for button in (self.flash_mode,self.ram_mode):
            self.mode_group.addButton(button);row.addWidget(button,1);button.toggled.connect(self.mode_changed)
        layout.addLayout(row)
        self.mode_hint=QLabel();self.mode_hint.setWordWrap(True);self.mode_hint.setObjectName('muted');layout.addWidget(self.mode_hint)
        row=QHBoxLayout();self.bit_button=QPushButton('Load FPGA only');self.arm_button=QPushButton('Load ARM only');self.both_button=QPushButton('Load both');self.both_button.setObjectName('primary')
        for button,target in [(self.bit_button,'fpga'),(self.arm_button,'arm'),(self.both_button,'both')]:button.clicked.connect(lambda checked=False,t=target:self.start(t));row.addWidget(button)
        layout.addLayout(row)
        self.bar=QProgressBar();self.bar.setRange(0,100);self.bar.setValue(0);layout.addWidget(self.bar)
        console_title=QLabel('Serial output');console_title.setObjectName('sectionTitle');layout.addWidget(console_title)
        self.log=QPlainTextEdit();self.log.setReadOnly(True);self.log.setPlaceholderText('Transfer progress and board messages will appear here.');self.log.setMaximumBlockCount(6000);self.log.setMinimumHeight(110);layout.addWidget(self.log,1)
        row=QHBoxLayout();row.addStretch();help_button=QPushButton('Help');help_button.clicked.connect(self.help);row.addWidget(help_button);layout.addLayout(row)
        self.scan();self.flash_mode.setChecked(True);self.mode_changed();self.validate()
        self.setStyleSheet('''
QMainWindow {background:#f3f5f9;} QWidget {font-family:"Segoe UI";font-size:10pt;color:#24324b;}
QLabel#badge {background:#edf2fb;color:#365b92;border-radius:4px;padding:3px 9px;font-size:9pt;font-weight:600;} QLabel#sectionTitle {font-weight:600;color:#536982;}
QCheckBox {background:white;border:1px solid #dbe2ec;border-radius:6px;padding:10px 14px;spacing:10px;} QCheckBox:checked {background:#edf3ff;border-color:#7295cd;}
QLabel#title {font-size:23pt;font-weight:700;color:#17233b;} QLabel#muted {color:#65738a;} QLabel#cardTitle {font-size:12pt;font-weight:600;}
QFrame#card {background:white;border:1px solid #dbe2ec;border-radius:10px;} QLabel#fileInfo {font-size:9pt;color:#536982;}
QLineEdit,QComboBox {background:white;border:1px solid #cbd5e3;border-radius:6px;padding:8px;} QComboBox::drop-down {border:0;width:22px;}
QPushButton {background:white;border:1px solid #cbd5e3;border-radius:6px;padding:9px 15px;font-weight:500;} QPushButton:hover {background:#eaf0fb;border-color:#7295cd;}
QPushButton#primary {background:#275ecc;border-color:#275ecc;color:white;font-weight:600;} QPushButton#primary:hover {background:#194eae;}
QPushButton:disabled {background:#e7ebf1;border-color:#e0e5ec;color:#9aa5b5;} QPushButton#primary:disabled {background:#b1c4e7;border-color:#b1c4e7;color:white;}
QPlainTextEdit {background:#192439;color:#dbe7fa;border:0;border-radius:8px;padding:10px;font-family:Consolas;font-size:9pt;}
QProgressBar {border:0;background:#e1e8f2;border-radius:4px;height:12px;text-align:center;} QProgressBar::chunk {background:#3476dd;border-radius:4px;}
''')
        self.serial_timer=QTimer(self);self.serial_timer.timeout.connect(self.poll_serial);self.serial_timer.start(100)
        self.ports.currentIndexChanged.connect(self.update_connection_controls)
        self.update_connection_controls()
        if auto_driver:QTimer.singleShot(0,self.ensure_driver)
    def update_connection_controls(self):
        connected=self.connection is not None and self.connection.is_open
        states=[(self.connect_button,not self.busy and not connected and self.ports.currentData() is not None),
                (self.disconnect_button,not self.busy and connected),
                (self.ports,not self.busy and not connected),
                (self.refresh,not self.busy and not connected)]
        # Enable and focus the next serial action before disabling the old one.
        # Otherwise Qt advances focus into the file path and selects its text.
        focused=QApplication.focusWidget()
        for widget,enabled in states:
            if enabled:widget.setEnabled(True)
        if any(widget is focused and not enabled for widget,enabled in states):
            target=self.disconnect_button if connected else self.connect_button
            (target if target.isEnabled() else self.log).setFocus(Qt.OtherFocusReason)
        for widget,enabled in states:
            if not enabled:widget.setEnabled(False)
        self.connection_label.setText('Connected: '+self.connection.port if connected else 'Disconnected')
    def connect_serial(self):
        if self.busy or self.connection is not None:return
        port=self.ports.currentData()
        if not port:return
        try:
            self.connection=serial.Serial(port,115200,timeout=.05,write_timeout=10)
            self.append_log('Connected to '+port+'.\n')
        except Exception as exc:
            self.connection=None;self.append_log('Connection failed: '+str(exc)+'\n')
        self.update_connection_controls();self.validate()
    def disconnect_serial(self):
        if self.busy:return
        connection=self.connection;self.connection=None
        if connection is not None:
            try:connection.close()
            except Exception as exc:self.append_log('Disconnect: '+str(exc)+'\n')
            self.append_log('Disconnected.\n')
        self.update_connection_controls();self.validate()
    def poll_serial(self):
        if self.busy or self.connection is None:return
        try:
            if not self.connection.is_open:raise OSError('Serial port is closed.')
            count=self.connection.in_waiting
            if count:self.append_log(self.connection.read(min(count,65536)).decode(errors='replace'))
        except Exception as exc:
            self.append_log('Connection lost: '+str(exc)+'\n');self.disconnect_serial()
    def ensure_driver(self):
        missing=needs_install()
        self.driver_button.setText('Install driver' if missing else 'Driver installed')
        self.driver_button.setEnabled(missing and not self.busy)
    def scan(self):
        previous=self.ports.currentData();self.ports.clear()
        ports=sorted(list_ports.comports(),key=lambda p:(p.vid!=0x10c4,p.device))
        for p in ports:self.ports.addItem(f'{p.device} — {p.description}',p.device)
        index=self.ports.findData(previous)
        if index>=0:self.ports.setCurrentIndex(index)
        self.ensure_driver()
        self.validate()
    def schedule_validate(self):
        for button in (self.bit_button,self.arm_button,self.both_button):button.setEnabled(False)
        self.timer.start(250)
    def validate(self):
        self.images={}
        for kind,card,reader in [('fpga',self.bit,read_bit),('arm',self.elf,read_elf)]:
            value=card.path.text().strip().strip('"')
            if not value:card.info.setText('No file selected');continue
            try:
                if not Path(value).is_file():raise ValueError('File not found.')
                if Path(value).suffix.lower()!=card.extension:raise ValueError(f'Please select a {card.extension} file.')
                image=reader(value);self.images[kind]=image;card.info.setText('✓ '+image.details)
            except Exception as exc:card.info.setText('✕ '+str(exc))
        ready=not self.busy and self.connection is not None and self.connection.is_open
        self.bit_button.setEnabled(ready and 'fpga' in self.images);self.arm_button.setEnabled(ready and 'arm' in self.images);self.both_button.setEnabled(ready and len(self.images)==2)
    def mode_changed(self):
        self.mode_hint.setText('Program FPGA and CPU separately or together.')
        destination='Flash' if self.flash_mode.isChecked() else 'RAM'
        for button,name in [(self.bit_button,'FPGA'),(self.arm_button,'CPU'),(self.both_button,'both')]:
            button.setText('Program '+name)
            button.setToolTip('Program '+name+' to '+destination)
    def drop_paths(self,paths):
        if self.busy:return
        bit=[p for p in paths if Path(p).suffix.lower()=='.bit'];elf=[p for p in paths if Path(p).suffix.lower()=='.elf']
        if len(bit)>1 or len(elf)>1 or len(bit)+len(elf)!=len(paths):
            self.append_log('Drop at most one .bit and one .elf file. Other file types are not supported.\n');return
        if bit:self.bit.path.setText(bit[0])
        if elf:self.elf.path.setText(elf[0])
        self.validate()
    def dragEnterEvent(self,event):
        if not self.busy and event.mimeData().hasUrls() and all(u.isLocalFile() for u in event.mimeData().urls()):event.acceptProposedAction()
    def dropEvent(self,event):self.drop_paths([u.toLocalFile() for u in event.mimeData().urls()]);event.acceptProposedAction()
    def start(self,target):
        if self.busy or target not in ('fpga','arm','both'):return
        self.validate();fpga=self.images.get('fpga') if target in ('fpga','both') else None;arm=self.images.get('arm') if target in ('arm','both') else None
        if (target in ('fpga','both') and fpga is None) or (target in ('arm','both') and arm is None):return
        self.launch(fpga,arm)
    def launch(self,fpga=None,arm=None):
        if self.busy or (fpga is None and arm is None):return
        port=self.ports.currentData()
        if not port or self.connection is None or not self.connection.is_open:self.append_log('Connect the serial port first.\n');return
        self.log.clear();self.busy=True;self.bar.setValue(0)
        for w in [self.bit,self.elf,self.ports,self.refresh,self.flash_mode,self.ram_mode,self.driver_button,self.connect_button,self.disconnect_button]:w.setEnabled(False)
        self.validate();self.worker=Worker(self.connection,'flash' if self.flash_mode.isChecked() else 'ram',fpga,arm);self.worker.text.connect(self.append_log);self.worker.progress.connect(self.on_progress);self.worker.result.connect(self.on_result);self.worker.finished.connect(self.on_finished);self.worker.start()
    def append_log(self,text):
        cursor=self.log.textCursor();cursor.movePosition(cursor.MoveOperation.End);cursor.insertText(text.replace('\r',''));self.log.setTextCursor(cursor);self.log.ensureCursorVisible()
    def on_progress(self,n,text):self.bar.setValue(n);self.append_log(text+'\n')
    def on_result(self,success,message,path):
        self.append_log('\n\n'+('Completed: ' if success else 'Failed: ')+message+('\nLog: '+path if path else '')+'\n')
        if success:self.bar.setValue(100)
    def on_finished(self):
        self.busy=False
        for w in [self.bit,self.elf,self.ports,self.refresh,self.flash_mode,self.ram_mode,self.driver_button,self.connect_button,self.disconnect_button]:w.setEnabled(True)
        self.ensure_driver();self.update_connection_controls()
        self.validate()
    def setup_driver(self):
        if self.busy:return
        if not needs_install():self.ensure_driver();return
        self.busy=True;self.bar.setValue(0);self.log.clear()
        for w in [self.bit,self.elf,self.ports,self.refresh,self.flash_mode,self.ram_mode,self.driver_button,self.connect_button,self.disconnect_button]:w.setEnabled(False)
        self.validate();self.worker=DriverTask(ASSETS/'cp210x/silabser.inf')
        self.worker.text.connect(self.append_log);self.worker.progress.connect(self.on_progress);self.worker.result.connect(self.on_result)
        self.worker.finished.connect(self.on_finished);self.worker.finished.connect(self.scan);self.worker.start()
    def help(self):
        QMessageBox.information(self,'Help',
            '1. Select the MicroZed USB-UART serial port and click Connect.\n'
            '2. Drop a .bit or .elf file, or click Browse.\n'
            '3. Choose Save to Flash or Run from RAM, then select an action.\n\n'
            'The CP210x driver is included and checked at startup. If missing, click Install driver above the serial port. Approve the Windows administrator prompt to install it.\n\n'
            'Flash mode supports the verified factory U-Boot / Linux layout only. '
            'The file area is limited to 576 KiB. Saving one component preserves the other. '
            'Saved programs run on the next boot.\n\n'
            'CPU files must be ARM Cortex-A9 standalone executables. '
            'If an application keeps running, press RST while the loader waits for U-Boot.\n\n'
            'USB-UART does not support breakpoint debugging.')
    def closeEvent(self,event):
        if self.busy:self.append_log('Operation in progress. Wait before closing and keep power connected during Flash writes.\n');event.ignore()
        else:self.disconnect_serial();event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv);app.setApplicationName('MicroZed USB Loader');window=Window();window.show();sys.exit(app.exec())
