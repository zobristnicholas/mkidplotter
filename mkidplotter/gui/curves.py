import logging
import warnings
import numpy as np
import pyqtgraph as pg

from pymeasure.display.Qt import QtCore
from pymeasure.display.curves import ResultsCurve

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MKIDResultsCurve(ResultsCurve):
    """Extension of the pymeasure ResultsCurve class
    """

    def __init__(self, results, x, y, xerr=None, yerr=None,
                 force_reload=False, **kwargs):
        super().__init__(results, x, y, xerr=xerr, yerr=yerr, force_reload=force_reload,
                         **kwargs)
        self.symbolBrush = kwargs.get('symbolBrush', None)
        color = kwargs.get('color')
        if self.pen is not None and color is not None:
            self.pen.setColor(pg.mkColor(color))
        if self.symbolBrush is not None and color is not None:
            self.symbolBrush.setColor(pg.mkColor(color))
