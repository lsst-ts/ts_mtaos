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
import logging
import os
import tempfile
import time
import unittest
from logging.handlers import RotatingFileHandler
from pathlib import Path

import numpy as np
import pytest
from lsst.daf.butler.registry.interfaces import DatabaseConflictError
from lsst.obs.lsst.translators.lsstCam import LsstCamTranslator
from lsst.ts import mtaos
from lsst.ts.wep.task.cutOutDonutsCwfsTask import CutOutDonutsCwfsTask
from lsst.ts.wep.utils import getModulePath as getModulePathWep


class TestUtility(unittest.TestCase):
    """Test the Utility functions."""

    def setUp(self):
        self.dataDir = tempfile.TemporaryDirectory(
            dir=mtaos.getModulePath().joinpath("tests").as_posix()
        )

    def tearDown(self):
        self.dataDir.cleanup()

    def testGetModulePath(self):
        modulePath = mtaos.getModulePath()
        self.assertTrue(modulePath.exists())
        self.assertTrue("ts_mtaos" in modulePath.name.lower())

    def testGetConfigDir(self):
        ansConfigDir = mtaos.getModulePath().joinpath("policy")
        self.assertEqual(mtaos.getConfigDir(), ansConfigDir)

    def testGetLogDir(self):
        ansLogDir = mtaos.getModulePath().joinpath("logs")
        self.assertEqual(mtaos.getLogDir(), ansLogDir)
        self.assertTrue(ansLogDir.exists())

    def testGetIsrDirPathNotAssigned(self):
        isrDir = mtaos.getIsrDirPath()
        self.assertEqual(isrDir, None)

    def testGetIsrDirPath(self):
        ISRDIRPATH = "/path/to/isr/dir"
        os.environ["ISRDIRPATH"] = ISRDIRPATH

        isrDir = mtaos.getIsrDirPath()
        self.assertEqual(isrDir, Path(ISRDIRPATH))

        os.environ.pop("ISRDIRPATH")

    def testGetCscName(self):
        cscName = mtaos.getCscName()
        self.assertEqual(cscName, "MTAOS")

    def testAddRotFileHandler(self):
        log = logging.Logger("test")
        dataDirPath = self.dataDir.name
        filePath = Path(dataDirPath).joinpath("test.log")
        mtaos.addRotFileHandler(
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

    def test_get_formatted_corner_wavefront_sensors_ids(self):
        mtaos_cwfs_detector_ids = set(
            [
                int(detector_id)
                for detector_id in mtaos.get_formatted_corner_wavefront_sensors_ids().split(
                    ","
                )
            ]
        )

        detector_mapping = LsstCamTranslator.detector_mapping()

        cwfs_task = CutOutDonutsCwfsTask()

        expected_cwfs_detector_ids = set(
            [
                detector_mapping[cwfs_detector_name][0]
                for cwfs_detector_name in cwfs_task.extraFocalNames
                + cwfs_task.intraFocalNames
            ]
        )

        assert mtaos_cwfs_detector_ids == expected_cwfs_detector_ids

    def test_timeit(self):
        @mtaos.timeit
        def my_retval(arg1, arg2, arg3, arg4, sleep_time, **kwargs):
            time.sleep(sleep_time)
            return arg1, arg2, arg3, arg4

        @mtaos.timeit
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

    @pytest.mark.xfail(
        reason="There is something wrong with the test data that causes this to fail.",
        raises=DatabaseConflictError,
    )
    def test_define_visit(self) -> None:
        data_path = os.path.join(
            getModulePathWep(), "tests", "testData", "gen3TestRepo"
        )

        mtaos.define_visit(
            data_path=data_path,
            collections=["LSSTCam/raw/all"],
            instrument_name="LSSTCam",
            exposures_str="exposure IN (4021123106001, 4021123106002)",
        )


if __name__ == "__main__":
    # Do the unit test
    unittest.main()
