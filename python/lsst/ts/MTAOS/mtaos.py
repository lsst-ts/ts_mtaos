# This file is part of MTAOS.
#
# Developed for the LSST.
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

__all__ = ["MTAOS"]

import enum
import warnings
import numpy as np
import time
import traceback

from lsst.ts import salobj
import SALPY_Hexapod
import SALPY_MTAOS
import SALPY_MTM1M3
import SALPY_MTM2

from lsst.ts.wep.Utility import FilterType
from lsst.ts.wep.ParamReader import ParamReader

from lsst.ts.ofc.ctrlIntf.CameraHexapodCorrection import CameraHexapodCorrection
from lsst.ts.ofc.ctrlIntf.M1M3Correction import M1M3Correction
from lsst.ts.ofc.ctrlIntf.M2Correction import M2Correction
from lsst.ts.ofc.ctrlIntf.M2HexapodCorrection import M2HexapodCorrection
from lsst.ts.ofc.ctrlIntf.OFCCalculationFactory import OFCCalculationFactory
from lsst.ts.ofc.ctrlIntf.SensorWavefrontError import SensorWavefrontError
from lsst.ts.wep.ctrlIntf.RawExpData import RawExpData
from lsst.ts.wep.ctrlIntf.WEPCalculationFactory import WEPCalculationFactory

from lsst.ts.MTAOS.Utility import getModulePath, getConfigDir, getIsrDirPath, \
    getCamType, getInstName


class WEPWarning(enum.Enum):
    NoWarning = SALPY_MTAOS.MTAOS_shared_WEPWarning_NoWarning
    InvalidSensorId = SALPY_MTAOS.MTAOS_shared_WEPWarning_InvalidSensorId
    InvalidAnnularZernikePoly = \
        SALPY_MTAOS.MTAOS_shared_WEPWarning_InvalidAnnularZernikePoly


class OFCWarning(enum.Enum):
    NoWarning = SALPY_MTAOS.MTAOS_shared_OFCWarning_NoWarning


class MTAOS(salobj.BaseCsc):
    def __init__(self, settingFileName="default.yaml",
                 initial_state=salobj.State.STANDBY,
                 initial_simulation_mode=0):
        super().__init__(SALPY_MTAOS, index=0, initial_state=initial_state,
                         initial_simulation_mode=initial_simulation_mode)

        # Read the configuration file
        settingFilePath = getConfigDir().joinpath(settingFileName)
        self.settingFile = ParamReader(filePath=settingFilePath)

        self.telemetry_period = 0.05
        self.salinfo.manager.setDebugLevel(0)

        self.mtcamerahexapod = salobj.Remote(SALPY_Hexapod, index=1)
        self.mtcamerahexapod.salinfo.manager.setDebugLevel(0)

        self.mtm1m3 = salobj.Remote(SALPY_MTM1M3, index=0)
        self.mtm1m3.salinfo.manager.setDebugLevel(0)

        self.mtm2 = salobj.Remote(SALPY_MTM2, index=0)
        self.mtm2.salinfo.manager.setDebugLevel(0)

        self.mtm2hexapod = salobj.Remote(SALPY_Hexapod, index=2)
        self.mtm2hexapod.salinfo.manager.setDebugLevel(0)

        self.bypassWavefrontErrorCheck = True

        self.cameraHexapodAlignment = CameraHexapodCorrection(
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.m2HexapodAlignment = M2HexapodCorrection(
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        self.wavefrontError = []

        numOfDOf = self.getNumOfDof()
        self.aggregatedDoF = np.zeros(numOfDOf)
        self.visitDoF = np.zeros(numOfDOf)

        self.cameraHexapodCorrection = CameraHexapodCorrection(
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.m1m3Correction = M1M3Correction(np.zeros(156))
        self.m2Correction = M2Correction(np.zeros(72))
        self.m2HexapodCorrection = M2HexapodCorrection(
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        self.numberOfWEPProcessors = 1

        camType = self.getCamType()
        isrDir = self.getIsrDir()
        self.wep = WEPCalculationFactory.getCalculator(camType, isrDir)

        instName = self.getInstName()
        self.ofc = OFCCalculationFactory.getCalculator(instName)

        print("READY")

    def getNumOfDof(self):
        """Get the number of degree of freedom (DOF).

        Returns
        -------
        int
            Number of DOF.
        """

        return int(self.settingFile.getSetting("numOfDof"))

    def getNumOfZk(self):
        """Get the number of annular Zernike polynomial.

        Returns
        -------
        int
            Number of annular Zernike polynomial.
        """

        return int(self.settingFile.getSetting("annularZernikePolyCount"))

    def getCamType(self):
        """Get the enum of camera type.

        Returns
        -------
        enum 'CamType' in lsst.ts.wep.Utility
            Camera type.
        """

        camera = self.settingFile.getSetting("camera")

        return getCamType(camera)

    def getInstName(self):
        """Get the enum of instrument name.

        Returns
        -------
        enum 'InstName' in lsst.ts.ofc.Utility
            Instrument name.
        """

        instName = self.settingFile.getSetting("instrument")

        return getInstName(instName)

    def getIsrDir(self):
        """Get the instrument signature removal (ISR) directory.

        This directory will have the input and output that the data butler
        needs.

        Returns
        -------
        str
            ISR directory.
        """

        isrDir = getIsrDirPath()
        if (isrDir is None):
            isrDir = self.settingFile.getSetting("defaultIsrDir")
            warnings.warn("No 'ISRDIRPATH' assigned. Use %s instead." % isrDir,
                          category=UserWarning)
            return isrDir
        else:
            return isrDir.as_posix()

    def getDefaultSkyFile(self):
        """Get the default sky file path.

        This is for the test only.

        Returns
        -------
        pathlib.PosixPath or None
            Get the default sky file path. Return None if there is no such
            setting.
        """

        try:
            relativePath = self.settingFile.getSetting("defaultSkyFilePath")
            return getModulePath().joinpath(relativePath)
        except KeyError:
            return None

    def getWep(self):
        """Get the wavefront estimation pipeline (WEP) calculation instance.

        Returns
        -------
        lsst.ts.wep.ctrlIntf.WEPCalculation or related derivatives
            WEP calculation instance.
        """

        return self.wep

    def getOfc(self):
        """Get the optical feedback control (OFC) calculation instance.

        Returns
        -------
        lsst.ts.ofc.ctrlIntf.OFCCalculation or related derivatives
            OFC calculation instance.
        """

        return self.ofc

    def do_measureAlignment(self, id_data):
        pass

    async def do_issueAlignmentCorrection(self, id_data):
        """Commands the MTAOS to issue alignment corrections to the Camera
        Hexapod and M2 Hexapod with using the most recently measured alignment
        error.

        Parameters
        ----------
        id_data.data.bypassCameraHexapod : bool
            If True the MTAOS will not issue the positionSet command to the
            Camera Hexapod.
        id_data.data.bypassM2Hexapod : bool
            If True the MTAOS will not issue the positionSet command to the M2
            Hexapod.
        """

        bypassCameraHexapod = id_data.data.bypassCameraHexapod
        bypassM2Hexapod = id_data.data.bypassM2Hexapod

        if not bypassCameraHexapod:
            data = self.mtcamerahexapod.cmd_positionSet.DataType()
            data.x, data.y, data.z, data.u, data.v, data.w = \
                self.cameraHexapodAlignment.getCorrection()
            data.sync = True
            await self.mtcamerahexapod.cmd_positionSet.start(data, timeout=1.0)

        if not bypassM2Hexapod:
            data = self.mtm2hexapod.cmd_positionSet.DataType()
            data.x, data.y, data.z, data.u, data.v, data.w = \
                self.m2HexapodAlignment.getCorrection()
            data.sync = True
            await self.mtm2hexapod.cmd_positionSet.start(data, timeout=1.0)

    def do_resetWavefrontCorrection(self, id_data):
        """Commands the MTAOS to reset the current wavefront error
        calculations.

        When resetting the wavefront corrections it is recommended that the
        issueWavefrontCorrection command be sent to push the cleared wavefront
        corrections to the AOS subsystems.
        """

        timestamp = time.time()

        self.cameraHexapodCorrection, self.m2HexapodCorrection, self.m1m3Correction, self.m2Correction = \
            self.ofc.resetOfcState()
        self.aggregatedDoF = self.ofc.getStateAggregated()
        self.visitDoF = self.ofc.getStateCorrectionFromLastVisit()

        self.logEvent_degreeOfFreedom(timestamp)
        self.logEvent_cameraHexapodCorrection(timestamp)
        self.logEvent_m1m3Correction(timestamp)
        self.logEvent_m2Correction(timestamp)
        self.logEvent_m2HexapodCorrection(timestamp)

    async def do_issueWavefrontCorrection(self, id_data):
        """Commands the MTAOS to issue wavefront corrections to the Camera
        Hexapod, M1M3, M2, and M2 Hexapod using the most recently measured
        wavefront error.

        Parameters
        ----------
        id_data.data.bypassCameraHexapod : bool
            If True the MTAOS will not issue the offset command to the Camera
            Hexapod.
        id_data.data.bypassM1M3 : bool
            If True the MTAOS will not issue the applyActiveOpticForces
            command to the M1M3.
        id_data.data.bypassM2 : bool
            If True the MTAOS will not issue the applyForce command to the M2.
        id_data.data.bypassM2Hexapod : bool
            If True the MTAOS will not issue the offset command to the M2
            Hexapod.
        """

        bypassCameraHexapod = id_data.data.bypassCameraHexapod
        bypassM1M3 = id_data.data.bypassM1M3
        bypassM2 = id_data.data.bypassM2
        bypassM2Hexapod = id_data.data.bypassM2Hexapod

        if not bypassCameraHexapod:
            data = self.mtcamerahexapod.cmd_offset.DataType()
            data.x, data.y, data.z, data.u, data.v, data.w = \
                self.cameraHexapodCorrection.getCorrection()
            data.sync = True
            await self.mtcamerahexapod.cmd_offset.start(data, timeout=1.0)

        if not bypassM1M3:
            data = self.mtm1m3.cmd_applyActiveOpticForces.DataType()
            zForces = self.m1m3Correction.getZForces()
            for i in range(156):
                data.zForces[i] = zForces[i]
            await self.mtm1m3.cmd_applyActiveOpticForces.start(data, timeout=1.0)

        if not bypassM2:
            data = self.mtm2.cmd_applyForce.DataType()
            zForces = self.m2Correction.getZForces()
            for i in range(72):
                data.forceSetPoint[i] = zForces[i]
            await self.mtm2.cmd_applyForce.start(data, timeout=1.0)

        if not bypassM2Hexapod:
            data = self.mtm2hexapod.cmd_offset.DataType()
            data.x, data.y, data.z, data.u, data.v, data.w = \
                self.m2HexapodCorrection.getCorrection()
            data.sync = True
            await self.mtm2hexapod.cmd_offset.start(data, timeout=1.0)

    def do_processCalibrationProducts(self, id_data):
        """Commands the MTAOS to process new calibration products.

        Parameters
        ----------
        id_data.data.directoryPath : str
            The local directory containing the calibration products.
        """

        imgDirectoryPath = id_data.data.directoryPath

        self.wep.ingestCalibs(imgDirectoryPath)

    def do_processWavefrontError(self, id_data):
        """Commands the MTAOS to process an intra/extra wavefront
        data collection.

        Parameters
        ----------
        id_data.data.directoryPath : str
            The local directory containing the image products.
        id_data.data.fieldRA : float
            The RA of the center of the imaging sensor.
        id_data.data.fieldDEC : float
            The DEC of the center of the imaging sensor.
        id_data.data.filter : int
            The filter used while collecting the images.
        id_data.data.cameraRotation : float
            The camera rotation used while collecting the images.
        id_data.data.userGain : float
            The user gain to apply to the images. Providing a -1 means the OFC
            will use the PSSN to determine the gain.
        """

        # imgDirectoryPath = id_data.data.directoryPath
        # imgRa = id_data.data.fieldRA
        # imgDec = id_data.data.fieldDEC
        # imgFilter = FilterType(id_data.data.filter)
        # imgCameraRotation = id_data.data.cameraRotation
        # imgUserGain = id_data.data.userGain
        pass

    def do_processIntraExtraWavefrontError(self, id_data):
        """Commands the MTAOS to process an intra/extra wavefront
        data collection.

        Parameters
        ----------
        id_data.data.intraVisit : int
            Intra-focal image visit number.
        id_data.data.extraVisit : int
            Extra-focal image visit number.
        id_data.data.intraDirectoryPath : str
            The local directory containing the intra-focal image products.
        id_data.data.extraDirectoryPath : str
            The local directory containing the extra-focal image products.
        id_data.data.fieldRA : float
            The RA of the center of the imaging sensor.
        id_data.data.fieldDEC : float
            The DEC of the center of the imaging sensor.
        id_data.data.filter : int
            The filter used while collecting the images.
        id_data.data.cameraRotation : float
            The camera rotation used while collecting the images.
        id_data.data.userGain : float
            The user gain to apply to the images. Providing a -1 means the OFC
            will use the PSSN to determine the gain.
        """

        timestamp = time.time()
        try:
            wavefrontDataValid = self.runWEP(
                timestamp=timestamp,
                fieldRA=id_data.data.fieldRA,
                fieldDEC=id_data.data.fieldDEC,
                fieldFilter=FilterType(id_data.data.filter),
                cameraRotation=id_data.data.cameraRotation,
                primaryVisit=id_data.data.intraVisit,
                primaryDirectory=id_data.data.intraDirectoryPath,
                secondaryVisit=id_data.data.extraVisit,
                secondaryDirectory=id_data.data.extraDirectoryPath)

            if wavefrontDataValid:
                self.runOFC(
                    timestamp=timestamp,
                    fieldFilter=FilterType(id_data.data.filter),
                    cameraRotation=id_data.data.cameraRotation,
                    userGain=id_data.data.userGain,
                    listOfFWHMSensorData=[])
        except Exception as e:
            print(e)
            traceback.print_exc()

    def do_processShWavefrontError(self, id_data):
        """Commands the MTAOS to process an intra/extra wavefront
        data collection.

        Parameters
        ----------
        id_data.data.fileName : str
            The local file containing the wavefront data.
        id_data.data.fieldRA : float
            The RA of the center of the imaging sensor.
        id_data.data.fieldDEC : float
            The DEC of the center of the imaging sensor.
        id_data.data.filter : int
            The filter used while collecting the images.
        id_data.data.cameraRotation : float
            The camera rotation used while collecting the images.
        id_data.data.userGain : float
            The user gain to apply to the images. Providing a -1 means the OFC
            will use the PSSN to determine the gain.
        """

        # imgFilePath = id_data.data.fileName
        # imgRa = id_data.data.fieldRA
        # imgDec = id_data.data.fieldDEC
        # imgFilter = FilterType(id_data.data.filter)
        # imgCameraRotation = id_data.data.cameraRotation
        # imgUserGain = id_data.data.userGain
        pass

    def runWEP(self, timestamp, fieldRA, fieldDEC, fieldFilter,
               cameraRotation, primaryVisit, primaryDirectory,
               secondaryVisit=None, secondaryDirectory=None):
        """Run the wavefront estimation pipeline (WEP) to estimate the
        wavefront error.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        fieldRA : float
            The RA of the center of the imaging sensor.
        fieldDEC : float
            The DEC of the center of the imaging sensor.
        fieldFilter : lsst.ts.wep.Utility.FilterType
            The filter used by the imaging sensor.
        cameraRotation : float
            The rotation of the imaging sensor.
        primaryVisit: int
            The primary visit number (intra-focal visit number).
        primaryDirectory : str
            The primary directory of image data (intra-focal images).
        secondaryVisit: int (optional)
            The secondary visit number (extra-focal visit number).
        secondaryDirectory : str (optional)
            The secondary directory of image data (extra-focal images).
        Returns
        -------
        bool
            True if the WEP calculation completed successfully.
        """

        startTime = time.time()

        # Not sure what this is for it isn't used for
        # WEP unit tests don't seem to call it
        # wcsData = WcsData(np.zeros(1))
        # self.wep.setWcsData(wcsData)

        # R22_S11
        # R22_S10

        intraExposureData, extraExposureData = self._collectRawExpData(
            primaryVisit, primaryDirectory, secondaryVisit=secondaryVisit,
            secondaryDirectory=secondaryDirectory)

        wavefrontData = self._calcWavefrontError(
            fieldRA, fieldDEC, fieldFilter, cameraRotation, intraExposureData,
            extraRawExpData=extraExposureData)

        wavefrontDataValid, wavefrontError = \
            self.convertWavefrontDataToWavefrontError(timestamp, wavefrontData)

        if wavefrontDataValid:
            self.wavefrontError = wavefrontError
            self.logEvent_wavefrontError(timestamp)
        else:
            self.logEvent_rejectedWavefrontError(timestamp, wavefrontData)

        stopTime = time.time()
        self.putSample_wepDuration(timestamp, (stopTime - startTime))

        return wavefrontDataValid

    def _collectRawExpData(self, primaryVisit, primaryDirectory,
                           secondaryVisit=None, secondaryDirectory=None):
        """Collect the raw exposure data.

        Parameters
        ----------
        primaryVisit: int
            The primary visit number (intra-focal visit number).
        primaryDirectory : str
            The primary directory of image data (intra-focal images).
        secondaryVisit: int (optional)
            The secondary visit number (extra-focal visit number).
        secondaryDirectory : str (optional)
            The secondary directory of image data (extra-focal images).

        Returns
        -------
        lsst.ts.wep.ctrlIntf.RawExpData
            Raw exposure data for the corner wavefront sensor. If the input of
            extraRawExpData is not None, this input will be the intra-focal raw
            exposure data.
        lsst.ts.wep.ctrlIntf.RawExpData
            This is the extra-focal raw exposure data if not None.
        """

        intraExposureData = RawExpData()
        intraExposureData.append(primaryVisit, 0, primaryDirectory)

        if (secondaryVisit is None) or (secondaryDirectory is None):
            extraExposureData = None
        else:
            extraExposureData = RawExpData()
            extraExposureData.append(secondaryVisit, 0, secondaryDirectory)

        return intraExposureData, extraExposureData

    def _calcWavefrontError(self, fieldRA, fieldDEC, fieldFilter,
                            cameraRotation, rawExpData, extraRawExpData=None):
        """Calculate the wavefront error.

        Parameters
        ----------
        fieldRA : float
            The RA of the center of the imaging sensor.
        fieldDEC : float
            The DEC of the center of the imaging sensor.
        fieldFilter : lsst.ts.wep.Utility.FilterType
            The filter used by the imaging sensor.
        cameraRotation : float
            The rotation of the imaging sensor.
        rawExpData : lsst.ts.wep.ctrlIntf.RawExpData
            Raw exposure data for the corner wavefront sensor. If the input of
            extraRawExpData is not None, this input will be the intra-focal raw
            exposure data.
        extraRawExpData : lsst.ts.wep.ctrlIntf.RawExpData, optional
            This is the extra-focal raw exposure data if not None. (the default
            is None.)

        Returns
        -------
        list [lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of SensorWavefrontData object.
        """

        # Set the default sky file for the test
        # This will be removed in the final
        self._setSkyFile()

        self.wep.setBoresight(fieldRA, fieldDEC)
        self.wep.setFilter(fieldFilter)
        self.wep.setRotAng(cameraRotation)

        wavefrontData = self.wep.calculateWavefrontErrors(
            rawExpData, extraRawExpData=extraRawExpData)

        return wavefrontData

    def _setSkyFile(self):
        """Set the sky file for the test.

        This function will be removed in the final.
        """

        skyFile = self.getDefaultSkyFile()
        if (skyFile is not None):
            self.wep.setSkyFile(skyFile)

    def convertWavefrontDataToWavefrontError(self, timestamp, wavefrontData):
        """Convert wavefront data from WEP to wavefront error for OFC.

        Parameters
        ----------
        wavefrontData : lsst.ts.wep.ctrlIntf.SensorWavefrontData
            The wavefront data from WEP.

        Returns
        -------
        bool
            True if the wavefront data is valid or the check is being bypassed.
        lsst.ts.ofc.ctrlIntf.SensorWavefrontError
            The wavefront error determined by WEP.
        """

        valid = True
        wavefrontError = []
        for data in wavefrontData:

            sensorId = data.getSensorId()
            if sensorId < 0:
                valid = False
                print(f"Invalid sensor Id {sensorId}. Must be >= 0.")
                self.logEvent_wepWarning(timestamp, WEPWarning.InvalidSensorId)
                sensorId = 0

            annularZernikePoly = data.getAnnularZernikePoly()
            numOfZk = self.getNumOfZk()
            if len(annularZernikePoly) != numOfZk:
                valid = False
                print(f"Invalid annular zernike polynomial length {len(annularZernikePoly)}. "
                      "Must be {numOfZk}.")
                self.logEvent_wepWarning(
                    timestamp, WEPWarning.InvalidAnnularZernikePoly)
                annularZernikePoly = [0.0] * 19

            wavefrontError.append(SensorWavefrontError(
                sensorId, annularZernikePoly))
        return (valid or self.bypassWavefrontErrorCheck), wavefrontError

    def runOFC(self, timestamp, fieldFilter, cameraRotation, userGain,
               listOfFWHMSensorData):
        """Run the optical feedback control (OFC) to estimate the hexapod
        position and mirror bending mode.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        fieldFilter : lsst.ts.wep.Utility.FilterType
            The filter used by the imaging sensor.
        cameraRotation : float
            The rotation of the imaging sensor.
        userGain : float
            The gain requested by the user. A value of -1 means don't use user
            gain.
        listOfFWHMSensorData : ???
            Unknown at this time.

        Returns
        -------
        bool
            True if the OFC calculation was successful.
        """

        startTime = time.time()

        m2HexapodCorrection, cameraHexapodCorrection, m1m3Correction, m2Correction = \
            self._calcCorrection(fieldFilter, cameraRotation, userGain,
                                 listOfFWHMSensorData)
        aggregatedDoF = self.ofc.getStateAggregated()
        visitDoF = self.ofc.getStateCorrectionFromLastVisit()

        correctionsValid = True

        if correctionsValid:
            self.aggregatedDoF = aggregatedDoF
            self.visitDoF = visitDoF
            self.cameraHexapodCorrection = cameraHexapodCorrection
            self.m2HexapodCorrection = m2HexapodCorrection
            self.m1m3Correction = m1m3Correction
            self.m2Correction = m2Correction

            self.logEvent_degreeOfFreedom(timestamp)
            self.logEvent_cameraHexapodCorrection(timestamp)
            self.logEvent_m1m3Correction(timestamp)
            self.logEvent_m2Correction(timestamp)
            self.logEvent_m2HexapodCorrection(timestamp)
        else:
            self.logEvent_rejectedDegreeOfFreedom(
                timestamp, aggregatedDoF, visitDoF)
            self.logEvent_rejectedCameraHexapodCorrection(
                timestamp, cameraHexapodCorrection)
            self.logEvent_rejectedM2HexapodCorrection(
                timestamp, m2HexapodCorrection)
            self.logEvent_rejectedM1M3Correction(timestamp, m1m3Correction)
            self.logEvent_rejectedM2Correction(timestamp, m2Correction)

        stopTime = time.time()
        self.putSample_ofcDuration(timestamp, (stopTime - startTime))

        return correctionsValid

    def _calcCorrection(self, fieldFilter, cameraRotation, userGain,
                        listOfFWHMSensorData):
        """Calculation the correction of subsystems.

        Parameters
        ----------
        fieldFilter : lsst.ts.wep.Utility.FilterType
            The filter used by the imaging sensor.
        cameraRotation : float
            The rotation of the imaging sensor.
        userGain : float
            The gain requested by the user. A value of -1 means don't use user
            gain.
        listOfFWHMSensorData : ???
            Unknown at this time.

        Returns
        -------
        lsst.ts.ofc.ctrlIntf.M2HexapodCorrection
            The position offset for the MT M2 Hexapod.
        lsst.ts.ofc.ctrlIntf.CameraHexapodCorrection
            The position offset for the MT Hexapod.
        lsst.ts.ofc.ctrlIntf.M1M3Correction
            The figure offset for the MT M1M3.
        lsst.ts.ofc.ctrlIntf.M2Correction
            The figure offset for the MT M2.
        """

        self.ofc.setFilter(fieldFilter)
        self.ofc.setRotAng(cameraRotation)
        if (userGain == -1):
            self.ofc.setGainByPSSN()
            self.ofc.setFWHMSensorDataOfCam(listOfFWHMSensorData)
        else:
            self.ofc.setGainByUser(userGain)

        return self.ofc.calculateCorrections(self.wavefrontError)

    def logEvent_cameraHexapodCorrection(self, timestamp):
        """Publishes the Camera Hexapod correction that would be commanded if
        the issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        x, y, z, u, v, w = self.cameraHexapodCorrection.getCorrection()
        self.evt_cameraHexapodCorrection.set_put(
            timestamp=timestamp, x=x, y=y, z=z, u=u, v=v, w=w)

    def logEvent_rejectedCameraHexapodCorrection(
            self, timestamp, rejectedCameraHexapodCorrection):
        """Publishes the rejected Camera Hexapod correction that would be
        commanded if the issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        rejectedCameraHexapodCorrection :
            lsst.ts.ofc.ctrlIntf.CameraHexapodCorrection
            The rejected correction.
        """

        x, y, z, u, v, w = rejectedCameraHexapodCorrection.getCorrection()
        self.evt_rejectedCameraHexapodCorrection.set_put(
            timestamp=timestamp, x=x, y=y, z=z, u=u, v=v, w=w)

    def logEvent_degreeOfFreedom(self, timestamp):
        """Publishes the degree of freedom arrays generated by the OFC
        calculation.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self.evt_degreeOfFreedom.set_put(
            timestamp=timestamp,
            aggregatedDoF=np.array(self.aggregatedDoF),
            visitDoF=np.array(self.visitDoF))

    def logEvent_rejectedDegreeOfFreedom(
            self, timestamp, rejectedAggregatedDoF, rejectedVisitDoF):
        """Publishes the rejected degree of freedom arrays generated by the OFC
        calculation.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        rejectedAggregatedDoF : float[50]
            The rejected aggregated degree of freedom.
        rejectedVisitDoF : float[50]
            The rejected visit degree of freedom.
        """

        self.evt_rejectedDegreeOfFreedom.set_put(
            timestamp=timestamp,
            aggregatedDoF=np.array(rejectedAggregatedDoF),
            visitDoF=np.array(rejectedVisitDoF))

    def logEvent_m1m3Correction(self, timestamp):
        """Publishes the M1M3 correction that would be commanded if the
        issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        zForces = self.m1m3Correction.getZForces()
        self.evt_m1m3Correction.set_put(
            timestamp=timestamp, zForces=np.array(zForces))

    def logEvent_rejectedM1M3Correction(self, timestamp, rejectedM1M3Correction):
        """Publishes the rejected M1M3 correction that would be commanded if
        the issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        rejectedM1M3Correction : lsst.ts.ofc.ctrlIntf.M1M3Correction
            The rejected correction.
        """

        zForces = rejectedM1M3Correction.getZForces()
        self.evt_rejectedM1M3Correction.set_put(
            timestamp=timestamp, zForces=np.array(zForces))

    def logEvent_m2Correction(self, timestamp):
        """Publishes the M2 correction that would be commanded if the
        issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        zForces = self.m2Correction.getZForces()
        self.evt_m2Correction.set_put(
            timestamp=timestamp, zForces=np.array(zForces))

    def logEvent_rejectedM2Correction(self, timestamp, rejectedM2Correction):
        """Publishes the rejected M2 correction that would be commanded if the
        issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        rejectedM2Correction : lsst.ts.ofc.ctrlIntf.M2Correction
            The rejected correction.
        """

        zForces = rejectedM2Correction.getZForces()
        self.evt_rejectedM2Correction.set_put(
            timestamp=timestamp, zForces=np.array(zForces))

    def logEvent_m2HexapodCorrection(self, timestamp):
        """Publishes the M2 Hexapod correction that would be commanded if the
        issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        x, y, z, u, v, w = self.m2HexapodCorrection.getCorrection()
        self.evt_m2HexapodCorrection.set_put(
            timestamp=timestamp, x=x, y=y, z=z, u=u, v=v, w=w)

    def logEvent_rejectedM2HexapodCorrection(
            self, timestamp, rejectedM2HexapodCorrection):
        """Publishes the rejected M2 Hexapod correction that would be
        commanded if the issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        rejectedM2HexapodCorrection : lsst.ts.ofc.ctrlIntf.M2HexapodCorrection
            The rejected correction.
        """

        x, y, z, u, v, w = rejectedM2HexapodCorrection.getCorrection()
        self.evt_rejectedM2HexapodCorrection.set_put(
            timestamp=timestamp, x=x, y=y, z=z, u=u, v=v, w=w)

    def logEvent_ofcWarning(self, timestamp, warning):
        """Publishes a warning generated during the OFC calculations.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        warning : OFCWarning
            The warning encountered.
        """

        self.evt_ofcWarning.set_put(timestamp=timestamp, warning=warning.value)

    def logEvent_wavefrontError(self, timestamp):
        """Publishes the calculated wavefront error calculated by WEP.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        for wavefrontError in self.wavefrontError:
            sensorId = wavefrontError.getSensorId()
            annularZernikePoly = wavefrontError.getAnnularZernikePoly()
            self.evt_wavefrontError.set_put(
                timestamp=timestamp,
                sensorId=sensorId,
                annularZernikePoly=np.array(annularZernikePoly))

    def logEvent_rejectedWavefrontError(self, timestamp, rejectedWavefrontError):
        """Publishes the rejected calculated wavefront error calculated by WEP.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        rejectedWavefrontError : lsst.ts.wep.ctrlIntf.SensorWavefrontData
            The rejected wavefront error.
        """

        for wavefrontError in rejectedWavefrontError:
            sensorId = wavefrontError.getSensorId()
            annularZernikePoly = wavefrontError.getAnnularZernikePoly()
            self.evt_rejectedWavefrontError.set_put(
                timestamp=timestamp,
                sensorId=sensorId,
                annularZernikePoly=np.array(annularZernikePoly))

    def logEvent_wepWarning(self, timestamp, warning):
        """Publishes a warning generated during the WEP calculations.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        warning : WEPWarning
            The warning encountered.
        """
        self.evt_wepWarning.set_put(timestamp=timestamp, warning=warning.value)

    def putSample_ofcDuration(self, timestamp, duration):
        """Publishes the duration of the OFC calculation.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        duration : float
            The duration in seconds of the calculation.
        """

        self.tel_ofcDuration.set_put(timestamp=timestamp, duration=duration)

    def putSample_wepDuration(self, timestamp, duration):
        """Publishes the duration of the WEP calculation.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        duration : float
            The duration in seconds of the calculation.
        """

        self.tel_wepDuration.set_put(timestamp=timestamp, duration=duration)


if __name__ == "__main__":
    pass
