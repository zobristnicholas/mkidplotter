import os
import copy
import logging
import tempfile
import numpy as np
from cycler import cycler
from datetime import datetime
from contextlib import contextmanager
import pymeasure.display.windows as w
from pymeasure.display.Qt import QtCore, QtGui
from pymeasure.display.widgets import LogWidget
from pymeasure.display.manager import Experiment

from mkidplotter.gui.results import Results
from mkidplotter.gui.managers import Manager
from mkidplotter.gui.browser import BrowserItem
from mkidplotter.gui.procedures import SweepGUIProcedure1
from mkidplotter.icons.manage_icons import get_image_icon
from mkidplotter.gui.widgets import (SweepPlotWidget, SweepInputsWidget, InputsWidget,
                                     BrowserWidget, ResultsDialog, IndicatorsWidget)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


@contextmanager
def wait_signal(signal, timeout=10000):
    """Block loop until signal emitted, or timeout (ms) elapses."""
    loop = QtCore.QEventLoop()
    signal.connect(loop.quit)

    yield

    if timeout is not None:
        QtCore.QTimer.singleShot(timeout, loop.quit)
    loop.exec_()


def load(file_name, **kwargs):
    try:
        npz_file = np.load(file_name, **kwargs)
    except TypeError:
        kwargs.pop("allow_pickle", None)
        npz_file = np.load(file_name, **kwargs)  # fallback for old numpy that doesn't have allow_pickle
    return npz_file


# TODO: fix memory leak
class ManagedWindow(w.ManagedWindow):
    def __init__(self, procedure_class, inputs=(), x_axes=(), y_axes=(), x_labels=(), y_labels=(), legend_text=(),
                 plot_widget_classes=(), plot_names=(), persistent_indicators=(), **kwargs):
        if not inputs:
            inputs = tuple(procedure_class().parameter_names)

        self.closing = False  # closeEvent() called twice on Mac
        self._abort_state = "abort"
        self._abort_all = False
        self.plot_widget_classes = plot_widget_classes
        self.plot_names = plot_names
        self.x_axes = x_axes
        self.y_axes = y_axes
        self.x_labels = x_labels
        self.y_labels = y_labels
        self.legend_text = legend_text
        if isinstance(persistent_indicators, (tuple, list)):
            self.persistent_indicators = persistent_indicators
        else:
            self.persistent_indicators = [persistent_indicators]

        # matplotlib 2.2.3 default colors
        self.color_cycle = cycler(color=[(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40),
                                         (148, 103, 189), (140, 86, 75), (227, 119, 194), (127, 127, 127),
                                         (188, 189, 34), (23, 190, 207)])
        displays = kwargs.pop('displays', None)
        if displays is None:
            displays = inputs
        super().__init__(procedure_class, displays=displays, inputs=inputs, x_axis=x_axes[0][0], y_axis=y_axes[0][0],
                         **kwargs)
        self.update_browser_column_width()

    def _setup_ui(self):
        load_configuration = QtGui.QAction("Load Configuration", self)
        load_configuration.triggered.connect(self.load_config)

        save_as_default = QtGui.QAction("Save Current Settings as Default", self)
        save_as_default.triggered.connect(self.save_as_default)

        main_menu = self.menuBar()
        file_menu = main_menu.addMenu('Options')
        file_menu.addAction(load_configuration)
        file_menu.addAction(save_as_default)
        
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
        self.browser_widget = BrowserWidget(self.procedure_class, self.displays, measured_quantities, parent=self)
        self.browser_widget.show_button.clicked.connect(self.show_experiments)
        self.browser_widget.hide_button.clicked.connect(self.hide_experiments)
        self.browser_widget.clear_button.clicked.connect(self.clear_experiments)
        self.browser_widget.open_button.clicked.connect(self.open_experiment)

        self.browser = self.browser_widget.browser
        self.browser.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.browser.customContextMenuRequested.connect(self.browser_item_menu)
        self.browser.itemChanged.connect(self.browser_item_changed)

        self.inputs = InputsWidget(self.procedure_class, self.inputs, parent=self)
        self.manager = Manager(self.plot, self.browser, log_level=self.log_level, parent=self)
        self.manager.abort_returned.connect(self.abort_returned)
        self.manager.queued.connect(self.queued)
        self.manager.running.connect(self.running)
        self.manager.finished.connect(self.finished)
        self.manager.failed.connect(self.failed)
        self.manager.log.connect(self.log.handle)

        self.indicators = IndicatorsWidget(self.procedure_class)

    def _layout(self):
        # main window widget
        self.main = QtGui.QWidget(self)

        # make the parameters dock widget
        inputs_dock = QtGui.QWidget(self)
        inputs_vbox = QtGui.QVBoxLayout()
        inputs_vbox.addWidget(self.inputs)
        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(-1, 6, -1, 6)
        hbox.addStretch()
        hbox.addWidget(self.queue_button)
        hbox.addStretch()
        hbox.addWidget(self.abort_button)
        hbox.addStretch()
        hbox.addWidget(self.abort_all_button)
        hbox.addStretch()
        inputs_vbox.addLayout(hbox)
        inputs_vbox.addStretch()
        inputs_dock.setLayout(inputs_vbox)
        # add the dock to the right
        dock = QtGui.QDockWidget('Parameters')
        dock.setWidget(inputs_dock)
        features = dock.features()
        dock.setFeatures(features & ~QtGui.QDockWidget.DockWidgetClosable)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        # make indicators dock widget on the left
        if self.indicators.inputs or self.persistent_indicators:
            indicator_dock = QtGui.QWidget(self)
            indicator_vbox = QtGui.QVBoxLayout()
            if self.indicators.inputs:
                indicator_vbox.addWidget(self.indicators)
            for indicator in self.persistent_indicators:
                indicator_vbox.addWidget(indicator)
            indicator_vbox.addStretch()
            indicator_dock.setLayout(indicator_vbox)
            indicator_dock_widget = QtGui.QDockWidget('Indicators')
            indicator_dock_widget.setWidget(indicator_dock)
            features = indicator_dock_widget.features()
            indicator_dock_widget.setFeatures(features & ~QtGui.QDockWidget.DockWidgetClosable)
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, indicator_dock_widget)

        # make the browser dock widget
        browser_dock = QtGui.QWidget(self)
        browser_vbox = QtGui.QVBoxLayout()
        browser_vbox.addWidget(self.browser_widget)
        browser_dock.setLayout(browser_vbox)
        # add the dock to the bottom
        browser_dock_widget = QtGui.QDockWidget('Browser')
        browser_dock_widget.setWidget(browser_dock)
        features = browser_dock_widget.features()
        browser_dock_widget.setFeatures(features & ~QtGui.QDockWidget.DockWidgetClosable)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, browser_dock_widget)

        # make the plot tabs
        tabs = QtGui.QTabWidget(self.main)
        for index, plot_widget in enumerate(self.plot_widget):
            tabs.addTab(plot_widget, self.plot_names[index])
        tabs.addTab(self.log_widget, "Log")
        self.plot_widget[0].setMinimumSize(100, 200)
        # add the tabs as the main window layout
        vbox = QtGui.QVBoxLayout(self.main)
        vbox.setSpacing(0)
        vbox.addWidget(tabs)
        self.main.setLayout(vbox)

        # set the central widget and show
        self.setCentralWidget(self.main)
        self.main.show()
        self.resize(1400, 1000)

    def browser_item_changed(self, item, column):
        if column == 0:
            state = item.checkState(0)
            experiment = self.manager.experiments.with_browser_item(item)
            # remove plot on uncheck
            if state == 0:
                for index, plot in enumerate(self.plot):
                    for curve in experiment.curve[index]:
                        plot.removeItem(curve)
            # add plot on check
            else:
                for index, plot in enumerate(self.plot):
                    for curve in experiment.curve[index]:
                        curve.update()
                        plot.addItem(curve)

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
            self.update_color(experiment, color)

    def update_color(self, experiment, color):
        pixelmap = QtGui.QPixmap(24, 24)
        pixelmap.fill(color)
        # disable browser_item_changed() while changing the icon
        self.browser.itemChanged.disconnect()
        experiment.browser_item.setIcon(0, QtGui.QIcon(pixelmap))
        self.browser.itemChanged.connect(self.browser_item_changed)
        # update all of the curves
        for index, _ in enumerate(self.plot):
            for _, curve in enumerate(experiment.curve[index]):
                if curve.pen is not None:
                    curve.pen.setColor(color)
                if curve.symbolBrush is not None:
                    curve.symbolBrush.setColor(color)
                curve.update()

    def resume(self):
        if self.manager.experiments.has_next() and not self.manager.is_running():
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

    def failed(self, experiment):
        if self.manager.experiments.has_next():
            self.abort_all_button.setEnabled(False)
            self.abort_button.setEnabled(True)
            self.abort_button.setText("Resume")
            self.abort_button.clicked.disconnect()
            self.abort_button.clicked.connect(self.resume)
            self._abort_state = "resume"
        else:
            self.abort_button.setEnabled(False)
            self.abort_all_button.setEnabled(False)
            self.browser_widget.clear_button.setEnabled(True)

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
            menu_dict = self.define_browser_menu(item)
            menu_dict["menu"].exec_(self.browser.viewport().mapToGlobal(position))

    def define_browser_menu(self, item):
        experiment = self.manager.experiments.with_browser_item(item)
        menu = QtGui.QMenu(self)

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
        action_use = QtGui.QAction(menu)
        action_use.setText("Use These Parameters")
        action_use.triggered.connect(lambda: self.set_parameters(experiment))
        menu.addAction(action_use)
        menu_dict = {"menu": menu, "color": action_change_color,
                     "remove": action_remove, "use": action_use}
        return menu_dict

    def clear_experiments(self):
        reply = QtGui.QMessageBox.question(self, 'Remove Graphs',
                                           "Are you sure you want to remove all of "
                                           "the graphs?", QtGui.QMessageBox.Yes |
                                           QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            self.manager.clear()

    def open_experiment(self):
        dialog = ResultsDialog(self.procedure_class.DATA_COLUMNS,
                               procedure_class=self.procedure_class,
                               x_axes=self.x_axes, y_axes=self.y_axes,
                               x_labels=self.x_labels, y_labels=self.y_labels,
                               legend_text=self.legend_text,
                               plot_widget_classes=self.plot_widget_classes,
                               plot_names=self.plot_names,
                               color_cycle=self.color_cycle)
        procedure = self.make_procedure()
        try:
            directory = procedure.directory
        except AttributeError:
            directory = ""
        dialog.setDirectory(directory)
        if dialog.exec_():
            file_names = dialog.selectedFiles()
            self.load_from_file(file_names)

    def load_from_file(self, file_names):
        for file_name in map(str, file_names):
            try:
                if file_name in self.manager.experiments:
                    message = "The file %s cannot be opened twice."
                    QtGui.QMessageBox.warning(self, "Load Error",
                                              message % os.path.basename(file_name))
                    log.warning(message, os.path.basename(file_name))
                elif file_name == '':
                    return
                else:
                    try:
                        results = self.procedure_class().load(file_name)
                    except AttributeError:
                        results = Results.load(file_name)
                    results.procedure.status = SweepGUIProcedure1.FINISHED
                    experiment = self.new_experiment(results)
                    for index, _ in enumerate(self.plot):
                        for _, curve in enumerate(experiment.curve[index]):
                            curve.update()
                    experiment.data_filename = os.path.basename(file_name)
                    experiment.browser_item.setText(1, os.path.basename(file_name))
                    experiment.browser_item.progressbar.setValue(100.)
                    self.manager.load(experiment)
                    log.info('Opened data file %s' % file_name)
                    self.browser_widget.show_button.setEnabled(True)
                    self.browser_widget.hide_button.setEnabled(True)
                    self.browser_widget.clear_button.setEnabled(True)
            except Exception:
                log.exception("'{}' could not be loaded".format(file_name))
        self.update_browser_column_width()

    def update_browser_column_width(self):
        for index in range(self.browser.columnCount()):
            self.browser.resizeColumnToContents(index)

    def closeEvent(self, event):
        # check if we already called closeEvent
        if self.closing:
            event.accept()
            return
        # check if things are running
        if self.manager.is_running() or self.manager.experiments.has_next():
            reply = QtGui.QMessageBox.question(self, 'Close Window',
                                               "Are you sure you want to exit with procedures still running?",
                                               QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.No:
                event.ignore()
                return
            # abort all the experiments
            while self.manager.experiments.has_next():
                with wait_signal(self.manager.abort_returned):
                    if not self.manager.is_running():
                        self.resume()
                    self.abort()
                self.resume()
        # try to close the DAC
        self.close_window()
        self.closing = True
        event.accept()
        
    def load_config(self):
        raise NotImplementedError
        
    def save_as_default(self):
        raise NotImplementedError

    def close_window(self):
        try:
            self.procedure_class.close()
        except AttributeError:
            pass
        
    def set_parameters(self, chosen_experiment):
        parameters = chosen_experiment.procedure.parameter_objects()
        self.inputs.set_parameters(parameters)


class SweepGUI(ManagedWindow):
    def __init__(self, procedure_class, base_procedure_class=SweepGUIProcedure1,
                 x_axes=('I',), y_axes=('Q',), x_labels=('I [V]',), y_labels=('Q [V]',),
                 legend_text=('sweep',), plot_widget_classes=(SweepPlotWidget,),
                 plot_names=("Sweep Plot",), **kwargs):
        log.info("Opening Sweep GUI")
        self.base_procedure_class = base_procedure_class
        self.ordering = copy.deepcopy(self.base_procedure_class().ordering)
        self.sweep_inputs = self.ordering["sweep_inputs"]
        self.directory_inputs = self.ordering["directory_inputs"]
        self.frequency_inputs = self.ordering["frequency_inputs"]
        self.pulse_window = None  # reserved for open_pulse_window()

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
        base_inputs = [self.directory_inputs]
        base_inputs += [inputs[0] for inputs in self.frequency_inputs]
        base_inputs += [inputs[0] for inputs in self.sweep_inputs]
        # create a list of all the non-required parameters
        inputs = []
        for parameter in parameters:
            if parameter not in base_inputs:
                inputs.append(parameter)
        super().__init__(procedure_class, inputs=inputs, displays=base_inputs + inputs,
                         x_axes=x_axes, y_axes=y_axes, x_labels=x_labels,
                         y_labels=y_labels, legend_text=legend_text,
                         plot_widget_classes=plot_widget_classes, plot_names=plot_names,
                         **kwargs)
        self.setWindowTitle('Sweep GUI')
        self.setWindowIcon(get_image_icon("loop.png"))

        directory = os.path.join(os.path.dirname(__file__), "user_data")
        if not os.path.isdir(directory):
            os.mkdir(directory)
        file_path = os.path.join(directory, "sweep_default.npz")
        if os.path.isfile(file_path):
            self.set_config(file_path)

    def _setup_ui(self):
        self.base_inputs_widget = SweepInputsWidget(self.base_procedure_class, self.ordering, parent=self)
        super()._setup_ui()

    def _layout(self):
        # make the sweep dock widget
        base_dock = QtGui.QWidget(self)
        base_inputs_vbox = QtGui.QVBoxLayout()
        base_inputs_vbox.addWidget(self.base_inputs_widget)
        base_inputs_vbox.addStretch(0)
        base_dock.setLayout(base_inputs_vbox)
        # add the dock widget to the left
        base_inputs_dock = QtGui.QDockWidget('Sweeps')
        base_inputs_dock.setWidget(base_dock)
        features = base_inputs_dock.features()
        base_inputs_dock.setFeatures(features & ~QtGui.QDockWidget.DockWidgetClosable)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, base_inputs_dock)

        super()._layout()

    def set_parameters(self, chosen_experiment):
        sweep_parameters = self.base_procedure_class().parameter_objects()
        parameters = chosen_experiment.procedure.parameter_objects()
        sweep_parameters[self.directory_inputs].value = \
            parameters[self.directory_inputs].value
        for input_list in self.frequency_inputs:
            sweep_parameters[input_list[1]].value = parameters[input_list[0]].value
        for input_list in self.sweep_inputs:
            sweep_parameters[input_list[1]].value = parameters[input_list[0]].value
            sweep_parameters[input_list[2]].value = parameters[input_list[0]].value
        self.inputs.set_parameters(parameters)
        self.base_inputs_widget.set_parameters(sweep_parameters)

    def open_experiment(self):
        dialog = ResultsDialog(self.procedure_class.DATA_COLUMNS,
                               procedure_class=self.procedure_class,
                               x_axes=self.x_axes, y_axes=self.y_axes,
                               x_labels=self.x_labels, y_labels=self.y_labels,
                               legend_text=self.legend_text,
                               plot_widget_classes=self.plot_widget_classes,
                               plot_names=self.plot_names,
                               color_cycle=self.color_cycle)
        sweep_procedure = self.base_inputs_widget.get_procedure()
        sweep_dict = sweep_procedure.parameter_values()
        directory = sweep_dict[self.directory_inputs]
        dialog.setDirectory(directory)
        if dialog.exec_():
            file_names = dialog.selectedFiles()
            self.load_from_file(file_names)
        
    def define_browser_menu(self, item):
        menu_dict = super().define_browser_menu(item)
        menu = menu_dict['menu']
        experiment = self.manager.experiments.with_browser_item(item)

        action_open_pulse = QtGui.QAction(menu)
        action_open_pulse.setText("Use Settings in Pulse GUI")
        if self.manager.is_running():
            if self.manager.running_experiment() == experiment:  # Experiment running
                action_open_pulse.setEnabled(False)

        action_open_pulse.triggered.connect(lambda: self.open_pulse_gui(experiment))

        menu.addAction(action_open_pulse)
        menu_dict['pulse'] = action_open_pulse
        
        return menu_dict
        
    def open_pulse_gui(self, experiment):
        """
        Programs must define their own logic to open a pulse GUI. The window can be saved
        as self.pulse_window for future access.
        """
        raise NotImplementedError

    @staticmethod
    def save_config(save_name, sweep_dict, parameter_dict):
        np.savez(save_name, sweep_dict=sweep_dict, parameter_dict=parameter_dict)

    def load_config(self):
        sweep_procedure = self.base_inputs_widget.get_procedure()
        sweep_dict = sweep_procedure.parameter_values()
        directory = sweep_dict[self.directory_inputs]
        file_name = QtGui.QFileDialog.getOpenFileName(self, 'Open file', directory,
                                                      "Config files (config_sweep*.npz)")
        if file_name:
            self.set_config(file_name)

    def set_config(self, file_name):
        log.info("loading configuration from {}".format(file_name))
        npz_file = load(file_name, allow_pickle=True)
        # set sweep parameters
        sweep_dict = npz_file['sweep_dict'].item()
        sweep_parameters = self.base_procedure_class().parameter_objects()
        for key, value in sweep_dict.items():
            sweep_parameters[key].value = value
        self.base_inputs_widget.set_parameters(sweep_parameters)
        # set additional parameters
        parameter_dict = npz_file['parameter_dict'].item()
        files = list(parameter_dict.keys())
        parameters = self.make_procedure().parameter_objects()
        ignore_parameters = [params[0] for params in self.sweep_inputs]
        ignore_parameters += [param for params in self.frequency_inputs
                              for param in params]
        for key, value in parameter_dict[files[0]].items():
            if key not in ignore_parameters and key in parameters.keys():
                parameters[key].value = value
        self.inputs.set_parameters(parameters)

    def save_as_default(self):
        sweep_procedure = self.base_inputs_widget.get_procedure()
        sweep_dict = sweep_procedure.parameter_values()
        procedure = self.make_procedure()
        parameter_values = procedure.parameter_values()
        parameter_dict = {"default": parameter_values}
        directory = os.path.join(os.path.dirname(__file__), "user_data")
        file_path = os.path.join(directory, "sweep_default.npz")
        log.info("saving configuration as default to {}".format(file_path))
        self.save_config(file_path, sweep_dict, parameter_dict)

    def queue(self):
        sweep_procedure = self.base_inputs_widget.get_procedure()
        sweep_dict = sweep_procedure.parameter_values()
        directory = sweep_dict[self.directory_inputs]
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
        start_time = datetime.now().strftime("%y%m%d_%H%M%S")
        files = []
        previous_files = []
        for experiment in self.manager.experiments:
            file_path = os.path.join(experiment.procedure.directory,
                                     experiment.browser_item.text(1))
            previous_files.append(file_path)
        # make the procedure
        procedure = self.make_procedure()
        parameter_values = procedure.parameter_values()
        # set the directory parameter
        parameter_values.update(
            {self.directory_inputs: sweep_dict[self.directory_inputs]})
        # parse the frequency list
        try:
            freq_dict = {}
            n_freq = 0
            for parameter, sweep_parameter in self.frequency_inputs:
                f_list = sweep_dict[sweep_parameter]
                freq_dict[parameter] = f_list
                if len(f_list) > n_freq:
                    n_freq = len(f_list)
            assert n_freq != 0
        except (ValueError, AssertionError):
            log.error("Invalid frequency and span lists")
            return
        # loop over sweep parameters
        parameter_dict = {}
        for index, _ in np.ndenumerate(sweep_grid[0]):
            # set sweep parameters
            for item, (parameter, _, _, _, _) in enumerate(self.sweep_inputs):
                value = sweep_grid[item][index]
                parameter_values.update({parameter: value})
            # loop over frequencies
            for f_index in range(n_freq):
                # set the frequency parameters
                for parameter, _ in self.frequency_inputs:
                    f_list = freq_dict[parameter]
                    if f_index < len(f_list):
                        parameter_values.update({parameter: f_list[f_index]})
                    elif len(f_list) != 0:
                        parameter_values.update({parameter: f_list[-1]})
                    else:
                        parameter_values.update({parameter: np.nan})
                # update the procedure
                procedure = self.make_procedure()  # new instance for each experiment
                procedure.set_parameters(parameter_values)
                # set up the experiment
                try:
                    file_path = tempfile.mktemp(suffix=".pickle")
                    results = Results(procedure, file_path)
                    experiment = self.new_experiment(results)
                    # change the file name to the real file name if it has one
                    # temp, field, atten, fr
                    numbers = [i for i in index] + [f_index]
                    file_name = procedure.file_name("sweep", numbers, start_time)
                    experiment.browser_item.setText(1, file_name)
                    experiment.data_filename = file_name
                    file_path = os.path.join(directory, file_name)
                    if file_path in files or file_path in previous_files:
                        message = "'{}' is already in the queue, skipping"
                        log.error(message.format(file_path))
                    elif os.path.isfile(file_path):
                        message = "'{}' already exists, skipping"
                        log.error(message.format(file_path))
                    else:
                        parameter_dict[file_name] = copy.deepcopy(parameter_values)
                        file_name = os.path.join(directory, file_name)
                        files.append(file_name)
                        self.manager.queue(experiment)
                except Exception:
                    log.error('Failed to queue experiment', exc_info=True)
        self.update_browser_column_width()
        save_name = os.path.join(directory, "config_sweep_" + start_time + ".npz")
        self.save_config(save_name, sweep_dict, parameter_dict)
        
    def close_window(self):
        if self.pulse_window is None or not self.pulse_window.isVisible():
            try:
                self.procedure_class.close()
            except AttributeError:
                pass
        if self.pulse_window is not None and self.pulse_window.sweep_window is not None:
            self.pulse_window.sweep_window = None  # remove reference to window that is closing


class PulseGUI(ManagedWindow):
    def __init__(self, *args, **kwargs):
        log.info("Opening Pulse GUI")
        super().__init__(*args, **kwargs)
        self.sweep_window = None  # reserved for open_pulse_window() in SweepGUI
        
        self.setWindowTitle('Pulse GUI')

        directory = os.path.join(os.path.dirname(__file__), "user_data")
        if not os.path.isdir(directory):
            os.mkdir(directory)
        file_path = os.path.join(directory, "pulse_default.npz")
        if os.path.isfile(file_path):
            self.set_config(file_path)
            
    def queue(self):
        # make results object to hold the gui data
        procedure = self.make_procedure()  # Procedure class was passed at construction
        file_path = tempfile.mktemp(suffix=".pickle")
        results = Results(procedure, file_path)
        # make the experiment
        experiment = self.new_experiment(results)
        start_time = datetime.now().strftime("%y%m%d_%H%M%S")
        file_name = procedure.file_name("pulse", time=start_time)
        experiment.browser_item.setText(1, file_name)
        experiment.data_filename = file_name
        # queue the experiment
        self.manager.queue(experiment)
        # do some post queuing stuff
        self.update_browser_column_width()
        save_name = os.path.join(experiment.procedure.directory, "config_pulse_" + start_time + ".npz")
        parameter_dict = experiment.procedure.parameter_values()
        self.save_config(save_name, parameter_dict)

    @staticmethod
    def save_config(save_name, parameter_dict):
        np.savez(save_name, parameter_dict=parameter_dict)
    
    def set_config(self, file_name):
        log.info("loading configuration from {}".format(file_name))
        npz_file = load(file_name, allow_pickle=True)
        parameter_dict = npz_file['parameter_dict'].item()
        parameters = self.make_procedure().parameter_objects()
        for key, value in parameter_dict.items():
            if key in parameters.keys():
                parameters[key].value = value
        self.inputs.set_parameters(parameters)

    def save_as_default(self):
        procedure = self.make_procedure()
        parameter_dict = procedure.parameter_values()
        directory = os.path.join(os.path.dirname(__file__), "user_data")
        file_path = os.path.join(directory, "pulse_default.npz")
        log.info("saving configuration as default to {}".format(file_path))
        self.save_config(file_path, parameter_dict)
        
    def load_config(self):
        procedure = self.make_procedure()
        try:
            directory = procedure.directory
        except AttributeError:
            directory = ""
        file_name = QtGui.QFileDialog.getOpenFileName(self, 'Open file', directory, "Config files (config_pulse*.npz)")
        if file_name:
            self.set_config(file_name)
            
    def close_window(self):
        if self.sweep_window is None or not self.sweep_window.isVisible():
            try:
                self.procedure_class.close()
            except AttributeError:
                pass
        if self.sweep_window is not None and self.sweep_window.pulse_window is not None:
            self.sweep_window.pulse_window = None  # remove reference to window that is closing
