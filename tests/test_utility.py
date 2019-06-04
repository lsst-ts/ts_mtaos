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

from lsst.ts.MTAOS.Utility import getModulePath, getConfigDir, getIsrDirPath


class TestUtility(unittest.TestCase):
    """Test the Utility functions."""

    def testGetConfigDir(self):

        ansConfigDir = os.path.join(getModulePath(), "policy")
        self.assertEqual(getConfigDir(), ansConfigDir)

    def testGetIsrDirPathNotAssigned(self):

        isrDir = getIsrDirPath()
        self.assertEqual(isrDir, None)

    def testGetIsrDirPath(self):

        ISRDIRPATH = "/path/to/isr/dir"
        os.environ["ISRDIRPATH"] = ISRDIRPATH

        isrDir = getIsrDirPath()
        self.assertEqual(isrDir, ISRDIRPATH)

        os.environ.pop("ISRDIRPATH")


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
