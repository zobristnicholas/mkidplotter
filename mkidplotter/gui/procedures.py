import logging
from pymeasure.experiment import Procedure
from pymeasure.experiment import (IntegerParameter, FloatParameter, Parameter)

from analogreadout.parameters import DirectoryParameter, TextEditParameter

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
