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
    "support_interrupt_wep_cmd",
    "get_formatted_corner_wavefront_sensors_ids",
    "define_visit",
]

import asyncio
import logging
import os
import re
import time
import typing
from enum import Enum, auto
from logging.handlers import RotatingFileHandler
from pathlib import Path

from lsst.daf.butler import Butler
from lsst.obs.base import DefineVisitsTask, Instrument
from lsst.obs.lsst.translators.lsstCam import LsstCamTranslator
from lsst.ts.idl import get_idl_dir
from lsst.ts.salobj import parse_idl
from lsst.ts.wep.utility import CamType
from lsst.utils import getPackageDir


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

    return Path(getPackageDir("ts_mtaos"))


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


# TODO: Remove when xml 11 is available (DM-33401).
def support_interrupt_wep_cmd() -> bool:
    """Check if interruptWEP command is defined in MTAOS idl file.

    This is a workaround to provide backward compatibility with xml 10.2
    and will be removed in the future (DM-33401).

    Returns
    -------
    `bool`
        True if CSC interfaces defines the command "interruptWEP", False
        otherwise.
    """
    csc_name = getCscName()

    idl_metadata = parse_idl(csc_name, get_idl_dir() / f"sal_revCoded_{csc_name}.idl")

    return "command_interruptWEP" in idl_metadata.topic_info


# TODO: Remove when xml 19 is available (DM-33401).
def support_offset_dof_cmd() -> bool:
    """Check if offsetDOF command is defined in MTAOS idl file.

    This is a workaround to provide backward compatibility with xml 19
    and will be removed in the future.

    Returns
    -------
    `bool`
        True if CSC interfaces defines the command "offsetDOF", False
        otherwise.
    """
    csc_name = getCscName()

    idl_metadata = parse_idl(csc_name, get_idl_dir() / f"sal_revCoded_{csc_name}.idl")

    return "command_offsetDOF" in idl_metadata.topic_info


def get_formatted_corner_wavefront_sensors_ids() -> str:
    """Return a list of ids for the corner wavefront sensors for LSSTCam.

    Returns
    -------
    str
        Comma-separeted string with the ids of the corner wavefront sensor for
        LSSTCam.
    """
    detector_mapping = LsstCamTranslator.detector_mapping()
    pattern = re.compile("R(?P<r>\\d{2})_SW(?P<sw>\\d{1})")

    return ", ".join(
        [
            f"{detector_mapping[detector][0]}"
            for detector in detector_mapping
            if pattern.match(detector) is not None
        ]
    )


def define_visit(
    data_path: str,
    collections: typing.List[str],
    instrument_name: str,
    exposures_str: str,
) -> None:
    """Define visit for a pair of images.

    This is required so that the DM pipeline can process the pair of
    intra/extra focal images together.

    Parameters
    ----------
    data_path : `str`
        Path to the butler repository.
    collections : `list` of `str`
        List of collections.
    instrument_name : `str`
        Instrument name.
    exposures_str : `str`
        A string that can be used by the pipeline task to query the data
        to be processed.
    """

    butler = Butler(data_path, collections=collections, writeable=True)

    exposure_data_ids = set(
        butler.registry.queryDataIds(["exposure"], where=exposures_str)
    )

    Instrument.fromName(instrument_name, registry=butler.registry)

    config = DefineVisitsTask.ConfigClass()

    config.groupExposures.name = "one-to-one"

    task = DefineVisitsTask(config=config, butler=butler)

    task.run(exposure_data_ids)


if __name__ == "__main__":
    pass
