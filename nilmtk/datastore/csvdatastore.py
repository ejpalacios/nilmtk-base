import re
from os import listdir, makedirs, remove
from os.path import dirname, exists, isdir, isfile, join
from shutil import rmtree
from typing import Iterator, Optional, Union

import numpy as np
import pandas as pd
import yaml
from nilm_metadata.convert_yaml_to_hdf5 import _load_file

from nilmtk.base.datastore import DataStore
from nilmtk.datastore.key import Key
from nilmtk.datastore.memory import MAX_MEM_ALLOWANCE_IN_BYTES
from nilmtk.timeframe.timeframe import TimeFrame
from nilmtk.timeframe.timeframegroup import TimeFrameGroup


class CSVDataStore(DataStore):
    def __init__(self, filename: str):
        self.filename = filename
        # make root directory
        path = self._key_to_abs_path("/")
        if not exists(path):
            makedirs(path)
        # make metadata directory
        path = self._get_metadata_path()
        if not exists(path):
            makedirs(path)
        super(CSVDataStore, self).__init__()

    def __getitem__(self, key: str) -> Union[pd.DataFrame, pd.Series]:
        file_path = self._key_to_abs_path(key)
        if isfile(file_path):
            return pd.read_csv(file_path)
        else:
            raise KeyError("{} not found".format(key))

    def load(
        self,
        key: str,
        columns: Optional[list] = None,
        sections=None,
        n_look_ahead_rows: int = 0,
        chunksize: int = MAX_MEM_ALLOWANCE_IN_BYTES,
    ) -> Iterator[pd.DataFrame]:
        file_path = self._key_to_abs_path(key)

        # Set `sections` variable
        sections = [TimeFrame()] if sections is None else sections
        sections = TimeFrameGroup(sections)

        self.all_sections_smaller_than_chunksize = True

        # iterate through parameter sections
        # requires 1 pass through file for each section
        for section in sections:
            window_intersect = self.window.intersection(section)
            header_rows = [0, 1]
            with pd.read_csv(
                file_path,
                index_col=0,
                header=header_rows,
                parse_dates=True,
                chunksize=chunksize,
            ) as text_file_reader:
                # iterate through all chunks in file
                for chunk_idx, chunk in enumerate(text_file_reader):
                    # filter dataframe by specified columns
                    if columns:
                        chunk = chunk[columns]

                    # mask chunk by window and section intersect
                    subchunk_idx = np.ones(len(chunk), dtype=bool)
                    if window_intersect.start:
                        subchunk_idx = np.logical_and(
                            subchunk_idx, (chunk.index >= window_intersect.start)
                        )
                    if window_intersect.end:
                        subchunk_idx = np.logical_and(
                            subchunk_idx, (chunk.index < window_intersect.end)
                        )
                    if window_intersect.empty:
                        subchunk_idx = np.zeros(len(chunk), dtype=bool)
                    subchunk = chunk[subchunk_idx]

                    if len(subchunk) > 0:
                        subchunk_end = int(np.max(np.nonzero(subchunk_idx)))
                        subchunk.attrs["timeframe"] = TimeFrame(
                            subchunk.index[0], subchunk.index[-1]
                        )
                        if n_look_ahead_rows > 0:
                            if len(subchunk.index) > 0:
                                rows_to_skip = (
                                    (len(header_rows) + 1)
                                    + (chunk_idx * chunksize)
                                    + subchunk_end
                                    + 1  # TODO: This fails sometimes
                                )
                                try:
                                    subchunk.attrs["look_ahead"] = pd.read_csv(
                                        file_path,
                                        index_col=0,
                                        header=None,
                                        parse_dates=True,
                                        skiprows=rows_to_skip,
                                        nrows=n_look_ahead_rows,
                                    )
                                except ValueError:
                                    subchunk.attrs["look_ahead"] = pd.DataFrame()
                            else:
                                subchunk.attrs["look_ahead"] = pd.DataFrame()

                        yield subchunk

    def append(self, key: str, value: pd.DataFrame) -> None:
        file_path = self._key_to_abs_path(key)
        path = dirname(file_path)
        if not exists(path):
            makedirs(path)
        value.to_csv(file_path, mode="a", header=True)

    def put(self, key: str, value: pd.DataFrame) -> None:
        file_path = self._key_to_abs_path(key)
        path = dirname(file_path)
        if not exists(path):
            makedirs(path)
        value.to_csv(file_path, mode="w", header=True)

    def remove(self, key: str, value: pd.DataFrame) -> None:
        file_path = self._key_to_abs_path(key)
        if isfile(file_path):
            remove(file_path)
        else:
            rmtree(file_path)

    def load_metadata(self, key: str = "/") -> dict:
        if key == "/":
            filepath = self._get_metadata_path()
            metadata = _load_file(filepath, "dataset.yaml")
            meter_devices = _load_file(filepath, "meter_devices.yaml")
            metadata["meter_devices"] = meter_devices
        else:
            key_object = Key(key)
            if key_object.building and not key_object.meter:
                # load building metadata from file
                filename = "building" + str(key_object.building) + ".yaml"
                filepath = self._get_metadata_path()
                metadata = _load_file(filepath, filename)
                # set data_location
                for meter_instance in metadata["elec_meters"]:
                    # not sure why I need to use meter_instance-1
                    data_location = "/building{:d}/elec/meter{:d}".format(
                        key_object.building, meter_instance
                    )
                    metadata["elec_meters"][meter_instance][
                        "data_location"
                    ] = data_location
            else:
                raise NotImplementedError("NotImplementedError")

        return metadata

    def save_metadata(self, key: str, metadata: dict) -> None:
        if key == "/":
            # Extract meter_devices
            meter_devices_metadata = metadata["meter_devices"]
            dataset_metadata = dict(metadata)
            del dataset_metadata["meter_devices"]
            # Write dataset metadata
            metadata_filename = join(self._get_metadata_path(), "dataset.yaml")
            self.write_yaml_to_file(metadata_filename, dataset_metadata)
            # Write meter_devices metadata
            metadata_filename = join(self._get_metadata_path(), "meter_devices.yaml")
            self.write_yaml_to_file(metadata_filename, meter_devices_metadata)
        else:
            # Write building metadata
            key_object = Key(key)
            assert key_object.building and not key_object.meter
            metadata_filename = join(
                self._get_metadata_path(),
                "building{:d}.yaml".format(key_object.building),
            )
            self.write_yaml_to_file(metadata_filename, metadata)

    def elements_below_key(self, key: str = "/") -> list[str]:
        elements = []
        if key == "/":
            for directory in listdir(self.filename):
                dir_path = join(self.filename, directory)
                if isdir(dir_path) and re.match("building[0-9]*", directory):
                    elements += [directory]
        else:
            relative_path = key[1:]
            dir_path = join(self.filename, relative_path)
            if isdir(dir_path):
                for element in listdir(dir_path):
                    elements += [directory]

        return elements

    def close(self) -> None:
        # not needed for CSV data store
        pass

    def open(self) -> None:
        # not needed for CSV data store
        pass

    def get_timeframe(self, key: str) -> TimeFrame:
        file_path = self._key_to_abs_path(key)
        text_file_reader = pd.read_csv(
            file_path,
            index_col=0,
            header=[0, 1],
            parse_dates=True,
            chunksize=MAX_MEM_ALLOWANCE_IN_BYTES,
        )
        start = None
        end = None
        for df in text_file_reader:
            if start is None:
                start = df.index[0]
            end = df.index[-1]
        timeframe = TimeFrame(start, end)
        return self.window.intersection(timeframe)

    def _get_metadata_path(self) -> str:
        return join(self.filename, "metadata")

    def _key_to_abs_path(self, key: str) -> str:
        abs_path = self.filename
        if key and len(key) > 1:
            relative_path = key
            if key[0] == "/":
                relative_path = relative_path[1:]
            abs_path = join(self.filename, relative_path)
            key_object = Key(key)
            if key_object.building and key_object.meter:
                abs_path += ".csv"
        return abs_path

    @staticmethod
    def write_yaml_to_file(metadata_filename: str, metadata: dict) -> None:
        with open(metadata_filename, "w") as metadata_file:
            yaml.dump(metadata, metadata_file)
