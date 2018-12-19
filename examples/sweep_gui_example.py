import sys
from pymeasure.display.Qt import QtGui
from mkidplotter import SweepGUI, SweepPlotWidget, NoisePlotWidget, get_image_icon
from sweep_procedure_example import Sweep


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
app = QtGui.QApplication(sys.argv)
app.setWindowIcon(get_image_icon("loop.png"))
window = SweepGUI(Sweep, x_axes=x_list, y_axes=y_list, x_labels=x_label,
                  y_labels=y_label, legend_text=legend_list,
                  plot_widget_classes=widgets_list, plot_names=names_list)
window.show()
ex = app.exec_()
del app  # prevents unwanted segfault on closing the window
sys.exit(ex)
