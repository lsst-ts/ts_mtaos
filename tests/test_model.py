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
import unittest
import numpy as np

from lsst.ts.wep.ctrlIntf.WEPCalculationOfComCam import WEPCalculationOfComCam
from lsst.ts.wep.Utility import runProgram
from lsst.ts.ofc.ctrlIntf.OFCCalculationOfComCam import OFCCalculationOfComCam
from lsst.ts.ofc.ctrlIntf.M1M3Correction import M1M3Correction
from lsst.ts.ofc.ctrlIntf.M2Correction import M2Correction

from lsst.ts.MTAOS.Utility import getModulePath
from lsst.ts.MTAOS.Model import Model


class TestModel(unittest.TestCase):
    """Test the Model class."""

    @classmethod
    def setUpClass(cls):

        cls.dataDir = getModulePath().joinpath("tests", "tmp")
        cls.isrDir = cls.dataDir.joinpath("input")

        # Let the MTAOS to set WEP based on this path variable
        os.environ["ISRDIRPATH"] = cls.isrDir.as_posix()

        cls.settingFilePath = getModulePath().joinpath("policy", "default.yaml")
        cls.model = Model(cls.settingFilePath)

    def setUp(self):
        os.environ["ISRDIRPATH"] = self.isrDir.as_posix()
        self._makeDir(self.isrDir)

    def _makeDir(self, directory):

        Path(directory).mkdir(parents=True, exist_ok=True)

    def tearDown(self):

        self.model.resetFWHMSensorData()
        self.model.resetWavefrontCorrection()

        shutil.rmtree(self.dataDir)
        try:
            os.environ.pop("ISRDIRPATH")
        except KeyError:
            pass

    def testInitOfModelMTAOS(self):

        wep = self.model.wep
        self.assertTrue(isinstance(wep, WEPCalculationOfComCam))

        isrDir = wep.getIsrDir()
        self.assertEqual(isrDir, self.isrDir.as_posix())

        ofc = self.model.ofc
        self.assertTrue(isinstance(ofc, OFCCalculationOfComCam))

    def testGetSettingFilePath(self):

        settingFilePath = self.model.getSettingFilePath()

        self.assertEqual(settingFilePath, self.settingFilePath)

    def testGetListOfWavefrontError(self):

        listOfWfErr = self.model.getListOfWavefrontError()
        self.assertEqual(listOfWfErr, [])

    def testGetListOfFWHMSensorData(self):

        listOfFWHMSensorData = self.model.getListOfFWHMSensorData()
        self.assertEqual(listOfFWHMSensorData, [])

    def testSetFWHMSensorData(self):

        self.model.setFWHMSensorData(1, np.zeros(2))

        listOfFWHMSensorData = self.model.getListOfFWHMSensorData()
        self.assertEqual(len(listOfFWHMSensorData), 1)

        self.model.setFWHMSensorData(2, np.zeros(2))
        self.assertEqual(len(listOfFWHMSensorData), 2)

    def testSetFWHMSensorDataRepeatSensorId(self):

        self.model.setFWHMSensorData(1, np.zeros(2))

        newFwhmValues = np.array([1, 2, 3])
        self.model.setFWHMSensorData(1, newFwhmValues)

        listOfFWHMSensorData = self.model.getListOfFWHMSensorData()
        self.assertEqual(len(listOfFWHMSensorData), 1)

        fwhmValuesInList = listOfFWHMSensorData[0].getFwhmValues()
        self.assertTrue((fwhmValuesInList == newFwhmValues).all())

    def testResetFWHMSensorData(self):

        self.model.setFWHMSensorData(1, np.zeros(2))
        self.model.resetFWHMSensorData()

        listOfFWHMSensorData = self.model.getListOfFWHMSensorData()
        self.assertEqual(listOfFWHMSensorData, [])

    def testGetSettingFilePathStr(self):

        self.modelTemp = Model(self.settingFilePath.as_posix())

        filePathInModel = self.modelTemp.getSettingFilePath()
        self.assertTrue(isinstance(filePathInModel, Path))
        self.assertFalse(isinstance(filePathInModel, str))

    def testGetDofAggr(self):

        dofAggr = self.model.getDofAggr()
        self.assertEqual(len(dofAggr), 50)

    def testGetDofVisit(self):

        dofVisit = self.model.getDofVisit()
        self.assertEqual(len(dofVisit), 50)

    def testGetDefaultSkyFile(self):

        filePath = self.model._getDefaultSkyFile()
        self.assertEqual(filePath.name, "skyComCamInfo.txt")

    def testGetM2HexCorr(self):

        x, y, z, u, v, w = self.model.getM2HexCorr()
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(z, 0)
        self.assertEqual(u, 0)
        self.assertEqual(v, 0)
        self.assertEqual(w, 0)

    def testGetCamHexCorr(self):

        x, y, z, u, v, w = self.model.getCamHexCorr()
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(z, 0)
        self.assertEqual(u, 0)
        self.assertEqual(v, 0)
        self.assertEqual(w, 0)

    def testGetM1M3ActCorr(self):

        actCorr = self.model.getM1M3ActCorr()
        self.assertEqual(len(actCorr), M1M3Correction.NUM_OF_ACT)

    def testGetM2ActCorr(self):

        actCorr = self.model.getM2ActCorr()
        self.assertEqual(len(actCorr), M2Correction.NUM_OF_ACT)

    def testProcIntraExtraWavefrontError(self):

        self._ingestCalibs()

        raInDeg = 0.0
        decInDeg = 0.0
        rotAngInDeg = 0.0
        aFilter = 7
        priVisit = 9006002
        secVisit = 9006001
        userGain = 1

        rawImgDir = getModulePath().joinpath(
            "tests", "testData", "phosimOutput", "realComCam")
        priDir = rawImgDir.joinpath("intra").as_posix()
        secDir = rawImgDir.joinpath("extra").as_posix()

        self.model.procIntraExtraWavefrontError(
            raInDeg, decInDeg, aFilter, rotAngInDeg, priVisit, priDir,
            secVisit, secDir, userGain)

        self.assertEqual(len(self.model.getListOfWavefrontError()), 9)

        dofAggr = self.model.getDofAggr()
        self.assertNotEqual(np.sum(np.abs(dofAggr)), 0)

        dofVisit = self.model.getDofVisit()
        self.assertNotEqual(np.sum(np.abs(dofVisit)), 0)

        xM2, yM2, zM2, uM2, vM2, wM2 = self.model.getM2HexCorr()
        self.assertNotEqual(xM2, 0)
        self.assertNotEqual(yM2, 0)
        self.assertNotEqual(zM2, 0)
        self.assertNotEqual(uM2, 0)
        self.assertNotEqual(vM2, 0)
        self.assertEqual(wM2, 0)

        xCam, yCam, zCam, uCam, vCam, wCam = self.model.getCamHexCorr()
        self.assertNotEqual(xCam, 0)
        self.assertNotEqual(yCam, 0)
        self.assertNotEqual(zCam, 0)
        self.assertNotEqual(uCam, 0)
        self.assertNotEqual(vCam, 0)
        self.assertEqual(wCam, 0)

        actCorrM1M3 = self.model.getM1M3ActCorr()
        self.assertNotEqual(np.sum(np.abs(actCorrM1M3)), 0)

        actCorrM2 = self.model.getM2ActCorr()
        self.assertNotEqual(np.sum(np.abs(actCorrM2)), 0)

    def _ingestCalibs(self):

        # Make fake gain images
        fakeFlatDir = self.dataDir.joinpath("fake_flats")
        self._makeDir(fakeFlatDir)

        sensorNameList = self._getComCamSensorNameList()
        detector = " ".join(sensorNameList)
        self._genFakeFlat(fakeFlatDir, detector)

        # Do the ingestion
        self.model.procCalibProducts(fakeFlatDir)

    def _getComCamSensorNameList(self):

        sensorNameList = ["R22_S00", "R22_S01", "R22_S02", "R22_S10", "R22_S11",
                          "R22_S12", "R22_S20", "R22_S21", "R22_S22"]
        return sensorNameList

    def _genFakeFlat(self, fakeFlatDir, detector):

        currWorkDir = self._getCurrWorkDir()

        self._changeWorkDir(fakeFlatDir)
        self._makeFakeFlat(detector)
        self._changeWorkDir(currWorkDir)

    def _getCurrWorkDir(self):

        return os.getcwd()

    def _changeWorkDir(self, dirPath):

        os.chdir(dirPath)

    def _makeFakeFlat(self, detector):

        command = "makeGainImages.py"
        argstring = "--detector_list %s" % detector
        runProgram(command, argstring=argstring)


if __name__ == "__main__":

    # Do the unit test
    unittest.main()