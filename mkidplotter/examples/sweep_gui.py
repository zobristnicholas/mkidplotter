import sys
from pymeasure.display.Qt import QtGui
from mkidplotter.examples.sweep_procedure import Sweep
from mkidplotter import (SweepGUI, SweepGUIProcedure2, SweepPlotWidget, NoisePlotWidget, TimePlotIndicator,
                         get_image_icon)


import numpy as np
from datetime import datetime
from collections import deque
from threading import Thread, Event

from mkidplotter.examples import pulse_gui

time_stamps = deque(maxlen=int(24 * 60))
temperatures = deque(maxlen=int(24 * 60))


class Updater(Thread):
    def __init__(self):
        Thread.__init__(self, daemon=True)  # stop process on program exit
        self.finished = Event()
        self.start()

    def cancel(self):
        self.finished.set()

    def run(self):
        while not self.finished.wait(5):
            self.update()

    @staticmethod
    def update():
        time_stamps.append(datetime.now().timestamp())
        temperatures.append(np.random.rand())


def open_pulse_gui(self, experiment):
    # Only make pulse gui if it hasn't been opened or was closed
    if self.pulse_window is None or not self.pulse_window.isVisible():
        self.pulse_window = pulse_gui.pulse_window()
        # make sure pulse window can see sweep window for properly closing daq
        self.pulse_window.sweep_window = self
    # set pulse window inputs to the current experiment values
    sweep_parameters = experiment.procedure.parameter_objects()
    pulse_parameters = self.pulse_window.make_procedure().parameter_objects()
    for key, value in sweep_parameters.items():
        if key in pulse_parameters.keys():
            pulse_parameters[key] = sweep_parameters[key]
    self.pulse_window.inputs.set_parameters(pulse_parameters)
    # show the window
    self.pulse_window.activateWindow()
    self.pulse_window.show()


def sweep_window():
    x_list = (('I1', 'bias I1'), ('frequency', 'frequency'),
              ('I2', 'bias I2'), ('frequency', 'frequency'))
    y_list = (('Q1', 'bias Q1'), ("Amplitude PSD1", "Phase PSD1"),
              ('Q2', 'bias Q2'), ("Amplitude PSD2", "Phase PSD2"))
    x_label = ("I [V]", "frequency [Hz]", "I [V]", "frequency [Hz]")
    y_label = ("Q [V]", "PSD [V² / Hz]", "Q [V]", "PSD [V² / Hz]")
    legend_list = (('sweep', 'bias point'), ('Amplitude Noise', 'Phase Noise'),
                   ('sweep', 'bias point'), ('Amplitude Noise', 'Phase Noise'))
    widgets_list = (SweepPlotWidget, NoisePlotWidget, SweepPlotWidget, NoisePlotWidget)
    Updater()
    indicators = TimePlotIndicator(time_stamps, temperatures, title='Device Temperature [mK]')
    names_list = ('Channel 1: Sweep', 'Channel 1: Noise',
                  'Channel 2: Sweep', 'Channel 2: Noise')

    SweepGUI.open_pulse_gui = open_pulse_gui
    w = SweepGUI(Sweep, base_procedure_class=SweepGUIProcedure2, x_axes=x_list,
                 y_axes=y_list, x_labels=x_label, y_labels=y_label,
                 legend_text=legend_list, plot_widget_classes=widgets_list,
                 plot_names=names_list, persistent_indicators=indicators, log_level="DEBUG")
    return w


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(get_image_icon("loop.png"))
    window = sweep_window()
    window.show()
    ex = app.exec_()
    del app  # prevents unwanted segfault on closing the window
    sys.exit(ex)
