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


import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path

# Remove the not-needed information from ipython:
# https://github.com/ipython/ipython/issues/10946
logging.getLogger("parso.python.diff").disabled = True


class InfoLog(object):

    SIZE_IN_MB_LOG_FILE = 1
    COUNT_LOG_FILE = 5

    def __init__(self, log=None, name=None):
        """Initialize the information log class.

        Parameters
        ----------
        log : logging.Logger, optional
            Logger object. (the default is None.)
        name : str, optional
            Name of the new logger. If no name is specified, return the root
            logger. (the default is None.)
        """

        # Assign the logger object
        if (log is None):
            self._log = logging.getLogger(name)
        else:
            self._log = log

        # File handler
        self._fileHandler = None

    def getLogger(self):
        """Get the logger.

        Returns
        -------
        logging.Logger
            Logger object.
        """

        return self._log

    def getFileHandler(self):
        """Get the file handler.

        Returns
        -------
        logging.FileHandler or None
            Filerhandler object. Return None if it does not exist.
        """

        return self._fileHandler

    def setLevel(self, level):
        """Set the logging level. The level of file handler will be set as well
        if it exists.

        Parameters
        ----------
        level : int or str
            Log level: NOTSET (0), DEBUG(10), INFO(20), WARNING(30), ERROR(40),
            and CRITICAL(50).
        """

        self._log.setLevel(level)
        if (self._fileHandler is not None):
            self._fileHandler.setLevel(level)

    def debug(self, msg):
        """Logs a message with level DEBUG on this logger.

        Parameters
        ----------
        msg : str
            Message.
        """

        self._log.debug(msg)

    def info(self, msg):
        """Logs a message with level INFO on this logger.

        Parameters
        ----------
        msg : str
            Message.
        """

        self._log.info(msg)

    def warning(self, msg):
        """Logs a message with level WARNING on this logger.

        Parameters
        ----------
        msg : str
            Message.
        """

        self._log.warning(msg)

    def error(self, msg):
        """Logs a message with level ERROR on this logger.

        Parameters
        ----------
        msg : str
            Message.
        """

        self._log.error(msg)

    def critical(self, msg):
        """Logs a message with level CRITICAL on this logger.

        Parameters
        ----------
        msg : str
            Message.
        """

        self._log.critical(msg)

    def exception(self, msg):
        """Logs a message with level ERROR on this logger. Exception info is
        added to the logging message. This method should only be called from
        an exception handler.

        Parameters
        ----------
        msg : None (Exception)
            Message.
        """

        self._log.exception(msg, exc_info=True)

    def setLogFile(self, fileName, fileDir=None):
        """Set the log file.

        Parameters
        ----------
        fileName : str
            Log file name (e.g. 'temp'). The output file will have the datetime
            and '.log' as the extension.
        fileDir : pathlib.PosixPath, optional
            Log file directory. (the default is None.)
        """

        self._rmAndResetFileHandler()

        fileTime = datetime.now().strftime("%y_%m_%d_%a_%H:%M:%S")
        filePath = Path(f"{fileName}_{fileTime}.log")
        if (fileDir is not None):
            filePath = fileDir.joinpath(filePath)

        self._fileHandler = RotatingFileHandler(
            filePath, mode='a', maxBytes=self.SIZE_IN_MB_LOG_FILE * 1e6,
            backupCount=self.COUNT_LOG_FILE)

        logFormat = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(message)s")
        self._fileHandler.setFormatter(logFormat)

        self._log.addHandler(self._fileHandler)

        self.setLevel(self._log.getEffectiveLevel())

    def _rmAndResetFileHandler(self):
        """Remove and reset the file handler."""

        if (self._fileHandler is not None):
            self._log.removeHandler(self._fileHandler)
            self._fileHandler = None


if __name__ == "__main__":
    pass
