.. |CSC_developer| replace:: *Te-Wei Tsai <ttsai@lsst.org>* and *Petr Kubánek <pkubanek@lsst.org>*
.. |CSC_product_owner| replace:: *Bo Xin <bxin@lsst.org>*

.. Note that the ts_ prefix is omitted from the title

########################
MTAOS
########################

.. image:: https://img.shields.io/badge/GitHub-ts__MTAOS-green.svg
    :target: https://github.com/lsst-ts/ts_MTAOS
.. image:: https://img.shields.io/badge/Jenkins-ts__MTAOS-green.svg
    :target: https://tssw-ci.lsst.org/job/LSST_Telescope-and-Site/job/ts_MTAOS
.. image:: https://img.shields.io/badge/Jira-ts__MTAOS-green.svg
    :target: https://jira.lsstcorp.org/issues/?jql=labels%20in%20(ts_MTAOS%2C%20%20MTAOS)
.. image:: https://img.shields.io/badge/ts__xml-MTAOS-green.svg
    :target: https://ts-xml.lsst.io/sal_interfaces/MTAOS.html

.. _Overview:

Overview
========

The Main Telescope Active Optics System (MTAOS) Commandable SAL Component (CSC) is operating the closed-loop optical system.
MTAOS calculates the wavefront error based on defocal images obtained with corner raft wavefront sensor, estimates the optical state, and sends the correction in the forms of bending modes and rigid body positions to the mirrors and hexapods.
DDS/SAL (Service Abstraction Layer) is used to send commands from MTAOS to M1M3 static support and M2 hexapod.

In automatic operations, MTAOS will be controlled by the Telescope Control System (TCS) to do the closed-loop correction.
MTAOS is part of the `Main Telescope Control Packages <https://obs-controls.lsst.io/System-Architecture/Control-Packages/index.html>`_.
The backbone of CSC is using the `ts_salobj <https://ts-salobj.lsst.io>`_ library, which defines the state transitions.
The summary state machine is defined in `TCS Software Component Interface <https://docushare.lsst.org/docushare/dsweb/Get/LTS-307>`_ and there is no detailed state defined in MTAOS.
The `eups <https://github.com/RobertLuptonTheGood/eups>`_ is used as the package manager.

The badges above navigate to the GitHub repository for the CSC code, Jenkins CI jobs, Jira issues, and communication interface for the software.

.. _User_Documentation:

User Documentation
==================

Observatory operators and other interested parties should consult the user guide for insights into MTAOS operations.

.. toctree::
    user-guide/user-guide
    :maxdepth: 1

.. _Configuration:

Configuring the MTAOS
=====================

MTAOSs configuration is described at the following link.

.. toctree::
    configuration/configuration
    :maxdepth: 1

.. _Development_Documentation:

Developer Documentation
=======================

Classes and their methods, and how to get involved in the MTAOS development is described in this section.

.. toctree::
    developer-guide/developer-guide
    :maxdepth: 1

.. _Version_History:

Version History
===============

The version history is at the following link.

.. toctree::
    versionHistory
    :maxdepth: 1

The released version is `here <https://github.com/lsst-ts/ts_MTAOS/releases>`_.

.. _Contact_Personnel:

Contacts
========

For questions not covered in the documentation, emails should be addressed to the developers: |CSC_developer|.
The product owner is |CSC_product_owner|.

This page was last modified |today|.
