# Widget logic tests use Qt offscreen; native Windows layout is checked separately.
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

# Keep one QApplication alive for the entire suite, including tests without qt fixture.
from PySide6.QtWidgets import QApplication
_test_application=QApplication.instance() or QApplication([])


def pytest_sessionfinish(session,exitstatus):
    import gc,shiboken6
    from PySide6.QtCore import QCoreApplication,QEvent,QTimer
    for widget in list(_test_application.topLevelWidgets()):
        if hasattr(widget,'busy'):widget.busy=False
        for timer in widget.findChildren(QTimer):timer.stop()
        widget.close();widget.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
    _test_application.processEvents();gc.collect()
    shiboken6.delete(_test_application)
