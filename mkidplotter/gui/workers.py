import logging
import numpy as np
import pymeasure.experiment.workers as w
from pymeasure.experiment import Procedure
try:
    import cloudpickle
except ImportError:
    cloudpickle = None

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def coerce_to_list(value):
    if isinstance(value, str):
        coerced = [value]
    else:
        try:
            coerced = list(value)
        except TypeError:
            coerced = [value]
    return coerced


class Worker(w.Worker):
    def emit(self, topic, record, clear=False):
        try:
            self.publisher.send_serialized((topic, record), serialize=cloudpickle.dumps)
        except (NameError, AttributeError, TypeError):
            pass  # No dumps defined
        if topic == 'results':
            for key, value in record.items():
                if key not in self.results.data.keys() or clear:
                    self.results.data[key] = []
                self.results.data[key] += coerce_to_list(value)
        else:
            self.monitor_queue.put((topic, record))
