.. _User_Guide:

####################
MTAOS User Guide
####################

The MTAOS CSC is generally commanded by TCS to correct the mirror bending mode and hexapod position to reach the high image quality of camera. It contains the modules of wavefront estimation pipeline (WEP) and optical feedback control (OFC). The WEP calculates the wavefornt error based on the transport of intensity equation (TIE) with defocal images. The OFC estimates the optical state based on the wavefront error, and then, the correction to mirror bending mode and hexapod position. The correction is estimated by minimizing the cost function contains the image quality and offset of degree of freedom (DOF). There are 50 terms of DOF. The mirrors of M1M3 and M2 have 20 bending modes individually. Each of camera and M2 hexapods has 5 terms of DOF to move (x, y, z, tilt-x, and tilt-y). It is noted that although the bending mode is used in DOF, the related correction to mirror is the aggregated actuator force actually.

.. _Interface:

Interface
===================

The full set of commands, events, and telemetry can be found in `MTAOS xml <https://ts-xml.lsst.io/sal_interfaces/MTAOS.html>`_. The principal use-case for this CSC is to calculate the wavefront error and send the correction to mirrors and hexapods.

Before processing the defocal images, you need to use the ``processCalibrationProducts`` command to ingest the calibration products such as the flat images. After this, use the ``processIntraExtraWavefrontError`` command to process the wavefront data of commissioning camera (ComCam). Only this camera type is supported at this moment. The defocal images are simulated by `PhoSim <https://github.com/lsst-ts/phosim_syseng4>`_ and the flat images are by `phosim_utils <https://github.com/lsst-dm/phosim_utils>`_. You can process multiple sets of wavefront data (e.g. 5 terms of intra- and extra-focal images).

Finially, use the ``issueWavefrontCorrection`` command to send the correction to subsystems. If you use multiple defocal images, the average of calculated wavefront error will be used for each charge-coupled device (CCD). Sometimes, you may want to reset all internal data such as the DOF by using the ``resetWavefrontCorrection`` command (e.g. long slew angle of telescope).

Although not often required, the MTAOS publishes the calculated wavefront error in the ``wavefrontError`` event and DOF in the ``degreeOfFreedom`` event. The telemetry of ``wepDuration`` and ``ofcDuration`` can be used to analyze the performance. The sensor name and ID can follow `sensorNameToId <https://github.com/lsst-ts/ts_wep/blob/master/policy/sensorNameToId.yaml>`_.

In the rare condition, certain subsystem might reject the correction from MTAOS. When it happens, the ``rejectedDegreeOfFreedom`` event will be published. You may want to know the internal data of aggregated DOF will not count this rejected DOF correction from the last visit. In addition, you may need to put the subsytems that accept the correction back to the previous state to be consistent with the internal data of MTAOS.

.. _Example_Use_Case:

Example Use-Case
================

The standard use-case, as mentioned in :ref:`Interface`, is to correct the DOF of subsystems.

There are multiple ways to use the MTAOS, likely it would be inside a high-level package, but it can also be done from the Jupyter Notebook or IPython.

You can instantiate a **Remote** object in *ts_salobj*, and then, bring the MTAOS CSC to the *ENABLED* state in IPython. Then, you can use the ``salobj.set_summary_state()`` to simplify the process and read the configuration file in *ts_config_mttcs*. 

.. code:: python

    from lsst.ts import salobj
    mtaosCsc = salobj.Remote("MTAOS", salobj.Domain())
    await salobj.set_summary_state(mtaosCsc, salobj.State.ENABLED, timeout=30)

You can use the *settingsToApply* argument in ``salobj.set_summary_state()`` to assign the configuration file such as *"default.yaml"* to use the file located in *ts_config_mttcs/MTAOS/v1*. Notice that the version number (e.g. v1) is assigned in *schema* of *ts_MTAOS*. Since the MTAOS needs some time to finish the configuration, it might be good to put a long *timeout* time such as 30 seconds when transitioning to the *ENABLED* state.

In addition, you need to make sure the system is either *OFFLINE* or *STANDBY* before entering the *ENABLED* state to be sure the settings are applied. You could do the following to promise this:

.. code:: python

    await salobj.set_summary_state(mtaosCsc, salobj.State.STANDBY)
    await salobj.set_summary_state(mtaosCsc, salobj.State.ENABLED, settingsToApply="default.yaml", timeout=30)

To issue the correction to subsystems, you can do:

.. code:: python

    await mtaosCsc.cmd_issueWavefrontCorrection.set_start(timeout=10, value=True)

If you ignore the inputs of parameters, the default values will be applied. However, it is always recommended to put the *timeout* in second. For example,

.. code:: python

    await mtaosCsc.cmd_issueWavefrontCorrection.set_start(timeout=10)

The ``processIntraExtraWavefrontError`` command (and all others) follows the same format as shown above:

.. code:: python

    await mtaosCsc.cmd_{nameOfCommand}.set_start(timeout=10, parameters)

It is noted that the ``processIntraExtraWavefrontError`` command will take some time. If the *timeout* is less than the calculation time, you will get the *salobj.AckTimeoutError*. In the simulation mode, it is safe to put the *timeout* to be 15 to 30 seconds.

To receive the events, you follow the format below, where the ``degreeOfFreedom`` event gives the most recent DOF. This syntax is generic and can be replaced with any other event.

.. code:: python

    dof = await mtaosCsc.evt_degreeOfFreedom.next(flush=False, timeout=30)

The *next* command will pop out the value in queue. If you just want to know the current value, you can do:

.. code:: python

    dof = await mtaosCsc.evt_degreeOfFreedom.aget(timeout=30)

Receiving telemetry, you follow a similar format as event except using the prefix of *tel_* instead of *evt_* now. You can follow `RemoteCommand <https://ts-salobj.lsst.io/py-api/lsst.ts.salobj.topics.RemoteCommand.html>`_, `RemoteEvent <https://ts-salobj.lsst.io/py-api/lsst.ts.salobj.topics.RemoteEvent.html>`_, and `RemoteTelemetry <https://ts-salobj.lsst.io/py-api/lsst.ts.salobj.topics.RemoteTelemetry.html>`_ for further details.
