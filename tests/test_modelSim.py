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

import os
import time
import numpy as np
import unittest
import yaml

from lsst.ts.wep.ctrlIntf.SensorWavefrontData import SensorWavefrontData

from lsst.ts import MTAOS


class Config(object):
    """Config Class for the test."""

    def __init__(self):

        self.camera = "comcam"
        self.instrument = "comcam"
        self.defaultIsrDir = os.path.join(os.sep, "home", "lsst", "input")
        self.defaultSkyFilePath = os.path.join(
            "tests", "testData", "phosimOutput", "realComCam", "skyComCamInfo.txt")


class TestModelSim(unittest.TestCase):
    """Test the ModelSim class."""

    def setUp(self):
        os.environ["ISRDIRPATH"] = "ISRDIRPATH"

    @classmethod
    def setUpClass(cls):

        config = Config()
        configObj = MTAOS.Config(config)
        state0Dof = yaml.safe_load(
            MTAOS.getModulePath()
            .joinpath("tests", "testData", "state0inDof.yaml")
            .open()
            .read()
        )
        cls.modelSim = MTAOS.ModelSim(configObj, state0Dof)

    def tearDown(self):

        self.modelSim.resetFWHMSensorData()
        self.modelSim.resetWavefrontCorrection()
        self.modelSim.calcTimeWep.resetRecord()
        self.modelSim.calcTimeOfc.resetRecord()

        try:
            os.environ.pop("ISRDIRPATH")
        except KeyError:
            pass

    def testProcCalibProducts(self):

        start = time.monotonic()
        self.modelSim.procCalibProducts("calibsDir")
        duration = time.monotonic() - start

        self.assertAlmostEqual(duration, 3, places=1)

    def testProcIntraExtraWavefrontError(self):

        self.assertEqual(self._getAvgCalcTimeWep(), 0.0)

        aFilter = 3
        rotAngInDeg = 10.0
        userGain = 0.8
        self._procIntraExtraWavefrontError(aFilter, rotAngInDeg, userGain)

        listOfWfErr = self.modelSim.getListOfWavefrontError()
        self.assertEqual(len(listOfWfErr), 9)

        wep = self.modelSim.wep
        self.assertEqual(wep.getFilter().value, aFilter)
        self.assertEqual(wep.getRotAng(), rotAngInDeg)
        self.assertEqual(self.modelSim.userGain, userGain)

        self.assertGreater(self._getAvgCalcTimeWep(), 14.0)

    def _procIntraExtraWavefrontError(self, aFilter, rotAngInDeg, userGain):

        raInDeg = 0.0
        decInDeg = 0.0
        priVisit = 9006002
        priDir = "priDir"
        secVisit = 9006001
        secDir = "secDir"
        self.modelSim.procIntraExtraWavefrontError(
            raInDeg, decInDeg, aFilter, rotAngInDeg, priVisit, priDir,
            secVisit, secDir, userGain)

    def _getAvgCalcTimeWep(self):

        return self.modelSim.getAvgCalcTimeWep()

    def testCalcCorrectionFromAvgWfErr(self):

        self.assertEqual(self._getAvgCalcTimeOfc(), 0.0)

        aFilter = 3
        rotAngInDeg = 10.0
        userGain = 0.8
        self._procIntraExtraWavefrontError(aFilter, rotAngInDeg, userGain)

        # Mimic the publish of event of MtaosCsc
        self.modelSim.getListOfWavefrontError()

        self.modelSim.calcCorrectionFromAvgWfErr()

        dofAggr = self.modelSim.getDofAggr()
        self.assertNotEqual(np.sum(np.abs(dofAggr)), 0)

        self.assertGreater(self._getAvgCalcTimeOfc(), 0.0)

    def _getAvgCalcTimeOfc(self):

        return self.modelSim.getAvgCalcTimeOfc()

    def testCalcCorrectionFromAvgWfErrException(self):

        self.assertRaisesRegex(RuntimeError,
                               "No data in the collection of taken data.",
                               self.modelSim.calcCorrectionFromAvgWfErr)

        sensorWavefrontData = SensorWavefrontData()
        sensorWavefrontData.setSensorId(96)
        sensorWavefrontData.setAnnularZernikePoly(np.random.rand(19))
        self.modelSim.collectionOfListOfWfErr.append([sensorWavefrontData])

        # Mimic the publish of event of MtaosCsc
        self.modelSim.getListOfWavefrontError()

        self.assertRaisesRegex(RuntimeError,
                               "Equation number < variable number.",
                               self.modelSim.calcCorrectionFromAvgWfErr)

    def testCalcCorrectionFromAvgWfErrMultiExp(self):

        aFilter = 3
        rotAngInDeg = 10.0
        userGain = 0.8
        for idx in range(2):
            self._procIntraExtraWavefrontError(aFilter, rotAngInDeg, userGain)

        self.assertEqual(self.modelSim.collectionOfListOfWfErr.getNumOfData(), 2)
        self.assertEqual(self.modelSim.collectionOfListOfWfErr.getNumOfDataTaken(), 0)

        # Mimic the publish of event of MtaosCsc
        for idx in range(2):
            self.modelSim.getListOfWavefrontError()

        self.assertEqual(self.modelSim.collectionOfListOfWfErr.getNumOfData(), 0)
        self.assertEqual(self.modelSim.collectionOfListOfWfErr.getNumOfDataTaken(), 2)

        self.modelSim.calcCorrectionFromAvgWfErr()

        dofAggr = self.modelSim.getDofAggr()
        self.assertNotEqual(np.sum(np.abs(dofAggr)), 0)

        self.assertGreater(self._getAvgCalcTimeOfc(), 0.0)


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
