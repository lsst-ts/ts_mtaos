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

__all__ = ["ConfigByFile"]

from lsst.ts.wep.ParamReader import ParamReader

from lsst.ts import MTAOS


class ConfigByFile(MTAOS.ConfigDefault):

    def __init__(self, config):
        """Initialize the configuration by file class.

        Parameters
        ----------
        config : pathlib.PosixPath or str
            Configuration setting file.
        """

        self.settingFile = ParamReader(filePath=config)

    def _getCamType(self):

        return self.settingFile.getSetting("camera")

    def _getInstName(self):

        return self.settingFile.getSetting("instrument")

    def _getIsrDir(self):

        return self.settingFile.getSetting("defaultIsrDir")

    def _getDefaultSkyFile(self):

        try:
            return self.settingFile.getSetting("defaultSkyFilePath")
        except ValueError:
            return None


if __name__ == "__main__":
    pass
