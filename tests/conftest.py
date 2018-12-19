import os
import pytest
import logging
import tempfile
import numpy as np
from time import sleep
from pymeasure.experiment import (IntegerParameter, FloatParameter, BooleanParameter,
                                  Parameter, Results)
from pymeasure.display.Qt import QtGui, QtCore
from mkidplotter.gui.procedures import SweepProcedure
from mkidplotter.gui.widgets import SweepPlotWidget, NoisePlotWidget
from mkidplotter.gui.sweep_gui import SweepGUI
from mkidplotter.examples.sweep_procedure import Sweep
from mkidplotter.examples.sweep_gui import sweep_window

log = logging.getLogger()
log.addHandler(logging.NullHandler())


@pytest.fixture
def sweep_procedure_class():
    """Returns a test sweep procedure"""
    Sweep.wait_time = 0.0001
    return Sweep


@pytest.fixture()
def sweep_gui(sweep_procedure_class, caplog, qtbot):
    # create window
    window = sweep_window()
    window.show()
    # add to qtbot so it gets tracked and deleted properly during teardown
    qtbot.addWidget(window)
    # set a temporary directory for the tests
    file_directory = tempfile.mkdtemp()
    window.base_inputs_widget.directory.line_edit.clear()
    qtbot.keyClicks(window.base_inputs_widget.directory.line_edit, file_directory)
    # return the window
    yield window
    # check for logging errors before teardown
    for when in ("setup", "call"):
        messages = [x.message for x in caplog.get_records(when)
                    if x.levelno > logging.INFO]
        if messages:
            pytest.fail("Failed from logging messages: {}".format(messages))