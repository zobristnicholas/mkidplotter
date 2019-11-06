import os
import pickle
import logging
import pandas as pd
from collections import OrderedDict

from pymeasure.experiment import Procedure
import pymeasure.experiment.results as results

from mkidplotter.gui.workers import coerce

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class ResultsHolder:
    """
    Keeps track of results data and writes/retrieves them from file when too
    many are open.
    """
    MAX_SIZE = 20

    def __init__(self):
        self._files = OrderedDict()

    def __getitem__(self, item):
        item = os.path.abspath(item)
        # check if already loaded
        if item in self._files.keys():
            log.debug("loaded from cache: {}".format(item))
            return self._files[item]
        # if it's a file load it
        elif os.path.isfile(item):
            with open(item, "rb") as f:
                data = pickle.load(f)
            log.debug("loaded: {}".format(item))
            self.add(item, data)
            return self._files[item]
        else:
            raise ValueError("the requested item was not in the cache or saved to disk")

    def add(self, file_name, data):
        self._files[file_name] = data
        log.debug("saved to cache: {}".format(file_name))
        self._check_size()

    def _check_size(self):
        for _ in range(max(len(self._files) - self.MAX_SIZE, 0)):
            key, value = self._files.popitem(last=False)
            log.debug("removed from cache: {}".format(key))
            with open(key, "wb") as f:
                pickle.dump(value, f)
            log.debug("saved to file: {}".format(key))


_results_cache = ResultsHolder()  # cache of already loaded files


class Results(results.Results):
    """
    Results class for holding GUI results. It acts like a dictionary and uses
    the ResultsHolder class to regulate memory management.
    """

    def __init__(self, procedure, data_filename):
        if not isinstance(procedure, Procedure):
            raise ValueError("Results require a Procedure object")
        self.procedure = procedure
        self.procedure_class = procedure.__class__
        self.parameters = procedure.parameter_objects()

        if isinstance(data_filename, (list, tuple)):
            data_filenames, data_filename = data_filename, data_filename[0]
        else:
            data_filenames = [data_filename]

        self.data_filename = data_filename
        self.data_filenames = data_filenames
        data = {"_procedure": self.procedure}
        data.update({key: [] for key in procedure.DATA_COLUMNS})
        _results_cache.add(data_filename, data)
        self.formatter = None

    @property
    def data(self):
        return _results_cache[self.data_filename]

    @data.setter
    def data(self, dictionary):
        if not isinstance(dictionary, dict):
            raise ValueError("data object must be set as a dictionary")
        data = {"_procedure": self.procedure}
        data.update({key: [] for key in self.procedure.DATA_COLUMNS})
        _results_cache.add(self.data_filename, data)
        for key, value in dictionary.items():
            if key in _results_cache[self.data_filename].keys():
                _results_cache[self.data_filename][key] += coerce(value)

    def reload(self):
        pass  # doesn't need to be reloaded like pymeasure Results class

    def __repr__(self):
        return "<{}(filename='{}',procedure={})>".format(
            self.__class__.__name__, self.data_filename,
            self.procedure.__class__.__name__)

    @staticmethod
    def load(data_filename, procedure_class=None):
        """ Returns a Results object with the associated Procedure object and
        data
        """
        with open(data_filename, "rb") as f:
            data = pickle.load(f)
        if procedure_class is not None:
            procedure = procedure_class()
        else:
            procedure = data["_procedure"]
        return Results(procedure, data_filename)

    def header(self):
        raise NotImplementedError

    def labels(self):
        raise NotImplementedError

    def format(self, data):
        raise NotImplementedError

    def parse(self, line):
        raise NotImplementedError

    @staticmethod
    def parse_header(header, procedure_class=None):
        raise NotImplementedError
