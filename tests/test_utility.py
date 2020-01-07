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
import logging
import tempfile
import shutil
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler
import unittest

from lsst.ts.wep.Utility import CamType
from lsst.ts.ofc.Utility import InstName

from lsst.ts import MTAOS


class TestUtility(unittest.TestCase):
    """Test the Utility functions."""

    def setUp(self):

        self.dataDir = tempfile.TemporaryDirectory(
            dir=MTAOS.getModulePath().joinpath("tests"))

    def tearDown(self):

        shutil.rmtree(self.dataDir.name)

    def testGetModulePath(self):

        modulePath = MTAOS.getModulePath()
        self.assertTrue(modulePath.exists())
        self.assertEqual(modulePath.name, "ts_MTAOS")

    def testGetConfigDir(self):

        ansConfigDir = MTAOS.getModulePath().joinpath("policy")
        self.assertEqual(MTAOS.getConfigDir(), ansConfigDir)

    def testGetSchemaDir(self):

        ansSchemaDir = MTAOS.getModulePath().joinpath("schema")
        self.assertEqual(MTAOS.getSchemaDir(), ansSchemaDir)

    def testGetLogDir(self):

        ansLogDir = MTAOS.getModulePath().joinpath("logs")
        self.assertEqual(MTAOS.getLogDir(), ansLogDir)

    def testGetIsrDirPathNotAssigned(self):

        isrDir = MTAOS.getIsrDirPath()
        self.assertEqual(isrDir, None)

    def testGetIsrDirPath(self):

        ISRDIRPATH = "/path/to/isr/dir"
        os.environ["ISRDIRPATH"] = ISRDIRPATH

        isrDir = MTAOS.getIsrDirPath()
        self.assertEqual(isrDir, Path(ISRDIRPATH))

        os.environ.pop("ISRDIRPATH")

    def testGetCamType(self):

        self.assertEqual(MTAOS.getCamType("lsstCam"), CamType.LsstCam)
        self.assertEqual(MTAOS.getCamType("lsstFamCam"), CamType.LsstFamCam)
        self.assertEqual(MTAOS.getCamType("comcam"), CamType.ComCam)

        self.assertRaises(ValueError, MTAOS.getCamType, "wrongType")

    def testGetInst(self):

        self.assertEqual(MTAOS.getInstName("lsst"), InstName.LSST)
        self.assertEqual(MTAOS.getInstName("comcam"), InstName.COMCAM)
        self.assertEqual(MTAOS.getInstName("sh"), InstName.SH)
        self.assertEqual(MTAOS.getInstName("cmos"), InstName.CMOS)

        self.assertRaises(ValueError, MTAOS.getInstName, "wrongName")

    def testGetCscName(self):

        cscName = MTAOS.getCscName()
        self.assertEqual(cscName, "MTAOS")

    def testAddRotFileHandler(self):

        log = logging.Logger("test")
        dataDirPath = self.dataDir.name
        filePath = Path(dataDirPath).joinpath("test.log")
        MTAOS.addRotFileHandler(log, filePath, maxBytes=1e3, backupCount=5)

        handlers = log.handlers
        self.assertEqual(len(handlers), 1)
        self.assertTrue(isinstance(handlers[0], RotatingFileHandler))

        for counter in range(20):
            log.critical("Test file rotation.")
            time.sleep(0.2)

        numOfFile = self._getNumOfFileInFolder(dataDirPath)
        self.assertEqual(numOfFile, 2)

    def _getNumOfFileInFolder(self, folder):

        items = Path(folder).glob("*")
        files = [aItem for aItem in items if aItem.is_file()]

        return len(files)


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
