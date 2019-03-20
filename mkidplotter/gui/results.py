import logging
import pandas as pd

import pymeasure.experiment.results as results

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Results(results.Results):
    """Bug fix for pymeasure Results class. Fixes reading in issue on Windows.
        
    Results class provides a convenient interface to reading and
    writing data in connection with a :class:`.Procedure` object.

    :cvar COMMENT: The character used to identify a comment (default: #)
    :cvar DELIMITER: The character used to delimit the data (default: ,)
    :cvar LINE_BREAK: The character used for line breaks (default \\n)
    :cvar CHUNK_SIZE: The length of the data chuck that is read

    :param procedure: Procedure object
    :param data_filename: The data filename where the data is or should be
                          stored
    """
    
    @property
    def data(self):
        # Need to update header count for correct referencing
        if self._header_count == -1:
            self._header_count = len(self.header()[-1].split(Results.LINE_BREAK))
        if self._data is None or len(self._data) == 0:
            # Data has not been read
            try:
                self.reload()
            except Exception:
                # Empty dataframe
                self._data = pd.DataFrame(columns=self.procedure.DATA_COLUMNS)
        else:  # Concatenate additional data, if any, to already loaded data
            skiprows = len(self._data) + self._header_count
            # 'c' engine broken on windows (line separator issue). Use 'python' instead
            chunks = pd.read_csv(self.data_filename, comment=Results.COMMENT,
                                 header=0, names=self._data.columns,
                                 chunksize=Results.CHUNK_SIZE, skiprows=skiprows,
                                 iterator=True, engine='python')
            try:
                tmp_frame = pd.concat(chunks, ignore_index=True)
                # only append new data if there is any
                # if no new data, tmp_frame dtype is object, which override's
                # self._data's original dtype - this can cause problems plotting
                # (e.g. if trying to plot int data on a log axis)
                if len(tmp_frame) > 0:
                    self._data = pd.concat([self._data, tmp_frame], ignore_index=True)
            except Exception:
                pass  # All data is up to date
        return self._data


class ContinuousResults(Results):
    """
    Overloads the data property of Results to reload the whole data set from the file
    each time self.refresh is set to True.
    """
    def __init__(self, procedure, data_filename):
        super().__init__(procedure, data_filename)
        self.refresh = False

    @property
    def data(self):
        # Need to update header count for correct referencing
        if self._header_count == -1:
            self._header_count = len(self.header()[-1].split(Results.LINE_BREAK))
        # If data has not been read yet return an empty data frame
        if self._data is None or len(self._data) == 0:
            try:
                self.reload()
            except Exception:
                # Empty dataframe
                self._data = pd.DataFrame(columns=self.procedure.DATA_COLUMNS)
        if self.refresh:
            self.refresh = False  # reset flag
            chunks = pd.read_csv(self.data_filename, comment=Results.COMMENT,
                                 header=0, names=self.procedure.DATA_COLUMNS,
                                 chunksize=Results.CHUNK_SIZE, skiprows=self._header_count,
                                 iterator=True, engine='python')
            tmp_frame = pd.concat(chunks, ignore_index=True)
            if len(tmp_frame) > 0:
                self._data = tmp_frame
            else:
                self._data = pd.DataFrame(columns=self.procedure.DATA_COLUMNS)
        return self._data
