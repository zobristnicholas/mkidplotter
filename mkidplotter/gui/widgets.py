import os
import copy
import logging
import numpy as np
import pyqtgraph as pg
from cycler import cycler
from datetime import datetime
import pyqtgraph.graphicsItems.LegendItem as li
from pyqtgraph.graphicsItems.ScatterPlotItem import drawSymbol
from pymeasure.experiment import Results
import pymeasure.display.widgets as widgets
from pymeasure.display.Qt import QtCore, QtGui
from pymeasure.display.curves import Crosshairs
from pymeasure.display.inputs import IntegerInput, BooleanInput, ListInput, StringInput
from pymeasure.experiment import FloatParameter, IntegerParameter, BooleanParameter, ListParameter, Parameter

from mkidplotter.gui.displays import StringDisplay, FloatDisplay
from mkidplotter.gui.curves import MKIDResultsCurve, NoiseResultsCurve, HistogramResultsCurve, ParameterResultsCurve
from mkidplotter.gui.parameters import FileParameter, DirectoryParameter, TextEditParameter
from mkidplotter.gui.indicators import Indicator, FloatIndicator, BooleanIndicator, IntegerIndicator
from mkidplotter.gui.inputs import (FileInput, DirectoryInput, FloatTextEditInput, NoiseInput, BooleanListInput,
                                    ScientificInput, RangeInput)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class ResultsDialog(widgets.ResultsDialog):
    def __init__(self, *args, procedure_class=None, x_axes=None, y_axes=None,
                 x_labels=None, y_labels=None, legend_text=None, plot_widget_classes=None,
                 plot_names=None, color_cycle=None, **kwargs):
        self.procedure_class = procedure_class
        self.x_axes = x_axes
        self.y_axes = y_axes
        self.x_labels = x_labels
        self.y_labels = y_labels
        self.legend_text = legend_text
        self.plot_widget_classes = plot_widget_classes
        self.plot_names = plot_names
        self.color_cycle = color_cycle
        super().__init__(*args, **kwargs)

    def _setup_ui(self):
        preview_tab = QtGui.QTabWidget()
        param_vbox = QtGui.QVBoxLayout()
        param_vbox_widget = QtGui.QWidget()

        self.plot_widget = []
        self.plot = []
        vbox_widget = []
        vbox = []
        for index, plot_widget in enumerate(self.plot_widget_classes):
            vbox_widget.append(QtGui.QWidget())
            vbox.append(QtGui.QVBoxLayout())
            color_cycle = self.color_cycle[:1]
            self.plot_widget.append(plot_widget(self.columns,
                                                x_axes=self.x_axes[index],
                                                y_axes=self.y_axes[index],
                                                x_label=self.x_labels[index],
                                                y_label=self.y_labels[index],
                                                legend_text=self.legend_text[index],
                                                color_cycle=color_cycle))
            self.plot.append(self.plot_widget[-1].plot)
            vbox[-1].addWidget(self.plot_widget[-1])
            vbox_widget[-1].setLayout(vbox[-1])
            preview_tab.addTab(vbox_widget[-1], self.plot_names[index])

        self.preview_param = QtGui.QTreeWidget()
        param_header = QtGui.QTreeWidgetItem(["Name", "Value"])
        self.preview_param.setHeaderItem(param_header)
        self.preview_param.setColumnWidth(0, 150)
        self.preview_param.setAlternatingRowColors(True)

        param_vbox.addWidget(self.preview_param)
        param_vbox_widget.setLayout(param_vbox)
        preview_tab.addTab(param_vbox_widget, "Run Parameters")
        self.layout().addWidget(preview_tab, 0, 3, 4, 1)
        self.layout().setColumnStretch(3, 2)
        self.setMinimumSize(900, 500)
        self.resize(1300, 500)

        self.setFileMode(QtGui.QFileDialog.ExistingFiles)
        self.currentChanged.connect(self.update_plot)

    def update_plot(self, filename):
        for plot in self.plot:
            plot.clear()
        if not os.path.isdir(filename) and filename != '':
            try:
                results = self.procedure_class().load(str(filename))
            except Exception as error:
                try:
                    results = Results.load(str(filename))
                except ValueError:
                    return
                except Exception as e:
                    raise e
            for index, plot_widget in enumerate(self.plot_widget):
                curve_list = plot_widget.new_curve(results)
                for curve in curve_list:
                    curve.update()
                    self.plot[index].addItem(curve)

            self.preview_param.clear()
            for key, param in results.procedure.parameter_objects().items():
                new_item = QtGui.QTreeWidgetItem([param.name, str(param)])
                self.preview_param.addTopLevelItem(new_item)
            self.preview_param.sortItems(0, QtCore.Qt.AscendingOrder)


class ParametersWidget(QtGui.QWidget):
    """ Displays parameters for multiple experiments."""

    def __init__(self, columns, parent=None, x_axes=None, x_label=None, **kwargs):
        super().__init__(parent)
        self.columns = columns
        self.x_axes = x_axes
        self.x_label = x_label
        self.curves = []
        # self.refresh_time = refresh_time
        # self.check_status = check_status
        self._setup_ui()
        self._layout()

    def _setup_ui(self):
        self.plot = QtGui.QTreeWidget()
        param_header = QtGui.QTreeWidgetItem(self.x_label)
        self.plot.setHeaderItem(param_header)
        self.plot.setColumnWidth(0, 150)
        self.plot.setAlternatingRowColors(True)

        # patch addItem and removeItem from pyqtgraph PlotItem
        self.plot.addItem = self.addItem
        self.plot.removeItem = self.removeItem

    def _layout(self):
        vbox = QtGui.QVBoxLayout(self)
        vbox.addWidget(self.plot)
        self.setLayout(vbox)

    def new_curve(self, results, **kwargs):
        curve = [ParameterResultsCurve(results, x=x, y=None, **kwargs) for x in self.x_axes]
        return curve

    def addItem(self, curve):
        results = []
        for x_axis in curve.x:
            try:
                result = curve.results.data[x_axis][0]
                if isinstance(result, str):
                    results.append(result)
                else:
                    results.append(f"{result:g}")
            except IndexError:
                pass
        if results:
            item = QtGui.QTreeWidgetItem(results)
            self.plot.addTopLevelItem(item)
            self.curves.append(curve)

        for index in range(self.plot.columnCount()):
            self.plot.resizeColumnToContents(index)

    def removeItem(self, curve):
        for index, c in enumerate(self.curves):
            if curve is c:
                self.curves.pop(index)
                self.plot.takeTopLevelItem(index)
                break


class BrowserWidget(widgets.BrowserWidget):
    def _layout(self):
        vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(0)

        hbox = QtGui.QHBoxLayout()
        hbox.setSpacing(10)
        hbox.setContentsMargins(-1, 6, -1, 6)
        hbox.addWidget(self.show_button)
        hbox.addWidget(self.hide_button)
        hbox.addWidget(self.clear_button)
        hbox.addStretch()
        hbox.addWidget(self.open_button)

        vbox.addLayout(hbox)
        vbox.addSpacing(10)
        vbox.addWidget(self.browser)
        self.setLayout(vbox)

    def sizeHint(self):
        return QtCore.QSize(0, 300)


class PlotWidget(widgets.PlotWidget):
    """Base class for all plot widgets. Only determines the user interface and layout."""
    def _setup_ui(self):
        self.columns_x = QtGui.QComboBox(self)
        self.columns_y = QtGui.QComboBox(self)
        self.columns_x.hide()
        self.columns_y.hide()
        for column in self.columns:
            self.columns_x.addItem(column)
            self.columns_y.addItem(column)
        self.columns_x.activated.connect(self.update_x_column)
        self.columns_y.activated.connect(self.update_y_column)

        if self.x_label is None:
            x_label = self.x_axes if isinstance(self.x_axes, str) else self.x_axes[0]
        else:
            x_label = self.x_label
        if self.y_label is None:
            y_label = self.y_axes if isinstance(self.y_axes, str) else self.y_axes[0]
        else:
            y_label = self.y_label
        self.plot_frame = widgets.PlotFrame(x_label, y_label, self.refresh_time,
                                            self.check_status)
        self.updated = self.plot_frame.updated
        self.plot = self.plot_frame.plot
        self.columns_x.setCurrentIndex(0)
        self.columns_y.setCurrentIndex(1)
        if self.legend_text is not None:
            style_cycle = self.style_cycle()
            self.legend = self.plot_frame.plot_widget.addLegend(offset=(-1, 1))
            for text in self.legend_text:
                legend_item = pg.PlotDataItem(**copy_options(next(style_cycle)))
                legend_item_sample = ItemSample(legend_item)
                self.legend.addItem(legend_item_sample, text)
        # Set the results curve class
        self.curve_class = MKIDResultsCurve

    def _layout(self):
        vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(0)
        vbox.addWidget(self.plot_frame)
        self.setLayout(vbox)

    def new_curve(self, results, **kwargs):
        curve = []
        for index, _ in enumerate(self.x_axes):
            # overwrite cycler with kwargs
            cycled_args = next(self.cycler)
            cycled_args.update(kwargs)
            # need to get copies of the QObjects otherwise they will be overwritten later
            cycled_args = copy_options(cycled_args)
            if 'color' not in cycled_args.keys():
                cycled_args.update({'color': pg.intColor(0)})
            if 'pen' not in cycled_args:
                cycled_args['pen'] = pg.mkPen(color=cycled_args['color'], width=2)
            if 'antialias' not in cycled_args:
                cycled_args['antialias'] = False

            curve.append(self.curve_class(results, x=self.x_axes[index],
                                          y=self.y_axes[index], **cycled_args))

        return curve


class FitPlotWidget(PlotWidget):
    """Plot widget for an IQ sweep fit"""
    def __init__(self, *args, color_cycle=None, x_axes=None, y_axes=None, x_label=None,
                 y_label=None, legend_text=None, **kwargs):
        self.x_axes = x_axes
        self.y_axes = y_axes
        self.x_label = x_label
        self.y_label = y_label
        self.legend_text = legend_text
        self._point_size = 6
        self.line_style = {"pen": [pg.mkPen(None), pg.mkPen(color='k', width=2, style=QtCore.Qt.DashLine),
                                   pg.mkPen(color='w', width=2),
                                   pg.mkPen(None), pg.mkPen(None)],
                           "shadowPen": [pg.mkPen(None),
                                         pg.mkPen(None),
                                         pg.mkPen(color='k', width=4),
                                         pg.mkPen(None),
                                         pg.mkPen(None)],
                           "symbol": ['o', None, None, 'd', '+'],
                           "symbolPen": [pg.mkPen(None), pg.mkPen(color='k', width=1),
                                         pg.mkPen(color='k', width=1),
                                         pg.mkPen(color='k', width=1),
                                         pg.mkPen(color='k', width=1)],
                           "symbolBrush": [pg.mkBrush(color='k'), pg.mkBrush(color='k'),
                                           pg.mkBrush(color='k'), pg.mkBrush(color='k'),
                                           pg.mkBrush(color='k')],
                           "symbolSize": [self._point_size, self._point_size,
                                          self._point_size, self._point_size,
                                          self._point_size],
                           "pxMode": [True, True, True, True, True]}
        n = int(np.ceil(len(self.x_axes) / len(self.line_style["pen"])))
        self.style_cycle = (cycler(**self.line_style) * n)[:len(self.x_axes)]
        self.cycler = (color_cycle * self.style_cycle)()
        super().__init__(*args, **kwargs)
        self.plot.setAspectLocked(True)


class SweepPlotWidget(PlotWidget):
    """Plot widget for an IQ sweep"""
    def __init__(self, *args, color_cycle=None, x_axes=None, y_axes=None, x_label=None,
                 y_label=None, legend_text=None, **kwargs):
        self.x_axes = x_axes
        self.y_axes = y_axes
        self.x_label = x_label
        self.y_label = y_label
        self.legend_text = legend_text
        self._point_size = 6
        self.line_style = {"pen": [pg.mkPen(None), pg.mkPen(None), pg.mkPen(None),
                                   pg.mkPen(None), pg.mkPen(None)],
                           "symbol": ['o', 's', 't', 'd', '+'],
                           "symbolPen": [pg.mkPen(None), pg.mkPen(color='k', width=1),
                                         pg.mkPen(color='k', width=1),
                                         pg.mkPen(color='k', width=1),
                                         pg.mkPen(color='k', width=1)],
                           "symbolBrush": [pg.mkBrush(color='k'), pg.mkBrush(color='k'),
                                           pg.mkBrush(color='k'), pg.mkBrush(color='k'),
                                           pg.mkBrush(color='k')],
                           "symbolSize": [self._point_size, self._point_size,
                                          self._point_size, self._point_size,
                                          self._point_size],
                           "pxMode": [True, True, True, True, True]}
        n = int(np.ceil(len(self.x_axes) / len(self.line_style["pen"])))
        self.style_cycle = (cycler(**self.line_style) * n)[:len(self.x_axes)]
        self.cycler = (color_cycle * self.style_cycle)()
        super().__init__(*args, **kwargs)
        self.plot.setAspectLocked(True)


class TransmissionPlotWidget(FitPlotWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plot.setAspectLocked(False)


class PulsePlotWidget(PlotWidget):
    """Plot widget for pulse IQ data"""
    def __init__(self, *args, color_cycle=None, x_axes=None, y_axes=None, x_label=None,
                 y_label=None, legend_text=None, **kwargs):
        self.x_axes = x_axes
        self.y_axes = y_axes
        self.x_label = x_label
        self.y_label = y_label
        self.legend_text = legend_text
        self._point_size = 6
        self.line_style = {"pen": [pg.mkPen(None), pg.mkPen(color='w', width=2),
                                   pg.mkPen(color='w', width=2, style=QtCore.Qt.DashLine),
                                   pg.mkPen(None), pg.mkPen(None)],
                           "shadowPen": [pg.mkPen(None),
                                         pg.mkPen(color='k', width=4),
                                         pg.mkPen(color='k', width=4),
                                         pg.mkPen(None),
                                         pg.mkPen(None)],
                           "symbol": ['o', None, None, 'd', '+'],
                           "symbolPen": [pg.mkPen(None), pg.mkPen(None),
                                         pg.mkPen(color='k', width=1),
                                         pg.mkPen(color='k', width=1),
                                         pg.mkPen(color='k', width=1)],
                           "symbolBrush": [pg.mkBrush(color='k'), pg.mkBrush(color='k'),
                                           pg.mkBrush(color='k'), pg.mkBrush(color='k'),
                                           pg.mkBrush(color='k')],
                           "symbolSize": [self._point_size, self._point_size,
                                          self._point_size, self._point_size,
                                          self._point_size],
                           "pxMode": [True, True, True, True, True]}
        n = int(np.ceil(len(self.x_axes) / len(self.line_style["pen"])))
        self.style_cycle = (cycler(**self.line_style) * n)[:len(self.x_axes)]
        self.cycler = (color_cycle * self.style_cycle)()
        super().__init__(*args, **kwargs)
        self.plot.setAspectLocked(True)


class ScatterPlotWidget(PlotWidget):
    """Plot widget for pulse amplitudes"""
    def __init__(self, *args, color_cycle=None, x_axes=None, y_axes=None, x_label=None,
                 y_label=None, legend_text=None, **kwargs):
        self.x_axes = x_axes
        self.y_axes = y_axes
        self.x_label = x_label
        self.y_label = y_label
        self.legend_text = legend_text
        self._point_size = 6
        self.line_style = {"pen": [pg.mkPen(None), pg.mkPen(None)],
                           "symbol": ['o', '+'],
                           "symbolPen": [pg.mkPen(None), pg.mkPen(None)],
                           "symbolBrush": [pg.mkBrush(color='k'), pg.mkBrush(color='k')],
                           "symbolSize": [self._point_size, self._point_size],
                           "pxMode": [True, True]}
        n = int(np.ceil(len(self.x_axes) / len(self.line_style["pen"])))
        self.style_cycle = (cycler(**self.line_style) * n)[:len(self.x_axes)]
        # add transparency
        color_cycle = cycler(color=[tuple(list(value) + [50]) for value in color_cycle.by_key()['color']])
        self.cycler = (color_cycle * self.style_cycle)()
        super().__init__(*args, **kwargs)


class HistogramPlotWidget(PlotWidget):
    """Plot widget for histogramming pulse amplitudes"""

    def __init__(self, *args, color_cycle=None, x_axes=None, y_axes=None, x_label=None,
                 y_label=None, legend_text=None, **kwargs):
        self.x_axes = x_axes
        self.y_axes = y_axes
        self.x_label = x_label
        self.y_label = y_label
        self.legend_text = legend_text
        self._point_size = 6
        self.line_style = {"pen": [pg.mkPen(color='w', width=2), pg.mkPen(color='w', width=2),
                                   pg.mkPen(color='w', width=2), pg.mkPen(color='w', width=2)]}
        n = int(np.ceil(len(self.x_axes) / len(self.line_style["pen"])))
        self.style_cycle = (cycler(**self.line_style) * n)[:len(self.x_axes)]
        self.cycler = (color_cycle * self.style_cycle)()
        super().__init__(*args, **kwargs)
        self.curve_class = HistogramResultsCurve


class NoisePlotWidget(PlotWidget):
    """Plot widget for noise"""
    def __init__(self, *args, color_cycle=None, x_axes=None, y_axes=None, x_label=None,
                 y_label=None, legend_text=None, **kwargs):
        self.x_axes = x_axes
        self.y_axes = y_axes
        self.x_label = x_label
        self.y_label = y_label
        self.legend_text = legend_text
        self._point_size = 6
        self.line_style = {"pen": [pg.mkPen(color='w', width=2, style=QtCore.Qt.DashLine),
                                   pg.mkPen(color='w', width=2, style=QtCore.Qt.DotLine),
                                   pg.mkPen(color='w', width=2,
                                            style=QtCore.Qt.DashDotLine),
                                   pg.mkPen(color='w', width=2,
                                            style=QtCore.Qt.DashDotDotLine)],
                           "shadowPen": [pg.mkPen(color='k', width=4),
                                         pg.mkPen(color='k', width=4),
                                         pg.mkPen(color='k', width=4),
                                         pg.mkPen(color='k', width=4)]}
        n = int(np.ceil(len(self.x_axes) / len(self.line_style["pen"])))
        self.style_cycle = (cycler(**self.line_style) * n)[:len(self.x_axes)]
        self.cycler = (color_cycle * self.style_cycle)()
        super().__init__(*args, **kwargs)
        # pyqtgraph version 0.12.1 log scaling in y is broken so we do it manually here
        # see also curves.NoiseResultsCurve, and y axis units in the config file
        self.plot.setLogMode(True, False)
        self.curve_class = NoiseResultsCurve


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [datetime.fromtimestamp(value).strftime("%H:%M:%S") for value in values]


class TimePlotIndicator(QtGui.QFrame):
    """Plot widget for plotting data over a long time. Intended for use as a persistent indicator."""
    def __init__(self, data_x, data_y, title='', refresh_time=2, **kwargs):
        super().__init__(**kwargs)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: #fff")
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.setFrameShadow(QtGui.QFrame.Sunken)
        self.setMidLineWidth(1)

        self.data_x = data_x
        self.data_y = data_y

        self.coordinates = QtGui.QLabel(self)
        self.coordinates.setMinimumSize(QtCore.QSize(0, 20))
        self.coordinates.setStyleSheet("background: #fff")
        self.coordinates.setText("")
        self.coordinates.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
        self.plot_widget = pg.PlotWidget(background='w', title=title,
                                         axisItems={'bottom': TimeAxisItem(orientation='bottom')}, **kwargs)
        self.plot = self.plot_widget.getPlotItem()
        self.curve = self.plot.plot(pen='k')
        self.crosshairs = Crosshairs(self.plot, pen=pg.mkPen(color='#AAAAAA', style=QtCore.Qt.DashLine))
        self.crosshairs.coordinates.connect(self.update_coordinates)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(refresh_time * 1000)

        vbox = QtGui.QVBoxLayout(self)
        vbox.addWidget(self.plot_widget)
        vbox.addWidget(self.coordinates)
        self.setLayout(vbox)

    def update(self):
        self.curve.setData(x=list(self.data_x), y=list(self.data_y))

    def update_coordinates(self, x, y):
        try:
            self.coordinates.setText("(%s, %g)" % (datetime.fromtimestamp(x).strftime("%H:%M:%S"), y))
        except OSError:
            pass

    def sizeHint(self):
        return QtCore.QSize(0, 300)


class IndicatorsWidget(QtGui.QWidget):
    NO_LABEL_INPUTS = ()

    def __init__(self, procedure_class, parent=None):
        super().__init__(parent)
        self._procedure_class = procedure_class
        self._procedure = procedure_class()
        self.inputs = []
        self._setup_ui()
        self._layout()

    def _setup_ui(self):
        for name, indicator in self._procedure.indicator_objects.items():
            self._make_input(name, indicator)

    def _make_input(self, name, indicator):
        if indicator.ui_class is not None:
            element = indicator.ui_class

        elif isinstance(indicator, BooleanIndicator):
            raise NotImplementedError
            
        elif isinstance(indicator, FloatIndicator):
            element = FloatDisplay(indicator)

        elif isinstance(indicator, (IntegerIndicator, Indicator)):
            element = StringDisplay(indicator)

        else:
            raise ValueError("unrecognized indicator type: {}".format(type(indicator)))
        self.inputs.append(name)
        setattr(self, name, element)

    def _layout(self):
        vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(6)
        vbox.setContentsMargins(0, 0, 0, 0)
        inputs = list(self._procedure.indicator_objects.keys())
        for name in inputs:
            self._add_widget(name, vbox)
        self.setLayout(vbox)

    def _add_widget(self, name, vbox):
        indicators = self._procedure.indicator_objects
        widget = getattr(self, name)
        hbox = QtGui.QHBoxLayout()
        if not isinstance(widget, self.NO_LABEL_INPUTS):
            label = QtGui.QLabel(self)
            label.setText("%s:" % indicators[name].name)
            hbox.addWidget(label)
        hbox.addWidget(widget)
        vbox.addLayout(hbox)
        
    def sizeHint(self):
        return QtCore.QSize(300, 0)


class InputsWidget(widgets.InputsWidget):
    """
    Fixes set_parameters bug in pymeasure (would always set to default if existed).
    Puts NoiseWidget last in layout column."""
    NO_LABEL_INPUTS = (BooleanInput, DirectoryInput, FileInput, BooleanListInput, NoiseInput, RangeInput)

    def set_parameters(self, parameter_objects):
        for name in self._inputs:
            parameter = parameter_objects[name]
            element = getattr(self, name)
            element.setValue(parameter.value)
            if hasattr(parameter, 'units') and parameter.units:
                element.setSuffix(" %s" % parameter.units)

    def _setup_ui(self):
        parameter_objects = self._procedure.parameter_objects()
        for name in self._inputs:
            parameter = parameter_objects[name]
            self._make_input(name, parameter)

    def _make_input(self, name, parameter):
        if parameter.ui_class is not None:
            element = parameter.ui_class(parameter)

        elif isinstance(parameter, FloatParameter):
            element = ScientificInput(parameter)

        elif isinstance(parameter, IntegerParameter):
            element = IntegerInput(parameter)

        elif isinstance(parameter, BooleanParameter):
            element = BooleanInput(parameter)

        elif isinstance(parameter, ListParameter):
            element = ListInput(parameter)

        elif isinstance(parameter, FileParameter):
            element = FileInput(parameter)

        elif isinstance(parameter, DirectoryParameter):
            element = DirectoryInput(parameter)

        elif isinstance(parameter, TextEditParameter):
            element = FloatTextEditInput(parameter)

        elif isinstance(parameter, Parameter):
            element = StringInput(parameter)

        else:
            raise ValueError("unrecognized parameter type: {}".format(type(parameter)))

        setattr(self, name, element)

    def _layout(self):
        vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(6)
        vbox.setContentsMargins(0, 0, 0, 0)
        inputs = list(self._inputs)

        remove_indices = []
        for ind, name in enumerate(inputs):
            if isinstance(getattr(self, name), (FileInput, DirectoryInput)):
                remove_indices.append(ind)
                self._add_widget(name, vbox)
        inputs = [inputs[ind] for ind in range(len(inputs)) if ind not in remove_indices]

        remove_indices = []
        for ind, name in enumerate(inputs):
            if isinstance(getattr(self, name), (NoiseInput, BooleanListInput, RangeInput)):
                continue
            remove_indices.append(ind)
            self._add_widget(name, vbox)
        inputs = [inputs[ind] for ind in range(len(inputs)) if ind not in remove_indices]

        for name in inputs:
            self._add_widget(name, vbox)
        self.setLayout(vbox)

    def _add_widget(self, name, vbox):
        parameters = self._procedure.parameter_objects()
        widget = getattr(self, name)
        hbox = QtGui.QHBoxLayout()
        if not isinstance(widget, self.NO_LABEL_INPUTS):
            label = QtGui.QLabel(self)
            label.setText("%s:" % parameters[name].name)
            hbox.addWidget(label)
        hbox.addWidget(widget)
        vbox.addLayout(hbox)
        vbox.addStretch(0)
        
    def sizeHint(self):
        return QtCore.QSize(300, 0)


class SweepInputsWidget(InputsWidget):
    NO_LABEL_INPUTS = (BooleanInput, BooleanListInput, NoiseInput)
    
    def _setup_ui(self):
        parameter_objects = self._procedure.parameter_objects()
        self._make_input(self._inputs["directory_inputs"],
                         parameter_objects[self._inputs["directory_inputs"]])
        for inputs in self._inputs["frequency_inputs"]:
            for name in inputs[1:]:
                self._make_input(name, parameter_objects[name])
        for inputs in self._inputs["sweep_inputs"]:
            for name in inputs[1:-1]:
                self._make_input(name, parameter_objects[name])

    def _layout(self):
        parameters = self._procedure.parameter_objects()
        vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(6)

        directory = getattr(self, self._inputs["directory_inputs"])
        font = QtGui.QFont()
        font.setBold(True)
        directory.label.setFont(font)
        vbox.addWidget(directory)
        grid = QtGui.QGridLayout()
        for index, (_, parameter) in enumerate(self._inputs["frequency_inputs"]):
            label = QtGui.QLabel()
            label.setText(parameters[parameter].name)
            grid.addWidget(label, 0, index)
            text_edit = QtGui.QTextEdit()
            text_edit.sizeHint = lambda: QtCore.QSize(0, 120)
            grid.addWidget(getattr(self, parameter), 1, index)
        vbox.addLayout(grid)

        for inputs in self._inputs["sweep_inputs"]:
            label = QtGui.QLabel()
            label.setText(inputs[-1] + ":")
            font = QtGui.QFont()
            font.setBold(True)
            label.setFont(font)
            vbox.addWidget(label)
            hbox = QtGui.QHBoxLayout()
            for name in inputs[1:-1]:
                if not isinstance(getattr(self, name), self.NO_LABEL_INPUTS):
                    label = QtGui.QLabel(self, width=1)
                    label.setText("%s:" % parameters[name].name)
                    hbox.addWidget(label)
                input_box = getattr(self, name)
                hbox.addWidget(input_box)
                hbox.addStretch()
            vbox.addLayout(hbox)

            self.setLayout(vbox)

        directory_inputs = [self._inputs["directory_inputs"]]
        frequency_inputs = [inputs[1] for inputs in self._inputs["frequency_inputs"]]
        sweep_inputs = [item for inputs in self._inputs["sweep_inputs"]
                        for item in inputs[1:-1]]

        self._inputs = directory_inputs + frequency_inputs + sweep_inputs


class ItemSample(li.ItemSample):
    """ Subclassed Legend ItemSample that draws a better legend then the default"""
    def __init__(self, item):
        self.line = [0, 20, 30, 0]
        super().__init__(item)

    def paint(self, p, *args):
        opts = self.item.opts
        if opts.get('fillLevel') is not None and opts.get('fillBrush') is not None:
            p.setBrush(pg.mkBrush(opts['fillBrush']))
            p.setPen(pg.mkPen(None))
            p.drawPolygon(QtGui.QPolygonF(
                [QtCore.QPointF(*self.line[:2]), QtCore.QPointF(*self.line[2:]),
                 QtCore.QPointF(*self.line[1:3][::-1])]))

        if not isinstance(self.item, pg.ScatterPlotItem):
            if opts.get('shadowPen') is not None:
                p.setPen(pg.mkPen(opts['shadowPen']))
                p.drawLine(*self.line)
            pen = pg.mkPen(opts['pen'])
            pattern = np.array(pen.dashPattern())
            new_pattern = pattern
            # something is wrong with pyqtgraph scaling. This sort of fixes it
            new_pattern[::2] = pattern[::2] / 5
            pen.setDashPattern(list(new_pattern))
            p.setPen(pen)
            p.drawLine(*self.line)
        symbol = opts.get('symbol')
        if symbol is not None:
            pen = pg.mkPen(opts.get('symbolPen'))
            brush = pg.mkBrush(opts.get('symbolBrush'))
            size = opts.get('symbolSize', 0)
            p.translate(np.mean([self.line[0], self.line[2]]),
                        np.mean([self.line[1], self.line[3]]))
            drawSymbol(p, symbol, size, pen, brush)

    def width(self):
        return np.abs(self.line[0] - self.line[2]) + 10


def copy_options(opts):
    """Properly copies a dictionary of pyqtgraph options that may have QBrush or QPen
    objects as items"""
    new_opts = {}
    for key, value in opts.items():
        if isinstance(value, QtGui.QBrush):
            new_opts[key] = pg.mkBrush(value)
        elif isinstance(value, QtGui.QPen):
            new_opts[key] = pg.mkPen(value)
        else:
            new_opts[key] = copy.copy(value)
    return new_opts
