import logging
import numpy as np
import pymeasure.experiment.workers as w

from mkidplotter.gui.results import ContinuousResults

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Worker(w.Worker):
    def emit(self, topic, record, clear=False):
        try:
            self.publisher.send_serialized((topic, record), serialize=cloudpickle.dumps)
        except (NameError, AttributeError):
            pass  # No dumps defined
        if topic == 'results':
            # clear the file if requested
            if clear:
                data = self.results.data
                with open(self.results.data_filename, 'w') as file_:
                    file_.write(self.results.header())
                    file_.write(self.results.labels())
                for key, value in data.items():  # add back in data that we aren't clearing
                    if key not in record.keys():
                        record[key] = data[key]
            # collect the data into a numpy structured array
            size = max([value.size if hasattr(value, "shape") and value.shape
                        else np.array([value]).size for value in record.values()])
            records = np.empty((size,), dtype=[(key, float) for key in self.procedure.DATA_COLUMNS])
            records.fill(np.nan)
            for key, value in record.items():
                try:
                    records[key][:value.size] = value
                except AttributeError:
                    records[key][:np.array(value).size] = value
            # add in unspecified columns to the array
            for key in self.procedure.DATA_COLUMNS:
                if key not in record.keys():
                    records[key] = np.nan
            # send the data to the file
            for index in range(size):
                self.recorder.handle(records[index])
            if isinstance(self.results, ContinuousResults):
                self.results.refresh = True
        else:
            self.monitor_queue.put((topic, record))
