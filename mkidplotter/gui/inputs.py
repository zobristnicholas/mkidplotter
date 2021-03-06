import os
import re
import logging
import numpy as np
import pymeasure.display.inputs as inputs
from pymeasure.display.Qt import QtCore, QtGui, qt_min_version
from pymeasure.experiment import IntegerParameter, FloatParameter, BooleanParameter
                                      
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class ScientificInput(inputs.ScientificInput):
    """ Fixes small precision of pymeasure ScientificInput"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDecimals(12)
        
    def textFromValue(self, value):
        string = "{:.12g}".format(value).replace("e+", "e")
        string = re.sub(r"e(-?)0*(\d+)", r"e\1\2", string)
        return string


class FloatInput(inputs.FloatInput):
    """ Fixes small precision of pymeasure FloatInput"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDecimals(12)


class FileInput(QtGui.QWidget, inputs.Input):
    """
    File name input box connected to a :class:`FileParameter`.
    """
    def __init__(self, parameter, parent=None, **kwargs):
        self.button = QtGui.QPushButton("Find")
        self.button.clicked.connect(self.get_file)
        self.line_edit = QtGui.QLineEdit()
        self.label = QtGui.QLabel()

        if qt_min_version(5):
            super().__init__(parameter=parameter, parent=parent, **kwargs)
        else:
            QtGui.QWidget.__init__(self, parent=parent, **kwargs)
            inputs.Input.__init__(self, parameter)
        vbox = QtGui.QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        if parameter.name:
            self.label.setText(self.parameter.name + ":")
            vbox.addWidget(self.label)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.button)
        hbox.addWidget(self.line_edit)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

    def setValue(self, value):
        # QtGui.QLineEdit has a setText() method instead of setValue()
        return self.line_edit.setText(value)

    def setSuffix(self, value):
        pass

    def value(self):
        # QtGui.QLineEdit has a text() method instead of value()
        return self.line_edit.text()

    def get_file(self):
        current = os.path.dirname(self.value())
        file_name, _ = QtGui.QFileDialog.getOpenFileName(parent=self, directory=current)
        if file_name:
            file_name = os.path.abspath(file_name)  # format separators
            self.setValue(file_name)


class DirectoryInput(FileInput):
    """
    Directory name input box connected to a :class:`FileParameter`.
    """
    def get_file(self):
        current = self.value()
        file_name = QtGui.QFileDialog.getExistingDirectory(parent=self, directory=current)
        if file_name:
            file_name = os.path.abspath(file_name)  # format separators
            self.setValue(file_name)


class FloatTextEditInput(QtGui.QTextEdit, inputs.Input):
    """
    Text edit input box connected to a :class:`TextEditParameter` that assumes
    floats input with line breaks in between.
    """
    def __init__(self, parameter, parent=None, **kwargs):
        if qt_min_version(5):
            super().__init__(parameter=parameter, parent=parent, **kwargs)
        else:
            QtGui.QWidget.__init__(self, parent=parent, **kwargs)
            inputs.Input.__init__(self, parameter)

    def setValue(self, value):
        # QtGui.QTextEdit has a setPlainText() method instead of setValue()
        if isinstance(value, (list, tuple)):
            value = os.linesep.join([str(item) for item in value])
        return self.setPlainText(str(value))

    def setSuffix(self, value):
        pass

    def value(self):
        # QtGui.QTextEdit has a toPlainText() method instead of value()
        list_of_strings = self.toPlainText().strip().splitlines()
        list_of_numbers = list(map(float, list_of_strings))
        return list_of_numbers

    def sizeHint(self):
        return QtCore.QSize(0, 120)
        

class NoiseInput(QtGui.QFrame, inputs.Input):
    def __init__(self, parameter, parent=None, **kwargs):
        if parameter._length == 3:
            self._populate_off_resonance = False
        elif parameter._length == 6:
            self._populate_off_resonance = True
        else:
            raise ValueError("Vector parameter must have a length of 3 or 6 to use the "
                             "Noise Input UI")
        self._setup_ui()
        if qt_min_version(5):
            super().__init__(parameter=parameter, parent=parent, **kwargs)
        else:
            QtGui.QWidget.__init__(self, parent=parent, **kwargs)
            inputs.Input.__init__(self, parameter)
        self._layout()

    def _setup_ui(self):
        self.take_noise = inputs.BooleanInput(BooleanParameter("Take Data"))
        self.take_noise.stateChanged.connect(self.noise_state)
        self.integration = inputs.ScientificInput(FloatParameter("Integration Time", units="s"))
        self.n_int = inputs.IntegerInput(IntegerParameter("# of Integrations"))
        if self._populate_off_resonance:
            self.off_resonance = inputs.BooleanInput(BooleanParameter("Take Off Resonance Data"))
            self.off_resonance.stateChanged.connect(self.off_resonance_state)
            self.offset = inputs.ScientificInput(FloatParameter("Frequency Offset", units="MHz"))
            self.n_off = inputs.IntegerInput(IntegerParameter("# of Points"))
    
    def _layout(self):
        vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(6)
        left, top, right, bottom = vbox.getContentsMargins()
        vbox.setContentsMargins(left, top // 2, right, bottom // 2)

        label = QtGui.QLabel(self)
        label.setText(self.parameter.name +":")
        vbox.addWidget(label)
        
        vbox.addWidget(self.take_noise)
        hbox = QtGui.QHBoxLayout()
        label = QtGui.QLabel(self)
        label.setText("%s:" % self.integration.parameter.name)
        hbox.addWidget(label)
        hbox.addWidget(self.integration)
        vbox.addLayout(hbox)
        hbox = QtGui.QHBoxLayout()
        label = QtGui.QLabel(self)
        label.setText("%s:" % self.n_int.parameter.name)
        hbox.addWidget(label)
        hbox.addWidget(self.n_int)
        vbox.addLayout(hbox)

        if self._populate_off_resonance:
            vbox.addWidget(self.off_resonance)
            hbox = QtGui.QHBoxLayout()
            label = QtGui.QLabel(self)
            label.setText("%s:" % self.offset.parameter.name)
            hbox.addWidget(label)
            hbox.addWidget(self.offset)
            vbox.addLayout(hbox)

            hbox = QtGui.QHBoxLayout()
            label = QtGui.QLabel(self)
            label.setText("%s:" % self.n_off.parameter.name)
            hbox.addWidget(label)
            hbox.addWidget(self.n_off)
            vbox.addLayout(hbox)
        self.setLayout(vbox)
        self.setFrameShape(QtGui.QFrame.Panel)
        self.setFrameShadow(QtGui.QFrame.Raised)
        self.setLineWidth(3)

    def setValue(self, value):
        self.take_noise.setValue(bool(value[0]))
        self.integration.setValue(value[1])
        self.n_int.setValue(value[2])
        if self._populate_off_resonance:
            self.off_resonance.setValue(bool(value[3]))
            self.offset.setValue(value[4])
            self.n_off.setValue(value[5])

    def setSuffix(self, value):
        pass

    def value(self):
        value = [float(self.take_noise.value()), self.integration.value(),
                 self.n_int.value()]
        if self._populate_off_resonance:
            value += [float(self.off_resonance.value()), self.offset.value(),
                      self.n_off.value()]
        return value
        
    def noise_state(self):
        if self.take_noise.value():
            self.integration.setEnabled(True)
            self.n_int.setEnabled(True)
            if self._populate_off_resonance:
                self.off_resonance.setEnabled(True)
                if self.off_resonance.value():
                    self.offset.setEnabled(True)
                    self.n_off.setEnabled(True)
        else:
            self.integration.setDisabled(True)
            self.n_int.setDisabled(True)
            if self._populate_off_resonance:
                self.off_resonance.setDisabled(True)
                self.offset.setDisabled(True)
                self.n_off.setDisabled(True)
            
    def off_resonance_state(self):
        if self.off_resonance.value() and self.take_noise.value():
            self.offset.setEnabled(True)
            self.n_off.setEnabled(True)
        else:
            self.offset.setDisabled(True)
            self.n_off.setDisabled(True)


class BooleanListInput(QtGui.QFrame, inputs.Input):
    labels = []

    def __init__(self, parameter, parent=None, horizontal=False, **kwargs):
        if not self.labels:
            self.labels = [""] * parameter._length
        self.horizontal = horizontal

        self._setup_ui()
        if qt_min_version(5):
            super().__init__(parameter=parameter, parent=parent, **kwargs)
        else:
            QtGui.QWidget.__init__(self, parent=parent, **kwargs)
            inputs.Input.__init__(self, parameter)
        self._layout()

    @classmethod
    def set_labels(cls, labels, **kwargs):
        class BooleanListInputSubClass(cls):
            def __init__(self, *args, **kws):
                kws.update(kwargs)
                super().__init__(*args, **kws)
        BooleanListInputSubClass.labels = labels
        return BooleanListInputSubClass

    def _setup_ui(self):
        self.rows = []
        for label in self.labels:
            self.rows.append(inputs.BooleanInput(BooleanParameter(label)))

    def _layout(self):
        if self.horizontal:
            box = QtGui.QHBoxLayout(self)
        else:
            box = QtGui.QVBoxLayout(self)

        box.setSpacing(6)
        left, top, right, bottom = box.getContentsMargins()
        box.setContentsMargins(left, top // 2, right, bottom // 2)
        if self.parameter.name:
            label = QtGui.QLabel(self)
            label.setText("%s:" % self.parameter.name)
            box.addWidget(label)
        for row in self.rows:
            if self.horizontal:
                box.addStretch()
            box.addWidget(row)

        self.setLayout(box)
        self.setFrameShape(QtGui.QFrame.Panel)
        self.setFrameShadow(QtGui.QFrame.Raised)
        self.setLineWidth(3)

    def setValue(self, value):
        for index, row in enumerate(self.rows):
            row.setValue(value[index])

    def setSuffix(self, value):
        pass

    def value(self):
        return [row.value() for row in self.rows]


class FitInput(QtGui.QWidget, inputs.Input):
    def __init__(self, parameter, parent=None, **kwargs):
        self._setup_ui()
        if qt_min_version(5):
            super().__init__(parameter=parameter, parent=parent, **kwargs)
        else:
            QtGui.QWidget.__init__(self, parent=parent, **kwargs)
            inputs.Input.__init__(self, parameter)
        self._layout()

    def _setup_ui(self):
        self.vary = inputs.BooleanInput(BooleanParameter("vary"))
        self.guess = inputs.StringInput(FloatParameter("guess"))
        self.min = inputs.StringInput(FloatParameter("min"))
        self.max = inputs.StringInput(FloatParameter("max"))

    def _layout(self):
        width = 60
        hbox = QtGui.QHBoxLayout(self)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.addStretch()
        hbox.addWidget(self.vary)

        self.guess.setFixedWidth(width)
        hbox.addWidget(self.guess)
        label = QtGui.QLabel(self)
        label.setText("guess")
        hbox.addWidget(label)

        self.min.setFixedWidth(width)
        hbox.addWidget(self.min)
        label = QtGui.QLabel(self)
        label.setText("min")
        hbox.addWidget(label)

        self.max.setFixedWidth(width)
        hbox.addWidget(self.max)
        label = QtGui.QLabel(self)
        label.setText("max")
        hbox.addWidget(label)

    def value(self):
        try:
            guess = float(self.guess.text())
        except ValueError:
            guess = np.nan
        try:
            minimum = float(self.min.text())
        except ValueError:
            minimum = np.nan
        try:
            maximum = float(self.max.text())
        except ValueError:
            maximum = np.nan
        value = [float(self.vary.value()), guess, minimum, maximum]
        return value

    def setValue(self, value):
        self.vary.setValue(bool(value[0]))
        self.guess.setValue(str(value[1]))
        if np.isnan(value[1]):
            self.guess.clear()
        self.min.setValue(str(value[2]))
        if np.isnan(value[2]):
            self.min.clear()
        self.max.setValue(str(value[3]))
        if np.isnan(value[3]):
            self.max.clear()

    def setSuffix(self, value):
        pass


class RangeInput(QtGui.QFrame, inputs.Input):
    labels = []

    def __init__(self, parameter, parent=None, **kwargs):
        if not self.labels:
            self.labels = [""] * (parameter._length // 2)

        self._setup_ui()
        if qt_min_version(5):
            super().__init__(parameter=parameter, parent=parent, **kwargs)
        else:
            QtGui.QWidget.__init__(self, parent=parent, **kwargs)
            inputs.Input.__init__(self, parameter)
        self._layout()

    @classmethod
    def set_labels(cls, labels):
        class RangeInputSubClass(cls):
            pass

        RangeInputSubClass.labels = labels
        return RangeInputSubClass

    def _setup_ui(self):
        self.rows = []
        for label in self.labels:
            self.rows.append([inputs.FloatInput(FloatParameter("left", units="%", minimum=0, maximum=100)),
                              inputs.FloatInput(FloatParameter("right", units="%", minimum=0, maximum=100))])
            for row in self.rows:
                for input in row:
                    input.setAlignment(QtCore.Qt.AlignRight)

    def _layout(self):
        if len(self.labels) > 1:
            width = 60
            vbox = QtGui.QVBoxLayout(self)
            vbox.setSpacing(6)
            left, top, right, bottom = vbox.getContentsMargins()
            vbox.setContentsMargins(left, top // 2, right, bottom // 2)
            if self.parameter.name:
                label = QtGui.QLabel(self)
                label.setText("%s:" % self.parameter.name)
                vbox.addWidget(label)
            for index, row in enumerate(self.rows):
                hbox = QtGui.QHBoxLayout()
                try:
                    label = QtGui.QLabel(self)
                    label.setText("%s" % self.labels[index])
                    hbox.addWidget(label)
                except IndexError:
                    pass
                for input in row:
                    input.setFixedWidth(width)
                    hbox.addWidget(input)
                    label = QtGui.QLabel(self)
                    label.setText(input._parameter.name)
                    hbox.addWidget(label)
                hbox.addStretch()
                vbox.addLayout(hbox)
            self.setLayout(vbox)
            self.setFrameShape(QtGui.QFrame.Panel)
            self.setFrameShadow(QtGui.QFrame.Raised)
            self.setLineWidth(3)
        else:
            width = 60
            hbox = QtGui.QHBoxLayout(self)
            left, top, right, bottom = hbox.getContentsMargins()
            hbox.setContentsMargins(0, top // 2, 0, bottom // 2)
            label = QtGui.QLabel(self)
            label.setText("%s:" % self.parameter.name)
            hbox.addWidget(label)
            for input in self.rows[0]:
                input.setFixedWidth(width)
                hbox.addWidget(input)
                label = QtGui.QLabel(self)
                label.setText(input._parameter.name)
                hbox.addWidget(label)
            hbox.addStretch()
            self.setLayout(hbox)

    def setSuffix(self, value):
        pass

    def value(self):
        result = []
        for row in self.rows:
            for input in row:
                try:
                    result.append(float(input.value()))
                except ValueError:
                    result.append(np.nan)
        return result

    def setValue(self, value):
        for index, row in enumerate(self.rows):
            row[0].setValue(value[2 * index])
            row[1].setValue(value[2 * index + 1])
            if np.isnan(value[2 * index]):
                row[0].clear()
            if np.isnan(value[2 * index + 1]):
                row[1].clear()
