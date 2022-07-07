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

from lsst.ts import mtaos


class Config(object):
    """Config Class for the test."""

    def __init__(self, hasSkyFile=True, hasState0Dof=True):

        self.camera = "comcam"
        self.instrument = "comcam"
        self.defaultIsrDir = "/home/lsst/input"

        if hasSkyFile:
            self.defaultSkyFilePath = (
                "tests/testData/phosimOutput/realComCam/skyComCamInfo.txt"
            )

        if hasState0Dof:
            self.state0DofFilePath = "tests/testData/state0inDof.yaml"


class TestConfigByObj(unittest.TestCase):
    """Test the Config class with an object."""

    def setUp(self):

        os.environ["ISRDIRPATH"] = os.path.join(os.sep, "isrDir")

        self.configObj = mtaos.Config(Config())

    def tearDown(self):

        try:
            os.environ.pop("ISRDIRPATH")
        except KeyError:
            pass

    def testGetCamType(self):

        camType = self.configObj.getCamType()
        self.assertEqual(camType, CamType.ComCam)

    def testGetInstName(self):

        instName = self.configObj.getInstName()
        self.assertEqual(instName, "comcam")

    def testGetIsrDirWithEnvPath(self):

        isrDir = self.configObj.getIsrDir()
        self.assertEqual(isrDir, os.environ["ISRDIRPATH"])

    def testGetIsrDirWithoutEnvPath(self):

        os.environ.pop("ISRDIRPATH")

        with self.assertWarns(UserWarning):
            isrDir = self.configObj.getIsrDir()

        self.assertEqual(isrDir, self.configObj.configObj.defaultIsrDir)

    def testGetDefaultSkyFile(self):

        skyFilePath = self.configObj.getDefaultSkyFile()
        self.assertTrue(skyFilePath.exists())

    def testGetDefaultSkyFileNot(self):

        config = Config(hasSkyFile=False)
        configObj = mtaos.Config(config)

        skyFilePath = configObj.getDefaultSkyFile()
        self.assertTrue(skyFilePath is None)

    def testGetState0DofFile(self):

        state0DofFilePath = self.configObj.getState0DofFile()
        self.assertTrue(state0DofFilePath.exists())

    def testGetState0DofFileNot(self):

        config = Config(hasState0Dof=False)
        configObj = mtaos.Config(config)

        state0DofFile = configObj.getState0DofFile()
        self.assertTrue(state0DofFile is None)


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
