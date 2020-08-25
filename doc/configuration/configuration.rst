#######################
MTAOS Configuration
#######################

MTAOS high-level configuration is handled using the yaml file located in the `ts_config_mttcs <https://github.com/lsst-ts/ts_config_mttcs/tree/develop/MTAOS>`_.
Of particular interests are the camera or instrument type settings, which should be changed to match the observatory configuration.
The former is for the wavefront estimation pipeline (WEP) and the latter is for the optical feedback control (OFC).

More configuration parameters can be found in a *schema* available at `ts_MTAOS <https://github.com/lsst-ts/ts_MTAOS/tree/master/schema>`_.
For example, you could modify the initial telescope's optical state in the multi-dimensional space formed by the DOFs.
This is used in simulations for setting the initial optical state when the subsystems' look-up tables (LUTs) are still under the calibration with real data.
The more detailed parameters of algorithms may need to go through the policy files in `ts_wep <https://github.com/lsst-ts/ts_wep/tree/master/policy>`_ and `ts_ofc <https://github.com/lsst-ts/ts_ofc/tree/master/policy>`_.
These two libraries provide the algorithms such as the deblending, control algorithm, etc. to use in MTAOS.
Details on how to configure these libraries will be included in separate documents (to be written).
