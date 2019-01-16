import logging
import pandas as pd

import pymeasure.experiment.results as results

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Results(results.Results):
    """ Bug fix for pymeasure Results class. Fixes reading in issue on Windows.
        
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
            self._header_count = len(
                self.header()[-1].split(Results.LINE_BREAK))
        if self._data is None or len(self._data) == 0:
            # Data has not been read
            try:
                self.reload()
            except Exception:
                # Empty dataframe
                self._data = pd.DataFrame(columns=self.procedure.DATA_COLUMNS)
        else:  # Concatenate additional data, if any, to already loaded data
            skiprows = len(self._data) + self._header_count
            chunks = pd.read_csv(self.data_filename, comment=Results.COMMENT,
                                 header=0, names=self._data.columns,
                                 chunksize=Results.CHUNK_SIZE, skiprows=skiprows,
                                 iterator=True, lineterminator='\n')
            try:
                tmp_frame = pd.concat(chunks, ignore_index=True)
                # only append new data if there is any
                # if no new data, tmp_frame dtype is object, which override's
                # self._data's original dtype - this can cause problems plotting
                # (e.g. if trying to plot int data on a log axis)
                if len(tmp_frame) > 0:
                    self._data = pd.concat([self._data, tmp_frame],
                                           ignore_index=True)
            except Exception:
                pass  # All data is up to date
        return self._data