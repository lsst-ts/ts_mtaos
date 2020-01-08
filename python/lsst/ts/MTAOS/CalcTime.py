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

__all__ = ["CalcTime"]

import time
import numpy as np


class CalcTime(object):

    def __init__(self):
        """Initialize the calculation time class."""

        # Collection of calculation times
        self._calcTimes = []

    def putRecord(self, record):
        """Put the record of calculation time.

        Parameters
        ----------
        record : float
            Record of calculation time in second.
        """

        self._calcTimes.append(float(record))

    def getRecordLatest(self):
        """Get the latest record.

        Returns
        -------
        float or None
            Latest record in second. Return None if there is no record.
        """

        if (self._recordExists()):
            return self._calcTimes[-1]
        else:
            return None

    def _recordExists(self):
        """Record exists or not.

        Returns
        -------
        bool
            Return True if there is the record. False if no record.
        """

        if (len(self._calcTimes) == 0):
            return False
        else:
            return True

    def resetRecord(self):
        """Reset the record of calculation time."""

        self._calcTimes = []

    def getAvgTime(self):
        """Get the average of calculation time.

        Returns
        -------
        float
            Average of calculation time in second. Return 0.0 if there is no
            record.
        """

        if (self._recordExists()):
            return np.average(self._calcTimes)
        else:
            return 0.0

    def evalCalcTimeAndPutRecord(self, func, *args):
        """Evaluate the calculation time of function in second and put the
        record.

        Parameters
        ----------
        func : object
            Function to evaluate the calculation time.
        *args : any
            Arguments needed in function.
        """

        startTime = time.perf_counter()
        func(*args)
        calcTime = time.perf_counter() - startTime
        self.putRecord(calcTime)


if __name__ == "__main__":
    pass
