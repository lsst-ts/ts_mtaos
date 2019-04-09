.. py:currentmodule:: lsst.ts.MTAOS

.. _lsst.ts.MTAOS:

########################
lsst.ts.MTAOS
########################

ts_MTAOS contains the `MTAOSCsc` and suport code.

.. _lsst.ts.MTAOS-using:

Using lsst.ts.MTAOS
==============================

ts_MTAOS requires the following SALPY libraries:

* SALPY_MTAOS
* SALPY_MTM1M3
* SALPY_MTM2MS
* SALPY_Hexapod

You can setup and build this package using eups and sconsUtils.
After setting up the package you can build it and run unit tests by typing ``scons``.
Building it merely copies ``bin.src/runMTAOS.py`` into ``bin/`` after tweaking the ``#!`` line.

To run the `MTAOS` CSC type ``runMTAOS.py``

.. _lsst.ts.MTAOS-contributing:

Contributing
============

``lsst.ts.MTAOS`` is developed at https://github.com/lsst-ts/ts_MTAOS.
You can find Jira issues for this module under the `ts_MTAOS <https://jira.lsstcorp.org/issues/?jql=project%20%3D%20DM%20AND%20component%20%3D%20ts_MTAOS>`_ component.

.. If there are topics related to developing this module (rather than using it), link to this from a toctree placed here.

.. .. toctree::
..    :maxdepth: 1

.. _lsst.ts.MTAOS-pyapi:

Python API reference
====================

.. automodapi:: lsst.ts.MTAOS
   :no-main-docstr:
   :no-inheritance-diagram:
