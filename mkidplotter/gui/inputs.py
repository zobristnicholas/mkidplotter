import os
import logging
import numpy as np
from pymeasure.display.Qt import QtCore, QtGui, qt_min_version
from pymeasure.display.inputs import Input

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
        file_name = QtGui.QFileDialog.getOpenFileName(parent=self)
        self.setValue(file_name)


class DirectoryInput(FileInput):
    """
    Directory name input box connected to a :class:`FileParameter`.
    """
    def get_file(self):
        file_name = QtGui.QFileDialog.getExistingDirectory(parent=self)
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