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

import unittest
import logging
from pathlib import Path
import shutil
import time

from lsst.ts.MTAOS.Utility import getModulePath
from lsst.ts.MTAOS.InfoLog import InfoLog


class TestInfoLog(unittest.TestCase):
    """Test the InfoLog class."""

    def setUp(self):

        self.dataDir = getModulePath().joinpath("tests", "tmp")
        self._makeDir(self.dataDir)

        self.infoLogName = "InfoLog"
        self.infoLog = InfoLog(name=self.infoLogName)

        self.logFileName = "testLog"
        self.infoLog.setLogFile(self.logFileName, fileDir=self.dataDir)

    def _makeDir(self, directory):

        Path(directory).mkdir(parents=True, exist_ok=True)

    def tearDown(self):

        self.infoLog.setLevel(logging.WARNING)
        shutil.rmtree(self.dataDir)

    def testGetLogger(self):

        logger = self.infoLog.getLogger()
        self.assertEqual(logger.name, self.infoLogName)

    def testGetFileHandlerNotSet(self):

        infoLog = InfoLog()
        self.assertEqual(infoLog.getFileHandler(), None)

    def testGetFileHandler(self):

        logFilePath = self._getLogFilePath()
        self.assertTrue(self.logFileName in logFilePath)

    def _getLogFilePath(self):

        fileHandler = self.infoLog.getFileHandler()
        return fileHandler.baseFilename

    def testSetLevel(self):

        logLevelDefault = logging.WARNING

        logger = self.infoLog.getLogger()
        self.assertEqual(logger.getEffectiveLevel(), logLevelDefault)

        fileHandler = self.infoLog.getFileHandler()
        self.assertEqual(fileHandler.level, logLevelDefault)

        logLevelNew = logging.CRITICAL
        self.infoLog.setLevel(logLevelNew)

        self.assertEqual(logger.getEffectiveLevel(), logLevelNew)
        self.assertEqual(fileHandler.level, logLevelNew)

    def testDebug(self):

        self.infoLog.setLevel(logging.DEBUG)

        msg = "test debug"
        self.infoLog.debug(msg)

        content = self._getLogFileContent()
        self.assertTrue("DEBUG" in content)
        self.assertTrue(msg in content)

        numOfLine = self._getNumOfLineInLogFile()
        self.assertEqual(numOfLine, 1)

    def _getLogFileContent(self):

        logFilePath = self._getLogFilePath()
        with open(logFilePath, "r") as file:
            return file.read()

    def _getNumOfLineInLogFile(self):

        logFilePath = self._getLogFilePath()
        with open(logFilePath, "r") as file:
            return sum(1 for line in file.readlines())

    def testInfo(self):

        self.infoLog.setLevel(logging.INFO)

        msg = "test info"
        self.infoLog.info(msg)

        content = self._getLogFileContent()
        self.assertTrue("INFO" in content)
        self.assertTrue(msg in content)

        numOfLine = self._getNumOfLineInLogFile()
        self.assertEqual(numOfLine, 1)

    def testWarning(self):

        msg = "test warning"
        self.infoLog.warning(msg)

        content = self._getLogFileContent()
        self.assertTrue("WARNING" in content)
        self.assertTrue(msg in content)

        numOfLine = self._getNumOfLineInLogFile()
        self.assertEqual(numOfLine, 1)

    def testError(self):

        msg = "test error"
        self.infoLog.error(msg)

        content = self._getLogFileContent()
        self.assertTrue("ERROR" in content)
        self.assertTrue(msg in content)

        numOfLine = self._getNumOfLineInLogFile()
        self.assertEqual(numOfLine, 1)

    def testCritical(self):

        msg = "test critical"
        self.infoLog.critical(msg)

        content = self._getLogFileContent()
        self.assertTrue("CRITICAL" in content)
        self.assertTrue(msg in content)

        numOfLine = self._getNumOfLineInLogFile()
        self.assertEqual(numOfLine, 1)

    def testException(self):

        try:
            self._divideByZero()
        except Exception as e:
            self.infoLog.exception(e)

        content = self._getLogFileContent()
        self.assertTrue("ERROR" in content)

        numOfLine = self._getNumOfLineInLogFile()
        self.assertEqual(numOfLine, 7)

    def _divideByZero(self):

        return 1/0

    def testSetLogFile(self):

        fileHandler = self.infoLog.getFileHandler()

        logNameNew = "testLogNew"
        self.infoLog.setLogFile(logNameNew, fileDir=self.dataDir)

        fileHandlerNew = self.infoLog.getFileHandler()

        self.assertNotEqual(id(fileHandler), id(fileHandlerNew))

    def testFileRotation(self):

        infoLog = InfoLog()
        infoLog.SIZE_IN_MB_LOG_FILE = 0.001
        infoLog.setLogFile("rotTest", fileDir=self.dataDir)

        for counter in range(20):
            infoLog.critical("Test file rotation.")
            time.sleep(0.2)

        numOfFile = self._getNumOfFileInFolder(self.dataDir)
        self.assertEqual(numOfFile, 3)

    def _getNumOfFileInFolder(self, folder):

        items = Path(folder).glob("*")
        files = [aItem for aItem in items if aItem.is_file()]

        return len(files)


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
