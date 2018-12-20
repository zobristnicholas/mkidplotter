import pytest
import logging
import tempfile
import mkidplotter.examples.sweep_gui as gui
import mkidplotter.examples.sweep_procedure as procedure


@pytest.fixture
def sweep_procedure_class():
    """Returns a test sweep procedure"""
    procedure.Sweep.wait_time = 0.0001
    return procedure.Sweep


@pytest.fixture()
def sweep_gui(sweep_procedure_class, caplog, qtbot):
    # create window
    window = gui.sweep_window()
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
