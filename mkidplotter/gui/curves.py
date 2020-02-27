import logging
import numpy as np
import pyqtgraph as pg

from pymeasure.display.curves import ResultsCurve

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MKIDResultsCurve(ResultsCurve):
    """Extension of the pymeasure ResultsCurve class"""

    def __init__(self, results, x, y, xerr=None, yerr=None, force_reload=False, **kwargs):
        super().__init__(results, x, y, xerr=xerr, yerr=yerr, force_reload=force_reload, **kwargs)
        self.symbolBrush = kwargs.get('symbolBrush', None)
        color = kwargs.get('color')
        if self.pen is not None and color is not None:
            self.pen.setColor(pg.mkColor(color))
        if self.symbolBrush is not None and color is not None:
            self.symbolBrush.setColor(pg.mkColor(color))

    def update(self):
        """Updates the data by polling the results"""
        if self.force_reload:
            self.results.reload()
        data = self.results.data  # get the current snapshot

        # Set x-y data
        if len(data[self.x]) == len(data[self.y]):
            self.setData(data[self.x], data[self.y])

            # Set error bars if enabled at construction
            if hasattr(self, '_errorBars'):
                self._errorBars.setOpts(
                    x=data[self.x],
                    y=data[self.y],
                    top=data[self.yerr],
                    bottom=data[self.yerr],
                    left=data[self.xerr],
                    right=data[self.yerr],
                    beam=max(data[self.xerr], data[self.yerr])
                )


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
        if len(x_data) > 1 and len(x_data) == len(y_data):
            dx = x_data[1] - x_data[0]
            x_data.append(x_data[-1] + dx)
            x_data = [x - dx / 2 for x in x_data]
            self.setData(x_data, y_data, stepMode=True)

        elif len(x_data) == len(y_data):
            self.setData(x_data, y_data, stepMode=False)
