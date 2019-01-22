import logging
import numpy as np
import pymeasure.experiment.workers as w

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
                with open(self.results.data_filename, 'w') as file_:
                    file_.write(self.results.header())
                    file_.write(self.results.labels())
            # collect the data into a numpy structured array
            size = max([value.size if hasattr(value, "shape") and value.shape
                        else np.array([value]).size for value in record.values()])
            records = np.empty((size,), dtype=[(key, float)
                                               for key in self.procedure.DATA_COLUMNS])
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
        elif topic == 'status' or topic == 'progress':
            self.monitor_queue.put((topic, record))