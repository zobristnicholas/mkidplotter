import os
import sys
import logging
import warnings
import tempfile
import numpy as np
import pyqtgraph as pg
from time import sleep
from cycler import cycler
from datetime import datetime
from pymeasure.experiment import Results
from pymeasure.display.Qt import QtCore, QtGui
from pymeasure.display.widgets import LogWidget
from pymeasure.display.manager import Experiment
from pymeasure.display.browser import BrowserItem
from pymeasure.display.windows import ManagedWindow

from mkidplotter.icons.manage_icons import get_image_icon
from mkidplotter.gui.managers import MKIDManager
from mkidplotter.gui.procedures import TestSweep, SweepBaseProcedure
from mkidplotter.gui.widgets import (SweepPlotWidget, NoisePlotWidget, MKIDInputsWidget,
                                     InputsWidget, MKIDBrowserWidget, MKIDResultsDialog)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class TestSweepGUI(ManagedWindow):
    def __init__(self, procedure_class, x_axes=('I',), y_axes=('Q',),
                 x_labels=('I [V]',), y_labels=('Q [V]',), legend_text=('sweep',),
                 plot_widget_classes=(SweepPlotWidget,), plot_names=("Sweep Plot",)):
        # catch warning for data that hasn't been emitted as anything other than nan
        warnings.filterwarnings("ignore", message="All-NaN slice encountered",
                                category=RuntimeWarning, module="numpy")
        warnings.filterwarnings("ignore", message="All-NaN axis encountered",
                                category=RuntimeWarning, module="numpy")

        self.base_procedure_class = SweepBaseProcedure
        self.base_inputs = self.base_procedure_class().ordering
        self.sweep_inputs = self.base_inputs[1:]
        self.plot_widget_classes = plot_widget_classes
        self.plot_names = plot_names
        self.x_axes = x_axes
        self.y_axes = y_axes
        self.x_labels = x_labels
        self.y_labels = y_labels
        self.legend_text = legend_text
        # matplotlib 2.2.3 default colors
        self.color_cycle = cycler(color=[(31, 119, 180), (255, 127, 14), (44, 160, 44),
                                         (214, 39, 40), (148, 103, 189), (140, 86, 75),
                                         (227, 119, 194), (127, 127, 127), (188, 189, 34),
                                         (23, 190, 207)])

        # get an ordered list of the procedure class names
        parameters = list(procedure_class().parameter_names)
        # grab the GUI name from the procedure class and check to make sure all required
        # parameters are defined
        for inputs in self.sweep_inputs:
            not_set = True
            for parameter in parameters:
                if parameter == inputs[0]:
                    inputs.append(procedure_class().parameter_objects()[parameter].name)
                    not_set = False
            if not_set:
                message = "Procedure class needs to have the {} parameter"
                raise ValueError(message.format(inputs[0]))

        # grab a list of just the base_input variable names
        base_inputs = [inputs if isinstance(inputs, str) else inputs[0]
                       for inputs in self.base_inputs]
        # create a list of all the non-required parameters
        inputs = []
        for parameter in parameters:
            if parameter not in base_inputs:
                inputs.append(parameter)
        super().__init__(procedure_class=procedure_class, inputs=inputs,
                         displays=base_inputs + inputs,
                         x_axis=x_axes[0][0], y_axis=y_axes[0][0])
        self.setWindowTitle('Test Sweep GUI')
        self._abort_all = False
        self._abort_state = "abort"
        self.setWindowIcon(get_image_icon("loop.png"))

    def _setup_ui(self):
        self.log_widget = LogWidget()
        self.log.addHandler(self.log_widget.handler)  # needs to be in Qt context?
        log.info("ManagedWindow connected to logging")

        self.queue_button = QtGui.QPushButton('Queue', self)
        self.queue_button.clicked.connect(self.queue)

        self.abort_button = QtGui.QPushButton('Abort', self)
        self.abort_button.setEnabled(False)
        self.abort_button.clicked.connect(self.abort)

        self.abort_all_button = QtGui.QPushButton('Abort All', self)
        self.abort_all_button.setEnabled(False)
        self.abort_all_button.clicked.connect(self.abort_all)

        self.plot_widget = []
        self.plot = []
        for index, plot_widget in enumerate(self.plot_widget_classes):
            self.plot_widget.append(plot_widget(self.procedure_class.DATA_COLUMNS,
                                                x_axes=self.x_axes[index],
                                                y_axes=self.y_axes[index],
                                                x_label=self.x_labels[index],
                                                y_label=self.y_labels[index],
                                                legend_text=self.legend_text[index],
                                                color_cycle=self.color_cycle))
            self.plot.append(self.plot_widget[-1].plot)

        measured_quantities = [item for x_axis in self.x_axes for item in x_axis]
        measured_quantities.extend([item for y_axis in self.x_axes for item in y_axis])
        self.browser_widget = MKIDBrowserWidget(self.procedure_class, self.displays,
                                                measured_quantities, parent=self)
        self.browser_widget.show_button.clicked.connect(self.show_experiments)
        self.browser_widget.hide_button.clicked.connect(self.hide_experiments)
        self.browser_widget.clear_button.clicked.connect(self.clear_experiments)
        self.browser_widget.open_button.clicked.connect(self.open_experiment)
        self.browser = self.browser_widget.browser

        self.browser.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.browser.customContextMenuRequested.connect(self.browser_item_menu)
        self.browser.itemChanged.connect(self.browser_item_changed)

        self.inputs = InputsWidget(self.procedure_class, self.inputs,
                                   parent=self)
        self.base_inputs_widget = MKIDInputsWidget(self.base_procedure_class,
                                                   self.base_inputs, parent=self)

        self.manager = MKIDManager(self.plot, self.browser,
                                   log_level=self.log_level, parent=self)
        self.manager.abort_returned.connect(self.abort_returned)
        self.manager.queued.connect(self.queued)
        self.manager.running.connect(self.running)
        self.manager.finished.connect(self.finished)
        self.manager.log.connect(self.log.handle)

    def _layout(self):
        self.main = QtGui.QWidget(self)

        inputs_dock = QtGui.QWidget(self)
        base_dock = QtGui.QWidget(self)
        inputs_vbox = QtGui.QVBoxLayout()
        base_inputs_vbox = QtGui.QVBoxLayout()

        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(-1, 6, -1, 6)
        hbox.addStretch()
        hbox.addWidget(self.queue_button)
        hbox.addStretch()
        hbox.addWidget(self.abort_button)
        hbox.addStretch()
        hbox.addWidget(self.abort_all_button)
        hbox.addStretch()

        base_inputs_vbox.addWidget(self.base_inputs_widget)
        base_inputs_vbox.addLayout(hbox)
        base_inputs_vbox.addStretch()
        base_dock.setLayout(base_inputs_vbox)

        base_inputs_dock = QtGui.QDockWidget('Sweeps')
        base_inputs_dock.setWidget(base_dock)
        features = base_inputs_dock.features()
        base_inputs_dock.setFeatures(features & ~QtGui.QDockWidget.DockWidgetClosable)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, base_inputs_dock)

        inputs_vbox.addWidget(self.inputs)
        inputs_vbox.addStretch()
        inputs_dock.setLayout(inputs_vbox)

        dock = QtGui.QDockWidget('Additional Parameters')
        dock.setWidget(inputs_dock)
        features = base_inputs_dock.features()
        dock.setFeatures(features & ~QtGui.QDockWidget.DockWidgetClosable)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        tabs = QtGui.QTabWidget(self.main)
        for index, plot_widget in enumerate(self.plot_widget):
            tabs.addTab(plot_widget, self.plot_names[index])
        tabs.addTab(self.log_widget, "Experiment Log")
        self.plot_widget[0].setMinimumSize(100, 200)

        browser_dock = QtGui.QWidget(self)

        browser_vbox = QtGui.QVBoxLayout()
        browser_vbox.addWidget(self.browser_widget)
        browser_dock.setLayout(browser_vbox)

        browser_dock_widget = QtGui.QDockWidget('Browser')
        browser_dock_widget.setWidget(browser_dock)
        features = browser_dock_widget.features()
        browser_dock_widget.setFeatures(features & ~QtGui.QDockWidget.DockWidgetClosable)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, browser_dock_widget)

        vbox = QtGui.QVBoxLayout(self.main)
        vbox.setSpacing(0)
        vbox.addWidget(tabs)

        self.main.setLayout(vbox)
        self.setCentralWidget(self.main)
        self.main.show()
        self.resize(1200, 800)

    def setup_plot(self, plots):
        pass

    def browser_item_changed(self, item, column):
        if column == 0:
            state = item.checkState(0)
            experiment = self.manager.experiments.with_browser_item(item)
            if state == 0:
                for index, plot in enumerate(self.plot):
                    for curve in experiment.curve[index]:
                        plot.removeItem(curve)
            else:
                for index, _ in enumerate(self.plot):
                    for _, curve in enumerate(experiment.curve[index]):
                        curve.update()
                        # ignoreBounds helps remove problem with resetting color
                        # then hiding/showing the plot
                        # not ideal because it breaks auto-ranging
                        self.plot[index].addItem(curve, ignoreBounds=True)

    def new_curve(self, results, **kwargs):
        curve = [plot_widget.new_curve(results, **kwargs)
                 for index, plot_widget in enumerate(self.plot_widget)]
        return curve

    def new_experiment(self, results, curve=None):
        if curve is None:
            curve = self.new_curve(results)
        browser_item = BrowserItem(results, curve[0][0])
        experiment = Experiment(results, curve, browser_item)

        return experiment

    def change_color(self, experiment):
        color = QtGui.QColorDialog.getColor(
            initial=experiment.curve[0][0].opts['symbolBrush'].color(), parent=self)
        if color.isValid():
            pixelmap = QtGui.QPixmap(24, 24)
            pixelmap.fill(color)
            # setIcon breaks auto-ranging when hiding/showing the plot
            # see comment in self.browser_item_changed()
            experiment.browser_item.setIcon(0, QtGui.QIcon(pixelmap))
            for index, _ in enumerate(self.plot):
                for _, curve in enumerate(experiment.curve[index]):
                    curve.pen.setColor(color)
                    curve.symbolBrush.setColor(color)
                    curve.update()

    def queue(self):
        sweep_procedure = self.base_inputs_widget.get_procedure()
        sweep_dict = sweep_procedure.parameter_values()
        sweeps = []
        for _, start, stop, n_points, _ in self.sweep_inputs:
            sweeps.append(np.linspace(sweep_dict[start], sweep_dict[stop],
                                      sweep_dict[n_points]))
        # so that meshgrid gets the orders based on input order
        sweeps[0], sweeps[1] = sweeps[1], sweeps[0]
        sweep_grid = np.meshgrid(*sweeps)
        # swap order back so that we can index correctly
        sweep_grid[0], sweep_grid[1] = sweep_grid[1], sweep_grid[0]
        # transpose to enumerate backwards through the list
        sweep_grid = [grid.T for grid in sweep_grid]
        start_time = datetime.now()
        files = []
        for index, _ in np.ndenumerate(sweep_grid[0]):
            procedure = self.make_procedure()
            parameter_values = procedure.parameter_values()
            for item, (parameter, _, _, _, _) in enumerate(self.sweep_inputs):
                value = sweep_grid[item][index]
                parameter_values.update({parameter: value})
            parameter_values.update(
                {self.base_inputs[0]: sweep_dict[self.base_inputs[0]]})
            procedure.set_parameters(parameter_values)
            try:
                file_path = tempfile.mktemp()
                results = Results(procedure, file_path)
                experiment = self.new_experiment(results)
                # change the file name to the real file name if it has one
                file_name = procedure.file_name(start_time)
                experiment.browser_item.setText(1, file_name)
                file_path = os.path.join(results.procedure.directory, file_name)
                if file_path in files:
                    message = "'{}' is already in the queue, skipping"
                    log.error(message.format(file_path))
                else:
                    files.append(os.path.join(results.procedure.directory, file_name))
                self.manager.queue(experiment)
            except Exception:
                log.error('Failed to queue experiment', exc_info=True)

    def resume(self):
        if self.manager.experiments.has_next():
            self.abort_button.setText("Abort")
            self.abort_button.clicked.disconnect()
            self.abort_button.clicked.connect(self.abort)
            self._abort_state = "abort"
            self.manager.resume()
            self.abort_all_button.setEnabled(True)

    def queued(self, experiment):
        if not self._abort_all and self._abort_state == "abort":
            self.abort_all_button.setEnabled(True)
        self.abort_button.setEnabled(True)
        self.browser_widget.show_button.setEnabled(True)
        self.browser_widget.hide_button.setEnabled(True)
        self.browser_widget.clear_button.setEnabled(True)

    def abort(self):
        self.abort_all_button.setEnabled(False)
        self.abort_button.setEnabled(False)
        self.abort_button.setText("Resume")
        self.abort_button.clicked.disconnect()
        self.abort_button.clicked.connect(self.resume)
        self._abort_state = "resume"
        try:
            self.manager.abort()
        except Exception:
            log.error('Failed to abort experiment', exc_info=True)
            self.abort_button.setText("Abort")
            self.abort_button.clicked.disconnect()
            self.abort_button.clicked.connect(self.abort)
            self._abort_state = "abort"

    def abort_returned(self, experiment):
        if self.manager.experiments.has_next():
            self.abort_button.setText("Resume")
            self.abort_button.setEnabled(True)
        else:
            self.browser_widget.clear_button.setEnabled(True)

        if self._abort_all and self.manager.experiments.has_next():
            self.resume()
            self.abort()
        else:
            self._abort_all = False

    def abort_all(self):
        self._abort_all = True
        self.abort()

    def finished(self, experiment):
        if not self.manager.experiments.has_next():
            self.abort_button.setEnabled(False)
            self.abort_all_button.setEnabled(False)
            self.browser_widget.clear_button.setEnabled(True)
        else:
            # hide the experiment if there is another one starting
            # keeps the graph uncluttered
            experiment.browser_item.setCheckState(0, QtCore.Qt.Unchecked)

    def browser_item_menu(self, position):
        item = self.browser.itemAt(position)

        if item is not None:
            experiment = self.manager.experiments.with_browser_item(item)
            menu = QtGui.QMenu(self)

            # Open
            action_open = QtGui.QAction(menu)
            action_open.setText("Open Data Externally")
            action_open.triggered.connect(
                lambda: self.open_file_externally(experiment.results.data_filename))
            menu.addAction(action_open)

            # Change Color
            action_change_color = QtGui.QAction(menu)
            action_change_color.setText("Change Color")
            action_change_color.triggered.connect(
                lambda: self.change_color(experiment))
            menu.addAction(action_change_color)

            # Remove
            action_remove = QtGui.QAction(menu)
            action_remove.setText("Remove Graph")
            if self.manager.is_running():
                if self.manager.running_experiment() == experiment:  # Experiment running
                    action_remove.setEnabled(False)
            action_remove.triggered.connect(lambda: self.remove_experiment(experiment))
            menu.addAction(action_remove)

            # Use parameters
            def set_parameters(chosen_experiment):
                sweep_parameters = self.base_procedure_class().parameter_objects()
                parameters = chosen_experiment.procedure.parameter_objects()
                for input_list in self.sweep_inputs:
                    sweep_parameters[input_list[1]] = parameters[input_list[0]]
                    sweep_parameters[input_list[2]] = parameters[input_list[0]]
                    sweep_parameters[input_list[3]] = sweep_parameters[input_list[3]]
                self.inputs.set_parameters(parameters)
                self.base_inputs_widget.set_parameters(sweep_parameters)
            action_use = QtGui.QAction(menu)
            action_use.setText("Use These Parameters")
            action_use.triggered.connect(lambda: set_parameters(experiment))
            menu.addAction(action_use)
            menu.exec_(self.browser.viewport().mapToGlobal(position))

    def open_experiment(self):
        dialog = MKIDResultsDialog(self.procedure_class.DATA_COLUMNS,
                                   procedure_class=self.procedure_class,
                                   x_axes=self.x_axes,
                                   y_axes=self.y_axes, legend_text=self.legend_text,
                                   plot_widget_classes=self.plot_widget_classes,
                                   plot_names=self.plot_names,
                                   color_cycle=self.color_cycle)
        if dialog.exec_():
            file_names = dialog.selectedFiles()
            for file_name in map(str, file_names):
                if file_name in self.manager.experiments:
                    message = "The file %s cannot be opened twice."
                    QtGui.QMessageBox.warning(self, "Load Error",
                                              message % os.path.basename(file_name))
                elif file_name == '':
                    return
                else:
                    try:
                        results = self.procedure_class().load(file_name)
                    except Exception:
                        results = Results.load(file_name)
                    results.procedure.status = SweepBaseProcedure.FINISHED
                    experiment = self.new_experiment(results)
                    for index, _ in enumerate(self.plot):
                        for _, curve in enumerate(experiment.curve[index]):
                            curve.update()
                    experiment.browser_item.setText(1, os.path.basename(file_name))
                    experiment.browser_item.progressbar.setValue(100.)
                    self.manager.load(experiment)
                    log.info('Opened data file %s' % file_name)


if __name__ == "__main__":
    x_list = (('I', 'bias I'), ('frequency', 'frequency'))
    y_list = (('Q', 'bias Q'), ("Amplitude PSD", "Phase PSD"))
    x_label = ("I [V]", "frequency [Hz]")
    y_label = ("Q [V]", "PSD [V² / Hz]")
    legend_list = (('sweep', 'bias point'), ('Amplitude Noise', 'Phase Noise'))
    widgets_list = (SweepPlotWidget, NoisePlotWidget)
    names_list = ('Sweep Plot', 'Noise Plot')
    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(get_image_icon("loop.png"))
    window = TestSweepGUI(TestSweep, x_axes=x_list, y_axes=y_list, x_labels=x_label,
                          y_labels=y_label, legend_text=legend_list,
                          plot_widget_classes=widgets_list, plot_names=names_list)
    window.show()
    ex = app.exec_()
    del app  # prevents unwanted segfault on closing the window
    sys.exit(ex)
