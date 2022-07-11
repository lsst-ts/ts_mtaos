# This file is part of ts_mtaos.
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


class TestConfigByFile(unittest.TestCase):
    """Test the Config class with a file."""

    def setUp(self):

        os.environ["ISRDIRPATH"] = os.path.join(os.sep, "isrDir")

        configFile = mtaos.getModulePath().joinpath("tests", "testData", "default.yaml")
        self.config = mtaos.Config(str(configFile))

    def tearDown(self):

        try:
            os.environ.pop("ISRDIRPATH")
        except KeyError:
            pass

    def testGetCamType(self):

        camType = self.config.getCamType()
        self.assertEqual(camType, CamType.ComCam)

    def testGetInstName(self):

        instName = self.config.getInstName()
        self.assertEqual(instName, "comcam")

    def testGetIsrDirWithEnvPath(self):

        isrDir = self.config.getIsrDir()
        self.assertEqual(isrDir, os.environ["ISRDIRPATH"])

    def testGetIsrDirWithoutEnvPath(self):

        os.environ.pop("ISRDIRPATH")

        with self.assertWarns(UserWarning):
            isrDir = self.config.getIsrDir()

        self.assertEqual(isrDir, "/home/lsst/input")

    def testGetDefaultSkyFile(self):

        skyFilePath = self.config.getDefaultSkyFile()
        self.assertTrue(skyFilePath.exists())

    def testGetState0DofFile(self):

        dofFileName = self.config.getState0DofFile()
        self.assertTrue(dofFileName.exists())


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
