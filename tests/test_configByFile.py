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

from lsst.ts.MTAOS.ConfigByFile import ConfigByFile
from lsst.ts.MTAOS.Utility import getModulePath

from lsst.ts.wep.Utility import CamType
from lsst.ts.ofc.Utility import InstName


class TestConfigByFile(unittest.TestCase):
    """Test the ConfigByFile class."""

    def setUp(self):

        os.environ["ISRDIRPATH"] = os.path.join(os.sep, "isrDir")

        config = getModulePath().joinpath("tests", "testData", "default.yaml")
        self.configByFile = ConfigByFile(config)

    def tearDown(self):

        try:
            os.environ.pop("ISRDIRPATH")
        except KeyError:
            pass

    def testGetCamTypeInConfig(self):

        camType = self.configByFile.getCamTypeInConfig()
        self.assertEqual(camType, CamType.ComCam)

    def testGetInstNameInConfig(self):

        instName = self.configByFile.getInstNameInConfig()
        self.assertEqual(instName, InstName.COMCAM)

    def testGetIsrDirWithEnvPath(self):

        isrDir = self.configByFile.getIsrDir()
        self.assertEqual(isrDir, os.environ["ISRDIRPATH"])

    def testGetIsrDirWithoutEnvPath(self):

        os.environ.pop("ISRDIRPATH")

        with self.assertWarns(UserWarning):
            isrDir = self.configByFile.getIsrDir()

        self.assertEqual(isrDir, "/home/lsst/input")

    def testGetDefaultSkyFileInConfig(self):

        skyFilePath = self.configByFile.getDefaultSkyFileInConfig()
        self.assertTrue(skyFilePath.exists())


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
