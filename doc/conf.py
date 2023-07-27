"""Sphinx configuration file for an LSST stack package.

This configuration only affects single-package Sphinx documentation builds.
"""

import lsst.ts.mtaos  # noqa
from documenteer.conf.pipelinespkg import *  # noqa

project = "ts_mtaos"
html_theme_options["logotext"] = project  # noqa
html_title = project
html_short_title = project
doxylink = {}  # Avoid warning: Could not find tag file _doxygen/doxygen.tag

intersphinx_mapping["ts_xml"] = ("https://ts-xml.lsst.io", None)  # noqa
intersphinx_mapping["ts_salobj"] = ("https://ts-salobj.lsst.io", None)  # noqa

# Support the sphinx extension of plantuml
extensions.append("sphinxcontrib.plantuml")  # noqa

# Put the path to plantuml.jar
plantuml = "java -jar /home/saluser/plantuml.jar"
