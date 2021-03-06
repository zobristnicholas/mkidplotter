import os
import logging
import tempfile
import numpy as np
from time import sleep
from mkidplotter import (NoiseInput, SweepBaseProcedure, Results, IntegerParameter, FloatParameter, VectorParameter,
                         IntegerIndicator, FloatIndicator, Indicator)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Sweep(SweepBaseProcedure):
    frequency1 = FloatParameter("Ch 1 Center Frequency", units="GHz", default=4.0)
    span1 = FloatParameter("Ch 1 Span", units="MHz", default=2)
    frequency2 = FloatParameter("Ch 2 Center Frequency", units="GHz", default=4.0)
    span2 = FloatParameter("Ch 2 Span", units="MHz", default=2)
    noise = VectorParameter("Noise", length=6, default=[1, 1, 10, 1, -1, 10],
                            ui_class=NoiseInput)
    n_points = IntegerParameter("Number of Points", default=500)
    index_counter = IntegerIndicator("Index")
    random_float = FloatIndicator("Random Float", precision=4)
    status_bar = Indicator("Status")

    DATA_COLUMNS = ['I1', 'Q1', "bias I1", "bias Q1", 'Amplitude PSD1', 'Phase PSD1',
                    'I2', 'Q2', "bias I2", "bias Q2", 'Amplitude PSD2', 'Phase PSD2',
                    'frequency']
    wait_time = 0.01

    def startup(self):
        log.info("Starting procedure")
        self.update_metadata()

    def execute(self):
        log.info("Measuring the loop with %d points", self.n_points)
        loop_x = np.zeros(self.n_points)
        loop_y = np.zeros(self.n_points)
        indices = np.arange(self.n_points)
        # sweep frequencies
        self.status_bar.value = "Sweeping"
        for i in indices:
            self.emit('progress', i / self.n_points * 100)
            loop_x[i] = 70 / self.attenuation * np.cos(2 * np.pi * i /
                                                       (self.n_points - 1))
            loop_y[i] = 70 / self.attenuation * np.sin(2 * np.pi * i /
                                                       (self.n_points - 1))
            data = {"I1": loop_x[i],
                    "Q1": loop_y[i],
                    "I2": loop_x[i] * 2,
                    "Q2": loop_y[i]}
            # send indicator values every 100 indexes
            if not i % 100:
                self.index_counter.value = i
                self.random_float.value = np.random.rand() * 10000
            self.emit("results", data)
            log.debug("Emitting results: %s" % data)
            sleep(self.wait_time)
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                return

        if self.noise[0]:
            self.status_bar.value = "Taking noise data"
            # calculate bias point
            bias_i1, bias_q1 = 70 / self.attenuation, 0
            bias_i2, bias_q2 = 0, 70 / self.attenuation

            self.emit("results", {"bias I1": bias_i1, "bias Q1": bias_q1})
            self.emit("results", {"bias I2": bias_i2, "bias Q2": bias_q2})
            # take noise data
            frequency = np.linspace(1e3, 1e5, 100)
            phase = 1 / frequency
            amplitude = 1 / frequency[-1] * np.ones(frequency.shape)
            data = {"frequency": frequency,
                    "Phase PSD1": phase,
                    "Amplitude PSD1": amplitude,
                    "Phase PSD2": phase / 2,
                    "Amplitude PSD2": amplitude * 2}
            self.emit("results", data)
        else:
            frequency = np.nan
            phase = np.nan
            amplitude = np.nan
            bias_i1 = np.nan
            bias_i2 = np.nan
            bias_q1 = np.nan
            bias_q2 = np.nan

        # save all the data we took
        data = {"I1": loop_x,
                "Q1": loop_y,
                "I2": loop_x * 2,
                "Q2": loop_y,
                "frequency": frequency,
                "Phase PSD1": phase,
                "Amplitude PSD1": amplitude,
                "Phase PSD2": phase / 2,
                "Amplitude PSD2": amplitude * 2,
                "bias I1": bias_i1,
                "bias Q1": bias_q1,
                "bias I2": bias_i2,
                "bias Q2": bias_q2}
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
        results.data = dict(npz_file)
        return results
