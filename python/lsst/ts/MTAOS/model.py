# This file is part of ts_MTAOS.
#
# Developed for the LSST Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__all__ = ["Model"]

import logging

import numpy as np

from lsst.ts.ofc import OFC
from lsst.ts.wep.bsc.CamFactory import CamFactory

from .wavefront_collection import WavefrontCollection
from .utility import timeit


class Model:

    # Maximum length of queue for wavefront error
    MAX_LEN_QUEUE = 10

    def __init__(self, config, ofc_data, log=None):
        """MTAOS model class.

        This class implements a model for the MTAOS operations. It encapsulates
        all business logic to isolate the CSC from the operation.

        Parameters
        ----------
        config : `lsst.ts.MTAOS.Config`
            Configuration.
        ofc_data : `OFCData`
            OFC data container class.
        log : `logging.Logger` or `None`, optional
            Optional logging class to be used for logging operations. If
            `None`, creates a new logger.

        Attributes
        ----------
        log : `Logger`
            Log facility.
        config : `lsst.ts.MTAOS.Config`
            Configuration.
        wavefront_errors : `WavefrontCollection`
            Object to manage list of wavefront errors.
        rejected_wavefront_errors : `WavefrontCollection`
            Object to manage list of rejected wavefront errors.
        user_gain : `float`
            User provided gain for the OFC. Value must be either -1, the gain
            value will be dicided by PSSN, or between 0 and 1.
        fwhm_data : `list` of `FWHMSensorData`
            List of FWHM (full width at half maximum) sensor data.
        ofc : `lsst.ts.ofc.OFC`
            Optical feedback control object.
        m2_hexapod_correction : `M2HexapodCorrection`
            M2 hexapod correction.
        cam_hexapod_correction : `CameraHexapodCorrection`
            Camera hexapod correction.
        m1m3_correction : `M1M3Correction`
            M1M3 correction.
        m2_correction : `M2Correction`
            M2 correction.
        camera : `lsst.ts.wep.bsc.CameraData.CameraData`
            Current camera instance.
        """

        if log is None:
            self.log = logging.getLogger(type(self).__name__)
        else:
            self.log = log.getChild(type(self).__name__)

        # Configuration
        self.config = config

        self.camera = CamFactory.createCam(self.config.getCamType())

        # Collection of calculated list of wavefront error
        self.wavefront_errors = WavefrontCollection(self.MAX_LEN_QUEUE)

        # Collection of calculated list of rejected wavefront error
        self.rejected_wavefront_errors = WavefrontCollection(self.MAX_LEN_QUEUE)

        # Dictionary of FWHM (full width at half maximum) sensor data
        self._fwhm_data = dict()

        # Optical feedback control
        self.ofc = OFC(ofc_data)

        # M2 hexapod correction
        self.m2_hexapod_correction = None

        # Camera hexapod correction
        self.cam_hexapod_correction = None

        # M1M3 actuator correction
        self.m1m3_correction = None

        # M2 actuator correction
        self.m2_correction = None

        self.reset_wfe_correction()

    @property
    def user_gain(self):
        """Return the user gain."""
        return self.ofc.ofc_controller.gain

    @user_gain.setter
    def user_gain(self, value):
        """Set user gain."""
        self.ofc.ofc_controller.gain = value

    def get_fwhm_sensors(self):
        """Get list of fwhm sensor ids.

        Returns
        -------
        `list`
            List with the fwhm sensors ids.
        """
        return list(self._fwhm_data.keys())

    def get_fwhm_data(self):
        """Get an ndarray with the FWHM data for all the sensors.

        FWHM: Full width at half maximum.

        Returns
        -------
        `np.ndarray`
            2-D array with the fwhm data. Each element of the array contains an
            array with the fwhm data (in arcsec).
        """

        # Note that the array dtype bellow is object instead of float. The
        # reason is that we need to be able to support vectors with different
        # sizes. For instance, say you have 5 measurements for sensor 1, 7 for
        # sensor 2 and so on. Numpy does not support arrays of arrays with
        # different sizes of type float.
        return np.array(
            [self._fwhm_data[sensor_id] for sensor_id in self._fwhm_data],
            ndmin=1,
            dtype=object,
        )

    def set_fwhm_data(self, sensor_id, fwhm_data):
        """Set the FWHM sensor data.

        FWHM: Full width at half maximum.

        Parameters
        ----------
        sensorId : int
            Sensor Id.
        fwhm_data : numpy.ndarray
            FWHM values for this sensor.

        Raises
        ------
        RuntimeError
            If input `sensor_id` is not in the list of ids for the configured
            camera.
        """

        if sensor_id not in self.ofc.ofc_data.field_idx.values():
            raise RuntimeError(
                f"Sensor {sensor_id} not in the list of wavefront sensors "
                f"{self.ofc.ofc_data.field_idx.values()}."
            )

        self._fwhm_data[sensor_id] = np.array(fwhm_data)

    def reset_fwhm_data(self):
        """Reset fhwm data."""
        self._fwhm_data = dict()

    def get_wfe(self):
        """Get the list of wavefront error from the collection.

        This is to let MtaosCsc to publish the latest calculated wavefront
        error.

        Returns
        -------
        list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of wavefront error data.
        """

        return self.wavefront_errors.pop()

    def get_rejected_wfe(self):
        """Get the list of rejected wavefront error from the collection.

        This is to let MtaosCsc to publish the latest rejected wavefront
        error.

        Returns
        -------
        list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of rejected wavefront error data.
        """

        return self.rejected_wavefront_errors.pop()

    def get_dof_aggr(self):
        """Get the aggregated DOF.

        DOF: Degree of freedom.

        Returns
        -------
        numpy.ndarray
            Aggregated DOF.
        """

        return self.ofc.ofc_controller.aggregated_state

    def get_dof_lv(self):
        """Get the DOF correction from the last visit.

        DOF: Degree of freedom.

        Returns
        -------
        numpy.ndarray
            DOF correction from the last visit.
        """

        return self.ofc.lv_dof

    def reject_correction(self):
        """Reject the correction of subsystems."""

        lv_dof = self.get_dof_lv()

        self.ofc.ofc_controller.aggregate_state(-lv_dof, self.ofc.ofc_data.dof_idx)

        self.ofc.lv_dof = self.ofc.ofc_controller.dof_state.copy()

        (
            self.m2_hexapod_correction,
            self.cam_hexapod_correction,
            self.m1m3_correction,
            self.m2_correction,
        ) = self.ofc.get_all_corrections()

    def reset_wfe_correction(self):
        """Reset the current calculation contains the wavefront error and
        subsystem corrections to be empty.

        This function is needed for the long slew angle of telescope.
        """

        self._clear_wfe_collections()
        (
            self.m2_hexapod_correction,
            self.cam_hexapod_correction,
            self.m1m3_correction,
            self.m2_correction,
        ) = self.ofc.reset()

    def _clear_wfe_collections(self):
        """Clear the collections of wavefront error contain the rejected
        one."""

        self.wavefront_errors.clear()
        self.rejected_wavefront_errors.clear()

    async def select_sources(self, ra, dec, sky_angle, obs_filter, mode):
        """Setup and run source selection algorithm.

        Parameters
        ----------
        ra : `float`
            Right ascension in degrees. The value should be in (0, 360).
        dec : `float`
            Declination in degrees. The value should be in (-90, 90).
        sky_angle : `float`
            The sky position angle in degrees (0 to 360). This is the angle
            measured relative to the north celestial pole (NCP), turning
            positive into the direction of the right ascension.
        obs_filter : `lsst.ts.idl.enums.MTAOS.FilterType`
            Filter used while collecting the images.
        mode : `lsst.ts.idl.enums.MTAOS.Mode`
            Enumeration specifying the wfs mode.

        Raises
        ------
        NotImplementedError
            This function is not supported yet (DM-28708).
        """
        # TODO: (DM-28708) Finish implementation of selectSources.
        raise NotImplementedError("This function is not supported yet (DM-28708).")

    async def pre_process(self, visit_id, config):
        """Pre-process image for WEP.

        The outputs of this command are donut images that are ready
        for curvature wavefront sensing.

        Parameters
        ----------
        visit_id : `int`
            Image visit id number.
        config : `dict`
            Configuration for the image processing algorithm.

        Raises
        ------
        NotImplementedError
            This function is not supported yet (DM-28708).
        """
        # TODO: (DM-28708) Finish implementation of preProcess.
        raise NotImplementedError("This function is not supported yet (DM-28708).")

    @timeit
    async def run_wep(self, visit_id, extra_id, config, **kwargs):
        """Process image or images with wavefront estimation pipeline.

        Parameters
        ----------
        visit_id : `int`
            Image visit id number.
        extra_id : `None` or `int`
            Additional image visit id number. If `None`, assume it is
            processing corner wavefront sensors data. This option is only valid
            if data is for the main camera.
        config : `dict`
            Configuration for the wavefront estimation pipeline.
        kwargs :
            Additional keyword arguments, required by the timer decorator.

        Raises
        ------
        NotImplementedError
            This function is not supported yet (DM-28710).

        """

        if extra_id is None:
            self.log.debug(
                f"Processing MainCamera corner wavefront sensor on image {visit_id}."
            )
        else:
            # Will have to verify images are ComCam and raise an exception if
            # they are main camera. Main camera intra/extra data will be
            # processed exclusively using OCPS.
            self.log.debug(f"Processing intra/extra pair: {visit_id}/{extra_id}.")

        # TODO: (DM-28710) Initial implementation of runWEP command in MTAOS
        raise NotImplementedError("This function is not supported yet (DM-28710).")

    def reject_unreasonable_wfe(self, listOfWfErr):
        """Reject the wavefront error that is unreasonable.

        The input listOfWfErr might be updated after calling this function.
        Some elements might be pop out for the bad values.

        Parameters
        ----------
        listOfWfErr : list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of wavefront error data.
        """

        # Need to have the algorithm to analyze the wavefront error is
        # reasonable or not. At this moment, just assume everything is good.

        return []

    @timeit
    def calculate_corrections(self, **kwargs):
        """Calculate the correction of subsystems based on the average
        wavefront error of multiple exposure images in a single visit.

        Parameters
        ----------
        kwargs :
            Additional keyword arguments, required by the timer decorator.

        Raises
        ------
        RuntimeError
            No FWHM sensor data to use.
        """
        try:
            if self.user_gain == -1:
                if len(self.fwhm_data) == 0:
                    raise RuntimeError("No FWHM sensor data to use.")
                else:
                    self.ofc.setGainByPSSN()
                    self.ofc.setFWHMSensorDataOfCam(self.fwhm_data)
            else:
                self.ofc.setGainByUser(self.user_gain)

            wfe_data_container = (
                self.wavefront_errors.getListOfWavefrontErrorAvgInTakenData()
            )

            field_idx = np.array(
                [wfe_data.getSensorId() for wfe_data in wfe_data_container]
            )

            wfe = np.array(
                [wfe_data.getAnnularZernikePoly() for wfe_data in wfe_data_container]
            )

            self._calculate_corrections(wfe=wfe, field_idx=field_idx, **kwargs)

        finally:
            # Clear the queue
            self._clear_wfe_collections()

    def _calculate_corrections(self, wfe, field_idx, **kwargs):
        """Compute corrections from input wavefront errors.

        Parameters
        ----------
        wfe: `np.ndarray`
            2D array with wavefront errors (in microns). Each element contains
            the wavefront errors for a specific field index.
        field_idx: `np.ndarray`
            Field index for the input wavefront errors.
        **kwargs: `dict`
            User input keyword arguments. Optional standard kwargs:
                gain: `float`
                    User gain (default -1).
                rot: `float`
                    Camera rotation angle in degrees (default 0).
                filter_name: `string`
                    Name of the filter used for the observations.
        """
        gain = kwargs.get("gain", -1.0)
        rot = kwargs.get("rot", 0.0)
        filter_name = kwargs.get("filter_name", "")

        if gain < 0.0:
            try:
                self.ofc.set_pssn_gain()
            except RuntimeError:
                self.log.debug(
                    f"Error setting pssn gain. Using default: {self.ofc.default_gain}."
                )
                gain = self.ofc.default_gain

        (
            self.m2_hexapod_correction,
            self.cam_hexapod_correction,
            self.m1m3_correction,
            self.m2_correction,
        ) = self.ofc.calculate_corrections(
            wfe=wfe, field_idx=field_idx, filter_name=filter_name, gain=gain, rot=rot
        )

    def add_correction(self, wavefront_errors, config=None):
        """Compute ofc corrections from user-defined wavefront erros.

        Parameters
        ----------
        wavefront_errors : `np.array` or `list` of `float`
            Input wavefront errors (in um). If an array or list it must have
            the same number of elements of the intrinsic zernike coeffients.
        config : `dict`, optional
            Optional additional configuration parameters to customize ofc.
            Default is `None`.
        """

        self.log.debug(f"Currently configured with {self.config.getCamType()!r}")

        # Get the intrinsic zernike coeffients. Will consider white light for
        # now but may use last filter set in select sources in the future.
        self.log.debug("Assuming white light filter to compute aberration.")

        # Note that it subtracts the users input wavefront from the intrinsic
        # data. The ofc will return corrections to remove the measured
        # aberration. That means, if we want to "add" an aberration we have to
        # pass the negative of what we want.
        final_wfe = np.copy(self.ofc.ofc_data.get_intrinsic_zk(filter_name=""))

        for wfe in final_wfe:
            wfe -= np.array(wavefront_errors)

        field_idx = np.arange(final_wfe.shape[0])

        self._calculate_corrections(
            wfe=final_wfe,
            field_idx=field_idx,
            **(config if config is not None else dict()),
        )

    async def set_ofc_data_values(self, **kwargs):
        """Set ofc data values.

        Parameters
        ----------
        kwargs: `dict`
            Input keyword arguments. The method does not expect any particular
            input.

        Returns
        -------
        original_ofc_data_values : `dict`
            Original values in `ofc_data`.

        Notes
        -----
        For each input argument, check whether it is a valid entry in
        `self.ofc.ofc_data`. If yes, save the original value to the
        `original_ofc_data_values` dictionary and so on. If it fails to set a
        particular value, undo all the other changes and raise the exception.

        Uppon success, return the original values so users can restore it
        later.
        """

        original_ofc_data_values = dict()

        try:
            for key in kwargs:
                if key == "name":
                    self.log.debug(f"Configuring ofc_data for new instrument: {key}.")
                    await self.ofc.ofc_data.configure_instrument(kwargs[key])
                elif hasattr(self.ofc.ofc_data, key):
                    self.log.debug(f"Overriding ofc_data parameter {key}.")
                    original_ofc_data_values[key] = getattr(self.ofc.ofc_data, key)
                    setattr(self.ofc.ofc_data, key, kwargs[key])
        except Exception:
            self.log.error(
                "Error setting value in ofc_data. Restoring original values."
            )
            for key in original_ofc_data_values:
                setattr(self.ofc.ofc_data, key, original_ofc_data_values[key])
            raise
        else:
            return original_ofc_data_values
