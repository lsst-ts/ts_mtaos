===============
Version History
===============

v0.4.4
-------------
* Use the sims_w_2020_42.
* Use the ts_salobj v6.0.3.
* Remove the deprecated functions for the new version of ts_salobj.
* Update the user-guide.rst for the use of CSC.

v0.4.3
-------------
* Update the M2 interface based on the ts_xml v6.1.0.
* Do some minor fixes.
* Update the test cases of CSC.
* Reformat the documents to improve the readibility.
* Use the sims_w_2020_29.

v0.4.2
-------------
* Reformat the rst documents to follow the standard.
* Add the user manual.
* Publish the document to `MTAOS document <https://ts-mtaos.lsst.io>`_.

v0.4.1
-------------
* Reformat the code by black.
* Add the black check to .githooks.
* Ignore flake8 check of E203 ans W503 for the black.

v0.4.0
-------------
* Configure the state0 in degree of freedom (DOF) from MTAOS files.
* Use the scientific pipeline w_2020_20.

v0.3.9
-------------
* Add the CollOfListOfWfErr class to support the multiple exposures in a single visit.
* Use the scientific pipeline w_2020_15.

v0.3.8
-------------
* Adapt to ts_xml v5.0.0.
* Add the logs directory.
* Support the change of debug level of log files.
* Use the CscTestCase from ts_salobj for CSC test.
* Remove the bin.src directory.
* Remove the dependency of version.py.

v0.3.7
-------------
* Adapt to ts_xml v4.7.0.

v0.3.6
-------------
* Use calcTime instead of duration and simulation_mode instead of initial_simulation_mode.

v0.3.5
-------------
* Restrict some commands can only be executed in the Enabled state.

v0.3.4
-------------
* Support the log file for debug.

v0.3.3
-------------
* Support the configurable CSC and simulation mode.

v0.3.2
-------------
* Add the model class and related test cases.

v0.3.1
-------------
* Workaround the Jenkins permission in Jenkinsfile.

v0.3.0
-------------
* Integrate with the PhoSim with the scientific pipeline tag: sims_w_2019_20.
* Add the Jenkinsfile.
* Update the documentation.

v0.2.0
-------------
* Integrate with ts_wep and ts_ofc.

v0.1.0
-------------
* Initial version of ts_MTAOS.
