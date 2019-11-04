.. py:currentmodule:: lsst.ts.MTAOS

.. _lsst.ts.MTAOS:

########################
lsst.ts.MTAOS
########################

Main telescope active optical system (MTAOS) is responsible for making the closed-loop optical system. It is a control system with the data distribution service (DDS) communication. The backbone of control system is ts_salobj, which is a high-level module to provide the state machine and use DDS.

.. _lsst.ts.MTAOS-using:

Using lsst.ts.MTAOS
==============================

.. toctree::
   :maxdepth: 1

Important class:

* `MtaosCsc` is a commandable SAL component (CSC) class inherits from the ConfigurableCsc in ts_salobj. This class integrates with the wavefront estimation pipeline (WEP) and optical feedback control (OFC) to do the wavefront analysis and correct the hexapod position and mirror bending mode.

.. _lsst.ts.MTAOS-pyapi:

Python API reference
====================

.. automodapi:: lsst.ts.MTAOS
    :no-inheritance-diagram:

.. _lsst.ts.MTAOS-content:

Content
====================

.. toctree::

   content

.. _lsst.ts.MTAOS-contributing:

Contributing
============

``lsst.ts.MTAOS`` is developed at https://github.com/lsst-ts/ts_MTAOS.

.. _lsst.ts.MTAOS-version:

Version
====================

.. toctree::

   versionHistory
