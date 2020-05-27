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

from lsst.ts.wep.ctrlIntf.SensorWavefrontData import SensorWavefrontData

from lsst.ts import MTAOS


class TestCollOfListOfWfErr(unittest.TestCase):
    """Test the CollOfListOfWfErr class."""

    def setUp(self):

        self.collOfListOfWfErr = MTAOS.CollOfListOfWfErr(10)

    def testGetNumOfData(self):

        self.assertEqual(self.collOfListOfWfErr.getNumOfData(), 0)

    def testGetNumOfDataTaken(self):

        self.assertEqual(self.collOfListOfWfErr.getNumOfDataTaken(), 0)

    def testAppend(self):

        listOfWfErr = self._prepareListOfWfErr()
        self.collOfListOfWfErr.append(listOfWfErr)

        self.assertEqual(self.collOfListOfWfErr.getNumOfData(), 1)

    def _prepareListOfWfErr(self):

        listSensorId = [1, 2]
        listSensorZk = [np.random.rand(19)] * 2
        return self._getListOfWfErr(listSensorId, listSensorZk)

    def _getListOfWfErr(self, listSensorId, listSensorZk):

        listOfWfErr = []
        for sensorId, sensorZk in zip(listSensorId, listSensorZk):
            sensorWavefrontData = SensorWavefrontData()
            sensorWavefrontData.setSensorId(sensorId)
            sensorWavefrontData.setAnnularZernikePoly(sensorZk)

            listOfWfErr.append(sensorWavefrontData)

        return listOfWfErr

    def testPopWithoutData(self):

        self.assertEqual(self.collOfListOfWfErr.pop(), [])

    def testPopWithData(self):

        self.assertEqual(self.collOfListOfWfErr.getNumOfDataTaken(), 0)

        listOfWfErr = self._prepareListOfWfErr()
        self.collOfListOfWfErr.append(listOfWfErr)

        listOfWfErrPop = self.collOfListOfWfErr.pop()
        self.assertEqual(len(listOfWfErrPop), 2)
        self.assertEqual(listOfWfErrPop[0].getSensorId(), 1)
        self.assertEqual(listOfWfErrPop[1].getSensorId(), 2)

        self.assertEqual(self.collOfListOfWfErr.getNumOfDataTaken(), 1)

    def testClear(self):

        listOfWfErr = self._prepareListOfWfErr()
        for idx in range(3):
            self.collOfListOfWfErr.append(listOfWfErr)
        self.collOfListOfWfErr.pop()

        self.assertEqual(self.collOfListOfWfErr.getNumOfData(), 2)
        self.assertEqual(self.collOfListOfWfErr.getNumOfDataTaken(), 1)

        self.collOfListOfWfErr.clear()

        self.assertEqual(self.collOfListOfWfErr.getNumOfData(), 0)
        self.assertEqual(self.collOfListOfWfErr.getNumOfDataTaken(), 0)

    def testGetListOfWavefrontErrorAvgInTakenDataWithoutData(self):

        self.assertRaises(
            RuntimeError, self.collOfListOfWfErr.getListOfWavefrontErrorAvgInTakenData
        )

    def testGetListOfWavefrontErrorAvgInTakenDataWithSglData(self):

        self._collectListOfWfErrForAvgTest()
        self.collOfListOfWfErr.pop()

        listOfWfErrAvg = self.collOfListOfWfErr.getListOfWavefrontErrorAvgInTakenData()

        self.assertEqual(len(listOfWfErrAvg), 3)
        self.assertEqual(listOfWfErrAvg[0].getAnnularZernikePoly()[0], 1)

    def _collectListOfWfErrForAvgTest(self):

        self._collectListOfWfErrForAvgTestSgl([1, 2, 3], [np.ones(19)] * 3)
        self._collectListOfWfErrForAvgTestSgl([2, 1, 3], [np.zeros(19)] * 3)
        self._collectListOfWfErrForAvgTestSgl([3, 2, 1], [np.ones(19) * 5] * 3)

    def _collectListOfWfErrForAvgTestSgl(self, listSensorId, listSensorZk):

        listOfWfErr = self._getListOfWfErr(listSensorId, listSensorZk)
        self.collOfListOfWfErr.append(listOfWfErr)

    def testGetListOfWavefrontErrorAvgInTakenDataWithMultiData(self):

        self._collectListOfWfErrForAvgTest()
        for idx in range(3):
            self.collOfListOfWfErr.pop()

        listOfWfErrAvg = self.collOfListOfWfErr.getListOfWavefrontErrorAvgInTakenData()

        self.assertEqual(len(listOfWfErrAvg), 3)
        self.assertEqual(listOfWfErrAvg[0].getAnnularZernikePoly()[0], 2)

    def testGetListOfWavefrontErrorAvgInTakenDataWithMultiDataAndMissData(self):

        # There are 3 sensor data hera
        self._collectListOfWfErrForAvgTest()

        # There are only 2 sensor data here
        listOfWfErr = self._prepareListOfWfErr()
        self.collOfListOfWfErr.append(listOfWfErr)

        for idx in range(4):
            self.collOfListOfWfErr.pop()

        listOfWfErrAvg = self.collOfListOfWfErr.getListOfWavefrontErrorAvgInTakenData()

        self.assertEqual(len(listOfWfErrAvg), 2)
        for idx in range(2):
            self.assertTrue(listOfWfErrAvg[idx].getSensorId() in (1, 2))


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
