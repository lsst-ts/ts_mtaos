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

from pathlib import Path
import warnings
import numpy as np

from lsst.ts.wep.ParamReader import ParamReader
from lsst.ts.ofc.ctrlIntf.M2HexapodCorrection import M2HexapodCorrection
from lsst.ts.ofc.ctrlIntf.CameraHexapodCorrection import CameraHexapodCorrection
from lsst.ts.ofc.ctrlIntf.M1M3Correction import M1M3Correction
from lsst.ts.ofc.ctrlIntf.M2Correction import M2Correction
from lsst.ts.wep.ctrlIntf.WEPCalculationFactory import WEPCalculationFactory
from lsst.ts.ofc.ctrlIntf.OFCCalculationFactory import OFCCalculationFactory
from lsst.ts.ofc.ctrlIntf.FWHMSensorData import FWHMSensorData
from lsst.ts.wep.ctrlIntf.RawExpData import RawExpData
from lsst.ts.wep.Utility import FilterType

from lsst.ts.MTAOS.Utility import getModulePath, getIsrDirPath, getCamType, \
    getInstName


class Model(object):

    def __init__(self, settingFilePath):
        """Initialize the model class of MTAOS.

        MTAOS: Main telescope active optics system.

        Parameters
        ----------
        settingFilePath : pathlib.PosixPath or str
            Configuration setting file.
        """

        # Configuration setting file
        self.settingFile = ParamReader(filePath=settingFilePath)

        # List of wavefront error
        self.listOfWfErr = []

        # List of FWHM (full width at half maximum) sensor data
        self.listOfFWHMSensorData = []

        # Wavefront estimation pipeline
        camType = self._getCamType()
        isrDir = self._getIsrDir()
        self.wep = WEPCalculationFactory.getCalculator(camType, isrDir)

        # Optical feedback control
        instName = self._getInstName()
        self.ofc = OFCCalculationFactory.getCalculator(instName)

        # M2 hexapod correction
        self.m2HexapodCorrection = M2HexapodCorrection(
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # Camera hexapod correction
        self.cameraHexapodCorrection = CameraHexapodCorrection(
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # M1M3 actuator correction
        self.m1m3Correction = M1M3Correction(np.zeros(
            M1M3Correction.NUM_OF_ACT))

        # M2 actuator correction
        self.m2Correction = M2Correction(np.zeros(
            M2Correction.NUM_OF_ACT))

    def getSettingFilePath(self):
        """Get the setting file path.

        Returns
        -------
        pathlib.PosixPath
            Setting file path.
        """

        return Path(self.settingFile.getFilePath())

    def _getCamType(self):
        """Get the enum of camera type.

        Returns
        -------
        enum 'CamType' in lsst.ts.wep.Utility
            Camera type.
        """

        camera = self.settingFile.getSetting("camera")

        return getCamType(camera)

    def _getIsrDir(self):
        """Get the ISR directory.

        ISR: Instrument signature removal.
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

    def _getInstName(self):
        """Get the enum of instrument name.

        Returns
        -------
        enum 'InstName' in lsst.ts.ofc.Utility
            Instrument name.
        """

        instName = self.settingFile.getSetting("instrument")

        return getInstName(instName)

    def getListOfWavefrontError(self):
        """Get the list of wavefront error.

        Returns
        -------
        list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of wavefront error data.
        """

        return self.listOfWfErr

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

        if (sensorData is None):
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
            if (fwhmSensorData.getSensorId() == sensorId):
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

    def resetWavefrontCorrection(self):
        """Reset the current calculation contains the wavefront error and
        subsystem corrections to be empty.

        This function is needed for the long slew angle of telescope.
        """

        self.listOfWfErr = []
        self.m2HexapodCorrection, self.cameraHexapodCorrection, self.m1m3Correction, self.m2Correction = \
            self.ofc.resetOfcState()

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

    def procIntraExtraWavefrontError(self, raInDeg, decInDeg, aFilter,
                                     rotAngInDeg, priVisit, priDir, secVisit,
                                     secDir, userGain):
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

        filterType = FilterType(aFilter)
        listOfWfErr = self._calcWavefrontError(
            raInDeg, decInDeg, filterType, rotAngInDeg, intraRawExpData,
            extraRawExpData=extraRawExpData)

        # Need to add a step of checking the calculated wavefront error
        # in the future
        self.listOfWfErr = listOfWfErr

        m2HexapodCorrection, cameraHexapodCorrection, m1m3Correction, m2Correction = \
            self._calcCorrection(filterType, rotAngInDeg, userGain)

        # Need to add a step of checking the calculated correction
        # in the future
        self.m2HexapodCorrection = m2HexapodCorrection
        self.cameraHexapodCorrection = cameraHexapodCorrection
        self.m1m3Correction = m1m3Correction
        self.m2Correction = m2Correction

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

    def _calcWavefrontError(self, raInDeg, decInDeg, filterType, rotAngInDeg,
                            rawExpData, extraRawExpData=None):
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

        Returns
        -------
        list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of SensorWavefrontData object.
        """

        # Set the default sky file for the test
        # This will be removed in the final
        self._setSkyFile()

        self.wep.setBoresight(raInDeg, decInDeg)
        self.wep.setFilter(filterType)
        self.wep.setRotAng(rotAngInDeg)

        listOfWfErr = self.wep.calculateWavefrontErrors(
            rawExpData, extraRawExpData=extraRawExpData)

        return listOfWfErr

    def _setSkyFile(self):
        """Set the sky file for the test.

        This function will be removed in the final.
        """

        skyFile = self._getDefaultSkyFile()
        if (skyFile is not None):
            self.wep.setSkyFile(skyFile.as_posix())

    def _getDefaultSkyFile(self):
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

    def _calcCorrection(self, filterType, rotAngInDeg, userGain):
        """Calculate the correction of subsystems.

        Parameters
        ----------
        filterType : enum 'FilterType' in lsst.ts.wep.Utility
            The new filter configuration to use for OFC data processing.
        rotAngInDeg : float
            The camera rotation angle in degree (-90 to 90).
        userGain : float
            The gain requested by the user. A value of -1 means don't use user
            gain.

        Returns
        -------
        lsst.ts.ofc.ctrlIntf.M2HexapodCorrection
            The position offset for the MT M2 hexapod.
        lsst.ts.ofc.ctrlIntf.CameraHexapodCorrection
            The position offset for the MT camera hexapod.
        lsst.ts.ofc.ctrlIntf.M1M3Correction
            The figure offset for the MT M1M3.
        lsst.ts.ofc.ctrlIntf.M2Correction
            The figure offset for the MT M2.

        Raises
        ------
        RuntimeError
            No FWHM sensor data to use.
        """

        self.ofc.setFilter(filterType)
        self.ofc.setRotAng(rotAngInDeg)
        if (userGain == -1):
            if (len(self.listOfFWHMSensorData) == 0):
                raise RuntimeError("No FWHM sensor data to use.")
            else:
                self.ofc.setGainByPSSN()
                self.ofc.setFWHMSensorDataOfCam(self.listOfFWHMSensorData)
        else:
            self.ofc.setGainByUser(userGain)

        return self.ofc.calculateCorrections(self.listOfWfErr)


if __name__ == "__main__":
    pass
