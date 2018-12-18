import pytest
from pymeasure.display.Qt import QtCore, QtGui


@pytest.mark.qt_log_level_fail("WARNING")
def test_init(sweep_gui, qtbot):
    qtbot.waitForWindowShown(sweep_gui)


@pytest.mark.qt_log_level_fail("WARNING")
def test_queue(sweep_gui, qtbot):
    qtbot.waitForWindowShown(sweep_gui)
    qtbot.mouseClick(sweep_gui.queue_button, QtCore.Qt.LeftButton)