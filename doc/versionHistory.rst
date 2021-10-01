===============
Version History
===============

v0.7.5
------

* Fix publishing Degrees of Freedom event when `issueCorrection` fails.

v0.7.4
------

* Update Jenkinsfile to notify gate keeper (tribeiro) on slack when build suffers a regression and when it is fixed.
* In `test_model`, update `test_process_comcam` to check the shape of the return arrays and the index of the maximum zernike coefficient instead of the values themselves.

v0.7.3
------

* Add visit_id_offset to configuration schema.
* Add visit_id_offset CSC configuration parameter to work around type of visitId being a long in runWEP and preProcess commands.
* Add unit tests for CSC configuration.
* Fix publishing wavefront errors.
* Fix gain feature in model.
* Fix pubTel_ofcDuration and pubTel_wepDuration methods in CSC. Rename to ``pubEvent_*`` and fix publishing of event topic instead of telemetry.
* In `rejectCorrection` publish degrees of freedom and corrections after rejecting correction.
* Fix setting user gain in model class.
* Deprecate the use of userGain in runOFC. It will now use the yaml configuration payload.
* In Model class use default ofc gain when initializing the class.
* Publish wepDuration at the end of runWEP.

v0.7.2
------

* Support the setting of **xref**.
* Add LSSTCam/calib to collections path in test Gen3 pipelines and fix the syntax of butler ``get()``.

v0.7.1
------

* Fix unit tests for reversed intra/extra image selection.

v0.7.0
------

* Implement ``runWEP`` command.
  The current implementation is designed to work for ComCam intra/extra data.
  It is also limited in a way that we cannot provide the target ahead of time for the pipeline task to select the sources.
* Add user-guide documentation on using ``runWEP``.
* Update UML class diagram.
* Enable pytest-black in unit tests.
* Fix bugs reported by Bo when trying to set ofc values in addAberration.
* Update model unit tests for fixed intra/extra definition.

v0.6.0
------

* In Jenkinsfile, run pytest in the entire package instead of only the `tests/` folder, to capture pep8 and black violations in the entire repo.
* Refactor module names to the current telescope and site standards (lower_camel_case).
* Refactor additional parts of the code to be compliant with the current style guide.
* Implement new version of OFC.
* In CSC:
  * Refactor log-to-file interface.
  * In `addAberration` command:
    * Stop issuing corrections. Users need to send a `issueAberration` for the aberrations to be applied.
    * Implement `config` feature, to allow users to customize ofc behavior.
    * Add some unit tests for `addAberration` config feature.
* Update tests/Sconscript to allow running scons with licensed version of OpenSplice.

v0.5.6
------

* Fixed a trailing space.

v0.5.5
------

* Fixed a too long comment line.

v0.5.4
------

* Reformat code using black 20.

v0.5.3
------

* Implement addAberration command.
* Remove `asynctest` and use `unittest.IsolatedAsyncioTestCase` instead.
* Fix version history.
* Minor documentation updates.

v0.5.2
------

* Refactor of the Model class to prepare it for integration with wep pipeline task.
* Modernize naming conventions in Model class and remove unused methods.
* Chance how execution time is calculated to use a decorator that stored the information in a dictionary and put that logic on the CSC instead.
* Remove simulation mode and ModelSim
* Implement new salobj configuration schema, replacing schema yaml file by string in a python module.
* Add support to publish CSC version.
* Update docs configuration.

v0.5.1
------

* Fix reference to undefined name `issue_corrections_tasks` -> `issued_corrections`.

v0.5.0
------

* Update MTAOS CSC to reflect new xml interface discussed in tstn-026.

v0.4.5
-------------
* Use the latest **ts_wep** that removes the dependency of ``sims`` package.
* Update the M2 interface based on the **ts_xml** v7.0.0.

v0.4.4
-------------
* Use the ``sims_w_2020_42``.
* Use the **ts_salobj** v6.0.3.
* Remove the deprecated functions for the new version of **ts_salobj**.
* Update the **user-guide.rst** for the use of CSC.

v0.4.3
-------------
* Update the M2 interface based on the **ts_xml** v6.1.0.
* Do some minor fixes.
* Update the test cases of CSC.
* Reformat the documents to improve the readibility.
* Use the ``sims_w_2020_29``.

v0.4.2
-------------
* Reformat the **rst** documents to follow the standard.
* Add the user manual.
* Publish the document to `MTAOS document <https://ts-mtaos.lsst.io>`_.

v0.4.1
-------------
* Reformat the code by ``black``.
* Add the ``black`` check to ``.githooks``.
* Ignore ``flake8`` check of E203 ans W503 for the ``black``.

v0.4.0
-------------
* Configure the ``state0`` in degree of freedom (DOF) from MTAOS files.
* Use the scientific pipeline ``w_2020_20``.

v0.3.9
-------------
* Add the **CollOfListOfWfErr** class to support the multiple exposures in a single visit.
* Use the scientific pipeline ``w_2020_15``.

v0.3.8
-------------
* Adapt to **ts_xml** v5.0.0.
* Add the logs directory.
* Support the change of debug level of log files.
* Use the **CscTestCase** from **ts_salobj** for CSC test.
* Remove the ``bin.src`` directory.
* Remove the dependency of **version.py**.

v0.3.7
-------------
* Adapt to **ts_xml** v4.7.0.

v0.3.6
-------------
* Use ``calcTime`` instead of ``duration`` and ``simulation_mode`` instead of ``initial_simulation_mode``.

v0.3.5
-------------
* Restrict some commands can only be executed in the **Enabled** state.

v0.3.4
-------------
* Support the log file for debug.

v0.3.3
-------------
* Support the configurable CSC and simulation mode.

v0.3.2
-------------
* Add the **Model** class and related test cases.

v0.3.1
-------------
* Workaround the Jenkins permission in **Jenkinsfile**.

v0.3.0
-------------
* Integrate with the PhoSim with the scientific pipeline tag: ``sims_w_2019_20``.
* Add the **Jenkinsfile**.
* Update the documentation.

v0.2.0
-------------
* Integrate with **ts_wep** and **ts_ofc**.

v0.1.0
-------------
* Initial version of **ts_MTAOS**.
