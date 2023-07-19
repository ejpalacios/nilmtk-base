from nilmtk.datastore import CSVDataStore, HDFDataStore, Key, TmpDataStore

from nilmtk.dataset import DataSet
from nilmtk.appliance import Appliance
from nilmtk.building import Building
from nilmtk.elecmeter import ElecMeter
from nilmtk.metergroup import MeterGroup
from nilmtk.timeframe.timeframe import TimeFrame
from nilmtk.version import version as __version__

global_meter_group = MeterGroup()
STATS_CACHE = TmpDataStore()
