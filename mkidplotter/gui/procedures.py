import os
import logging
import numpy as np
from datetime import datetime
from pymeasure.experiment import Procedure
from pymeasure.experiment import (IntegerParameter, FloatParameter, Parameter, VectorParameter)

from mkidplotter.gui.inputs import FitInput
from mkidplotter.gui.indicators import Indicator
from mkidplotter.gui.parameters import DirectoryParameter, FileParameter, TextEditParameter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SweepGUIProcedure1(Procedure):
    """Procedure class for holding the mandatory sweep input arguments"""
    TOOLTIPS = {}
    ordering = {"directory_inputs": "directory",
                "frequency_inputs": [["frequency", "frequencies"],
                                     ["span", "spans"]],
                "sweep_inputs": [
                    ["attenuation", "start_atten", "stop_atten", "n_atten"],
                    ["field", "start_field", "stop_field", "n_field"],
                    ["temperature", "start_temp", "stop_temp", "n_temp"]]}

    directory = DirectoryParameter("Data Directory", default="/")

    frequencies = TextEditParameter("F List [GHz]", default="4.0\n5.0")
    spans = TextEditParameter("Span List [MHz]", default="2.0")

    start_atten = FloatParameter("Start", units="dB", default=70)
    stop_atten = FloatParameter("Stop", units="dB", default=70)
    n_atten = IntegerParameter("# of Points", default=1, minimum=1, maximum=1000)

    start_field = FloatParameter("Start", units="V", default=0)
    stop_field = FloatParameter("Stop", units="V", default=0)
    n_field = IntegerParameter("# of Points", default=1, minimum=1, maximum=1000)

    start_temp = FloatParameter("Start", units="mK", default=100)
    stop_temp = FloatParameter("Stop", units="mK", default=100)
    n_temp = IntegerParameter("# of Points", default=1, minimum=1, maximum=1000)


class SweepGUIProcedure2(Procedure):
    """Procedure class for holding the mandatory sweep input arguments"""
    TOOLTIPS = {}
    ordering = {"directory_inputs": "directory",
                "frequency_inputs": [["frequency1", "frequencies1"],
                                     ["span1", "spans1"],
                                     ["frequency2", "frequencies2"],
                                     ["span2", "spans2"]],
                "sweep_inputs": [
                    ["attenuation", "start_atten", "stop_atten", "n_atten"],
                    ["field", "start_field", "stop_field", "n_field"],
                    ["temperature", "start_temp", "stop_temp", "n_temp"]]}

    directory = DirectoryParameter("Data Directory")

    frequencies1 = TextEditParameter("F1 List [GHz]", default=[4.0, 5.0])
    spans1 = TextEditParameter("Span1 List [MHz]", default=[2.0])

    frequencies2 = TextEditParameter("F2 List [GHz]", default=[6.0])
    spans2 = TextEditParameter("Span2 List [MHz]", default=[2.0])

    start_atten = FloatParameter("Start", units="dB", default=70)
    stop_atten = FloatParameter("Stop", units="dB", default=70)
    n_atten = IntegerParameter("# of Points", default=1, minimum=1, maximum=1000)

    start_field = FloatParameter("Start", units="V", default=0)
    stop_field = FloatParameter("Stop", units="V", default=0)
    n_field = IntegerParameter("# of Points", default=1, minimum=1, maximum=1000)

    start_temp = FloatParameter("Start", units="mK", default=100)
    stop_temp = FloatParameter("Stop", units="mK", default=100)
    n_temp = IntegerParameter("# of Points", default=1, minimum=1, maximum=1000)


class MKIDProcedure(Procedure):
    # optional daq from analogreadout connect to the class with connect_daq()
    daq = None
    TOOLTIPS = {}
    directory = None

    def __init__(self, *args, **kwargs):
        self._parameter_names()
        self._file_name = None
        self.metadata = {"parameters": {}}
        super().__init__(*args, **kwargs)
        self.indicator_objects = {}
        self._update_indicators()

    def _update_indicators(self):
        """ Collects all the Indicator objects for the procedure and stores
        them in a meta dictionary so that they are accessible.
        """
        for item in dir(self):
            indicator = getattr(self, item)
            if isinstance(indicator, Indicator):
                self.indicator_objects[item] = indicator

    def file_name(self, prefix="", numbers=(), time=None, ext="npz"):
        """Returns a unique name for saving the file"""
        if self._file_name is not None:
            return self._file_name

        if not isinstance(numbers, (list, tuple)):
            numbers = [numbers]
        if prefix:
            base = prefix + "_"
        else:
            base = ""
        if numbers:
            for number in numbers:
                base += "{:d}_".format(number)
        if time is None:
            time = datetime.now()
        if isinstance(time, datetime):
            base += "%y%m%d_%H%M%S"
            base = time.strftime(base)
        else:
            base += time
        base += "." + ext
        self._file_name = base
        return self._file_name

    def file_name_parts(self, file_name=None):
        """Returns the arguments used to create the file_name in file_name()."""
        if file_name is None:
            file_name = self.file_name()
        file_name = file_name.split("_")
        time = "_".join(file_name[-2:]).split(".")[0]
        numbers = []
        names = []
        for number in file_name[:-2]:
            try:
                numbers.append(int(number))
            except ValueError:
                names.append(number)
        name = "_".join(names)
        return {"prefix": name, "numbers": numbers, "time": time}

    def emit(self, topic, record, clear=False):
        """Stops emit() from being required to be patched by a worker."""
        pass

    def should_stop(self):
        """Stops should_stop() from being required to be patched by a worker."""
        pass

    def refresh_plot(self):
        """Stops refresh_plot() from being required to be patched by a worker."""
        pass

    def _parameter_names(self):
        """Provides an ordered list of parameter names before base class init."""
        parameters = []
        for item in dir(self):
            if item != "file_name":
                attribute = getattr(self, item)
                if isinstance(attribute, Parameter):
                    parameters.append(item)
        self.parameter_names = parameters
        
    def update_metadata(self):
        """Saves information about the process to the metadata dictionary."""
        # save current parameters
        for name in dir(self):
            if name in self._parameters.keys():
                value = getattr(self, name)
                log.debug("Parameter {}: {}".format(name, value))
                self.metadata['parameters'][name] = value
        # save some data from the current state of the daq sensors
        if callable(getattr(self.daq, "system_state", None)):
            self.metadata.update(self.daq.system_state())
        # save the file name
        self.metadata["file_name"] = self.file_name()
        
    @classmethod
    def connect_daq(cls, daq):
        """Connects all current and future instances of the procedure class to the DAQ."""
        cls.daq = daq
    
    @classmethod    
    def close(cls):
        """Close the DAQ resource."""
        if cls.daq is not None and callable(cls.daq.close):
            cls.daq.close()
            
    def setup_procedure_log(self, name='temperature',
                            file_name='temperature.log', filter_=None):
        """Set up a log that saves to a file following the procedure directory.
        All filters previously in the log are removed if filter is not None."""
        if self.directory is None:
            raise IOError("Cannot setup a procedure log if no directory "
                          "parameter is provided.")

        # Get the handler for the file log.
        logger = logging.getLogger(name)  # get the logger
        file_path = os.path.join(self.directory, file_name)
        for h in logger.handlers:
            is_current_handler = (isinstance(h, logging.FileHandler) and
                                  h.baseFilename == os.path.abspath(file_path))
            if is_current_handler:
                handler = h  # get the handler for this filename
                break
        else:
            # create the handler if it hasn't been made yet
            handler = logging.FileHandler(file_path, encoding='utf-8',
                                          mode='a')

        # set the formatting string for this log file
        handler.setFormatter(
            logging.Formatter('%(asctime)s : %(message)s',
                              datefmt='%Y-%m-%d %I:%M:%S %p'))

        # filter log messages if requested
        handler.filters = []  # clear all filters
        if filter_ is not None:
            if isinstance(filter_, str):
                filter_ = [filter_]
            for f in filter_:
                handler.addFilter(lambda record: record.name != f)
        logger.addHandler(handler)


class SweepBaseProcedure(MKIDProcedure):
    """Procedure class to subclass when making a custom MKID sweep procedure."""
    # mandatory parameters
    directory = DirectoryParameter("Data Directory")
    attenuation = FloatParameter("DAC Attenuation", units="dB")
    field = FloatParameter("Auxiliary Field", units="V")
    temperature = FloatParameter("Temperature", units="mK")


class Meta(type):
    def __new__(mcs, name, bases, dct):
        cls = super().__new__(mcs, name, bases, dct)
        for param in cls.FIT_PARAMETERS:
            setattr(cls, param, VectorParameter(param, length=4, ui_class=FitInput,
                                                default=[1, np.nan, np.nan, np.nan]))
        return cls


class FitProcedure(MKIDProcedure, metaclass=Meta):
    """Procedure class to subclass when making a custom Fit procedure."""
    # mandatory parameters
    directory = DirectoryParameter("Output Directory")
    sweep_file = FileParameter("Sweep File")
    config_file = None
    fitted_resonators = {}
    clear_fits = False
    FIT_PARAMETERS = []
    DERIVED_PARAMETERS = []
    CHANNELS = []

    def file_name(self, prefix="", numbers=(), time=None, ext="yaml"):
        """Returns a unique name for saving the file that uses the sweep file suffix."""
        if self._file_name is not None:
            return self._file_name
        parts = self.file_name_parts(file_name=os.path.basename(self.sweep_file))
        if not prefix:
            prefix = parts['prefix']
        if not numbers:
            numbers = parts['numbers']
        if time is None:
            time = parts['time']
        numbers = list(numbers)
        numbers.insert(0, 0)  # add a number to differentiate different fits
        name = super().file_name(prefix=prefix, numbers=numbers, time=time, ext=ext)
        while os.path.isfile(os.path.join(self.directory, name)):
            numbers[0] += 1
            self._file_name = None  # reset persistent file name so super() call recalculates the name
            name = super().file_name(prefix=prefix, numbers=numbers, time=time, ext=ext)
        return name

    def _parameter_names(self):
        """
        Provides an ordered list of parameter names before base class init.
        Overriding base class to allow for FIT_PARAMETERS attribute to specify
        the parameter order."""
        parameters = []
        parameters += self.FIT_PARAMETERS
        for item in dir(self):
            if item != "file_name":
                attribute = getattr(self, item)
                if isinstance(attribute, Parameter) and item not in parameters:
                    parameters.append(item)
        self.parameter_names = parameters
