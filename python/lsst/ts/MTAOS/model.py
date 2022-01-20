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

import yaml
import asyncio
import logging
import tempfile

import numpy as np

from lsst.ts.ofc import OFC
from lsst.ts.salobj import DefaultingValidator

from lsst.afw.image import VisitInfo

from .config_schema import WEP_PIPELINE_CONFIG

from .wavefront_collection import WavefrontCollection
from .utility import timeit

from lsst.ts.wep.Utility import writePipetaskCmd

from lsst.daf import butler as dafButler


class Model:

    # Maximum length of queue for wavefront error
    MAX_LEN_QUEUE = 10

    def __init__(
        self,
        instrument,
        data_path,
        ofc_data,
        log=None,
        run_name="mtaos_wep",
        collections="LSSTComCam/raw/all,LSSTComCam/calib",
        pipeline_instrument=None,
        pipeline_n_processes=9,
        data_instrument_name=None,
        reference_detector=0,
        zernike_table_name="zernikeEstimateRaw",
    ):
        """MTAOS model class.

        This class implements a model for the MTAOS operations. It encapsulates
        all business logic to isolate the CSC from the operation.

        Parameters
        ----------
        instrument : `str`
            Name of the instrument.
        data_path : `str`
            Path to the data butler.
        ofc_data : `OFCData`
            OFC data container class.
        log : `logging.Logger` or `None`, optional
            Optional logging class to be used for logging operations. If
            `None`, creates a new logger.

        Other Parameters
        ----------------
        run_name : `str`, optional
            Which name to use when running the pipeline task. This defines
            the location where the data is written in the butler.
            Default is "mtaos_wep".
        collections : `str`, optional
            String with the data collections to add to the pipeline task.
            Default is "LSSTComCam/raw/all,LSSTComCam/calib".
        pipeline_instrument : `dict` or `None`, optional
            A dictionary that maps the name of the instrument to the name used
            in the pipeline task. If None, use default dictionary mapping.
        pipeline_n_processes : `int`, optional
            Number of processes to use when running pipeline. Default is 9.
        data_instrument_name : `dict` or `None`, optional
            A dictionary that maps the name of the instrument to the name used
            by the pipeline task to store the data products. If None, use
            default dictionary mapping.
        reference_detector : `int`, optional
            Which detector to use as a referece to construct the WCS.
        zernike_table_name : `str`, optional
            Name of the table in the butler with zernike coeffients.
            Default is "zernikeEstimateRaw".

        Attributes
        ----------
        log : `Logger`
            Log facility.
        instrument : `str`
            Name of the instrument.
        data_path : `str`
            Path to the data butler.
        run_name : `str`, optional
            Which name to use when running the pipeline task. This defines
            the location where the data is written in the butler.
            Default is "mtaos_wep".
        collections : `str`, optional
            String with the data collections to add to the pipeline task.
            Default is "LSSTComCam/raw/all,LSSTComCam/calib".
        pipeline_instrument : `dict` or `None`, optional
            A dictionary that maps the name of the instrument to the name used
            in the pipeline task. If None, use default dictionary mapping.
        pipeline_n_processes : `int`, optional
            Number of processes to use when running pipeline. Default is 9.
        data_instrument_name : `dict` or `None`, optional
            A dictionary that maps the name of the instrument to the name used
            by the pipeline task to store the data products. If None, use
            default dictionary mapping.
        reference_detector : `int`, optional
            Which detector to use as a referece to construct the WCS.
        zernike_table_name : `str`, optional
            Name of the table in the butler with zernike coeffients.
            Default is "zernikeEstimateRaw".
        wep_configuration_validation : `DefaultingValidator`
            Provide schema validation for wavefront estimation pipeline task.
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

        self.instrument = instrument
        self.data_path = data_path
        self.run_name = run_name

        self.collections = collections
        self.pipeline_instrument = (
            pipeline_instrument
            if pipeline_instrument is not None
            else dict(
                comcam="lsst.obs.lsst.LsstComCam",
                lsstCam="lsst.obs.lsst.LsstCam",
                lsstFamCam="lsst.obs.lsst.LsstCam",
            )
        )
        self.pipeline_n_processes = pipeline_n_processes
        self.data_instrument_name = (
            data_instrument_name
            if data_instrument_name is not None
            else dict(
                comcam="LSSTComCam",
                lsstCam="LSSTCam",
                lsstFamCam="LSSTCam",
            )
        )
        self.zernike_table_name = zernike_table_name
        self.reference_detector = reference_detector

        self.wep_configuration_validation = DefaultingValidator(WEP_PIPELINE_CONFIG)

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

        self._user_gain = self.ofc.default_gain

        self.reset_wfe_correction()

    @property
    def user_gain(self):
        """Return the user gain."""
        return self._user_gain

    @user_gain.setter
    def user_gain(self, value):
        """Set user gain.

        Parameters
        ----------
        value : `float`
            New value for user_gain. Must be between 0 and 1.

        Raises
        ------
        ValueError
            If input `value` is outside the range (0.0, 1.0).
        """

        if 0.0 <= value <= 1.0:
            self._user_gain = value
        else:
            raise ValueError("User gain must be between 0 and 1.")

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
        one.
        """

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
    async def run_wep(
        self,
        visit_id,
        extra_id,
        config,
        run_name_extention="",
        **kwargs,
    ):
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
            If executed to process LSST corner wavefront sensors data, e.g.
            `extra_id` is not provided.
        """

        if extra_id is None:
            self.log.debug(
                f"Processing MainCamera corner wavefront sensor on image {visit_id}."
            )
            raise NotImplementedError(
                "LSSTCam Corner wavefront sensor processing not implemented yet."
            )
        else:
            # If data is intra/extra it must be ComCam at this point. Main
            # camera intra/extra data will be processed exclusively using OCPS.
            self.log.debug(
                f"Processing intra/extra pair: {visit_id}/{extra_id}. Expecting ComCam data."
            )

            await self.process_comcam(
                intra_id=visit_id,
                extra_id=extra_id,
                config=config,
                run_name_extention=run_name_extention,
            )

    async def process_comcam(
        self,
        intra_id,
        extra_id,
        config,
        run_name_extention="",
    ):
        """Process ComCam intra/extra focual images.

        Parameters
        ----------
        intra_id : `int`
            Id of the intra-focal image.
        extra_id : `int`
            Id of the extra-focal image.
        config : `dict`
            A dictionary with additional configuration for the pipeline task.
        run_name_extention : `str`, optional
            A string to be appended to the run name.
        """
        self.log.debug(f"Processing ComCam intra/extra pair: {intra_id}/{extra_id}.")

        wep_configuration = self.generate_wep_configuration(
            instrument="comcam", reference_id=intra_id, config=config
        )

        comcam_config_file = tempfile.NamedTemporaryFile(suffix=".yaml")

        comcam_config_file.write(yaml.safe_dump(wep_configuration).encode())

        comcam_config_file.flush()

        run_name = f"{self.run_name}{run_name_extention}"

        self.log.debug(
            f"Run name: {run_name}. Pipeline configuration in {comcam_config_file.name}."
        )

        run_pipetask_cmd = writePipetaskCmd(
            self.data_path,
            run_name,
            self.pipeline_instrument["comcam"],
            "refcats," + self.collections,
            pipelineYaml=comcam_config_file.name,
        )

        run_pipetask_cmd += f' -d "exposure IN ({intra_id}, {extra_id})"'
        run_pipetask_cmd += f" -j {self.pipeline_n_processes}"

        self.log.debug(f"Running: {run_pipetask_cmd}")

        # Run pipeline task in a process asynchronously
        wep_process = await asyncio.create_subprocess_shell(
            run_pipetask_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        log_task = asyncio.create_task(self.log_stream(wep_process.stderr))

        await wep_process.wait()

        if not log_task.done():
            log_task.cancel()

        try:
            await log_task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.log.debug(f"Exception in log task: {e}. Ignoring.")

        self.log.debug(f"Process returned: {wep_process.returncode}")

        # returncode contains the exit value of the process started with
        # asyncio.create_subprocess_shell. A value of zero means the process
        # finished successfully, anything else is considered an error. If we
        # get return code different than zero, assume the pipeline task
        # failed and raise an exception with the error report.
        if wep_process.returncode != 0:
            stdout, stderr = await wep_process.communicate()

            if len(stdout) > 0:
                self.log.debug(stdout.decode())

            if len(stderr) > 0:
                self.log.error(stderr.decode())

            raise RuntimeError(f"Error running pipeline task: {stderr.decode()}")

        self.log.debug("Data processing completed successfully. Gathering output.")

        comcam_config_file.close()

        butler = dafButler.Butler(self.data_path)

        # We may need to run the following in an executor so we won't block the
        # event loop.

        datasetRefs = list(
            butler.registry.queryDatasets(
                datasetType="postISRCCD", collections=[run_name]
            )
        )
        for ref in datasetRefs:
            self.log.debug(ref.dataId)

        # Get output
        data_ids = butler.registry.queryDatasets(
            self.zernike_table_name,
            dataId=dict(
                instrument=self.data_instrument_name["comcam"], exposure=intra_id
            ),
            collections=[run_name],
        )

        self.log.debug(f"Processing yielded: {data_ids}")

        self.wavefront_errors.append(
            [
                (
                    data_id.dataId["detector"],
                    butler.get(
                        self.zernike_table_name,
                        dataId=data_id.dataId,
                        collections=[run_name],
                    ),
                )
                for data_id in data_ids
            ]
        )

    def generate_wep_configuration(self, instrument, reference_id, config):
        """Generate configuration dictionary for running the WEP pipeline based
        on a reference image id and a configuration dictionary.

        Parameters
        ----------
        instrument : `str`
            Name of the instrument.
        reference_id : `int`
            Id of the reference image.
        config : `dict`
            Additional configuration overrides provided by the user.

        Returns
        -------
        wep_configuration : `dict`
            Configuration dictionary validated against the WEP schema.
        """

        # TODO: Implement configuration when user runs select_sources
        # beforehand.

        return self.wep_configuration_validation.validate(config)

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
            field_idx, wfe = self.get_wavefront_errors()

            self._calculate_corrections(wfe=wfe, field_idx=field_idx, **kwargs)

        finally:
            # Clear the queue
            self._clear_wfe_collections()

    def get_wavefront_errors(self):
        """Get wavefront errors.

        Returns
        -------
        field_idx : `np.ndarray [int]`
            Array with field indexes.
        wfe : `np.ndarray`
            Array of arrays with the zernike coeficients for each field index.
        """

        wfe_data_container = (
            self.wavefront_errors.getListOfWavefrontErrorAvgInTakenData()
        )

        return self.get_field_idx_wfe_from_data_container(wfe_data_container)

    def get_rejected_wavefront_errors(self):
        """Get rejected wavefront errors.

        Returns
        -------
        field_idx : `np.ndarray [int]`
            Array with field indexes.
        wfe : `np.ndarray`
            Array of arrays with the zernike coeficients for each field index.
        """

        wfe_data_container = (
            self.rejected_wavefront_errors.getListOfWavefrontErrorAvgInTakenData()
        )

        return self.get_field_idx_wfe_from_data_container(wfe_data_container)

    def _calculate_corrections(self, wfe, field_idx, **kwargs):
        """Compute corrections from input wavefront errors.

        Parameters
        ----------
        wfe : `np.ndarray`
            2D array with wavefront errors (in microns). Each element contains
            the wavefront errors for a specific field index.
        field_idx : `np.ndarray`
            Field index for the input wavefront errors.
        **kwargs : `dict`
            User input keyword arguments. Optional standard kwargs:
                gain: `float`
                    User gain (default -1).
                rot: `float`
                    Camera rotation angle in degrees (default 0).
                filter_name: `string`
                    Name of the filter used for the observations.
        """
        gain = kwargs.get("user_gain", self.user_gain)
        rot = kwargs.get("rot", 0.0)
        filter_name = kwargs.get("filter_name", "")

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

        self.log.debug(f"Currently configured with {self.instrument} instrument.")

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
        **kwargs : `dict`
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

                    # Check if there is a type annotation and try to cast the
                    # values as such.
                    if (key in self.ofc.ofc_data.__annotations__) and (
                        self.ofc.ofc_data.__annotations__[key] != np.ndarray
                    ):
                        setattr(
                            self.ofc.ofc_data,
                            key,
                            self.ofc.ofc_data.__annotations__[key](kwargs[key]),
                        )

                    elif (key in self.ofc.ofc_data.__annotations__) and (
                        self.ofc.ofc_data.__annotations__[key] == np.ndarray
                    ):

                        setattr(
                            self.ofc.ofc_data,
                            key,
                            np.array(kwargs[key]),
                        )

                    elif key == "comp_dof_idx":
                        # Handle special case comp_dof_idx.
                        if not isinstance(kwargs[key], dict):
                            raise RuntimeError(
                                f"comp_dof_idx must be a dictionary. Got {type(kwargs[key])}."
                            )

                        new_comp_dof_idx = kwargs[key].copy()

                        for comp_dof_idx_key in new_comp_dof_idx:
                            new_comp_dof_idx[comp_dof_idx_key] = np.array(
                                new_comp_dof_idx[comp_dof_idx_key], dtype=bool
                            )

                    elif key == "xref":
                        self.ofc.ofc_data.xref = kwargs[key]

        except Exception:
            self.log.error(
                "Error setting value in ofc_data. Restoring original values."
            )
            for key in original_ofc_data_values:
                setattr(self.ofc.ofc_data, key, original_ofc_data_values[key])
            raise
        else:
            return original_ofc_data_values

    async def log_stream(self, stream: asyncio.subprocess.PIPE) -> None:
        """Log messages from input stream asynchronously.

        Parameters
        ----------
        stream : `asyncio.subprocess.PIPE`
            Output stream pipe to process and log.
        """

        while True:
            message = await stream.readline()
            self.log.debug(message.decode())

    def _get_visit_info(self, instrument: str, exposure: int) -> VisitInfo:
        """Get visit info from the butler.

        Parameters
        ----------
        instrument : `str`
            Name of the instrument.
        exposure : `int`
            exposure id of data to retrieve information from.

        Returns
        -------
        `VisitInfo`
            Object with information about a single exposure of an imaging
            camera.
        """
        return dafButler.Butler(self.data_path).get(
            "raw.visitInfo",
            dataId={
                "instrument": self.data_instrument_name[instrument],
                "exposure": exposure,
                "detector": self.reference_detector,
            },
            collections=self.collections.split(","),
        )

    @staticmethod
    def get_field_idx_wfe_from_data_container(data_container):
        """Parse data container generated from calling
        `WavefrontCollection.getListOfWavefrontErrorAvgInTakenData` into an
        array with field indices and an array of wavefront errors.

        Parameters
        ----------
        data_container : `dict`
            Dictionary returned by
            `WavefrontCollection.getListOfWavefrontErrorAvgInTakenData()`.

        Returns
        -------
        field_idx : `np.ndarray [int]`
            Array with field indexes.
        wfe : `np.ndarray`
            Array of arrays with the zernike coeficients for each field index.
        """
        field_idx = np.array([sensor_id for sensor_id in data_container])

        wfe = np.array([data_container[sensor_id] for sensor_id in data_container])

        return field_idx, wfe
