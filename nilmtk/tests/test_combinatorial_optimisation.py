import unittest
from os import remove
from os.path import join

import pandas as pd

from nilmtk import DataSet
from nilmtk.datastore import HDFDataStore
from nilmtk.legacy.disaggregate import CombinatorialOptimisation

from .testingtools import data_dir


class TestCO(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        filename = join(data_dir(), "co_test.h5")
        cls.dataset = DataSet(filename)

    @classmethod
    def tearDownClass(cls):
        cls.dataset.store.close()

    def test_co_correctness(self):
        elec = self.dataset.buildings[1].elec
        co = CombinatorialOptimisation()
        co.train(elec)
        mains = elec.mains()

        mains_data = next(mains.load(sample_period=10))

        pred = co.disaggregate_chunk(mains_data)
        gt = {}
        for meter in elec.submeters().meters:
            meter_data = next(meter.load(sample_period=10))
            gt[meter] = meter_data.squeeze()
        gt = pd.DataFrame(gt)
        pred = pred[gt.columns]
        self.assertTrue(gt.equals(pred))


if __name__ == "__main__":
    unittest.main()
