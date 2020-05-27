.. py:currentmodule:: lsst.ts.MTAOS

.. _lsst.ts.MTAOS-modules:

##########
Modules
##########

The classes and files for each module are listed below.

.. _lsst.ts.MTAOS-modules_MTAOS:

-------------
MTAOS
-------------

.. uml:: uml/mtaosClass.uml
    :caption: Class diagram of MTAOS

* **MtaosCsc**: Commandable SAL component (CSC) class inherits from the ConfigurableCsc in ts_salobj.
* **CalcTime**: Calculation time class to collect and analyze the calculation time of time-consuming jobs.
* **CollOfListOfWfErr**: Collection of list of wavefront sensor data.
* **Config**: Configuration class as with functions to get the configuration details.
* **Model**: Model class that contains the wavefront estimation pipeline (WEP) and optical feedback control (OFC).
* **ModelSim**: Simulation model class inherits from the Model class to support the simulation mode needed in the MtaosCsc class.
