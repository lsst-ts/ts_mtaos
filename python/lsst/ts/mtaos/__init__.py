# This file is part of ts_ATDomeTrajectory.
#
# Developed for the LSST Data Management System.
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

# The version file is gotten by the scons. However, the scons does not support
# the build without unit tests. This is a needed function for the Jenkins to
# use.
import typing

# For an explanation why these next lines are so complicated, see
# https://confluence.lsstcorp.org/pages/viewpage.action?spaceKey=LTS&title=Enabling+Mypy+in+Pytest
if typing.TYPE_CHECKING:
    __version__ = "?"
else:
    try:
        from .version import *
    except ImportError:
        __version__ = "?"

from .config import *
from .config_schema import *
from .model import *
from .mtaos import *
from .utility import *
from .wavefront_collection import *
