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
from pathlib import Path
import shutil
import time
import numpy as np
import unittest

from lsst.ts.MTAOS.Utility import getModulePath
from lsst.ts.MTAOS.ConfigByObj import ConfigByObj
from lsst.ts.MTAOS.ModelSim import ModelSim


class Config(object):
    """Config Class for the test."""

    def __init__(self):

        self.camera = "comcam"
        self.instrument = "comcam"
        self.defaultIsrDir = "/home/lsst/input"
        self.defaultSkyFilePath = "tests/testData/phosimOutput/realComCam/skyComCamInfo.txt"


class TestModelSim(unittest.TestCase):
    """Test the ModelSim class."""

    def setUp(self):

        self.dataDir = getModulePath().joinpath("tests", "tmp")
        self.isrDir = self.dataDir.joinpath("input")
        os.environ["ISRDIRPATH"] = self.isrDir.as_posix()
        self._makeDir(self.isrDir)

        config = Config()
        configByObj = ConfigByObj(config)
        self.modelSim = ModelSim(configByObj)

    def _makeDir(self, directory):

        Path(directory).mkdir(parents=True, exist_ok=True)

    def tearDown(self):

        self.modelSim.resetFWHMSensorData()
        self.modelSim.resetWavefrontCorrection()

        shutil.rmtree(self.dataDir)
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
        self.assertEqual(self._getAvgCalcTimeOfc(), 0.0)

        raInDeg = 0.0
        decInDeg = 0.0
        aFilter = 7
        rotAngInDeg = 0.0
        priVisit = 9006002
        priDir = "priDir"
        secVisit = 9006001
        secDir = "secDir"
        userGain = 1
        self.modelSim.procIntraExtraWavefrontError(
            raInDeg, decInDeg, aFilter, rotAngInDeg, priVisit, priDir,
            secVisit, secDir, userGain)

        listOfWfErr = self.modelSim.getListOfWavefrontError()
        self.assertEqual(len(listOfWfErr), 9)

        dofAggr = self.modelSim.getDofAggr()
        self.assertNotEqual(np.sum(np.abs(dofAggr)), 0)

        self.assertGreater(self._getAvgCalcTimeWep(), 14.0)
        self.assertGreater(self._getAvgCalcTimeOfc(), 0.0)

    def _getAvgCalcTimeWep(self):

        return self.modelSim.getAvgCalcTimeWep()

    def _getAvgCalcTimeOfc(self):

        return self.modelSim.getAvgCalcTimeOfc()


if __name__ == "__main__":

    # Do the unit test
    unittest.main()