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

__all__ = ["Config"]

import warnings
from collections import namedtuple

import yaml

from . import utility


class Config(object):
    def __init__(self, config):
        """Configuration class.

        Parameters
        ----------
        config : str or object
            Source of the configuration. Either object received in configure
            CSC call, or string for a filename.
        """
        if isinstance(config, str):
            data = yaml.safe_load(open(config).read())
            self.configObj = namedtuple("configObj", data.keys())(*data.values())
        else:
            self.configObj = config

    def getCamType(self):
        """Get the enum of camera type in the configuration.

        Returns
        -------
        enum 'CamType' in lsst.ts.wep.utility
            Camera type.
        """

        return utility.getCamType(self.configObj.camera)

    def getInstName(self):
        """Get the enum of instrument name in the configuration.

        Returns
        -------
        enum 'InstName' in lsst.ts.ofc.utility
            Instrument name.
        """

        return self.configObj.instrument

    def getIsrDir(self):
        """Get the ISR directory.

        ISR: Instrument signature removal.
        This directory will have the input and output that the data butler
        needs.

        Returns
        -------
        str
            ISR directory.
        """

        isrDir = utility.getIsrDirPath()
        if isrDir is None:
            isrDir = self.configObj.defaultIsrDir
            warnings.warn(
                f"No 'ISRDIRPATH' assigned. Using {isrDir} instead.",
                category=UserWarning,
            )
            return isrDir
        else:
            return isrDir.as_posix()

    def getDefaultSkyFile(self):
        """Get the default sky file path in the configuration.

        This is for the test only.

        Returns
        -------
        pathlib.PosixPath or None
            Get the default sky file path. Return None if there is no such
            setting.
        """

        try:
            relativePath = self.configObj.defaultSkyFilePath
        except AttributeError:
            return None
        return utility.getModulePath().joinpath(relativePath)

    def getState0DofFile(self):
        """Get the state 0 DoF filename.

        Returns
        -------
        pathlib.PosixPath or None
            Default state 0 DoF file path. Return None if value isn't
            specified.
        """

        try:
            relativePath = self.configObj.state0DofFilePath
        except AttributeError:
            return None
        return utility.getModulePath().joinpath(relativePath)
