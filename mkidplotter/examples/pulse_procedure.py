import os
import logging
import tempfile
import numpy as np
from time import sleep
from mkidplotter import (NoiseInput, MKIDProcedure, Results, DirectoryParameter, IntegerParameter, FloatParameter,
                         VectorParameter, BooleanListInput)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Pulse(MKIDProcedure):
    directory = DirectoryParameter("Data Directory", default='/Users/nicholaszobrist/Desktop/test')
    frequency1 = FloatParameter("Ch 1 Center Frequency", units="GHz", default=4.0)
    frequency2 = FloatParameter("Ch 2 Center Frequency", units="GHz", default=4.0)
    attenuation = FloatParameter("DAC Attenuation", units="dB", default=0)
    noise = VectorParameter("Noise", default=[1, 1, 10], ui_class=NoiseInput)
    n_trace = IntegerParameter("Number of Points", default=500)
    n_pulses = IntegerParameter("Number of Pulses", default=100)
    ui = BooleanListInput.set_labels(["808 nm", "920 nm", "980 nm", "1120 nm", "1310 nm"])  # class factory
    laser = VectorParameter("Laser", default=[0, 0, 0, 0, 0], length=5, ui_class=ui)

    DATA_COLUMNS = ['t', 'phase 1', 'amplitude 1', 'phase 2', 'amplitude 2', 'frequency',
                    'phase PSD1', 'amplitude PSD1', 'phase PSD2', 'amplitude PSD2']
    wait_time = 0.1

    def startup(self):
        log.info("Starting procedure")
        self.update_metadata()

    def execute(self):
        log.info("Measuring the loop with %d points", self.n_trace)
        pulse1_p = np.zeros((self.n_pulses, self.n_trace))
        pulse1_a = np.zeros((self.n_pulses, self.n_trace))
        pulse2_p = np.zeros((self.n_pulses, self.n_trace))
        pulse2_a = np.zeros((self.n_pulses, self.n_trace))
        # take pulse data
        for i in np.arange(self.n_pulses):
            pulse1_p[i, :] = np.random.random_sample(self.n_trace)
            pulse1_a[i, :] = np.random.random_sample(self.n_trace) + 10
            pulse2_p[i, :] = np.random.random_sample(self.n_trace)
            pulse2_a[i, :] = np.random.random_sample(self.n_trace) + 10
            data = {"t": np.arange(self.n_trace),
                    "phase 1": pulse1_p[i, :],
                    "amplitude 1": pulse1_a[i, :],
                    "phase 2": pulse2_p[i, :],
                    "amplitude 2": pulse2_a[i, :]}
            self.emit("results", data, clear=True)  # clear last pulse from gui file
            self.emit('progress', i / self.n_pulses * 100)
            log.debug("Emitting results: %s" % data)
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                return
            sleep(np.random.random_sample() * self.wait_time)

        if self.noise[0]:
            # take noise data
            frequency = np.linspace(1e3, 1e5, 100)
            phase = 1 / frequency
            amplitude = 1 / frequency[-1] * np.ones(frequency.shape)
            data = {"frequency": frequency,
                    "phase PSD1": phase,
                    "amplitude PSD1": amplitude,
                    "phase PSD2": phase / 2,
                    "amplitude PSD2": amplitude * 2}
            self.emit("results", data)  # don't clear last pulse
        else:
            frequency = np.nan
            phase = np.nan
            amplitude = np.nan

        # save all the data we took
        data = {"t": np.arange(self.n_trace),
                "phase 1": pulse1_p,
                "amplitude 1": pulse1_a,
                "phase 2": pulse2_p,
                "amplitude 2": pulse2_a,
                "frequency": frequency,
                "phase PSD1": phase,
                "amplitude PSD1": amplitude,
                "phase PSD2": phase / 2,
                "amplitude PSD2": amplitude * 2}
        self.save(data)

    def shutdown(self):
        log.info("Finished procedure")

    def save(self, data):
        """Save the output of the procedure"""
        data.update({"parameters": self.parameter_values()})
        file_path = os.path.join(self.directory, self.file_name())
        log.info("Saving data to %s", file_path)
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
        # make a results object
        file_path = tempfile.mktemp(suffix='.pickle')
        results = Results(procedure, file_path)
        # update the data in the results
        data = dict(npz_file)
        keys = ['phase 1', 'phase 2', 'amplitude 1', 'amplitude 2']
        for key in keys:
            data[key] = data[key][0, :]
        results.data = data
        return results
