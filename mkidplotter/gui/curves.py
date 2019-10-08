import logging
import numpy as np
import pyqtgraph as pg

from pymeasure.display.curves import ResultsCurve

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MKIDResultsCurve(ResultsCurve):
    """Extension of the pymeasure ResultsCurve class"""

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


class NoiseResultsCurve(MKIDResultsCurve):
    """Extension of the pymeasure ResultsCurve class"""

    def update(self):
        """Updates the data by polling the results"""
        if self.force_reload:
            self.results.reload()
        data = self.results.data  # get the current snapshot        

        # Set x-y data
        x_data = data[self.x].copy()
        y_data = data[self.y]
        if len(x_data) > 1:
            dx = x_data[1] - x_data[0]
            x_data.append(x_data[-1] + dx)
            x_data = [x - dx / 2 for x in x_data]
            self.setData(x_data, y_data, stepMode=True)

        else:
            self.setData(x_data, y_data, stepMode=False)
