import sys
from pymeasure.display.Qt import QtGui
from mkidplotter.examples.pulse_procedure import Pulse
from mkidplotter import PulseGUI, PulsePlotWidget, NoisePlotWidget, get_image_icon


def pulse_window():
    x_list = (('t', 't'), ('frequency', 'frequency'),
              ('t', 't'), ('frequency', 'frequency'))
    y_list = (('phase 1', 'amplitude 1'), ("phase PSD1", "amplitude PSD1"),
              ('phase 2', 'amplitude 2'), ("phase PSD2", "amplitude PSD2"))
    x_label = ("time [µs]", "frequency [Hz]", "time [µs]", "frequency [Hz]")
    y_label = ("signal [V]", "PSD [V² / Hz]", "signal [V]", "PSD [V² / Hz]")
    legend_list = (('Phase', 'Amplitude'), ('Phase Noise', 'Amplitude Noise'),
                   ('Phase', 'Amplitude'), ('Phase Noise', 'Amplitude Noise'))
    widgets_list = (PulsePlotWidget, NoisePlotWidget, PulsePlotWidget, NoisePlotWidget)
    names_list = ('Channel 1: Data', 'Channel 1: Noise',
                  'Channel 2: Data', 'Channel 2: Noise')
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
