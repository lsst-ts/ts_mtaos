# This file is part of ts_MTAOS.
#
# Developed for the LSST Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import numpy as np
import unittest

from lsst.ts.mtaos import WavefrontCollection


class TestWavefrontCollection(unittest.TestCase):
    """Test the CollOfListOfWfErr class."""

    def setUp(self):
        self.wavefront_collection = WavefrontCollection(10)

    def testGetNumOfData(self):
        self.assertEqual(self.wavefront_collection.getNumOfData(), 0)

    def testGetNumOfDataTaken(self):
        self.assertEqual(self.wavefront_collection.getNumOfDataTaken(), 0)

    def testAppend(self):
        listOfWfErr = self._prepareListOfWfErr()
        self.wavefront_collection.append(listOfWfErr)

        self.assertEqual(self.wavefront_collection.getNumOfData(), 1)

    def _prepareListOfWfErr(self):
        listSensorId = [1, 2]
        listSensorZk = [np.random.rand(19)] * 2
        return self._getListOfWfErr(listSensorId, listSensorZk)

    def _getListOfWfErr(self, listSensorId, listSensorZk):
        listOfWfErr = list(zip(listSensorId, listSensorZk))

        return listOfWfErr

    def testPopWithoutData(self):
        self.assertEqual(self.wavefront_collection.pop(), [])

    def testPopWithData(self):
        self.assertEqual(self.wavefront_collection.getNumOfDataTaken(), 0)

        listOfWfErr = self._prepareListOfWfErr()
        self.wavefront_collection.append(listOfWfErr)

        listOfWfErrPop = self.wavefront_collection.pop()
        self.assertEqual(len(listOfWfErrPop), 2)
        self.assertEqual(listOfWfErrPop[0][0], 1)
        self.assertEqual(listOfWfErrPop[1][0], 2)

        self.assertEqual(self.wavefront_collection.getNumOfDataTaken(), 1)

    def testClear(self):
        listOfWfErr = self._prepareListOfWfErr()
        for idx in range(3):
            self.wavefront_collection.append(listOfWfErr)
        self.wavefront_collection.pop()

        self.assertEqual(self.wavefront_collection.getNumOfData(), 2)
        self.assertEqual(self.wavefront_collection.getNumOfDataTaken(), 1)

        self.wavefront_collection.clear()

        self.assertEqual(self.wavefront_collection.getNumOfData(), 0)
        self.assertEqual(self.wavefront_collection.getNumOfDataTaken(), 0)

    def testGetListOfWavefrontErrorAvgInTakenDataWithoutData(self):
        self.assertRaises(
            RuntimeError,
            self.wavefront_collection.getListOfWavefrontErrorAvgInTakenData,
        )

    def testGetListOfWavefrontErrorAvgInTakenDataWithSglData(self):
        self._collectListOfWfErrForAvgTest()
        self.wavefront_collection.pop()

        listOfWfErrAvg = (
            self.wavefront_collection.getListOfWavefrontErrorAvgInTakenData()
        )

        self.assertEqual(len(listOfWfErrAvg), 3)
        for sensor_id in listOfWfErrAvg:
            self.assertTrue(np.all(listOfWfErrAvg[sensor_id] == 1.0))

    def _collectListOfWfErrForAvgTest(self):
        self._collectListOfWfErrForAvgTestSgl([1, 2, 3], [np.ones(19)] * 3)
        self._collectListOfWfErrForAvgTestSgl([2, 1, 3], [np.zeros(19)] * 3)
        self._collectListOfWfErrForAvgTestSgl([3, 2, 1], [np.ones(19) * 5] * 3)

    def _collectListOfWfErrForAvgTestSgl(self, listSensorId, listSensorZk):
        listOfWfErr = self._getListOfWfErr(listSensorId, listSensorZk)
        self.wavefront_collection.append(listOfWfErr)

    def testGetListOfWavefrontErrorAvgInTakenDataWithMultiData(self):
        self._collectListOfWfErrForAvgTest()
        for idx in range(3):
            self.wavefront_collection.pop()

        listOfWfErrAvg = (
            self.wavefront_collection.getListOfWavefrontErrorAvgInTakenData()
        )

        self.assertEqual(len(listOfWfErrAvg), 3)
        for sensor_id in listOfWfErrAvg:
            self.assertEqual(len(listOfWfErrAvg[sensor_id]), 19)
            self.assertTrue(np.all(listOfWfErrAvg[sensor_id] == 2.0))

    def testGetListOfWavefrontErrorAvgInTakenDataWithMultiDataAndMissData(self):
        # There are 3 sensor data hera
        self._collectListOfWfErrForAvgTest()

        # There are only 2 sensor data here
        listOfWfErr = self._prepareListOfWfErr()
        self.wavefront_collection.append(listOfWfErr)

        for idx in range(4):
            self.wavefront_collection.pop()

        listOfWfErrAvg = (
            self.wavefront_collection.getListOfWavefrontErrorAvgInTakenData()
        )

        self.assertEqual(len(listOfWfErrAvg), 3)
        for idx in {1, 2, 3}:
            self.assertTrue(idx in listOfWfErrAvg)


if __name__ == "__main__":
    # Do the unit test
    unittest.main()
