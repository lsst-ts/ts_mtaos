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

from lsst.ts.ofc.ctrlIntf.M2HexapodCorrection import M2HexapodCorrection
from lsst.ts.ofc.ctrlIntf.CameraHexapodCorrection import CameraHexapodCorrection
from lsst.ts.ofc.ctrlIntf.M1M3Correction import M1M3Correction
from lsst.ts.ofc.ctrlIntf.M2Correction import M2Correction
from lsst.ts.ofc.ctrlIntf.OFCCalculationFactory import OFCCalculationFactory
from lsst.ts.ofc.ctrlIntf.FWHMSensorData import FWHMSensorData
from lsst.ts.wep.ctrlIntf.SensorWavefrontError import SensorWavefrontError
from lsst.ts.wep.Utility import FilterType
from lsst.ts.wep.bsc.CamFactory import CamFactory

from .CollOfListOfWfErr import CollOfListOfWfErr
from .Utility import timeit


class Model:

    # Maximum length of queue for wavefront error
    MAX_LEN_QUEUE = 10

    def __init__(self, config, state0Dof, log=None):
        """MTAOS model class.

        This class implements a model for the MTAOS operations. It encapsulates
        all business logic to isolate the CSC from the operation.

        Parameters
        ----------
        config : `lsst.ts.MTAOS.Config`
            Configuration.
        state0Dof : `dict`
            Dictionary with state0 DoF data. None for default DoF.
        log : `logging.Logger` or `None`, optional
            Optional logging class to be used for logging operations. If
            `None`, creates a new logger.

        Attributes
        ----------
        log : `Logger`
            Log facility.
        config : `lsst.ts.MTAOS.Config`
            Configuration.
        wavefront_errors : `CollOfListOfWfErr`
            Object to manage list of wavefront errors.
        rejected_wavefront_errors : `CollOfListOfWfErr`
            Object to manage list of rejected wavefront errors.
        user_gain : `float`
            User provided gain for the OFC. Value must be either -1, the gain
            value will be dicided by PSSN, or between 0 and 1.
        fwhm_data : `list` of `FWHMSensorData`
            List of FWHM (full width at half maximum) sensor data.
        ofc : `lsst.ts.ofc.ctrlIntf.OFCCalculation`
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

        # Store user gain value in a private variable. Use self.user_gain to
        # access the variable. Value is guarded and must be equal to -1 or
        # between 0 and 1. Set to -1 to ignore user gain. In this case, the
        # gain value will be dicided by PSSN
        self._user_gain = -1

        # Collection of calculated list of wavefront error
        self.wavefront_errors = CollOfListOfWfErr(self.MAX_LEN_QUEUE)

        # Collection of calculated list of rejected wavefront error
        self.rejected_wavefront_errors = CollOfListOfWfErr(self.MAX_LEN_QUEUE)

        # List of FWHM (full width at half maximum) sensor data
        self.fwhm_data = []

        # Optical feedback control
        instName = self.config.getInstName()
        self.ofc = OFCCalculationFactory.getCalculator(instName, state0Dof)

        # M2 hexapod correction
        self.m2_hexapod_correction = M2HexapodCorrection(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # Camera hexapod correction
        self.cam_hexapod_correction = CameraHexapodCorrection(
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        )

        # M1M3 actuator correction
        self.m1m3_correction = M1M3Correction(np.zeros(M1M3Correction.NUM_OF_ACT))

        # M2 actuator correction
        self.m2_correction = M2Correction(np.zeros(M2Correction.NUM_OF_ACT))

    @property
    def user_gain(self):
        """Return the user gain.
        """
        if self._user_gain == -1 or 0.0 <= self._user_gain <= 1.0:
            return self._user_gain
        else:
            self.log.warning(f"Invalid user gain {self._user_gain}. Reseting to -1.")
            self.user_gain = -1
            return -1

    @user_gain.setter
    def user_gain(self, value):
        """Set user gain.
        """
        if value == -1 or 0.0 <= value <= 1.0:
            self._user_gain = value
        else:
            ValueError(
                f"User gain must be either -1 or in the range (0., 1.). Received: {value}."
            )

    def getListOfWavefrontError(self):
        """Get the list of wavefront error from the collection.

        This is to let MtaosCsc to publish the latest calculated wavefront
        error.

        Returns
        -------
        list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of wavefront error data.
        """

        return self.wavefront_errors.pop()

    def getListOfWavefrontErrorRej(self):
        """Get the list of rejected wavefront error from the collection.

        This is to let MtaosCsc to publish the latest rejected wavefront
        error.

        Returns
        -------
        list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of rejected wavefront error data.
        """

        return self.rejected_wavefront_errors.pop()

    def getListOfFWHMSensorData(self):
        """Get the list of FWHM sensor data.

        FWHM: Full width at half maximum.

        Returns
        -------
        list[lsst.ts.ofc.ctrlIntf.FWHMSensorData]
            List of FWHM sensor data.
        """

        return self.fwhm_data

    def setFWHMSensorData(self, sensorId, fwhmValues):
        """Set the FWHM sensor data.

        FWHM: Full width at half maximum.

        Parameters
        ----------
        sensorId : int
            Sensor Id.
        fwhmValues : numpy.ndarray
            FWHM values for this sensor.
        """

        sensorData = self._getFWHMSensorDataInList(sensorId)

        if sensorData is None:
            sensorDataNew = FWHMSensorData(sensorId, fwhmValues)
            self.fwhm_data.append(sensorDataNew)
        else:
            sensorData.setFwhmValues(fwhmValues)

    def _getFWHMSensorDataInList(self, sensorId):
        """Get the FWHM sensor data of specified sensor Id in list.

        FWHM: Full width at half maximum.

        Parameters
        ----------
        sensorId : int
            Sensor Id.

        Returns
        -------
        lsst.ts.ofc.ctrlIntf.FWHMSensorData or None
            Return the object of FWHMSensorData if found in list. Otherwise,
            return None.
        """

        for fwhmSensorData in self.fwhm_data:
            if fwhmSensorData.getSensorId() == sensorId:
                return fwhmSensorData

        return None

    def resetFWHMSensorData(self):
        """Reset the FWHM sensor data to be empty.

        FWHM: Full width at half maximum.
        """

        self.fwhm_data = []

    def getDofAggr(self):
        """Get the aggregated DOF.

        DOF: Degree of freedom.

        Returns
        -------
        numpy.ndarray
            Aggregated DOF.
        """

        return self.ofc.getStateAggregated()

    def getDofVisit(self):
        """Get the DOF correction from the last visit.

        DOF: Degree of freedom.

        Returns
        -------
        numpy.ndarray
            DOF correction from the last visit.
        """

        return self.ofc.getStateCorrectionFromLastVisit()

    def rejCorrection(self):
        """Reject the correction of subsystems."""

        ztaac = self.ofc.getZtaac()

        paramData = ztaac.getParamData()
        dofIdx = paramData.getDofIdx()

        dofVisit = self.getDofVisit()

        ztaac.aggState(-dofVisit[dofIdx])

        self.ofc.initDofFromLastVisit()

    def resetWavefrontCorrection(self):
        """Reset the current calculation contains the wavefront error and
        subsystem corrections to be empty.

        This function is needed for the long slew angle of telescope.
        """

        self._clearCollectionsOfWfErr()
        (
            self.m2_hexapod_correction,
            self.cam_hexapod_correction,
            self.m1m3_correction,
            self.m2_correction,
        ) = self.ofc.resetOfcState()

    def _clearCollectionsOfWfErr(self):
        """Clear the collections of wavefront error contain the rejected one.
        """

        self.wavefront_errors.clear()
        self.rejected_wavefront_errors.clear()

    def getM2HexCorr(self):
        """Get the M2 hexapod correction.

        Returns
        -------
        float
            X position offset in um.
        float
            Y position offset in um.
        float
            Z position offset in um.
        float
            X rotation offset in deg.
        float
            Y rotation offset in deg.
        float
            Z rotation offset in deg.
        """

        return self.m2_hexapod_correction.getCorrection()

    def getCamHexCorr(self):
        """Get the camera hexapod correction.

        Returns
        -------
        float
            X position offset in um.
        float
            Y position offset in um.
        float
            Z position offset in um.
        float
            X rotation offset in deg.
        float
            Y rotation offset in deg.
        float
            Z rotation offset in deg.
        """

        return self.cam_hexapod_correction.getCorrection()

    def getM1M3ActCorr(self):
        """Get the M1M3 actuator force correction.

        Returns
        -------
        numpy.ndarray
            The forces to apply to the 156 force actuators in N.
        """

        return self.m1m3_correction.getZForces()

    def getM2ActCorr(self):
        """Get the M2 actuator force correction.

        Returns
        -------
        numpy.ndarray
            The forces to apply to the 72 axial actuators in N.
        """

        return self.m2_correction.getZForces()

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

    def rejWavefrontErrorUnreasonable(self, listOfWfErr):
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
        # FIXME: (DM-28710) Once we implement run_wep we will be able to get
        # this information from it. Right now there is no way of knowing it
        # for sure. This will come from the images metadata.
        filterType = FilterType.REF
        rotAngInDeg = 0

        try:
            self.ofc.setFilter(filterType)
            self.ofc.setRotAng(rotAngInDeg)
            if self.user_gain == -1:
                if len(self.fwhm_data) == 0:
                    raise RuntimeError("No FWHM sensor data to use.")
                else:
                    self.ofc.setGainByPSSN()
                    self.ofc.setFWHMSensorDataOfCam(self.fwhm_data)
            else:
                self.ofc.setGainByUser(self.user_gain)

            listOfWfErrAvg = (
                self.wavefront_errors.getListOfWavefrontErrorAvgInTakenData()
            )

            self._calculate_corrections(listOfWfErrAvg)

        finally:
            # Clear the queue
            self._clearCollectionsOfWfErr()

    def add_correction(self, wavefront_errors, config=None):
        """Compute ofc corrections from user-defined wavefront erros.

        Parameters
        ----------
        wavefront_errors : `np.array` or `list` of `float`
            Input wavefront errors (in um).
        config : `dict`, optional
            Optional additional configuration parameters to customize ofc.
        """

        self.log.debug(f"Currently configured with {self.config.getCamType()!r}")

        # Get list of detectors. Since the method considers that aberration is
        # uniform across all detectors, it will build a set of corrections
        # based of this assumption. So need to get list of detectors.
        detector_list = self.camera.getWfsCcdList()

        # Get the intrinsic zernike coeffients. Will consider white light for
        # now but may use last filter set in select sources in the future.
        self.log.debug("Assuming white light filter to compute aberration.")

        intrinsic_zk = self.ofc.ztaac.dataShare.getIntrinsicZk(
            FilterType.REF, self.ofc.ztaac.dataShare.getFieldIdx(detector_list)
        )

        # Now compute the wavefront error matrix by summing the input with the
        # intrinsic zernike coeffients.
        sensor_ids = self.ofc.ztaac.mapSensorNameToId(detector_list)
        all_sensor_wavefront_errors = []
        for sid, zk in zip(sensor_ids, intrinsic_zk):
            sensor_wavefront_errors = SensorWavefrontError(numOfZk=len(zk))
            sensor_wavefront_errors.setSensorId(sid)
            # Note that it subtracts the users input wavefront from the
            # intrinsic data. The ofc will return corrections to remove the
            # measured aberration. That means, if we want to "add" an
            # aberration we have to pass the negative of what we want.
            sensor_wavefront_errors.setAnnularZernikePoly(zk - wavefront_errors)
            all_sensor_wavefront_errors.append(sensor_wavefront_errors)

        self._calculate_corrections(all_sensor_wavefront_errors)

    def _calculate_corrections(self, wavefront_errors):
        """Utility method to calculate corrections using ofc.

        Parameters
        ----------
        wavefront_errors : `list` of `SensorWavefrontError`

        """

        (
            m2_hex_correction,
            cam_hex_correction,
            m1m3_correction,
            m2_correction,
        ) = self.ofc.calculateCorrections(wavefront_errors)

        # Need to add a step of checking the calculated correction
        # in the future
        self.m2_hexapod_correction = m2_hex_correction
        self.cam_hexapod_correction = cam_hex_correction
        self.m1m3_correction = m1m3_correction
        self.m2_correction = m2_correction
