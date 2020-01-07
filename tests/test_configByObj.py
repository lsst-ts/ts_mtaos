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
import unittest

from lsst.ts.wep.Utility import CamType
from lsst.ts.ofc.Utility import InstName

from lsst.ts import MTAOS


class Config(object):
    """Config Class for the test."""

    def __init__(self, hasSkyFile=True):

        self.camera = "comcam"
        self.instrument = "comcam"
        self.defaultIsrDir = "/home/lsst/input"

        if (hasSkyFile):
            self.defaultSkyFilePath = "tests/testData/phosimOutput/realComCam/skyComCamInfo.txt"


class TestConfigByObj(unittest.TestCase):
    """Test the ConfigByObj class."""

    def setUp(self):

        os.environ["ISRDIRPATH"] = os.path.join(os.sep, "isrDir")

        config = Config()
        self.configByObj = MTAOS.ConfigByObj(config)

    def tearDown(self):

        try:
            os.environ.pop("ISRDIRPATH")
        except KeyError:
            pass

    def testGetCamTypeInConfig(self):

        camType = self.configByObj.getCamTypeInConfig()
        self.assertEqual(camType, CamType.ComCam)

    def testGetInstNameInConfig(self):

        instName = self.configByObj.getInstNameInConfig()
        self.assertEqual(instName, InstName.COMCAM)

    def testGetIsrDirWithEnvPath(self):

        isrDir = self.configByObj.getIsrDir()
        self.assertEqual(isrDir, os.environ["ISRDIRPATH"])

    def testGetIsrDirWithoutEnvPath(self):

        os.environ.pop("ISRDIRPATH")

        with self.assertWarns(UserWarning):
            isrDir = self.configByObj.getIsrDir()

        self.assertEqual(isrDir, self.configByObj.configObj.defaultIsrDir)

    def testGetDefaultSkyFileInConfig(self):

        skyFilePath = self.configByObj.getDefaultSkyFileInConfig()
        self.assertTrue(skyFilePath.exists())

    def testGetDefaultSkyFileNotInConfig(self):

        config = Config(hasSkyFile=False)
        configByObj = MTAOS.ConfigByObj(config)

        skyFilePath = configByObj.getDefaultSkyFileInConfig()
        self.assertTrue(skyFilePath is None)


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
