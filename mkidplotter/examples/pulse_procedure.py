import os
import logging
import tempfile
import numpy as np
from time import sleep
from mkidplotter import (NoiseInput, MKIDProcedure, Results, DirectoryParameter, IntegerParameter, FloatParameter,
                         VectorParameter)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Pulse(MKIDProcedure):
    directory = DirectoryParameter("Data Directory", default='/Users/nicholaszobrist/Desktop/test')
    frequency1 = FloatParameter("Ch 1 Center Frequency", units="GHz", default=4.0)
    frequency2 = FloatParameter("Ch 2 Center Frequency", units="GHz", default=4.0)
    attenuation = FloatParameter("DAC Attenuation", units="dB", default=0)
    noise = VectorParameter("Noise", default=[1, 1, 10], ui_class=NoiseInput)
    n_points = IntegerParameter("Number of Points", default=500)
    n_pulses = IntegerParameter("Number of Pulses", default=100)

    DATA_COLUMNS = ['t', 'phase 1', 'amplitude 1', 'phase 2', 'amplitude 2', 'frequency',
                    'phase PSD1', 'amplitude PSD1', 'phase PSD2', 'amplitude PSD2']
    wait_time = 0.1

    def startup(self):
        log.info("Starting procedure")
        self.update_metadata()

    def execute(self):
        log.info("Measuring the loop with %d points", self.n_points)
        pulse1_p = np.zeros((self.n_pulses, self.n_points))
        pulse1_a = np.zeros((self.n_pulses, self.n_points))
        pulse2_p = np.zeros((self.n_pulses, self.n_points))
        pulse2_a = np.zeros((self.n_pulses, self.n_points))
        # take pulse data
        for i in np.arange(self.n_pulses):
            pulse1_p[i, :] = np.random.random_sample(self.n_points)
            pulse1_a[i, :] = np.random.random_sample(self.n_points) + 10
            pulse2_p[i, :] = np.random.random_sample(self.n_points)
            pulse2_a[i, :] = np.random.random_sample(self.n_points) + 10
            data = {"t": np.arange(self.n_points),
                    "phase 1": pulse1_p[i, :],
                    "amplitude 1": pulse1_a[i, :],
                    "phase 2": pulse2_p[i, :],
                    "amplitude 2": pulse2_a[i, :]}
            if i % 10 == 0:
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
        data = {"phase 1": pulse1_p,
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
        file_path = tempfile.mktemp(suffix='.txt')
        results = Results(procedure, file_path)
        log.info("Loading dataset into the temporary file %s", file_path)
        with open(file_path, mode='a') as temporary_file:
            for index in range(size):
                temporary_file.write(results.format(records[index]))
                temporary_file.write(os.linesep)
        return results
