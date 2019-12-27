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
import unittest

from lsst.ts.wep.Utility import CamType
from lsst.ts.ofc.Utility import InstName

from lsst.ts.MTAOS.Utility import getModulePath, getConfigDir, getLogDir, \
    getIsrDirPath, getCamType, getInstName, getSchemaDir, getCscName


class TestUtility(unittest.TestCase):
    """Test the Utility functions."""

    def testGetConfigDir(self):

        ansConfigDir = getModulePath().joinpath("policy")
        self.assertEqual(getConfigDir(), ansConfigDir)

    def testGetSchemaDir(self):

        ansSchemaDir = getModulePath().joinpath("schema")
        self.assertEqual(getSchemaDir(), ansSchemaDir)

    def testGetLogDir(self):

        ansLogDir = getModulePath().joinpath("logs")
        self.assertEqual(getLogDir(), ansLogDir)

    def testGetIsrDirPathNotAssigned(self):

        isrDir = getIsrDirPath()
        self.assertEqual(isrDir, None)

    def testGetIsrDirPath(self):

        ISRDIRPATH = "/path/to/isr/dir"
        os.environ["ISRDIRPATH"] = ISRDIRPATH

        isrDir = getIsrDirPath()
        self.assertEqual(isrDir, Path(ISRDIRPATH))

        os.environ.pop("ISRDIRPATH")

    def testGetCamType(self):

        self.assertEqual(getCamType("lsstCam"), CamType.LsstCam)
        self.assertEqual(getCamType("lsstFamCam"), CamType.LsstFamCam)
        self.assertEqual(getCamType("comcam"), CamType.ComCam)

        self.assertRaises(ValueError, getCamType, "wrongType")

    def testGetInst(self):

        self.assertEqual(getInstName("lsst"), InstName.LSST)
        self.assertEqual(getInstName("comcam"), InstName.COMCAM)
        self.assertEqual(getInstName("sh"), InstName.SH)
        self.assertEqual(getInstName("cmos"), InstName.CMOS)

        self.assertRaises(ValueError, getInstName, "wrongName")

    def testGetCscName(self):

        cscName = getCscName()
        self.assertEqual(cscName, "MTAOS")


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
