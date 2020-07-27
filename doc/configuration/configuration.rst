#######################
MTAOS Configuration
#######################

The high-level configuration is handled using the yaml file located in the `ts_config_mttcs <https://github.com/lsst-ts/ts_config_mttcs/tree/develop/MTAOS>`_. The setting may require changing is the camera or instrument type. The former is for the wavefront estimation pipeline (WEP) and the latter is for the optical feedback control (OFC).

However, more configuration parameters are available, as described by the *schema* found in the `ts_MTAOS <https://github.com/lsst-ts/ts_MTAOS>`_. For example, you could modify the initial telescope's optical state in the basis of degree of freedom (DOF). This is used in the initial optical alignment that the subsystem's look-up table (LUT) is still under the calibration with real data. The more detailed parameters of algorithms may need to go through the policy files in `ts_wep <https://github.com/lsst-ts/ts_wep>`_ and `ts_ofc <https://github.com/lsst-ts/ts_ofc>`_. These two libraries provide the algorithms such as the deblending, control algorithm, etc. to use in MTAOS.
