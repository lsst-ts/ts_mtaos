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

import time
import unittest

from lsst.ts import MTAOS


class TestCalcTime(unittest.TestCase):
    """Test the CalcTime class."""

    def setUp(self):

        self.calcTime = MTAOS.CalcTime()

    def testPutRecord(self):

        record = 2.0
        self.calcTime.putRecord(record)

        recordInCalcTime = self.calcTime.getRecordLatest()
        self.assertEqual(recordInCalcTime, record)

    def testGetRecordLatestWithoutRecord(self):

        self.assertEqual(self.calcTime.getRecordLatest(), None)

    def testGetRecordLatestWithRecord(self):

        self.calcTime.putRecord(1.0)
        self.calcTime.putRecord(2.0)

        recordLatest = 3.0
        self.calcTime.putRecord(recordLatest)

        self.assertEqual(self.calcTime.getRecordLatest(), recordLatest)

    def testResetRecord(self):

        self.calcTime.putRecord(1.0)

        self.calcTime.resetRecord()

        self.assertEqual(self.calcTime.getRecordLatest(), None)

    def testGetAvgTimeWithRecord(self):

        self.calcTime.putRecord(1.0)
        self.calcTime.putRecord(2.0)

        avgTime = self.calcTime.getAvgTime()
        self.assertEqual(avgTime, 1.5)

    def testGetAvgTimeWithoutRecord(self):

        self.assertEqual(self.calcTime.getAvgTime(), 0.0)

    def testEvalCalcTimeAndPutRecord(self):

        # Try to put 1 argument
        self.calcTime.evalCalcTimeAndPutRecord(self._testFunc, 2)

        timeLatest = self.calcTime.getRecordLatest()
        self.assertGreater(timeLatest, 2.0)

        # Try to put 2 arguments
        self.calcTime.evalCalcTimeAndPutRecord(self._testFunc, 2, 1.5)

        timeLatest = self.calcTime.getRecordLatest()
        self.assertGreater(timeLatest, 3.0)

    def _testFunc(self, a, defaultTime=1.0):
        sleepTime = a * defaultTime
        time.sleep(sleepTime)


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
