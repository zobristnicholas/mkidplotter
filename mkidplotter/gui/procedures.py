import os
import logging
import tempfile
import numpy as np
from time import sleep
from datetime import datetime
from pymeasure.experiment import Results
from pymeasure.experiment import Procedure
from pymeasure.experiment import (IntegerParameter, FloatParameter, BooleanParameter,
                                  Parameter)

from mkidplotter.gui.parameters import DirectoryParameter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MKIDProcedure(Procedure):
    def __init__(self, *args, **kwargs):
        self._parameter_names()
        self._file_name = None
        super().__init__(*args, **kwargs)

    def file_name(self, time=None):
        """Returns a unique name for saving the file depending on it's mandatory
        parameters"""
        raise NotImplementedError

    def emit_results(self, dictionary):
        """Wrapper for the emit function so that not all of the dictionary keys need to
        be defined in order to emit the data. Replaces empty fields with np.nan"""
        # collect the data into a numpy structured array
        size = max([value.size if hasattr(value, "shape") and value.shape
                    else np.array([value]).size for value in dictionary.values()])
        records = np.empty((size,), dtype=[(key, float) for key in self.DATA_COLUMNS])
        records.fill(np.nan)
        for key, value in dictionary.items():
            try:
                records[key][:value.size] = value
            except AttributeError:
                records[key][:np.array(value).size] = value

        for key in self.DATA_COLUMNS:
            if key not in dictionary.keys():
                records[key] = np.nan

        for index in range(size):
            self.emit('results', records[index])

    def _parameter_names(self):
        """Provides an ordered list of parameter names before base class init"""
        parameters = []
        for item in dir(self):
            if item != "file_name":
                attribute = getattr(self, item)
                if isinstance(attribute, Parameter):
                    parameters.append(item)
        self.parameter_names = parameters


class SweepBaseProcedure(Procedure):
    """Procedure class for holding the mandatory sweep input arguments"""
    ordering = ["directory",
                ["attenuation", "start_atten", "stop_atten", "n_atten"],
                ["field", "start_field", "stop_field", "n_field"],
                ["temperature", "start_temp", "stop_temp", "n_temp"]]

    directory = DirectoryParameter("Data Directory", default="/")

    start_atten = FloatParameter("Start", units="dB", default=70)
    stop_atten = FloatParameter("Stop", units="dB", default=70)
    n_atten = IntegerParameter("# of Points", default=1, minimum=1, maximum=1000)

    start_field = FloatParameter("Start", units="V", default=0)
    stop_field = FloatParameter("Stop", units="V", default=0)
    n_field = IntegerParameter("# of Points", default=1, minimum=1, maximum=1000)

    start_temp = FloatParameter("Start", units="mK", default=100)
    stop_temp = FloatParameter("Stop", units="mK", default=100)
    n_temp = IntegerParameter("# of Points", default=1, minimum=1, maximum=1000)


class SweepProcedure(MKIDProcedure):
    """Procedure class to subclass when making a custom mkid sweep procedure"""
    # mandatory parameters
    directory = DirectoryParameter("Data Directory")
    attenuation = FloatParameter("DAC Attenuation", units="dB")
    field = FloatParameter("Auxiliary Field", units="V")
    temperature = FloatParameter("Temperature", units="mK")

    def file_name(self, time=None):
        """Returns a unique name for saving the file depending on it's parameters"""
        base = ("sweep_{:.1f}_{:.1f}_{:.1f}_%y%m%d_%H%M%S"
                .format(self.attenuation, self.field, self.temperature).replace(".", "p"))
        if time is None:
            base = datetime.now().strftime(base)
        else:
            base = time.strftime(base)
        return base + ".npz"
