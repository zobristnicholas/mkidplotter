import sys
from pymeasure.display.Qt import QtGui
from mkidplotter.examples.pulse_procedure import Pulse
from mkidplotter import (PulseGUI, PulsePlotWidget, NoisePlotWidget, HistogramPlotWidget, ScatterPlotWidget,
                         get_image_icon)


def pulse_window():
    x_list = (('t', 't'), ('frequency', 'frequency'), ('hist x',),
              ('t', 't'), ('frequency', 'frequency'), ('peaks 1',))
    y_list = (('phase 1', 'amplitude 1'), ("phase PSD1", "amplitude PSD1"), ('hist y',),
              ('phase 2', 'amplitude 2'), ("phase PSD2", "amplitude PSD2"), ('peaks 2',))
    x_label = ("time [µs]", "frequency [Hz]", "Amplitudes", "time [µs]", "frequency [Hz]", "Channel 1 Amplitudes")
    y_label = ("signal [V]", "PSD [V² / Hz]", "probability density", "signal [V]", "PSD [V² / Hz]",
               "Channel 2 Amplitudes")
    legend_list = (('phase', 'amplitude'), ('phase Noise', 'amplitude Noise'), None,
                   ('phase', 'amplitude'), ('phase Noise', 'amplitude Noise'), None)
    widgets_list = (PulsePlotWidget, NoisePlotWidget, HistogramPlotWidget, PulsePlotWidget, NoisePlotWidget,
                    ScatterPlotWidget)
    names_list = ('Channel 1: Data', 'Channel 1: Noise', 'Channel1: Amplitudes',
                  'Channel 2: Data', 'Channel 2: Noise', 'Amplitudes')
    w = PulseGUI(Pulse, x_axes=x_list, y_axes=y_list, x_labels=x_label, y_labels=y_label,
                 legend_text=legend_list, plot_widget_classes=widgets_list,
                 plot_names=names_list, log_level="DEBUG")
    return w


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    # app.setWindowIcon(get_image_icon("pulse.png"))
    window = pulse_window()
    window.show()
    ex = app.exec_()
    del app  # prevents unwanted segfault on closing the window
    sys.exit(ex)
