from types import SimpleNamespace
from PySide6.QtWidgets import QApplication
import app as gui
from backend import Board

class Port:
    def __init__(self,*args,**kwargs):self.port=args[0];self.is_open=True;self.in_waiting=0
    def read(self,n):return b''
    def close(self):self.is_open=False

def test_connect_disconnect_and_busy(monkeypatch):
    qt=QApplication.instance() or QApplication([])
    monkeypatch.setattr(gui.serial,'Serial',Port)
    w=gui.Window(auto_driver=False);w.ports.clear();w.ports.addItem('Test','TEST')
    w.connect_serial();port=w.connection
    assert port.is_open and not w.ports.isEnabled() and w.disconnect_button.isEnabled()
    with Board(port,'.') as board:assert board.s is port
    assert port.is_open
    w.busy=True;w.disconnect_serial();assert w.connection is port
    w.busy=False;w.disconnect_serial()
    assert not port.is_open and w.connection is None and w.connect_button.isEnabled()
    w.connect_serial();assert w.connection.is_open
    w.connection.close();w.poll_serial();assert w.connection is None
    w.close()

def test_connection_failure_and_idle_read(monkeypatch):
    qt=QApplication.instance() or QApplication([])
    def fail(*a,**kw):raise OSError('Port in use')
    monkeypatch.setattr(gui.serial,'Serial',fail)
    w=gui.Window(auto_driver=False);w.ports.clear();w.ports.addItem('Test','TEST');w.connect_serial()
    assert w.connection is None and 'Port in use' in w.log.toPlainText()
    w.connection=Port('TEST');w.connection.in_waiting=4;w.connection.read=lambda n:b'test'
    w.poll_serial();assert w.log.toPlainText().endswith('test')
    w.close();assert w.connection is None


def test_serial_actions_do_not_select_file_paths(monkeypatch):
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    qt=QApplication.instance() or QApplication([])
    monkeypatch.setattr(gui.serial,'Serial',Port)
    w=gui.Window(auto_driver=False);w.ports.clear();w.ports.addItem('Test','TEST')
    w.bit.path.setText('example.bit');w.elf.path.setText('example.elf')
    w.show();w.activateWindow();qt.processEvents()
    w.connect_button.setFocus();w.bit.path.deselect();w.elf.path.deselect()
    for keyboard in (False,True):
        for _ in range(5):
            for button,next_button in ((w.connect_button,w.disconnect_button),(w.disconnect_button,w.connect_button)):
                if keyboard:
                    button.setFocus();QTest.keyClick(button,Qt.Key_Space)
                else:QTest.mouseClick(button,Qt.LeftButton)
                qt.processEvents()
                assert QApplication.focusWidget() is next_button
                assert not w.bit.path.hasSelectedText() and not w.elf.path.hasSelectedText()
                assert w.bit.path.text()=='example.bit' and w.elf.path.text()=='example.elf'
    w.close()


def test_file_paths_are_not_restored():
    qt=QApplication.instance() or QApplication([])
    w=gui.Window(auto_driver=False)
    assert w.bit.path.text()=='' and w.elf.path.text()==''
    w.bit.path.setText('private/example.bit');w.elf.path.setText('private/example.elf')
    w.close()
    fresh=gui.Window(auto_driver=False)
    assert fresh.bit.path.text()=='' and fresh.elf.path.text()==''
    fresh.close()
