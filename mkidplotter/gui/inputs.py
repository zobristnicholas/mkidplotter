import os
import logging
from pymeasure.display.inputs import Input
from pymeasure.display.Qt import QtCore, QtGui, qt_min_version
from pymeasure.experiment import IntegerParameter, FloatParameter, BooleanParameter
from pymeasure.display.inputs import (ScientificInput, IntegerInput, BooleanInput)
                                      
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class FileInput(QtGui.QWidget, Input):
    """
    File name input box connected to a :class:`FileParameter`.
    """
    def __init__(self, parameter, parent=None, **kwargs):
        self.button = QtGui.QPushButton("Find")
        self.button.clicked.connect(self.get_file)
        self.line_edit = QtGui.QLineEdit()

        if qt_min_version(5):
            super().__init__(parameter=parameter, parent=parent, **kwargs)
        else:
            QtGui.QWidget.__init__(self, parent=parent, **kwargs)
            Input.__init__(self, parameter)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.button)
        hbox.addWidget(self.line_edit)
        self.setLayout(hbox)

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
        file_name = QtGui.QFileDialog.getOpenFileName(parent=self, directory=current)
        if file_name:
            file_name = os.path.abspath(file_name)  # format seperators
            self.setValue(file_name)


class DirectoryInput(FileInput):
    """
    Directory name input box connected to a :class:`FileParameter`.
    """
    def get_file(self):
        current = self.value()
        file_name = QtGui.QFileDialog.getExistingDirectory(parent=self, directory=current)
        if file_name:
            file_name = os.path.abspath(file_name)  # format seperators
            self.setValue(file_name)


class FloatTextEditInput(QtGui.QTextEdit, Input):
    """
    Text edit input box connected to a :class:`TextEditParameter` that assumes
    floats input with line breaks in between.
    """
    def __init__(self, parameter, parent=None, **kwargs):
        if qt_min_version(5):
            super().__init__(parameter=parameter, parent=parent, **kwargs)
        else:
            QtGui.QWidget.__init__(self, parent=parent, **kwargs)
            Input.__init__(self, parameter)

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
        

class NoiseInput(QtGui.QFrame, Input):
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
            Input.__init__(self, parameter)
        self._layout()
        
    def _setup_ui(self):
        self.take_noise = BooleanInput(BooleanParameter("Take Data"))
        self.take_noise.stateChanged.connect(self.noise_state)
        self.integration = ScientificInput(FloatParameter("Integration Time", units="s"))
        self.n_int = IntegerInput(IntegerParameter("# of Integrations"))
        if self._populate_off_resonance:
            self.off_resonance = BooleanInput(BooleanParameter("Take Off Resonance Data"))
            self.off_resonance.stateChanged.connect(self.off_resonance_state)
            self.offset = ScientificInput(FloatParameter("Frequency Offset", units="MHz"))
            self.n_off = IntegerInput(IntegerParameter("# of Points"))
    
    def _layout(self):
        vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(6)
        
        vbox.addWidget(self.take_noise)
        label = QtGui.QLabel(self)
        label.setText("%s:" % self.integration.parameter.name)
        vbox.addWidget(label)
        vbox.addWidget(self.integration)
        label = QtGui.QLabel(self)
        label.setText("%s:" % self.n_int.parameter.name)
        vbox.addWidget(label)
        vbox.addWidget(self.n_int)
        if self._populate_off_resonance:
            vbox.addWidget(self.off_resonance)
            label = QtGui.QLabel(self)
            label.setText("%s:" % self.offset.parameter.name)
            vbox.addWidget(label)
            vbox.addWidget(self.offset)
            label = QtGui.QLabel(self)
            label.setText("%s:" % self.n_off.parameter.name)
            vbox.addWidget(label)
            vbox.addWidget(self.n_off)
        
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