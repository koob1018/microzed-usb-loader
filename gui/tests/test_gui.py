from types import SimpleNamespace
import sys
from pathlib import Path
from PySide6.QtCore import QMimeData,QUrl,QPoint,QPointF,Qt
from PySide6.QtGui import QDragEnterEvent,QDropEvent
from PySide6.QtWidgets import QApplication
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import Window

def test_drop_validation_and_busy_guard():
    app=QApplication.instance() or QApplication([])
    root=Path(__file__).resolve().parents[2]
    w=Window(auto_driver=False);w.ports.clear();w.ports.addItem('TEST','FAKE');w.connection=SimpleNamespace(port='FAKE',is_open=True,close=lambda:None)
    w.bit.path.clear();w.elf.path.clear();w.validate()
    assert not w.bit.path.acceptDrops() and not w.elf.path.acceptDrops()
    assert not w.both_button.isEnabled()
    mime=QMimeData();mime.setUrls([QUrl.fromLocalFile(str(root/'build/usb_probe.bit')),QUrl.fromLocalFile(str(root/'build/hello.elf'))])
    enter=QDragEnterEvent(QPoint(10,10),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier)
    app.sendEvent(w,enter);assert enter.isAccepted()
    drop=QDropEvent(QPointF(10,10),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier)
    app.sendEvent(w,drop)
    assert w.both_button.isEnabled() and set(w.images)=={'fpga','arm'}
    old=w.bit.path.text();w.drop_paths(['wrong.txt']);assert w.bit.path.text()==old
    w.busy=True;w.drop_paths(['different.bit']);assert w.bit.path.text()==old
    w.validate();assert not w.both_button.isEnabled()
    w.busy=False;assert w.flash_mode.isChecked() and not w.ram_mode.isChecked()
    assert w.both_button.text()=='Program both'
    w.ram_mode.click();assert w.ram_mode.isChecked() and not w.flash_mode.isChecked()
    assert w.both_button.text()=='Program both'
    w.flash_mode.click();w.flash_mode.click()
    assert w.flash_mode.isChecked() and not w.ram_mode.isChecked()
    assert w.mode_hint.text()=='Program FPGA and CPU separately or together.'
    w.close()
