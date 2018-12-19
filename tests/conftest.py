import os
import pytest
import logging
import tempfile
import numpy as np
from time import sleep
from pymeasure.experiment import (IntegerParameter, FloatParameter, BooleanParameter,
                                  Parameter, Results)
from pymeasure.display.Qt import QtGui, QtCore
from mkidplotter.gui.procedures import SweepProcedure, TestSweep as TS
from mkidplotter.gui.widgets import SweepPlotWidget, NoisePlotWidget
from mkidplotter.gui.sweep_gui import SweepGUI

log = logging.getLogger()
log.addHandler(logging.NullHandler())


@pytest.fixture
def sweep_procedure_class():
    """Returns a test sweep procedure"""
    # TODO: make mock procedure
    class Sweep(SweepProcedure):
        frequency = FloatParameter("Center Frequency", units="GHz", default=4.0)
        span = FloatParameter("Span", units="MHz", default=2)
        take_noise = BooleanParameter("Take Noise Data", default=True)
        n_points = IntegerParameter("Number of Points", default=500)

        DATA_COLUMNS = ['I1', 'Q1', "bias I1", "bias Q1", 'Amplitude PSD1', 'Phase PSD1',
                        'I2', 'Q2',  "bias I2", "bias Q2", 'Amplitude PSD2', 'Phase PSD2',
                        'frequency']

        def startup(self):
            log.info("Starting procedure")

        def execute(self):
            log.info("Measuring the loop with %d points", self.n_points)
            loop_x = np.zeros(self.n_points)
            loop_y = np.zeros(self.n_points)
            indices = np.arange(self.n_points)
            # sweep frequencies
            for i in indices:
                self.emit('progress', i / self.n_points * 100)
                loop_x[i] = 70 / self.attenuation * np.cos(2 * np.pi * i /
                                                           (self.n_points - 1))
                loop_y[i] = 70 / self.attenuation * np.sin(2 * np.pi * i /
                                                           (self.n_points - 1))
                data = {"I1": loop_x[i],
                        "Q1": loop_y[i],
                        "I2": loop_x[i] * 2,
                        "Q2": loop_y[i]}
                self.emit_results(data)
                log.debug("Emitting results: %s" % data)
                sleep(.0001)
                if self.should_stop():
                    log.warning("Caught the stop flag in the procedure")
                    break

            if self.take_noise:
                # calculate bias point
                bias_i1, bias_q1 = 70 / self.attenuation, 0
                bias_i2, bias_q2 = 0, 70 / self.attenuation

                self.emit_results({"bias I1": bias_i1, "bias Q1": bias_q1})
                self.emit_results({"bias I2": bias_i2, "bias Q2": bias_q2})
                # take noise data
                frequency = np.linspace(1e3, 1e5, 100)
                phase = 1 / frequency
                amplitude = 1 / frequency[-1] * np.ones(frequency.shape)
                data = {"frequency": frequency,
                        "Phase PSD1": phase,
                        "Amplitude PSD1": amplitude,
                        "Phase PSD2": phase / 2,
                        "Amplitude PSD2": amplitude * 2}
                self.emit_results(data)
            else:
                frequency = np.nan
                phase = np.nan
                amplitude = np.nan
                bias_i1 = np.nan
                bias_i2 = np.nan
                bias_q1 = np.nan
                bias_q2 = np.nan

            # save all the data we took
            data = {"I1": loop_x,
                    "Q1": loop_y,
                    "I2": loop_x * 2,
                    "Q2": loop_y,
                    "frequency": frequency,
                    "Phase PSD1": phase,
                    "Amplitude PSD1": amplitude,
                    "Phase PSD2": phase / 2,
                    "Amplitude PSD2": amplitude * 2,
                    "bias I1": bias_i1,
                    "bias Q1": bias_q1,
                    "bias I2": bias_i2,
                    "bias Q2": bias_q2}
            self.save(data)

        def shutdown(self):
            log.info("Finished procedure")

        def save(self, data):
            """Save the output of the procedure"""
            data.update({"parameters": self.parameter_values()})
            file_path = os.path.join(self.directory, self.file_name())
            log.info("Saving data to %s", file_path)
            if os.path.isfile(file_path):
                message = "{} already exists".format(file_path)
                log.error(message)
                return
            else:
                np.savez(file_path, **data)

        def load(self, file_path):
            """Load the procedure output into a pymeasure Results class instance"""
            # load in the data
            npz_file = np.load(file_path)
            parameter_dict = npz_file['parameters'].item()
            # make a procedure object with the right parameters
            procedure = self.__class__()
            for name, value in parameter_dict.items():
                setattr(procedure, name, value)
            procedure.refresh_parameters()  # Enforce update of meta data
            # collect the data into a numpy structured array
            size = max([value.size if hasattr(value, "shape") and value.shape
                        else np.array([value]).size for _, value in npz_file.items()])
            records = np.empty((size,), dtype=[(key, float) for key in npz_file.keys()
                                               if key != "parameters"])
            records.fill(np.nan)
            for key, value in npz_file.items():
                if key != "parameters":
                    try:
                        records[key][:value.size] = value
                    except AttributeError:
                        records[key][:np.array(value).size] = value
            # make a temporary file for the gui data
            file_path = tempfile.mktemp()
            results = Results(procedure, file_path)
            log.info("Loading the file into the temporary file %s", file_path)
            with open(file_path, mode='a') as temporary_file:
                for index in range(size):
                    temporary_file.write(results.format(records[index]))
                    temporary_file.write(os.linesep)
            return results
    return Sweep


@pytest.fixture()
def sweep_gui(sweep_procedure_class, caplog, qtbot):
    # create window
    x_list = (('I1', 'bias I1'), ('frequency', 'frequency'),
              ('I2', 'bias I2'), ('frequency', 'frequency'))
    y_list = (('Q1', 'bias Q1'), ("Amplitude PSD1", "Phase PSD1"),
              ('Q2', 'bias Q2'), ("Amplitude PSD2", "Phase PSD2"))
    x_label = ("I [V]", "frequency [Hz]", "I [V]", "frequency [Hz]")
    y_label = ("Q [V]", "PSD [V² / Hz]", "Q [V]", "PSD [V² / Hz]")
    legend_list = (('sweep', 'bias point'), ('Amplitude Noise', 'Phase Noise'),
                   ('sweep', 'bias point'), ('Amplitude Noise', 'Phase Noise'))
    widgets_list = (SweepPlotWidget, NoisePlotWidget, SweepPlotWidget, NoisePlotWidget)
    names_list = ('Channel 0: Sweep', 'Channel 0: Noise',
                  'Channel 1: Sweep', 'Channel 1: Noise')
    window = SweepGUI(sweep_procedure_class, x_axes=x_list, y_axes=y_list,
                      x_labels=x_label, y_labels=y_label, legend_text=legend_list,
                      plot_widget_classes=widgets_list, plot_names=names_list)
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