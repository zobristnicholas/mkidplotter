import logging
import numpy as np
import pandas as pd
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
        logic = np.logical_not(pd.isnull(data[self.x]))
        data = data[logic].reset_index()
        x_data = data[self.x]
        y_data = data[self.y]
        if x_data.size > 1:
            dx = x_data[1] - x_data[0]
            last_point = pd.DataFrame([x_data[x_data.index[-1]] + dx], columns=[self.x])
            x_data = pd.DataFrame(x_data, columns=[self.x])
            x_data = x_data.append(last_point, ignore_index=True) - dx / 2
            x_data = x_data[self.x]
            self.setData(x_data, y_data, stepMode=True)
        else:
            self.setData(x_data, y_data, stepMode=False)
