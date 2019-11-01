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

import os
from enum import Enum, auto
from pathlib import Path
from lsst.utils import getPackageDir

from lsst.ts.wep.Utility import CamType
from lsst.ts.ofc.Utility import InstName


class WEPWarning(Enum):
    NoWarning = 0
    InvalidSensorId = auto()
    InvalidAnnularZernikePoly = auto()


class OFCWarning(Enum):
    NoWarning = 0
    NoEnoughAnnularZernikePoly = auto()


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


def getSchemaDir():
    """Get the directory of schema files.

    Returns
    -------
    pathlib.PosixPath
        Directory of schema files.
    """

    return getModulePath().joinpath("schema")


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

    if (camera == "lsstCam"):
        return CamType.LsstCam
    elif (camera == "lsstFamCam"):
        return CamType.LsstFamCam
    elif (camera == "comcam"):
        return CamType.ComCam
    else:
        raise ValueError("The camera (%s) is not supported." % camera)


def getInstName(instName):
    """Get the enum of instrument name.

    Parameters
    ----------
    instName : str
        Instrument name.

    Returns
    -------
    enum 'InstName' in lsst.ts.ofc.Utility
        Instrument name.

    Raises
    ------
    ValueError
        This instrument is not supported.
    """

    if (instName == "lsst"):
        return InstName.LSST
    elif (instName == "comcam"):
        return InstName.COMCAM
    elif (instName == "sh"):
        return InstName.SH
    elif (instName == "cmos"):
        return InstName.CMOS
    else:
        raise ValueError("This instrument (%s) is not supported." % instName)


def getCscName():
    """Get the CSC name.

    CSC: Configurable SAL component.
    SAL: Service abstraction layer.
    """

    return "MTAOS"


if __name__ == "__main__":
    pass
