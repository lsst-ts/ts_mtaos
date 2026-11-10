# This file is part of ts_mtaos.
#
# Developed for the Vera C. Rubin Observatory Telescope and Site Systems.
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Sphinx configuration file for an LSST stack package.

This configuration only affects single-package Sphinx documentation builds.
"""

import lsst.ts.mtaos  # noqa
from documenteer.conf.guide import *  # type: ignore # noqa

project = "ts_mtaos"
html_theme_options["logotext"] = project  # type: ignore # noqa
html_title = project
html_short_title = project
doxylink = {}  # type: ignore # Avoid warning: Could not find tag file _doxygen/doxygen.tag

intersphinx_mapping["ts_xml"] = ("https://ts-xml.lsst.io", None)  # type: ignore # noqa
intersphinx_mapping["ts_salobj"] = ("https://ts-salobj.lsst.io", None)  # type: ignore # noqa

# Support the sphinx extension of plantuml
extensions.append("sphinxcontrib.plantuml")  # type: ignore # noqa

# Put the path to plantuml.jar
plantuml = "java -jar /home/saluser/plantuml.jar"
