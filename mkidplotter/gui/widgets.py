import os
import copy
import logging
import numpy as np
import pyqtgraph as pg
from cycler import cycler
from pymeasure.experiment import Results
import pymeasure.display.widgets as widgets
from pymeasure.display.Qt import QtCore, QtGui
from pyqtgraph.graphicsItems.LegendItem import ItemSample
from pyqtgraph.graphicsItems.ScatterPlotItem import drawSymbol
from pymeasure.experiment import (FloatParameter, IntegerParameter, BooleanParameter,
                                  ListParameter, Parameter)
from pymeasure.display.inputs import (ScientificInput, IntegerInput, BooleanInput,
                                      ListInput, StringInput)

from mkidplotter.gui.curves import MKIDResultsCurve, NoiseResultsCurve
from mkidplotter.gui.parameters import FileParameter, DirectoryParameter
from mkidplotter.gui.inputs import FileInput, DirectoryInput

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MKIDResultsDialog(widgets.ResultsDialog):
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
        self.resize(1200, 500)

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


class MKIDBrowserWidget(widgets.BrowserWidget):
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


class MKIDPlotWidget(widgets.PlotWidget):
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
                legend_item_sample = MKIDItemSample(legend_item)
                self.legend.addItem(legend_item_sample, text)

    def _layout(self):
        vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(0)
        vbox.addWidget(self.plot_frame)
        self.setLayout(vbox)


class SweepPlotWidget(MKIDPlotWidget):
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
        self.plot.enableAutoRange(True)

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

            curve.append(MKIDResultsCurve(results, x=self.x_axes[index],
                                          y=self.y_axes[index], **cycled_args))

        return curve


class NoisePlotWidget(MKIDPlotWidget):
    """Plot widget for noise"""
    def __init__(self, *args, color_cycle=None, x_axes=None, y_axes=None, x_label=None,
                 y_label=None, legend_text=None, **kwargs):
        self.x_axes = x_axes
        self.y_axes = y_axes
        self.x_label = x_label
        self.y_label = y_label
        self.legend_text = legend_text
        self._point_size = 6
        self.line_style = {"pen": [pg.mkPen(color='w', width=4, style=QtCore.Qt.DashLine),
                                   pg.mkPen(color='w', width=4, style=QtCore.Qt.DotLine),
                                   pg.mkPen(color='w', width=4,
                                            style=QtCore.Qt.DashDotLine),
                                   pg.mkPen(color='w', width=4,
                                            style=QtCore.Qt.DashDotDotLine)],
                           "shadowPen": [pg.mkPen(color='k', width=4),
                                         pg.mkPen(color='k', width=4),
                                         pg.mkPen(color='k', width=4),
                                         pg.mkPen(color='k', width=4)]}
        n = int(np.ceil(len(self.x_axes) / len(self.line_style["pen"])))
        self.style_cycle = (cycler(**self.line_style) * n)[:len(self.x_axes)]
        self.cycler = (color_cycle * self.style_cycle)()
        super().__init__(*args, **kwargs)
        self.plot.setLogMode(True, True)

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
                cycled_args['pen'] = pg.mkPen(color=cycled_args['color'], width=4)
            if 'antialias' not in cycled_args:
                cycled_args['antialias'] = False
            curve.append(NoiseResultsCurve(results, x=self.x_axes[index],
                                           y=self.y_axes[index], **cycled_args))

        return curve


class InputsWidget(widgets.InputsWidget):
    """Fixes set_parameters bug in pymeasure (would always set to default if existed)"""
    def set_parameters(self, parameter_objects):
        for name in self._inputs:
            parameter = parameter_objects[name]
            element = getattr(self, name)
            element._parameter = parameter
            element.setValue(parameter.value)
            if hasattr(parameter, 'units') and parameter.units:
                element.setSuffix(" %s" % parameter.units)


class MKIDInputsWidget(InputsWidget):
    def _setup_ui(self):
        parameter_objects = self._procedure.parameter_objects()
        self._make_input(self._inputs[0], parameter_objects[self._inputs[0]])
        for inputs in self._inputs[1:]:
            for name in inputs[1:-1]:
                self._make_input(name, parameter_objects[name])

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

        elif isinstance(parameter, Parameter):
            element = StringInput(parameter)

        else:
            raise ValueError("unrecognized parameter type: {}"
                             .format(type(parameter)))

        setattr(self, name, element)

    def _layout(self):
        parameters = self._procedure.parameter_objects()
        vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(6)

        label = QtGui.QLabel()
        label.setText(parameters[self._inputs[0]].name)
        font = QtGui.QFont()
        font.setBold(True)
        label.setFont(font)
        vbox.addWidget(label)
        vbox.addWidget(getattr(self, self._inputs[0]))

        for inputs in self._inputs[1:]:
            label = QtGui.QLabel()
            label.setText(inputs[-1])
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

        self._inputs = [self._inputs[0]] + \
                       [item for inputs in self._inputs[1:] for item in inputs[1:-1]]


class MKIDItemSample(ItemSample):
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