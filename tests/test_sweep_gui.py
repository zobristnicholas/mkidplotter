import os
import pytest
import numpy as np
from pathlib import Path
from pymeasure.display.Qt import QtCore, QtGui

SWEEP_PARAMETERS = ["start_atten", "stop_atten", "n_atten",
                    "start_field", "stop_field", "n_field",
                    "start_temp", "stop_temp", "n_temp",
                    "frequencies1", "spans1", "frequencies2", "spans2"]

PROCEDURE_PARAMETERS = ["noise", "n_points"]


@pytest.mark.qt_log_level_fail("WARNING")
def test_init(sweep_gui, qtbot):
    qtbot.waitForWindowShown(sweep_gui)


@pytest.mark.parametrize("start_atten, stop_atten, n_atten, "
                         "start_field, stop_field, n_field, "
                         "start_temp, stop_temp, n_temp, "
                         "frequencies1, spans1, frequencies2, spans2,"
                         "noise, n_points",
                         [(80, 100, 2,
                           0, 4, 2,
                           100, 200, 2,
                           [5.0, 6], 3.0, 7.0, 2.0,
                           [1, 1, 10, 1, -1, 10], 20),
                          (90, 90, 1,
                           2, 2, 1,
                           300, 300, 1,
                           5.0, 2.0, 4.0, 3.0,
                           [0, 1, 10, 1, -1, 10], 100)])
@pytest.mark.qt_log_level_fail("WARNING")
def test_queue(sweep_gui, qtbot, request, start_atten, stop_atten, n_atten,
               start_field, stop_field, n_field, start_temp, stop_temp, n_temp,
               frequencies1, spans1, frequencies2, spans2, noise, n_points):
    # set the sweep parameters
    for parameter in SWEEP_PARAMETERS:
        parameter_input = getattr(sweep_gui.base_inputs_widget, parameter)
        parameter_input.setValue(locals()[parameter])
    for parameter in PROCEDURE_PARAMETERS:
        parameter_input = getattr(sweep_gui.inputs, parameter)
        parameter_input.setValue(locals()[parameter])
    # grab the directory and sweep parameters for the run and cache them
    directory = sweep_gui.base_inputs_widget.directory.value()
    saved_parameters = sweep_gui.make_procedure().parameter_values()
    saved_sweep = sweep_gui.base_inputs_widget.get_procedure().parameter_values()
    request.config.cache.set('directory', directory)
    request.config.cache.set('saved_parameters', saved_parameters)
    request.config.cache.set('saved_sweep', saved_sweep)
    # start the queue and wait until it's finished
    n_freq = np.max([np.array(frequencies1).size, np.array(frequencies2).size])
    n_sweep = n_atten * n_field * n_temp * n_freq
    qtbot.mouseClick(sweep_gui.queue_button, QtCore.Qt.LeftButton)
    for _ in range(n_sweep):
        with qtbot.waitSignal(sweep_gui.manager.finished, timeout=1000, raising=True):
            pass
    # check that everything went well
    assert os.path.isdir(directory), "the output directory does not exist"
    files = os.listdir(directory)
    n_files = len(files)
    message = "there should be {} not {} files in the output directory"
    assert len(files) == n_sweep + 1, message.format(n_sweep, n_files)
    shown_names = []
    for experiment in sweep_gui.manager.experiments.queue:
        shown_names.append(experiment.browser_item.text(1))
    for file_ in files:
        assert file_ in shown_names or file_[:6] == 'config', \
            "{} not in {}".format(file_, shown_names)
    for file_ in shown_names:
        assert file_ in files, "{} not in {}".format(file_, files)
    assert files[0].split('.')[-1] == "npz", "the output file has the wrong extension"


@pytest.mark.qt_log_level_fail("WARNING")
def test_color_change(sweep_gui, qtbot):
    n_atten = sweep_gui.base_inputs_widget.n_atten.value()
    n_field = sweep_gui.base_inputs_widget.n_field.value()
    n_temp = sweep_gui.base_inputs_widget.n_temp.value()
    frequencies1 = sweep_gui.base_inputs_widget.frequencies1.value()
    frequencies2 = sweep_gui.base_inputs_widget.frequencies2.value()
    n_freq = np.max([np.array(frequencies1).size, np.array(frequencies2).size])
    n_sweep = n_atten * n_field * n_temp * n_freq
    qtbot.mouseClick(sweep_gui.queue_button, QtCore.Qt.LeftButton)
    for _ in range(n_sweep):
        with qtbot.waitSignal(sweep_gui.manager.finished, timeout=1000, raising=True):
            pass
    item = sweep_gui.browser.topLevelItem(0)
    experiment = sweep_gui.manager.experiments.with_browser_item(item)
    color = QtGui.QColor(255, 0, 0)
    sweep_gui.update_color(experiment, color)


@pytest.mark.qt_log_level_fail("WARNING")
def test_load_and_run(sweep_gui, qtbot, request):
    # grab a previously saved data set and load it
    saved_directory = request.config.cache.get("directory", None)
    saved_parameters = request.config.cache.get("saved_parameters", None)
    saved_sweep = request.config.cache.get("saved_sweep", None)
    file_name = os.listdir(saved_directory)[0]
    sweep_gui.load_from_file([os.path.join(saved_directory, file_name)])
    # find the corresponding browser item and use those parameters in the gui
    item = sweep_gui.browser.topLevelItem(0)
    assert item is not None, "browser item was not loaded"
    menu_dict = sweep_gui.define_browser_menu(item)
    menu_dict["use"].trigger()
    # check that the parameters that we loaded are the same as those that we saved
    loaded_parameters = sweep_gui.make_procedure().parameter_values()
    loaded_sweep = sweep_gui.base_inputs_widget.get_procedure().parameter_values()
    n_loaded = len(loaded_parameters)
    n_saved = len(saved_parameters)
    message = "loaded {} parameters when there should only be {}"
    assert n_loaded == n_saved, message.format(n_loaded, n_saved)
    for key, value in loaded_parameters.items():
        message = "{} not in the saved parameters"
        assert key in saved_parameters.keys(), message.format(key)
        message = "the saved and loaded values for {} are different"
        assert value == saved_parameters[key], message.format(key)
    for key, value in loaded_sweep.items():
        message = "{} not in the saved parameters"
        assert key in saved_sweep.keys(), message.format(key)
        message = "the saved and loaded values for {} are different"
        assert value == saved_sweep[key], message.format(key)
    # run the loaded file
    with qtbot.waitSignal(sweep_gui.manager.finished, timeout=1000, raising=True):
        qtbot.mouseClick(sweep_gui.queue_button, QtCore.Qt.LeftButton)
    # TODO: understand why this test breaks any that come after it

# #TODO: test load configuration
# def test_load_config(sweep_gui, qtbot):
#     saved_directory = request.config.cache.get("directory", None)
#     saved_directory = Path(saved_directory)
#     config_file = saved_directory.glob("config_sweep*.npy")[0]


