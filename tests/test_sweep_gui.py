import pytest
from pymeasure.display.Qt import QtCore, QtGui


@pytest.mark.qt_log_level_fail("WARNING")
def test_init(sweep_gui, qtbot):
    qtbot.waitForWindowShown(sweep_gui)


@pytest.mark.qt_log_level_fail("WARNING")
def test_queue(sweep_gui, qtbot):
    qtbot.waitForWindowShown(sweep_gui)
    with qtbot.waitSignal(sweep_gui.manager.finished, timeout=600, raising=True):
        qtbot.mouseClick(sweep_gui.queue_button, QtCore.Qt.LeftButton)
