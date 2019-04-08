import re
import logging
from pymeasure.display.Qt import QtGui, qt_min_version

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Display(object):
    """
    Mix-in class that connects a :mod:`Indicator <.indicators>` object to a GUI
    display box.

    :param indicator: The indicator to connect to this input box.
    :attr indicator: Read-only property to access the associated parameter.
    """
    def __init__(self, indicator, **kwargs):
        super().__init__(**kwargs)
        self._indicator = None
        self.set_indicator(indicator)

    def set_indicator(self, indicator):
        """
        Connects a new indicator to the input box, and initializes the box
        value.

        :param indicator: indicator to connect.
        """
        self._indicator = indicator

        if indicator.default is not None:
            self.setValue(indicator.default)

        if hasattr(indicator, 'units') and indicator.units:
            self.setSuffix(" %s" % indicator.units)
        indicator.updated.connect(self.update_indicator)

    @property
    def indicator(self):
        """
        The connected indicator object. Read-only property; see
        :meth:`set_indicator`.
        """
        return self._indicator

    def update_indicator(self):
        """Must be overridden by subclass."""
        raise NotImplementedError


class StringDisplay(QtGui.QLineEdit, Display):
    """
    String display box connected to a :class:`Indicator`. Indicator subclasses
    that can be displayed as strings may use this input, but non-string indicators
    should use more specialised display classes.
    """
    def __init__(self, indicator, parent=None, **kwargs):
        if qt_min_version(5):
            super().__init__(indicator=indicator, parent=parent, **kwargs)
        else:
            QtGui.QLineEdit.__init__(self, parent=parent, **kwargs)
            Display.__init__(self, indicator)
        self.setReadOnly(True)

    def update_indicator(self):
        super().setText(str(self.indicator))

    def value(self):
        # QtGui.QLineEdit has a text() method instead of value()
        return super().text()
        
        
class FloatDisplay(QtGui.QDoubleSpinBox, Display):
    """
    Spin input box for floating-point values, connected to a
    :class:`FloatParameter`.
    .. seealso::
        Class :class:`~.ScientificInput`
            For inputs in scientific notation.
    """
    def __init__(self, indicator, parent=None, **kwargs):
        if qt_min_version(5):
            super().__init__(indicator=indicator, parent=parent, **kwargs)
        else:
            QtGui.QDoubleSpinBox.__init__(self, parent=parent, **kwargs)
            Display.__init__(self, indicator)
        self.setButtonSymbols(QtGui.QAbstractSpinBox.NoButtons)
        self.setDecimals(12)
        self.setMaximum(10**indicator.precision)
        self.setMinimum(-10**indicator.precision)
        
    def update_indicator(self):
        super().setValue(self.indicator.value)
        
    def textFromValue(self, value):
        string = "{:.12g}".format(value).replace("e+", "e")
        string = re.sub("e(-?)0*(\d+)", r"e\1\2", string)
        return string

