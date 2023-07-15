from abc import abstractmethod
from io import open
from typing import Any, Iterator, Optional, Union

import pandas as pd
import yaml

from nilmtk.datastore.memory import MAX_MEM_ALLOWANCE_IN_BYTES
from nilmtk.timeframe.timeframe import TimeFrame


class DataStore(object):
    """
    Provides a common interface to all physical data stores.
    Supports hierarchical stores.

    The DataStore class lives in the bottom layer of NILMTK.  It loads
    a single chunk at a time from physical location and returns a
    DataFrame.

    * Deals with: retrieving data from disk / network / direct from a meter
    * Optimised for: handling large amounts of data
    * Services it provides: delivering a generator of pd.DataFrames of data given a
      specific time span and columns
    * Totally agnostic about what the data 'means'. It could be voltage,
      current, temperature, PIR readings etc.
    * could have subclasses for NILMTK HDF5, NILMTK CSV, Xively,
      Current Cost meters etc.
    * One DataStore per HDF5 file or folder or CSV files or Xively
      feed etc.

    Attributes
    ----------
    window : nilmtk.TimeFrame
        Defines the timeframe we are interested in.
    """

    def __init__(self):
        """
        Parameters
        ----------
        filename : string
        """
        self.window = TimeFrame()

    @abstractmethod
    def __getitem__(self, key: str) -> Union[pd.DataFrame, pd.Series]:
        """Loads all of a DataFrame from disk.

        Parameters
        ----------
        key : str

        Returns
        -------
        DataFrame

        Raises
        ------
        KeyError if `key` is not found.
        """

    @property
    def window(self) -> TimeFrame:
        return self._window

    @window.setter
    def window(self, window: TimeFrame):
        window.check_tz()
        self._window = window

    @abstractmethod
    def load(
        self,
        key: str,
        columns: Optional[list] = None,
        sections=None,
        n_look_ahead_rows: int = 0,
        chunksize: int = MAX_MEM_ALLOWANCE_IN_BYTES,
    ) -> Iterator[pd.DataFrame]:
        """
        Parameters
        ----------
        key : string, the location of a table within the DataStore.
        columns : list of Measurements, optional
            e.g. [('power', 'active'), ('power', 'reactive'), ('voltage')]
            if not provided then will return all columns from the table.
        sections : TimeFrameGroup; or list of nilmtk.TimeFrame objects;
            or a pd.PeriodIndex, optional.
            Defines the time sections to load.  If `self.window` is enabled
            then each `section` will be intersected with `self.window`.
        n_look_ahead_rows : int, optional, defaults to 0
            If >0 then each returned DataFrame will have a `look_ahead`
            property which will be a DataFrame of length `n_look_ahead_rows`
            of the data immediately in front of the data in the main DataFrame.
        chunksize : int, optional

        Returns
        -------
        generator of DataFrame objects
            Each DataFrame is has extra attributes:
                - timeframe : TimeFrame of section intersected with self.window
                - look_ahead : pd.DataFrame:
                    with `n_look_ahead_rows` rows.  The first row will be for
                    `section.end`.  `look_ahead` stores data which appears on
                    disk immediately after `section.end`; i.e. it ignores
                    the next `section.start`.

            Returns an empty DataFrame if no data is available for the
            specified section (or if the section.intersection(self.window)
            is empty).

        Raises
        ------
        KeyError if `key` is not in store.
        """

    @abstractmethod
    def append(self, key: str, value: pd.DataFrame) -> None:
        """
        Parameters
        ----------
        key : str
        value : pd.DataFrame

        Notes
        -----
        To quote the Pandas documentation for pandas.io.pytables.HDFStore.append:
        Append does *not* check if data being appended overlaps with existing
        data in the table, so be careful.
        """

    @abstractmethod
    def put(self, key: str, value: pd.DataFrame) -> None:
        """
        Parameters
        ----------
        key : str
        value : pd.DataFrame
        """

    @abstractmethod
    def remove(self, key: str, value: pd.DataFrame) -> None:
        """
        Parameters
        ----------
        key : str
        value : pd.DataFrame
        """

    @abstractmethod
    def load_metadata(self, key: str = "/") -> dict:
        """
        Parameters
        ----------
        key : string, optional
            if '/' then load metadata for the whole dataset.

        Returns
        -------
        metadata : dict
        """

    @abstractmethod
    def save_metadata(self, key: str, metadata: dict) -> None:
        """
        Parameters
        ----------
        key : string
        metadata : dict
        """

    @abstractmethod
    def elements_below_key(self, key: str = "/") -> list[str]:
        """
        Returns
        -------
        list of strings
        """

    @abstractmethod
    def close(self) -> None:
        """
        Close data store
        """

    @abstractmethod
    def open(self) -> None:
        """
        Close data store
        """

    @abstractmethod
    def get_timeframe(self, key: str) -> TimeFrame:
        """
        Returns
        -------
        nilmtk.TimeFrame of entire table after intersecting with self.window.
        """


def write_yaml_to_file(metadata_filename, metadata) -> None:
    metadata_file = open(metadata_filename, "w")
    yaml.dump(metadata, metadata_file)
    metadata_file.close()


def join_key(*args) -> str:
    """
    Examples
    --------
    >>> join_key('building1', 'elec', 'meter1')
    '/building1/elec/meter1'

    >>> join_key('/')
    '/'

    >>> join_key('')
    '/'
    """
    key = "/"
    for arg in args:
        arg_stripped = str(arg).strip("/")
        if arg_stripped:
            key += arg_stripped + "/"
    if len(key) > 1:
        key = key[:-1]  # remove last trailing slash
    return key


def convert_datastore(input_store: DataStore, output_store: DataStore):
    """
    Parameters
    ----------
    input_store : nilmtk.DataStore
    output_store : nilmtk.DataStore
    """
    # dataset metadata
    metadata = input_store.load_metadata()
    output_store.save_metadata("/", metadata)
    for building in input_store.elements_below_key():
        building_key = "/" + building
        # building metadata
        metadata = input_store.load_metadata(building_key)
        output_store.save_metadata(building_key, metadata)
        for utility in input_store.elements_below_key(building):
            utility_key = building_key + "/" + utility
            for meter in input_store.elements_below_key(utility_key):
                # ignore cache (should this appear as an element below key?)
                if meter == "cache":
                    continue
                meter_key = utility_key + "/" + meter
                # store meter data
                for df in input_store.load(meter_key):
                    output_store.append(meter_key, df)
