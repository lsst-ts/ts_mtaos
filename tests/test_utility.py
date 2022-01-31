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

import asyncio
import os
import logging
import tempfile
import time
import unittest

import numpy as np
from pathlib import Path
from logging.handlers import RotatingFileHandler

from lsst.ts.wep.Utility import CamType

from lsst.ts import MTAOS


class TestUtility(unittest.TestCase):
    """Test the Utility functions."""

    def setUp(self):

        self.dataDir = tempfile.TemporaryDirectory(
            dir=MTAOS.getModulePath().joinpath("tests").as_posix()
        )

    def tearDown(self):

        self.dataDir.cleanup()

    def testGetModulePath(self):

        modulePath = MTAOS.getModulePath()
        self.assertTrue(modulePath.exists())
        self.assertTrue("ts_MTAOS" in modulePath.name)

    def testGetConfigDir(self):

        ansConfigDir = MTAOS.getModulePath().joinpath("policy")
        self.assertEqual(MTAOS.getConfigDir(), ansConfigDir)

    def testGetLogDir(self):

        ansLogDir = MTAOS.getModulePath().joinpath("logs")
        self.assertEqual(MTAOS.getLogDir(), ansLogDir)
        self.assertTrue(ansLogDir.exists())

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

    def testGetCscName(self):

        cscName = MTAOS.getCscName()
        self.assertEqual(cscName, "MTAOS")

    def testAddRotFileHandler(self):

        log = logging.Logger("test")
        dataDirPath = self.dataDir.name
        filePath = Path(dataDirPath).joinpath("test.log")
        MTAOS.addRotFileHandler(
            log, filePath, logging.DEBUG, maxBytes=1e3, backupCount=5
        )

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

    def test_timeit(self):
        @MTAOS.timeit
        def my_retval(arg1, arg2, arg3, arg4, sleep_time, **kwargs):
            time.sleep(sleep_time)
            return arg1, arg2, arg3, arg4

        @MTAOS.timeit
        async def amy_retval(arg1, arg2, arg3, arg4, sleep_time, **kwargs):
            await asyncio.sleep(sleep_time)
            return arg1, arg2, arg3, arg4

        exec_time = {}
        sleep_time = 0.1

        for i in range(10):
            r_a1, r_a2, r_a3, r_a4 = my_retval(
                arg1="this",
                arg2="is",
                arg3="a",
                arg4="test",
                sleep_time=sleep_time,
                log_time=exec_time,
            )
            self.assertEqual(r_a1, "this")
            self.assertEqual(r_a2, "is")
            self.assertEqual(r_a3, "a")
            self.assertEqual(r_a4, "test")

        for i in range(10):
            r_a1, r_a2, r_a3, r_a4 = asyncio.run(
                amy_retval(
                    arg1="this",
                    arg2="is",
                    arg3="a",
                    arg4="test",
                    sleep_time=sleep_time,
                    log_time=exec_time,
                )
            )
            self.assertEqual(r_a1, "this")
            self.assertEqual(r_a2, "is")
            self.assertEqual(r_a3, "a")
            self.assertEqual(r_a4, "test")

        self.assertTrue("MY_RETVAL" in exec_time)
        self.assertTrue("AMY_RETVAL" in exec_time)

        self.assertAlmostEqual(sleep_time, np.mean(exec_time["MY_RETVAL"]), 2)
        self.assertAlmostEqual(sleep_time, np.mean(exec_time["AMY_RETVAL"]), 2)


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
