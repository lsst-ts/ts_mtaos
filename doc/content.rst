.. py:currentmodule:: lsst.ts.MTAOS

.. _lsst.ts.MTAOS-modules:

##########
Modules
##########

The classes and files for each module are listed below.

.. _lsst.ts.MTAOS-modules_wep:

-------------
MTAOS
-------------

.. uml:: uml/mtaosClass.uml
    :caption: Class diagram of MTAOS

* **MTAOS**: Commandable SAL component (CSC) class inherits from the BaseCsc in ts_salobj. This class integrates with the wavefront estimation pipeline (WEP) and optical feedback control (OFC) to do the wavefront analysis and correct the hexapod position and mirror bending mode.
* **WEPWarning**: WEP warning class to simplify the SAL user-defined warning in WEP.
* **OFCWarning**: OFC warning class to simplify the SAL user-defined warning in OFC.
