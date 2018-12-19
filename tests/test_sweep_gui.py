import os
import pytest
from pymeasure.display.Qt import QtCore, QtGui

SWEEP_PARAMETERS = ["start_atten", "stop_atten", "n_atten",
                    "start_field", "stop_field", "n_field",
                    "start_temp", "stop_temp", "n_temp"]


@pytest.mark.qt_log_level_fail("WARNING")
def test_init(sweep_gui, qtbot):
    qtbot.waitForWindowShown(sweep_gui)


@pytest.mark.parametrize("start_atten, stop_atten, n_atten, "
                         "start_field, stop_field, n_field, "
                         "start_temp, stop_temp, n_temp",
                         [(80, 100, 2, 0, 4, 2, 100, 200, 2),
                          (90, 90, 1, 2, 2, 1, 300, 300, 1)])
@pytest.mark.qt_log_level_fail("WARNING")
def test_queue(sweep_gui, qtbot, request, start_atten, stop_atten, n_atten,
               start_field, stop_field, n_field, start_temp, stop_temp, n_temp):
    # set the sweep parameters
    for parameter in SWEEP_PARAMETERS:
        parameter_input = getattr(sweep_gui.base_inputs_widget, parameter)
        parameter_input.setValue(locals()[parameter])
    # grab the directory and sweep parameters for the run and cache them
    directory = sweep_gui.base_inputs_widget.directory.value()
    sweep_parameters = sweep_gui.make_procedure().parameter_values()
    request.config.cache.set('directory', directory)
    request.config.cache.set('sweep_parameters', sweep_parameters)
    # start the queue and wait until it's finished
    n_sweep = n_atten * n_field * n_temp
    qtbot.mouseClick(sweep_gui.queue_button, QtCore.Qt.LeftButton)
    for _ in range(n_sweep):
        with qtbot.waitSignal(sweep_gui.manager.finished, timeout=400, raising=True):
            pass
    # check that everything went well
    assert os.path.isdir(directory), "the output directory does not exist"
    files = os.listdir(directory)
    n_files = len(files)
    message = "there should be {} not {} files in the output directory"
    assert len(files) == n_sweep, message.format(n_sweep, n_files)
    assert files[0].split('.')[-1] == "npz", "the output file has the wrong extension"


@pytest.mark.qt_log_level_fail("WARNING")
def test_load(sweep_gui, qtbot, request):
    # grab a previously saved data set and load it
    directory = request.config.cache.get("directory", None)
    saved_parameters = request.config.cache.get("sweep_parameters", None)
    file_name = os.listdir(directory)[0]
    sweep_gui.load_from_file([os.path.join(directory, file_name)])
    # find the corresponding browser item and use those parameters in the gui
    item = sweep_gui.browser.topLevelItem(0)
    assert item is not None, "browser item was not loaded"
    sweep_gui.define_browser_menu(item)
    sweep_gui.action_use.trigger()
    # check that the parameters that we loaded are the same as those that we saved
    loaded_parameters = sweep_gui.make_procedure().parameter_values()
    n_loaded = len(loaded_parameters)
    n_saved = len(saved_parameters)
    message = "loaded {} parameters when there should only be {}"
    assert n_loaded == n_saved, message.format(n_loaded, n_saved)
    for key, value in loaded_parameters.items():
        message = "{} not in the saved parameters"
        assert key in saved_parameters.keys(), message.format(key)
        message = "the saved and loaded values for {} are different"
        assert value == saved_parameters[key], message.format(key)

