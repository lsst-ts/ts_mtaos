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
* **ConfigDefault**: Configuration default class as a parent class to define the funtions to get the configuration details.
* **ConfigByFile**: Configuration by file class as a child class of ConfigDefault class. Get the configuration details from the file. This is for the test to use.
* **CanfigByObj**: Configuration by object class as a child class of ConfigDefault class. Get the configuration details from the object provided by ts_salobj. This is for the production environment.
* **Model**: Model class that contains the wavefront estimation pipeline (WEP) and optical feedback control (OFC).
* **ModelSim**: Simulation model class inherits from the Model class to support the simulation mode needed in the MtaosCsc class.
* **InfoLog**: Information log class that records the messages.
