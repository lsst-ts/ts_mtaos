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

import numpy as np

from lsst.ts.ofc.ctrlIntf.M2HexapodCorrection import M2HexapodCorrection
from lsst.ts.ofc.ctrlIntf.CameraHexapodCorrection import CameraHexapodCorrection
from lsst.ts.ofc.ctrlIntf.M1M3Correction import M1M3Correction
from lsst.ts.ofc.ctrlIntf.M2Correction import M2Correction
from lsst.ts.wep.ctrlIntf.WEPCalculationFactory import WEPCalculationFactory
from lsst.ts.ofc.ctrlIntf.OFCCalculationFactory import OFCCalculationFactory
from lsst.ts.ofc.ctrlIntf.FWHMSensorData import FWHMSensorData
from lsst.ts.wep.ctrlIntf.RawExpData import RawExpData
from lsst.ts.wep.Utility import FilterType

from .CalcTime import CalcTime
from .CollOfListOfWfErr import CollOfListOfWfErr


class Model(object):

    # Maximum length of queue for wavefront error
    MAX_LEN_QUEUE = 10

    def __init__(self, config, state0Dof):
        """Initialize the model class.

        Parameters
        ----------
        config : Config
            Configuration.
        state0Dof : dict
            Dictionary with state0 DoF data. None for default DoF.
        """

        # Configuration
        self._config = config

        # Collection of calculated list of wavefront error
        self.collectionOfListOfWfErr = CollOfListOfWfErr(self.MAX_LEN_QUEUE)

        # Collection of calculated list of rejected wavefront error
        self.collectionOfListOfWfErrRej = CollOfListOfWfErr(self.MAX_LEN_QUEUE)

        # Gain value between 0 and 1. Set to -1 to ignore user gain. In this
        # case, the gain value will be dicided by PSSN
        self.userGain = -1

        # List of FWHM (full width at half maximum) sensor data
        self.listOfFWHMSensorData = []

        # Calculation time of WEP
        self.calcTimeWep = CalcTime()

        # Calculation time of OFC
        self.calcTimeOfc = CalcTime()

        # Wavefront estimation pipeline
        camType = self._config.getCamType()
        isrDir = self._config.getIsrDir()
        self.wep = WEPCalculationFactory.getCalculator(camType, isrDir)

        # Optical feedback control
        instName = self._config.getInstName()
        self.ofc = OFCCalculationFactory.getCalculator(instName, state0Dof)

        # M2 hexapod correction
        self.m2HexapodCorrection = M2HexapodCorrection(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # Camera hexapod correction
        self.cameraHexapodCorrection = CameraHexapodCorrection(
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        )

        # M1M3 actuator correction
        self.m1m3Correction = M1M3Correction(np.zeros(M1M3Correction.NUM_OF_ACT))

        # M2 actuator correction
        self.m2Correction = M2Correction(np.zeros(M2Correction.NUM_OF_ACT))

    def getConfig(self):
        """Get the configuration.

        Returns
        -------
        Config
            Configuration.
        """

        return self._config

    def getListOfWavefrontError(self):
        """Get the list of wavefront error from the collection.

        This is to let MtaosCsc to publish the latest calculated wavefront
        error.

        Returns
        -------
        list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of wavefront error data.
        """

        return self.collectionOfListOfWfErr.pop()

    def getListOfWavefrontErrorRej(self):
        """Get the list of rejected wavefront error from the collection.

        This is to let MtaosCsc to publish the latest rejected wavefront
        error.

        Returns
        -------
        list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of rejected wavefront error data.
        """

        return self.collectionOfListOfWfErrRej.pop()

    def getListOfFWHMSensorData(self):
        """Get the list of FWHM sensor data.

        FWHM: Full width at half maximum.

        Returns
        -------
        list[lsst.ts.ofc.ctrlIntf.FWHMSensorData]
            List of FWHM sensor data.
        """

        return self.listOfFWHMSensorData

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
            self.listOfFWHMSensorData.append(sensorDataNew)
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

        for fwhmSensorData in self.listOfFWHMSensorData:
            if fwhmSensorData.getSensorId() == sensorId:
                return fwhmSensorData

        return None

    def resetFWHMSensorData(self):
        """Reset the FWHM sensor data to be empty.

        FWHM: Full width at half maximum.
        """

        self.listOfFWHMSensorData = []

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

        dataShare = ztaac.dataShare
        dofIdx = dataShare.getDofIdx()

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
            self.m2HexapodCorrection,
            self.cameraHexapodCorrection,
            self.m1m3Correction,
            self.m2Correction,
        ) = self.ofc.resetOfcState()

    def _clearCollectionsOfWfErr(self):
        """Clear the collections of wavefront error contain the rejected one.
        """

        self.collectionOfListOfWfErr.clear()
        self.collectionOfListOfWfErrRej.clear()

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

        return self.m2HexapodCorrection.getCorrection()

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

        return self.cameraHexapodCorrection.getCorrection()

    def getM1M3ActCorr(self):
        """Get the M1M3 actuator force correction.

        Returns
        -------
        numpy.ndarray
            The forces to apply to the 156 force actuators in N.
        """

        return self.m1m3Correction.getZForces()

    def getM2ActCorr(self):
        """Get the M2 actuator force correction.

        Returns
        -------
        numpy.ndarray
            The forces to apply to the 72 axial actuators in N.
        """

        return self.m2Correction.getZForces()

    def procCalibProducts(self, calibsDir):
        """Process new calibration products.

        Parameters
        ----------
        calibsDir : str
            Calibration products directory.
        """

        self.wep.ingestCalibs(calibsDir)

    def procIntraExtraWavefrontError(
        self,
        raInDeg,
        decInDeg,
        aFilter,
        rotAngInDeg,
        priVisit,
        priDir,
        secVisit,
        secDir,
        userGain,
    ):
        """Process the intra- and extra-focal wavefront error.

        Parameters
        ----------
        raInDeg : float
            Right ascension in degree. The value should be in (0, 360).
        decInDeg : float
            Declination in degree. The value should be in (-90, 90).
        aFilter : int
            Filter used while collecting the images (1: u, 2: g, 3: r, 4: i,
            5: z, 6: y, 7: ref).
        rotAngInDeg : float
            The camera rotation angle in degree (-90 to 90).
        priVisit : int
            Primary visit number (intra-focal visit number).
        priDir : str
            Primary directory of image data (intra-focal images).
        secVisit : int
            Secondary visit number (extra-focal visit number).
        secDir : str
            Secondary directory of image data (extra-focal images).
        userGain : float
            The gain requested by the user. A value of -1 means don't use user
            gain.
        """

        intraRawExpData = self._collectRawExpData(priVisit, priDir)
        extraRawExpData = self._collectRawExpData(secVisit, secDir)

        # Get the filter type as the enum
        filterType = FilterType(aFilter)

        # Do WEP and record time
        self.calcTimeWep.evalCalcTimeAndPutRecord(
            self._calcWavefrontError,
            raInDeg,
            decInDeg,
            filterType,
            rotAngInDeg,
            intraRawExpData,
            extraRawExpData,
        )

        # Record the user gain value for OFC to use
        self.userGain = userGain

    def _collectRawExpData(self, visit, imgDir):
        """Collect the raw exposure data.

        Parameters
        ----------
        visit: int
            Visit number.
        imgDir : str
            Image directory.

        Returns
        -------
        lsst.ts.wep.ctrlIntf.RawExpData
            Raw exposure data of the wavefront sensor.
        """

        expData = RawExpData()

        # Hard coded to use snap=0 here. DM might use the sequense number
        # instead in the future.
        expData.append(visit, 0, imgDir)

        return expData

    def _calcWavefrontError(
        self,
        raInDeg,
        decInDeg,
        filterType,
        rotAngInDeg,
        rawExpData,
        extraRawExpData=None,
    ):
        """Calculate the wavefront error.

        Parameters
        ----------
        raInDeg : float
            Right ascension in degree. The value should be in (0, 360).
        decInDeg : float
            Declination in degree. The value should be in (-90, 90).
        filterType : enum 'FilterType' in lsst.ts.wep.Utility
            The new filter configuration to use for WEP data processing.
        rotAngInDeg : float
            The camera rotation angle in degree (-90 to 90).
        rawExpData : lsst.ts.wep.ctrlIntf.RawExpData
            Raw exposure data for the wavefront sensor. If the input of
            extraRawExpData is not None, this input will be the intra-focal raw
            exposure data.
        extraRawExpData : lsst.ts.wep.ctrlIntf.RawExpData, optional
            This is the extra-focal raw exposure data if not None. (the default
            is None.)
        """

        # Set the default sky file for the test
        # This will be removed in the final
        self._setSkyFile()

        self.wep.setBoresight(raInDeg, decInDeg)
        self.wep.setFilter(filterType)
        self.wep.setRotAng(rotAngInDeg)

        listOfWfErr = self.wep.calculateWavefrontErrors(
            rawExpData, extraRawExpData=extraRawExpData
        )
        listOfWfErrRej = self.rejWavefrontErrorUnreasonable(listOfWfErr)

        # Collect the data
        self.collectionOfListOfWfErr.append(listOfWfErr)
        self.collectionOfListOfWfErrRej.append(listOfWfErrRej)

    def _setSkyFile(self):
        """Set the sky file for the test.

        This function will be removed in the final.
        """

        skyFile = self._config.getDefaultSkyFile()
        if skyFile is not None:
            self.wep.setSkyFile(skyFile.as_posix())

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

    def calcCorrectionFromAvgWfErr(self):
        """Calculate the correction of subsystems based on the average
        wavefront error of multiple exposure images in a single visit."""

        filterType = self.wep.getFilter()
        rotAngInDeg = self.wep.getRotAng()

        # Use the try loop to enforce to clear the collection of wavefront
        # error to avoid the mistakes in the next visit
        try:
            # Do OFC and record time
            self.calcTimeOfc.evalCalcTimeAndPutRecord(
                self._calcCorrection, filterType, rotAngInDeg
            )
        except Exception:
            raise
        finally:
            # Clear the queue
            self._clearCollectionsOfWfErr()

    def _calcCorrection(self, filterType, rotAngInDeg):
        """Calculate the correction of subsystems.

        Parameters
        ----------
        filterType : enum 'FilterType' in lsst.ts.wep.Utility
            The new filter configuration to use for OFC data processing.
        rotAngInDeg : float
            The camera rotation angle in degree (-90 to 90).

        Raises
        ------
        RuntimeError
            No FWHM sensor data to use.
        """

        self.ofc.setFilter(filterType)
        self.ofc.setRotAng(rotAngInDeg)
        if self.userGain == -1:
            if len(self.listOfFWHMSensorData) == 0:
                raise RuntimeError("No FWHM sensor data to use.")
            else:
                self.ofc.setGainByPSSN()
                self.ofc.setFWHMSensorDataOfCam(self.listOfFWHMSensorData)
        else:
            self.ofc.setGainByUser(self.userGain)

        listOfWfErrAvg = (
            self.collectionOfListOfWfErr.getListOfWavefrontErrorAvgInTakenData()
        )
        (
            m2HexapodCorrection,
            cameraHexapodCorrection,
            m1m3Correction,
            m2Correction,
        ) = self.ofc.calculateCorrections(listOfWfErrAvg)

        # Need to add a step of checking the calculated correction
        # in the future
        self.m2HexapodCorrection = m2HexapodCorrection
        self.cameraHexapodCorrection = cameraHexapodCorrection
        self.m1m3Correction = m1m3Correction
        self.m2Correction = m2Correction

    def getAvgCalcTimeWep(self):
        """Get the average of calculation time of WEP.

        WEP: Wavefront estimation pipeline.

        Returns
        -------
        float
            Average of calculation time in second.
        """

        return self.calcTimeWep.getAvgTime()

    def getAvgCalcTimeOfc(self):
        """Get the average of calculation time of OFC.

        OFC: Optical feedback control.

        Returns
        -------
        float
            Average of calculation time in second.
        """

        return self.calcTimeOfc.getAvgTime()
