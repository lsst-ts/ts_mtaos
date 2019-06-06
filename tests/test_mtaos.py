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
import shutil
import unittest

from lsst.ts.wep.Utility import runProgram, FilterType, CamType
from lsst.ts.ofc.Utility import InstName

from lsst.ts.MTAOS import MTAOS
from lsst.ts.MTAOS.Utility import getModulePath


class TestMTAOS(unittest.TestCase):
    """Test the MTAOS class."""

    def setUp(self):

        os.environ["ISRDIRPATH"] = self.isrDir
        self._makeDir(self.isrDir)

    def _makeDir(self, directory):

        if (not os.path.exists(directory)):
            os.makedirs(directory)

    @classmethod
    def setUpClass(cls):

        cls.dataDir = os.path.join(getModulePath(), "tests", "tmp")
        cls.isrDir = os.path.join(cls.dataDir, "input")

        # Let the MTAOS to set WEP based on this path variable
        os.environ["ISRDIRPATH"] = cls.isrDir

        cls.mtaos = MTAOS()

    def tearDown(self):

        shutil.rmtree(self.dataDir)
        try:
            os.environ.pop("ISRDIRPATH")
        except KeyError:
            pass

    def testGetNumOfDof(self):

        numOfDof = self.mtaos.getNumOfDof()
        self.assertEqual(numOfDof, 50)

    def testGetNumOfZk(self):

        numOfZk = self.mtaos.getNumOfZk()
        self.assertEqual(numOfZk, 19)

    def testGetCamType(self):

        camType = self.mtaos.getCamType()
        self.assertEqual(camType, CamType.ComCam)

    def testGetInstName(self):

        instName = self.mtaos.getInstName()
        self.assertEqual(instName, InstName.COMCAM)

    def testGetIsrDirByPathVar(self):

        isrDir = self.mtaos.getIsrDir()
        self.assertEqual(isrDir, self.isrDir)

    def testGetIsrDirBySettingFile(self):

        os.environ.pop("ISRDIRPATH")

        isrDir = self.mtaos.getIsrDir()
        self.assertEqual(isrDir, "/home/lsst/input")

    def testGetDefaultSkyFile(self):

        defaultSkyFilePath = self.mtaos.getDefaultSkyFile()

        ansSkyFilePath = os.path.join(getModulePath(), "tests", "testData",
                                      "phosimOutput", "realComCam",
                                      "skyComCamInfo.txt")
        self.assertEqual(defaultSkyFilePath, ansSkyFilePath)

    def testRunWepAndOfc(self):

        # Calculate the wavefront error
        self._ingestCalibs()

        intraVisit = 9006002
        extraVisit = 9006001

        rawImgDir = os.path.join(getModulePath(), "tests", "testData",
                                 "phosimOutput", "realComCam")
        intraRawDir = os.path.join(rawImgDir, "intra")
        extraRawDir = os.path.join(rawImgDir, "extra")
        intraExposureData, extraExposureData = self.mtaos._collectRawExpData(
            intraVisit, intraRawDir, secondaryVisit=extraVisit,
            secondaryDirectory=extraRawDir)

        fieldRA = 0.0
        fieldDEC = 0.0
        cameraRotation = 0.0
        fieldFilter = FilterType.REF
        wavefrontData = self.mtaos._calcWavefrontError(
            fieldRA, fieldDEC, fieldFilter, cameraRotation, intraExposureData,
            extraRawExpData=extraExposureData)

        self.assertEqual(len(wavefrontData), 9)

        # Need to modify this step in the final after modifying the function of
        # convertWavefrontDataToWavefrontError
        # At this moment, just do this as a sloppy fix
        self.mtaos.wavefrontError = wavefrontData

        # Calculate the DOF
        self.mtaos._calcCorrection(fieldFilter, cameraRotation, 1, [])

        ofc = self.mtaos.getOfc()
        aggregatedDoF = ofc.getStateAggregated()

        self.assertEqual(len(aggregatedDoF), 50)
        self.assertNotEqual(aggregatedDoF[0], 0)

    def _ingestCalibs(self):

        # Make fake gain images
        fakeFlatDir = os.path.join(self.dataDir, "fake_flats")
        self._makeDir(fakeFlatDir)

        sensorNameList = self._getComCamSensorNameList()
        detector = " ".join(sensorNameList)
        self._genFakeFlat(fakeFlatDir, detector)

        # Do the ingestion
        wep = self.mtaos.getWep()
        wep.ingestCalibs(fakeFlatDir)

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
