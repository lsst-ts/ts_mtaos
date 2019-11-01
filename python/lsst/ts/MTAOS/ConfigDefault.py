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

import warnings

from lsst.ts.MTAOS.Utility import getIsrDirPath, getCamType, getInstName, \
    getModulePath


class ConfigDefault(object):

    def __init__(self, config):
        """Initialize the configuration default class.

        This is a parent class.

        Parameters
        ----------
        config : pathlib.PosixPath, str, or object.
            Needed input of the configuration.

        Raises
        ------
        NotImplementedError
            Child class should implement this.
        """

        raise NotImplementedError("Child class should implement this.")

    def getCamTypeInConfig(self):
        """Get the enum of camera type in the configuration.

        Returns
        -------
        enum 'CamType' in lsst.ts.wep.Utility
            Camera type.
        """

        camera = self._getCamType()
        return getCamType(camera)

    def _getCamType(self):
        """Get the value of camera type in the configration.

        Returns
        -------
        str
            Camera type.

        Raises
        ------
        NotImplementedError
            Child class should implement this.
        """
        raise NotImplementedError("Child class should implement this.")

    def getInstNameInConfig(self):
        """Get the enum of instrument name in the configuration.

        Returns
        -------
        enum 'InstName' in lsst.ts.ofc.Utility
            Instrument name.
        """

        instName = self._getInstName()
        return getInstName(instName)

    def _getInstName(self):
        """Get the value of instrument name in the configration.

        Returns
        -------
        str
            Instrument name.

        Raises
        ------
        NotImplementedError
            Child class should implement this.
        """

        raise NotImplementedError("Child class should implement this.")

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

        isrDir = getIsrDirPath()
        if (isrDir is None):
            isrDir = self._getIsrDir()
            warnings.warn("No 'ISRDIRPATH' assigned. Use %s instead." % isrDir,
                          category=UserWarning)
            return isrDir
        else:
            return isrDir.as_posix()

    def _getIsrDir(self):
        """Get the value of ISR directory in the configration.

        ISR: Instrument signature removal.

        Returns
        -------
        str
            ISR directory.

        Raises
        ------
        NotImplementedError
            Child class should implement this.
        """

        raise NotImplementedError("Child class should implement this.")

    def getDefaultSkyFileInConfig(self):
        """Get the default sky file path in the configuration.

        This is for the test only.

        Returns
        -------
        pathlib.PosixPath or None
            Get the default sky file path. Return None if there is no such
            setting.
        """

        relativePath = self._getDefaultSkyFile()
        if (relativePath is None):
            return None
        else:
            return getModulePath().joinpath(relativePath)

    def _getDefaultSkyFile(self):
        """Get the value of default sky file path in the configuration.

        Returns
        -------
        str
            Default sky file path. Return None if there is no such
            setting.

        Raises
        ------
        NotImplementedError
            Child class should implement this.
        """

        raise NotImplementedError("Child class should implement this.")


if __name__ == "__main__":
    pass
