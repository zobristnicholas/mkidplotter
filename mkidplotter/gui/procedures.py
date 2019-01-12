import logging
import numpy as np
from datetime import datetime
from pymeasure.experiment import Procedure
from pymeasure.experiment import (IntegerParameter, FloatParameter, Parameter)

from mkidplotter.gui.parameters import DirectoryParameter, TextEditParameter

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SweepGUIProcedure(Procedure):
    """Procedure class for holding the mandatory sweep input arguments"""
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
    ordering = {"directory_inputs": "directory",
                "frequency_inputs": [["frequency1", "frequencies1"],
                                     ["span1", "spans1"],
                                     ["frequency2", "frequencies2"],
                                     ["span2", "spans2"]],
                "sweep_inputs": [
                    ["attenuation", "start_atten", "stop_atten", "n_atten"],
                    ["field", "start_field", "stop_field", "n_field"],
                    ["temperature", "start_temp", "stop_temp", "n_temp"]]}

    directory = DirectoryParameter("Data Directory",
                                   default=r"C:\Documents and Settings\kids\nzobrist")

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
    def __init__(self, *args, **kwargs):
        self._parameter_names()
        self._file_name = None
        self.metadata = {"parameters": {}}
        super().__init__(*args, **kwargs)

    def file_name(self, prefix="", numbers=(), time=None):
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
        base += ".npz"
        self._file_name = base
        return self._file_name

    def send(self, topic, record):
        """
        Sends data to the Gui. It is a layer of logic over the built in emit() so that not
        all of the parameters need to be defined in order to emit the data. Replaces empty
        fields with np.nan. This function will not error if no gui is attached to the
        procedure.
        
        emit() was not simply overloaded since it is monkey patched by the pymeasure
        worker class.
        """
        if topic == "results":
            # collect the data into a numpy structured array
            size = max([value.size if hasattr(value, "shape") and value.shape
                        else np.array([value]).size for value in record.values()])
            records = np.empty((size,), dtype=[(key, float) for key in self.DATA_COLUMNS])
            records.fill(np.nan)
            for key, value in record.items():
                try:
                    records[key][:value.size] = value
                except AttributeError:
                    records[key][:np.array(value).size] = value
    
            for key in self.DATA_COLUMNS:
                if key not in record.keys():
                    records[key] = np.nan
            for index in range(size):
                try:
                    # log.warning("sending {}".format(records[index]))
                    self.emit(topic, records[index])
                except NotImplementedError:
                    pass
        else:
            try:
                self.emit(topic, record)
            except NotImplementedError:
                pass
            
    def stop(self):
        """
        Checks if the procedure should stop. It is a layer of logic over the built in
        should_stop() so that the function will not error if no gui is attached to the
        procedure.
        
        should_stop() was not simply overloaded since it is monkey patched by the
        pymeasure worker class.
        """
        try:
            return self.should_stop()
        except NotImplementedError:
            return False
        
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
                log.info("Parameter {}: {}".format(name, value))
                self.metadata['parameters'][name] = value
        # save some data from the current state of the daq sensors
        if callable(getattr(self.daq, "system_state", None)):
            self.metadata.update(self.daq.system_state())
        # save the file name
        self.metadata["file_name"] = self.file_name()
        
    @classmethod
    def connect_daq(cls, daq):
        """Connects all current and future instances of the procedure class to the daq"""
        cls.daq = daq


class SweepBaseProcedure(MKIDProcedure):
    """Procedure class to subclass when making a custom MKID sweep procedure"""
    # mandatory parameters
    directory = DirectoryParameter("Data Directory")
    attenuation = FloatParameter("DAC Attenuation", units="dB")
    field = FloatParameter("Auxiliary Field", units="V")
    temperature = FloatParameter("Temperature", units="mK")