..
  This is a template for documentation that will accompany each CSC.
  It consists of a user guide and development guide, however, cross linking between the guides is expected.
  This template is provided to ensure that the documentation remains similar in look, feel, and contents to users.
  The headings below are expected to be present for all CSCs, but for many CSCs, additional fields will be required.

  ** All text in square brackets [] must be re-populated accordingly **

  See https://developer.lsst.io/restructuredtext/style.html
  for a guide to reStructuredText writing.

  Use the following syntax for sections:

  Sections
  ========

  and

  Subsections
  -----------

  and

  Subsubsections
  ^^^^^^^^^^^^^^

  To add images, add the image file (png, svg or jpeg preferred) to the
  images/ directory. The reST syntax for adding the image is

  .. figure:: /images/filename.ext
  :name: fig-label

  Caption text.

  Feel free to delete this instructional comment.

.. Fill out data so contacts section below is auto-populated
.. add name and email between the *'s below e.g. *Marie Smith <msmith@lsst.org>*

.. |CSC_developer| replace:: *Te-Wei Tsai <ttsai@lsst.org>* and *Petr Kubanek <pkubanek@lsst.org>*
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

The main telescope active optical system (MTAOS) is responsible for making the closed-loop optical system. It calculates the wavefront error based on defocal images, estimates the optical state, and sends the correction of bending modes and rigid body positions to mirrors and hexapods. This control system is with the data distribution service (DDS) as a commandable SAL component (CSC). The service abstraction layer (SAL) provides the access from services of the control, management and application plane to services and applications of the application plane.

Under normal operations, MTAOS will be controlled by the telescope control system (TCS) to do the closed-loop correction. The MTAOS is part of the `Main Telescope Control Packages <https://obs-controls.lsst.io/System-Architecture/Control-Packages/index.html>`_. The backbone of CSC is using the `ts_salobj <https://ts-salobj.lsst.io>`_ library. The `eups <https://github.com/RobertLuptonTheGood/eups>`_ is used as the package manager.

The badges above navigate to the GitHub repository for the CSC code, Jenkins CI jobs, Jira issues, and communication interface for the software.

.. _User_Documentation:

User Documentation
==================

User-level documentation, found at the link below, is aimed at personnel looking to perform the standard use-cases/operations with MTAOS.

.. toctree::
    user-guide/user-guide
    :maxdepth: 1

.. _Configuration:

Configuring the MTAOS
=========================

The configuration is described at the following link.

.. toctree::
    configuration/configuration
    :maxdepth: 1

.. _Development_Documentation:

Development Documentation
=========================

This area of documentation focuses on the class and function, and how to participate to the development of MTAOS software package.

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

Contact Personnel
=================

For questions not covered in the documentation, emails should be addressed to the developers: |CSC_developer|. The product owner is |CSC_product_owner|.

This page was last modified |today|.
