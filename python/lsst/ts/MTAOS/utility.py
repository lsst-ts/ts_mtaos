# This file is part of MTAOS.
#
# Developed for the LSST.
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

__all__ = [
    "WEPWarning",
    "OFCWarning",
    "MTHexapodIndex",
    "getModulePath",
    "getConfigDir",
    "getLogDir",
    "getIsrDirPath",
    "getCamType",
    "getCscName",
    "addRotFileHandler",
    "timeit",
]

import asyncio
import logging
import os
import time

from logging.handlers import RotatingFileHandler
from enum import Enum, auto
from pathlib import Path
from lsst.utils import getPackageDir

from lsst.ts.wep.Utility import CamType


class WEPWarning(Enum):
    NoWarning = 0
    InvalidSensorId = auto()
    InvalidAnnularZernikePoly = auto()


class OFCWarning(Enum):
    NoWarning = 0
    NoEnoughAnnularZernikePoly = auto()


class MTHexapodIndex(Enum):
    Camera = 1
    M2 = auto()


def getModulePath():
    """Get the path of module.

    Returns
    -------
    pathlib.PosixPath
        Directory path of module.
    """

    return Path(getPackageDir("ts_MTAOS"))


def getConfigDir():
    """Get the directory of configuration files.

    Returns
    -------
    pathlib.PosixPath
        Directory of configuration files.
    """

    return getModulePath().joinpath("policy")


def getLogDir():
    """Get the directory of log files.

    Returns
    -------
    pathlib.PosixPath
        Directory of log files.
    """

    return getModulePath().joinpath("logs")


def getIsrDirPath(isrDirPathVar="ISRDIRPATH"):
    """Get the instrument signature removal (ISR) directory path.

    Parameters
    ----------
    isrDirPathVar : str, optional
        ISR directory path variable. (the default is "isrDirPathVar".)

    Returns
    -------
    pathlib.PosixPath or None
        ISR directory path. Return None if the path variable is not defined.
    """

    try:
        return Path(os.environ[isrDirPathVar])
    except KeyError:
        return None


def getCamType(camera):
    """Get the enum of camera type.

    Parameters
    ----------
    camera : str
        Camera ("lsstCam", "lsstFamCam", or "comcam").

    Returns
    -------
    enum 'CamType' in lsst.ts.wep.Utility
        Camera type.

    Raises
    ------
    ValueError
        The camera is not supported.
    """

    if camera == "lsstCam":
        return CamType.LsstCam
    elif camera == "lsstFamCam":
        return CamType.LsstFamCam
    elif camera == "comcam":
        return CamType.ComCam
    else:
        raise ValueError("The camera (%s) is not supported." % camera)


def getCscName():
    """Get the CSC name.

    CSC: Configurable SAL component.
    SAL: Service abstraction layer.
    """

    return "MTAOS"


def addRotFileHandler(log, filePath, debugLevel, maxBytes=1e6, backupCount=5):
    """Add a rotating file handler to a logger.

    Note: The input log object will be updated directly.

    Parameters
    ----------
    log : logging.Logger
        Logger.
    filePath : pathlib.PosixPath
        File path.
    debugLevel : int or str
        Logging level of file handler.
    maxBytes : int, optional
        Maximum file size in bytes for each file. (the default is 1e6.)
    backupCount : int, optional
        Number of log files to retain. (the default is 5.)

    Returns
    -------
    fileHandler : logging.RotatingFileHandler
        The file handler added.
    """

    fileHandler = RotatingFileHandler(
        filename=filePath,
        mode="a",
        maxBytes=int(maxBytes),
        backupCount=int(backupCount),
    )

    logFormat = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s")
    fileHandler.setFormatter(logFormat)

    fileHandler.setLevel(debugLevel)

    log.addHandler(fileHandler)

    return fileHandler


def timeit(func):
    """Decorator to compute execution time.

    Add this decorator to a method to allow computing execution times.

    Parameters
    ----------
    func : `function` or `coroutine`
        Method to be decorated.

    Usage
    -----

    This decorator allows one to compute and store execution times of methods
    and coroutines. To add the decorator the method must either support
    `kwargs` argument or contain an additional parameter named `log_time`,
    which must receive a dictionary. The dictionary passed to `log_time` will
    receive a new item, with the name of the method in upper case as the key,
    and a list as value. The decorator will append the execution time to the
    list every time the method is called.

    Examples
    --------

    Timing a regular method.

    >>> @timeit
        def my_method(arg1, arg2, **kwargs):
            # Do something here....

    Timing a coroutine

    >>> @timeit
        async def my_coroutine(arg1, arg2, **kwargs):
            # Do something here....

    >>> log_time = dict()

    >>> ret_val_1 = my_method(arg1=arg1, arg2=arg2, log_time=log_time)

    >>> log_time
    {'MY_METHOD': [6.699992809444666e-06]}

    >>> ret_val_2 = await my_coroutine(arg1=arg1, arg2=arg2, log_time=log_time)

    >>> log_time
    {'MY_METHOD': [6.699992809444666e-06],
    'MY_COROUTINE': [1.2299977242946625e-05]}

    """

    if asyncio.iscoroutinefunction(func):

        async def atimed(*args, **kwargs):
            """Time execution of function `func`.

            The method can either me a normal method or a coroutine.
            """
            start_time = time.perf_counter()
            result = await func(*args, **kwargs)
            calc_time = time.perf_counter() - start_time
            if "log_time" in kwargs:
                name = kwargs.get("log_name", func.__name__.upper())
                if name not in kwargs["log_time"]:
                    kwargs["log_time"][name] = []
                kwargs["log_time"][name].append(calc_time)
            return result

        return atimed
    else:

        def timed(*args, **kwargs):
            """Time execution of function `func`.

            The method can either me a normal method or a coroutine.
            """
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            calc_time = time.perf_counter() - start_time

            if "log_time" in kwargs:
                name = kwargs.get("log_name", func.__name__.upper())
                if name not in kwargs["log_time"]:
                    kwargs["log_time"][name] = []
                kwargs["log_time"][name].append(calc_time)
            return result

        return timed


if __name__ == "__main__":
    pass