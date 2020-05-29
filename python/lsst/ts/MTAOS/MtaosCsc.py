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

__all__ = ["MtaosCsc"]

import inspect
import asyncio
import concurrent
import logging
import sys
import yaml

from lsst.ts import salobj

from .Config import Config
from .Model import Model
from .ModelSim import ModelSim
from . import Utility


class MtaosCsc(salobj.ConfigurableCsc):

    DEFAULT_TIMEOUT = 10.0
    LOG_FILE_NAME = "MTAOS.log"

    def __init__(
        self, config_dir=None, log_to_file=False, debug_level=None, simulation_mode=0
    ):
        """Initialize the MTAOS CSC class.

        MTAOS: Main telescope active optical system.
        CSC: Commandable SAL component.
        SAL: Service abstraction layer.

        Parameters
        ----------
        config_dir : str or None, optional
            Directory of configuration files, or None for the standard
            configuration directory (obtained from get_default_config_dir()).
            This is provided for unit testing. (the default is None.)
        log_to_file : bool, optional
            Output the log to files. The files will be in logs directory. (the
            default is False.)
        debug_level : int or str, optional
            Logging level of file handler. It can be "DEBUG" (10), "INFO" (20),
            "WARNING" (30), "ERROR" (40), or "CRITICAL" (50). (the default is
            None.)
        simulation_mode : int, optional
            Simulation mode. (the default is 0: do not simulate.)
        """

        cscName = Utility.getCscName()
        index = 0
        schemaPath = Utility.getSchemaDir().joinpath("MTAOS.yaml")
        super().__init__(
            cscName,
            index,
            schemaPath,
            config_dir=config_dir,
            initial_state=salobj.State.STANDBY,
            simulation_mode=int(simulation_mode),
        )

        # Logger attribute comes from the upstream Controller class
        if debug_level is None:
            debug_level = logging.DEBUG
        self.log = self._addLogWithFileHandlerIfDebug(
            debug_level, outputLogFile=log_to_file
        )
        self.log.info("Prepare MTAOS CSC.")

        schema = yaml.safe_load(
            Utility.getSchemaDir().joinpath("telescopedof.yaml").open().read()
        )
        self.state0DofValidator = salobj.DefaultingValidator(schema=schema)

        # CSC of M2 hexapod
        self._cscM2Hex = salobj.Remote(self.domain, "Hexapod", index=2)

        # CSC of camera hexapod
        self._cscCamHex = salobj.Remote(self.domain, "Hexapod", index=1)

        # CSC of M1M3
        self._cscM1M3 = salobj.Remote(self.domain, "MTM1M3")

        # CSC of M2
        self._cscM2 = salobj.Remote(self.domain, "MTM2")

        # Model class to do the real data processing
        self.model = None

        self.log.info("MTAOS CSC is ready.")

    def _addLogWithFileHandlerIfDebug(self, debugLevel, outputLogFile=False):
        """Add the internal logger with file handler if doing the debug.

        Note: This logger attribute comes from the upstream Controller class.

        Parameters
        ----------
        debugLevel : int or str
            Logging level of file handler.
        outputLogFile : bool, optional
            Output the log file or not. (the default is False.)

        Returns
        -------
        logging.Logger
            Logger object.
        """

        if outputLogFile:
            fileDir = Utility.getLogDir()
            filePath = fileDir.joinpath(self.LOG_FILE_NAME)
            Utility.addRotFileHandler(self.log, filePath, debugLevel)
        else:
            logging.basicConfig(stream=sys.stdout, level=debugLevel)

        return self.log

    async def configure(self, config):

        self._logExecFunc()
        self.log.info("Begin to configure MTAOS CSC.")

        configObj = Config(config)
        state0DofFile = configObj.getState0DofFile()
        if state0DofFile is None:
            state0Dof = None
        else:
            state0Dof = self.state0DofValidator.validate(
                yaml.safe_load(open(state0DofFile).read())
            )

        if self._isNormalMode():
            self.model = Model(configObj, state0Dof)
            self.log.info("Configure MTAOS CSC in the normal operation mode.")
        else:
            self.model = ModelSim(configObj, state0Dof)
            self.log.info("Configure MTAOS CSC in the simulation mode.")

    def _logExecFunc(self):
        """Log the executed function."""

        funcName = inspect.stack()[1].function
        self.log.info(f"Execute {funcName}().")

    def _isNormalMode(self):
        """Is the normal operation mode or not.

        Returns
        -------
        bool
            True if normal operation. False if simulation.
        """

        # Simulation_mode comes from the upstream property function of BaseCsc
        # class.
        return self.simulation_mode == 0

    @staticmethod
    def get_config_pkg():

        return "ts_config_mttcs"

    async def start(self):

        self._logExecFunc()

        await asyncio.gather(
            self._cscM2Hex.start_task,
            self._cscCamHex.start_task,
            self._cscM1M3.start_task,
            self._cscM2.start_task,
        )
        await super().start()

    async def implement_simulation_mode(self, simulation_mode):

        self._logExecFunc()

        if simulation_mode not in (0, 1):
            raise salobj.ExpectedError(
                f"Simulation_mode={simulation_mode} must be 0 or 1"
            )

    def getModel(self):
        """Get the model.

        Returns
        -------
        Model or ModelSim
            Model object.
        """

        return self.model

    async def do_resetWavefrontCorrection(self, data):
        """Command to reset the current wavefront error calculations.

        When resetting the wavefront corrections it is recommended that the
        issueWavefrontCorrection command be sent to push the cleared wavefront
        corrections to the AOS (active optical system) subsystems.
        """

        self._logExecFunc()
        self._checkEnabledState()

        try:
            timestamp = self._getTimestamp()
            self.model.resetWavefrontCorrection()

            self.pubEvent_degreeOfFreedom(timestamp)

            self.pubEvent_m2HexapodCorrection(timestamp)
            self.pubEvent_cameraHexapodCorrection(timestamp)
            self.pubEvent_m1m3Correction(timestamp)
            self.pubEvent_m2Correction(timestamp)

        except Exception:
            self.log.exception("Failed to reset wavefront correction.")

    def _checkEnabledState(self):
        """Check the system is in the Enabled state."""

        funcName = inspect.stack()[1].function
        action = funcName + "()"
        try:
            super().assert_enabled(action)
        except Exception:
            self.log.exception("Not the Enabled state.")
            raise

    def _getTimestamp(self):
        """Get the timestamp.

        Returns
        -------
        float
            Timestamp.
        """

        return salobj.current_tai()

    async def do_issueWavefrontCorrection(self, data):
        """Command to issue the wavefront corrections to the M2 hexapod, camera
        hexapod, M1M3, and M2 using the most recently measured wavefront error.

        Parameters
        ----------
        data : object
            Data to put in the DDS (data distribution service) topic.
        """

        self._logExecFunc()
        self._checkEnabledState()

        timestamp = self._getTimestamp()

        try:
            self.model.calcCorrectionFromAvgWfErr()
            self.log.info("Calculate the subsystem correction successfully.")

            self.pubEvent_ofcWarning(timestamp, Utility.OFCWarning.NoWarning)
            self.pubEvent_degreeOfFreedom(timestamp)
            self.pubEvent_m2HexapodCorrection(timestamp)
            self.pubEvent_cameraHexapodCorrection(timestamp)
            self.pubEvent_m1m3Correction(timestamp)
            self.pubEvent_m2Correction(timestamp)

            self.pubTel_ofcDuration(timestamp)

        except Exception:
            self.log.exception("Failed to calculate the subsystem correction.")

        sync = True

        try:
            await self._issueCorrM2Hex(timestamp, sync)
            await self._issueCorrCamHex(timestamp, sync)
            await self._issueCorrM1M3(timestamp)
            await self._issueCorrM2(timestamp)

        except (salobj.AckError, salobj.AckTimeoutError):
            self.pubEvent_rejectedDegreeOfFreedom(timestamp)
            self.model.rejCorrection()

        except Exception:
            self.log.exception("Failed to issue the wavefront correction.")

    async def _issueCorrM2Hex(self, timestamp, sync):
        """Issue the correction of M2 hexapod.

        Parameters
        ----------
        timestamp : float
            Timestamp.
        sync : bool
            True if the actuators do the synchronized move.
        """

        x, y, z, u, v, w = self.model.getM2HexCorr()

        try:
            await self._cscM2Hex.cmd_move.set_start(
                timeout=self.DEFAULT_TIMEOUT, x=x, y=y, z=z, u=u, v=v, w=w, sync=sync
            )

            self.log.info("Issue the M2 hexapod correction successfully.")

        except (salobj.AckError, salobj.AckTimeoutError):
            self.log.warning("M2 hexapod failed the correction command.")
            self.pubEvent_rejectedM2HexapodCorrection(timestamp)
            raise

    async def _issueCorrCamHex(self, timestamp, sync):
        """Issue the correction of camera hexapod.

        Parameters
        ----------
        timestamp : float
            Timestamp.
        sync : bool
            True if the actuators do the synchronized move.
        """

        x, y, z, u, v, w = self.model.getCamHexCorr()

        try:
            await self._cscCamHex.cmd_move.set_start(
                timeout=self.DEFAULT_TIMEOUT, x=x, y=y, z=z, u=u, v=v, w=w, sync=sync
            )

            self.log.info("Issue the camera hexapod correction successfully.")

        except (salobj.AckError, salobj.AckTimeoutError):
            self.log.warning("Camera hexapod failed the correction command.")
            self.pubEvent_rejectedCameraHexapodCorrection(timestamp)
            raise

    async def _issueCorrM1M3(self, timestamp):
        """Issue the correction of M1M3.

        Parameters
        ----------
        timestamp : float
            Timestamp.
        """

        zForces = self.model.getM1M3ActCorr()

        try:
            await self._cscM1M3.cmd_applyActiveOpticForces.set_start(
                timeout=self.DEFAULT_TIMEOUT, zForces=zForces
            )

            self.log.info("Issue the M1M3 correction successfully.")

        except (salobj.AckError, salobj.AckTimeoutError):
            self.log.warning("M1M3 failed the correction command.")
            self.pubEvent_rejectedM1M3Correction(timestamp)
            raise

    async def _issueCorrM2(self, timestamp):
        """Issue the correction of M2.

        Parameters
        ----------
        timestamp : float
            Timestamp.
        """

        zForces = self.model.getM2ActCorr()

        try:
            await self._cscM2.cmd_applyForces.set_start(
                timeout=self.DEFAULT_TIMEOUT, axialForceSetPoints=zForces
            )

            self.log.info("Issue the M2 correction successfully.")

        except (salobj.AckError, salobj.AckTimeoutError):
            self.log.warning("M2 failed the correction command.")
            self.pubEvent_rejectedM2Correction(timestamp)
            raise

    async def do_processCalibrationProducts(self, data):
        """Command to process the new calibration products.

        Parameters
        ----------
        data : object
            Data to put in the DDS (data distribution service) topic.
        """

        self._logExecFunc()
        self._checkEnabledState()

        try:
            calibsDir = data.directoryPath
            await self._runTaskInNewEventLoop(self.model.procCalibProducts, calibsDir)

            self.log.info("Process the calibration products successfully.")

        except Exception:
            self.log.exception("Failed to process the calibration products.")

    async def _runTaskInNewEventLoop(self, func, *args):
        """Run the task in the new event loop.

        Parameters
        ----------
        func : object
            Function to put in the new event loop.
        *args : any
            Arguments needed in function.
        """

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, func, *args)

    async def do_processWavefrontError(self, data):
        """Command to process an intra/extra wavefront data collection by the
        corner wavefront sensor.

        Parameters
        ----------
        data : object
            Data to put in the DDS (data distribution service) topic.

        Raises
        ------
        NotImplementedError
            This function is not supported yet.
        """

        raise NotImplementedError("This function is not supported yet.")

    async def do_processIntraExtraWavefrontError(self, data):
        """Command to process an intra/extra wavefront data collection by the
        camera piston.

        This function is for the ComCam and LSST full-array mode camera.

        Parameters
        ----------
        data : object
            Data to put in the DDS (data distribution service) topic.
        """

        self._logExecFunc()
        self._checkEnabledState()

        try:
            timestamp = self._getTimestamp()

            raInDeg = data.fieldRA
            decInDeg = data.fieldDEC
            aFilter = data.filter
            rotAngInDeg = data.cameraRotation
            priVisit = data.intraVisit
            priDir = data.intraDirectoryPath
            secVisit = data.extraVisit
            secDir = data.extraDirectoryPath
            userGain = data.userGain
            await self._runTaskInNewEventLoop(
                self.model.procIntraExtraWavefrontError,
                raInDeg,
                decInDeg,
                aFilter,
                rotAngInDeg,
                priVisit,
                priDir,
                secVisit,
                secDir,
                userGain,
            )

            self.log.info("Process the intra- and extra-focal images successfully.")

            self.pubEvent_wepWarning(timestamp, Utility.WEPWarning.NoWarning)
            self.pubEvent_wavefrontError(timestamp)
            self.pubEvent_rejectedWavefrontError(timestamp)

            self.pubTel_wepDuration(timestamp)

        except Exception:
            self.log.exception(
                "Failed to process the intra- and extra-focal wavefront data."
            )

    async def do_processShWavefrontError(self, data):
        """Command to process an intra/extra wavefront data collection by the
        Shack–Hartmann wavefront sensor.

        Parameters
        ----------
        data : object
            Data to put in the DDS (data distribution service) topic.

        Raises
        ------
        NotImplementedError
            This function is not supported yet.
        """

        raise NotImplementedError("This function is not supported yet.")

    async def do_processCmosWavefrontError(self, data):
        """Command to process an intra/extra wavefront data collection by the
        high speed CMOS camera.

        CMOS: Complementary metal-oxide semiconductor.

        Parameters
        ----------
        data : object
            Data to put in the DDS (data distribution service) topic.

        Raises
        ------
        NotImplementedError
            This function is not supported yet.
        """

        raise NotImplementedError("This function is not supported yet.")

    def pubEvent_wavefrontError(self, timestamp):
        """Publish the calculated wavefront error calculated by WEP.

        WEP: Wavefront estimation pipeline.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        listOfWfErr = self.model.getListOfWavefrontError()
        for wavefrontError in listOfWfErr:
            sensorId, zk = self._getIdAndZkFromWavefrontErr(wavefrontError)
            self.evt_wavefrontError.set_put(
                timestamp=timestamp,
                sensorId=sensorId,
                annularZernikePoly=zk,
                force_output=True,
            )

    def _getIdAndZkFromWavefrontErr(self, wavefrontError):
        """Get the sensor Id and annular Zernike polynomial from the wavefront
        error data.

        Parameters
        ----------
        wavefrontError : lsst.ts.wep.ctrlIntf.SensorWavefrontData
            Wavefront error data.

        Returns
        -------
        int
            The Id of the sensor this wavefront error is for.
        numpy.ndarray
            The poly describing the wavefront error in um.
        """

        sensorId = wavefrontError.getSensorId()
        annularZernikePoly = wavefrontError.getAnnularZernikePoly()

        return sensorId, annularZernikePoly

    def pubEvent_rejectedWavefrontError(self, timestamp):
        """Publish the rejected calculated wavefront error calculated by WEP.

        WEP: Wavefront estimation pipeline.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        listOfWfErrRej = self.model.getListOfWavefrontErrorRej()
        for wavefrontError in listOfWfErrRej:
            sensorId, zk = self._getIdAndZkFromWavefrontErr(wavefrontError)
            self.evt_rejectedWavefrontError.set_put(
                timestamp=timestamp,
                sensorId=sensorId,
                annularZernikePoly=zk,
                force_output=True,
            )

    def pubEvent_degreeOfFreedom(self, timestamp):
        """Publish the degree of freedom generated by the OFC calculation.

        OFC: Optical feedback control.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        dofAggr = self.model.getDofAggr()
        dofVisit = self.model.getDofVisit()
        self.evt_degreeOfFreedom.set_put(
            timestamp=timestamp,
            aggregatedDoF=dofAggr,
            visitDoF=dofVisit,
            force_output=True,
        )

    def pubEvent_rejectedDegreeOfFreedom(self, timestamp):
        """Publish the rejected degree of freedom generated by the OFC
        calculation.

        OFC: Optical feedback control.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        dofAggr = self.model.getDofAggr()
        dofVisit = self.model.getDofVisit()
        self.evt_rejectedDegreeOfFreedom.set_put(
            timestamp=timestamp,
            aggregatedDoF=dofAggr,
            visitDoF=dofVisit,
            force_output=True,
        )

    def pubEvent_m2HexapodCorrection(self, timestamp):
        """Publish the M2 hexapod correction that would be commanded if the
        issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        x, y, z, u, v, w = self.model.getM2HexCorr()
        self.evt_m2HexapodCorrection.set_put(
            timestamp=timestamp, x=x, y=y, z=z, u=u, v=v, w=w, force_output=True
        )

    def pubEvent_rejectedM2HexapodCorrection(self, timestamp):
        """Publish the rejected M2 hexapod correction that would be commanded
        if the issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        x, y, z, u, v, w = self.model.getM2HexCorr()
        self.evt_rejectedM2HexapodCorrection.set_put(
            timestamp=timestamp, x=x, y=y, z=z, u=u, v=v, w=w, force_output=True
        )

    def pubEvent_cameraHexapodCorrection(self, timestamp):
        """Publish the camera hexapod correction that would be commanded if the
        issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        x, y, z, u, v, w = self.model.getCamHexCorr()
        self.evt_cameraHexapodCorrection.set_put(
            timestamp=timestamp, x=x, y=y, z=z, u=u, v=v, w=w, force_output=True
        )

    def pubEvent_rejectedCameraHexapodCorrection(self, timestamp):
        """Publish the rejected camera hexapod correction that would be
        commanded if the issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        x, y, z, u, v, w = self.model.getCamHexCorr()
        self.evt_rejectedCameraHexapodCorrection.set_put(
            timestamp=timestamp, x=x, y=y, z=z, u=u, v=v, w=w, force_output=True
        )

    def pubEvent_m1m3Correction(self, timestamp):
        """Publish the M1M3 correction that would be commanded if the
        issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        zForces = self.model.getM1M3ActCorr()
        self.evt_m1m3Correction.set_put(
            timestamp=timestamp, zForces=zForces, force_output=True
        )

    def pubEvent_rejectedM1M3Correction(self, timestamp):
        """Publish the rejected M1M3 correction that would be commanded if the
        issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        zForces = self.model.getM1M3ActCorr()
        self.evt_rejectedM1M3Correction.set_put(
            timestamp=timestamp, zForces=zForces, force_output=True
        )

    def pubEvent_m2Correction(self, timestamp):
        """Publish the M2 correction that would be commanded if the
        issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        zForces = self.model.getM2ActCorr()
        self.evt_m2Correction.set_put(
            timestamp=timestamp, zForces=zForces, force_output=True
        )

    def pubEvent_rejectedM2Correction(self, timestamp):
        """Publish the rejected M2 correction that would be commanded if the
        issueWavefrontCorrection command was sent.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        zForces = self.model.getM2ActCorr()
        self.evt_rejectedM2Correction.set_put(
            timestamp=timestamp, zForces=zForces, force_output=True
        )

    def pubEvent_wepWarning(self, timestamp, warning):
        """Publish a warning generated during the WEP calculations.

        WEP: Wavefront estimation pipeline.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        warning : enum 'WEPWarning'
            The warning encountered.
        """

        self._logExecFunc()

        self.evt_wepWarning.set_put(timestamp=timestamp, warning=warning.value)

    def pubEvent_ofcWarning(self, timestamp, warning):
        """Publish a warning generated during the OFC calculations.

        OFC: Optical feedback control.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        warning : enum 'OFCWarning'
            The warning encountered.
        """

        self._logExecFunc()

        self.evt_ofcWarning.set_put(timestamp=timestamp, warning=warning.value)

    def pubTel_wepDuration(self, timestamp):
        """Publish the duration of the WEP calculation as telemetry.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        duration = self.model.getAvgCalcTimeWep()
        self.tel_wepDuration.set_put(timestamp=timestamp, calcTime=duration)

    def pubTel_ofcDuration(self, timestamp):
        """Publish the duration of the OFC calculation as telemetry.

        Parameters
        ----------
        timestamp : float
            The timestamp of the calculation.
        """

        self._logExecFunc()

        duration = self.model.getAvgCalcTimeOfc()
        self.tel_ofcDuration.set_put(timestamp=timestamp, calcTime=duration)

    @classmethod
    def add_arguments(cls, parser):
        super(MtaosCsc, cls).add_arguments(parser)
        parser.add_argument(
            "-s", "--simulate", action="store_true", help="Run in simuation mode?"
        )
        parser.add_argument(
            "--logToFile",
            action="store_true",
            help="""
                            Output the log to files. The files will be in logs
                            directory. The default debug level is "DEBUG".
                            """,
        )
        parser.add_argument(
            "--debugLevel",
            type=int,
            help="""
                            Debug level of log files. It can be "DEBUG" (10),
                            "INFO" (20), "WARNING" (30), "ERROR" (40), or
                            "CRITICAL" (50).
                            """,
        )

    @classmethod
    def add_kwargs_from_args(cls, args, kwargs):
        super(MtaosCsc, cls).add_kwargs_from_args(args, kwargs)
        kwargs["simulation_mode"] = 1 if args.simulate else 0
        kwargs["log_to_file"] = args.logToFile
        kwargs["debug_level"] = args.debugLevel


if __name__ == "__main__":
    pass
