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

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MKIDProcedure(Procedure):
    def __init__(self, *args, **kwargs):
        self._parameter_names()
        self._file_name = None
        super().__init__(*args, **kwargs)

    def file_name(self, time=None):
        """Returns a unique name for saving the file depending on it's manditory
        parameters"""
        raise NotImplementedError

    def emit_results(self, dictionary):
        """Wrapper for the emit function so that not all of the dictionary keys need to
        be defined in order to emit the data. Replaces empty fields with np.nan"""
        for key in self.DATA_COLUMNS:
            if key not in dictionary.keys():
                dictionary.update({key: np.nan})
        self.emit('results', dictionary)

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

    directory = Parameter("Data Directory", default="/Users/nicholaszobrist/Desktop/test")

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
    directory = Parameter("Data Directory")
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


class TestSweep(SweepProcedure):
    frequency = FloatParameter("Center Frequency", units="GHz", default=4.0)
    span = FloatParameter("Span", units="MHz", default=2)
    take_noise = BooleanParameter("Take Noise Data", default=True)
    n_points = IntegerParameter("Number of Points", default=500)

    DATA_COLUMNS = ['Index', 'I [V]', 'Q [V]', 'I2 [V]', 'Q2 [V]', "bias I", "bias Q"]
    # 'PSD [V² / Hz]', 'frequency [Hz]']

    def startup(self):
        pass

    def execute(self):
        log.info("Measuring the loop with %d points", self.n_points)
        loop_x = np.zeros(self.n_points)
        loop_y = np.zeros(self.n_points)
        indices = np.arange(self.n_points)

        for i in indices:
            self.emit('progress', i / self.n_points * 100)
            loop_x[i] = 70 / self.attenuation * np.cos(2 * np.pi * i /
                                                       (self.n_points - 1))
            loop_y[i] = 70 / self.attenuation * np.sin(2 * np.pi * i /
                                                       (self.n_points - 1))
            data = {"Index": i,
                    "I [V]": loop_x[i],
                    "Q [V]": loop_y[i],
                    "I2 [V]": loop_x[i],
                    "Q2 [V]": 2 * loop_y[i]}
            self.emit_results(data)
            log.debug("Emitting results: %s" % data)
            sleep(.005)
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break
        self.emit_results({"bias I": 70 / self.attenuation, "bias Q": 0})
        log.info("Saving data to %s", self.directory)
        data = {"Index": indices,
                "I [V]": loop_x,
                "Q [V]": loop_y,
                "I2 [V]": loop_x,
                "Q2 [V]": 2 * loop_y,
                "bias I": 70 / self.attenuation,
                "bias Q": 0}
        self.save(data)

    def shutdown(self):
        pass

    def save(self, data):
        """Save the output of the procedure"""
        data.update({"parameters": self.parameter_values()})
        file_path = os.path.join(self.directory, self.file_name())
        if os.path.isfile(file_path):
            message = "{} already exists".format(file_path)
            log.error(message)
            return
        else:
            np.savez(file_path, **data)

    def load(self, file_path):
        """Load the procedure output into a pymeasure Results class instance"""
        # load in the data
        npz_file = np.load(file_path)
        parameter_dict = npz_file['parameters'].item()
        # make a procedure object with the right parameters
        procedure = self.__class__()
        for name, value in parameter_dict.items():
            setattr(procedure, name, value)
        procedure.refresh_parameters()  # Enforce update of meta data
        # collect the data into a numpy structured array
        size = max([value.size if hasattr(value, "shape") and value.shape
                    else np.array([value]).size for _, value in npz_file.items()])
        records = np.empty((size,), dtype=[(key, float) for key in npz_file.keys()
                                           if key != "parameters"])
        records.fill(np.nan)
        for key, value in npz_file.items():
            if key != "parameters":
                try:
                    records[key][:value.size] = value
                except AttributeError:
                    records[key][:np.array(value).size] = value
        # make a temporary file for the gui data
        file_path = tempfile.mktemp()
        results = Results(procedure, file_path)
        with open(file_path, mode='a') as temporary_file:
            for index in range(size):
                temporary_file.write(results.format(records[index]))
                temporary_file.write(os.linesep)
        return results
