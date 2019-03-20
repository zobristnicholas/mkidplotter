import numpy as np
from pymeasure.display.Qt import QtCore


class Indicator(QtCore.QObject):
    """ Encapsulates the information for an experiment indicator
    with information about the name, and units if supplied.
    :var value: The value of the parameter
    :param name: The parameter name
    :param default: The default value
    :param ui_class: A Qt class to use for the UI of this parameter
    """
    updated = QtCore.QSignal()

    def __init__(self, name, default=None, ui_class=None):
        super().__init__()
        self.name = name
        self._value = default
        self.default = default
        self.ui_class = ui_class

    @property
    def value(self):
        if self.is_set():
            return self._value
        else:
            raise ValueError("Indicator value is not set")

    @value.setter
    def value(self, value):
        self._value = value
        self.updated.emit()

    def is_set(self):
        """ Returns True if the Parameter value is set
        """
        return self._value is not None

    def __str__(self):
        return str(self._value) if self.is_set() else ''

    def __repr__(self):
        return "<%s(name=%s,value=%s,default=%s)>" % (self.__class__.__name__, self.name, self._value, self.default)


class IntegerIndicator(Indicator):
    """ :class:`Indicator` sub-class that uses the integer type to store the value.

        :var value: The integer value of the parameter

        :param name: The parameter name
        :param units: The units of measure for the parameter
        :param default: The default integer value
        :param ui_class: A Qt class to use for the UI of this parameter
        """
    def __init__(self, name, units=None, **kwargs):
        super().__init__(name, **kwargs)
        self.units = units

    @property
    def value(self):
        return super().value

    @value.setter
    def value(self, value):
        try:
            self._value = int(value)
            self.updated.emit()
        except ValueError:
            raise ValueError("IntegerIndicator given non-integer value of type '%s'" % type(value))

    def __str__(self):
        if not self.is_set():
            return ''
        result = "%d" % self._value
        if self.units:
            result += " %s" % self.units
        return result

    def __repr__(self):
        return "<%s(name=%s,value=%s,units=%s,default=%s)>" % (
            self.__class__.__name__, self.name, self._value, self.units, self.default)


class FloatIndicator(IntegerIndicator):
    """ :class:`Indicator` sub-class that uses the float type to store the value.

        :var value: The integer value of the parameter

        :param name: The parameter name
        :param precision: The number of digits to display
        :param units: The units of measure for the parameter
        :param default: The default integer value
        :param ui_class: A Qt class to use for the UI of this parameter
        """
    def __init__(self, name, precision=3, **kwargs):
        super().__init__(name, **kwargs)
        self.precision = precision

    @property
    def value(self):
        return super().value

    @value.setter
    def value(self, value):
        try:
            self._value = float(value)
            self.updated.emit()
        except ValueError:
            raise ValueError("FloatIndicator given non-float value of type '%s'" % type(value))

    def __str__(self):
        if not self.is_set():
            return ''
        value = self._value
        n_before = len(str(value).split('.')[0])
        if n_before < self.precision:
            result = ("{:." + str(int(self.precision - n_before)) + "f}").format(value)
        else:
            result = ("{:." + str(int(self.precision) - 1) + "E}").format(value)
        if self.units:
            result += " %s" % self.units
        return result


class BooleanIndicator(Indicator):
    """ :class:`Indicator` sub-class that uses the boolean type to store the value.

    :var value: The boolean value of the parameter

    :param name: The parameter name
    :param default: The default boolean value
    :param ui_class: A Qt class to use for the UI of this parameter
    """
    @property
    def value(self):
        return super().value

    @value.setter
    def value(self, value):
        try:
            self._value = bool(value)
            self.updated.emit()
        except ValueError:
            raise ValueError("BooleanIndicator given non-boolean value of type '%s'" % type(value))
