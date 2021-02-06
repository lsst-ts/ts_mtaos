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
import logging
import sys
import yaml

import numpy as np

from lsst.ts import salobj

from .Config import Config
from .Model import Model
from .ModelSim import ModelSim
from . import Utility


class MtaosCsc(salobj.ConfigurableCsc):

    # Class attribute comes from the upstream BaseCsc class
    valid_simulation_modes = [0, 1]

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
        # Use the "include = []" to get rid of all event and telemetry topics
        # to save the resourse
        self.remotes = {
            "m2hex": salobj.Remote(
                self.domain,
                "MTHexapod",
                index=Utility.MTHexapodIndex.M2.value,
                include=[],
            ),
            "camhex": salobj.Remote(
                self.domain,
                "MTHexapod",
                index=Utility.MTHexapodIndex.Camera.value,
                include=[],
            ),
            "m1m3": salobj.Remote(self.domain, "MTM1M3", include=[]),
            "m2": salobj.Remote(self.domain, "MTM2", include=[]),
        }

        self.issue_corrections_func = {
            "m2hex": self.issue_m2hex_correction,
            "camhex": self.issue_camhex_correction,
            "m1m3": self.issue_m1m3_correction,
            "m2": self.issue_m2_correction,
        }

        # Model class to do the real data processing
        self.model = None

        # estimated timeout for issueCorrection command in seconds.
        self.issue_correction_timeout = 60

        # lock to prevent multiple issueCorrection commands to execute at the
        # same time.
        self.issue_correction_lock = asyncio.Lock()

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

        await asyncio.gather(*[self.remotes[rem].start_task for rem in self.remotes])

        await super().start()

    def getModel(self):
        """Get the model.

        Returns
        -------
        Model or ModelSim
            Model object.
        """

        return self.model

    async def do_resetCorrection(self, data):
        """Command to reset the current wavefront error calculations.

        When resetting the wavefront corrections it is recommended that the
        issueWavefrontCorrection command be sent to push the cleared wavefront
        corrections to the AOS (active optical system) subsystems.

        Parameters
        ----------
        data : object
            Data for the command being executed.
        """

        self._logExecFunc()
        self.assert_enabled()

        # If resetting wavefront error fails (e.g. raise an exception) command
        # will be rejected. Events will not be published.
        self.model.resetWavefrontCorrection()

        self.pubEvent_degreeOfFreedom()
        self.pubEvent_m2HexapodCorrection()
        self.pubEvent_cameraHexapodCorrection()
        self.pubEvent_m1m3Correction()
        self.pubEvent_m2Correction()

    async def do_issueCorrection(self, data):
        """Command to issue the wavefront corrections to the M2 hexapod, camera
        hexapod, M1M3, and M2 using the most recently measured wavefront error.

        Parameters
        ----------
        data : object
            Data for the command being executed.
        """

        self._logExecFunc()
        self.assert_enabled()

        # This command may take some time to execute, so will send
        # ack_in_progress with estimated timeout.
        self.cmd_issueCorrection.ack_in_progress(
            data,
            timeout=self.issue_correction_timeout,
            result="issueCorrection started.",
        )

        # We dont want multiple commands to be executed at the same time.
        # This lock will block any subsequent command from being executed until
        # this one is done.
        async with self.issue_correction_lock:

            # This is where the bulk of the work is done. If any correction
            # fail this method will take care of unsetting the ones that
            # succedded and generate a report at the end. Also, if it fails,
            # it raises an exception and the command is rejected.
            await self.handle_corrections()

    async def do_rejectCorrection(self, data):
        """Reject the most recent wavefront correction.
        """

        self._logExecFunc()
        self.assert_enabled()

        self.pubEvent_rejectedDegreeOfFreedom()
        self.model.rejCorrection()

    async def do_selectSources(self, data):
        """Run source selection algorithm for a specific field and visit
        configuration.

        Parameters
        ----------
        data : object
            Data for the command being executed.

        Raises
        ------
        NotImplementedError
            This function is not supported yet.
        """
        self.assert_enabled()

        # TODO: (DM-28708) Finish implementation of selectSources.
        raise NotImplementedError("This function is not supported yet (DM-28708).")

    async def do_preProcess(self, data):
        """Pre-process image for WEP.

        Parameters
        ----------
        data : object
            Data for the command being executed.

        Raises
        ------
        NotImplementedError
            This function is not supported yet.
        """
        self.assert_enabled()

        # TODO: (DM-28708) Finish implementation of preProcess.
        raise NotImplementedError("This function is not supported yet (DM-28708).")

    async def do_runWEP(self, data):
        """Process wavefront data.

        Parameters
        ----------
        data : object
            Data for the command being executed.

        Raises
        ------
        NotImplementedError
            This function is not supported yet.
        """
        self.assert_enabled()

        # TODO: (DM-28710) Initial implementation of runWEP command in MTAOS
        raise NotImplementedError("This function is not supported yet (DM-28710).")

    async def do_runOFC(self, data):
        """Run OFC on the latest wavefront errors data. Before running this
        command, you must have ran runWEP at least once.

        This command will run ofc to compute corrections but won't apply them.
        Use `issueCorrection` to apply the corrections. This allow users to
        evaluate whether the corrections are sensible before applying them.

        Parameters
        ----------
        data : object
            Data for the command being executed.

        """

        self.assert_enabled()

        # This command may take some time to execute, so will send
        # ack_in_progress with estimated timeout.
        self.cmd_issueCorrection.ack_in_progress(
            data, timeout=self.issue_correction_timeout, result="runOFC started.",
        )

        if len(data.config) > 0:
            raise NotImplementedError(
                "User provided configuration overrides not supported yet."
            )

        async with self.issue_correction_lock:

            # If this call fails (raise an exeception), command will be
            # rejected.
            self.model.calcCorrectionFromAvgWfErr()
            self.log.debug("Calculate the subsystem correction successfully.")

            self.pubEvent_degreeOfFreedom()
            self.pubEvent_m2HexapodCorrection()
            self.pubEvent_cameraHexapodCorrection()
            self.pubEvent_m1m3Correction()
            self.pubEvent_m2Correction()
            self.pubEvent_ofcDuration()

    async def do_addAberration(self, data):
        """Utility command to add aberration to the system based on user
        provided wavefront errors. The command assume uniform aberration on all
        sensors.
        """
        self.assert_enabled()

        # TODO: DM-28711
        raise NotImplementedError(
            "Command addAberration not implemented yet (DM-28711)."
        )

    async def handle_corrections(self):
        """Handle applying the corrections to all components.

        If one or more correction fail to apply to method will try to undo the
        successfull corrections. If any of those fails to undo, it will
        continue and generate a report at the end.

        Raises
        ------
        RuntimeError:
            If one or more correction failed.
        """

        # Issue all corrections concurrently. If any of them fails, undo
        # corrections and reject command.
        issue_corrections_tasks = dict(
            [
                (comp, asyncio.create_task(self.issue_corrections_func[comp]()))
                for comp in self.issue_corrections_func
            ]
        )

        # Wait for all corrections to complete
        await asyncio.gather(
            *[task for task in issue_corrections_tasks.values()],
            return_exceptions=True,
        )

        # Check if there was any exception. If so, undo all successfull
        # corrections and reject command.
        if any(
            [task.exception() is not None for task in issue_corrections_tasks.values()]
        ):
            self.pubEvent_rejectedDegreeOfFreedom()
            self.model.rejCorrection()
            # Undo corrections that completed.
            failed_to_do = []
            failed_to_undo = []
            for comp in self.issue_corrections_func:
                if issue_corrections_tasks[comp].exception() is None:
                    self.log.warning(f"Undoing {comp} correction.")
                    try:
                        await self.issue_corrections_func[comp](undo=True)
                    except Exception:
                        self.log.exception(
                            f"Failed to undo successfull correction in {comp}."
                        )
                        failed_to_undo.append(comp)
                else:
                    failed_to_do.append(comp)
            # Need to generate a report about the issue.
            error_report = f"Failed to apply correction to: {failed_to_do}. "
            if len(failed_to_undo) > 0:
                error_report += f"Failed to undo correction to: {failed_to_undo}"
            raise RuntimeError(error_report)

    async def issue_m2hex_correction(self, undo=False):
        """Issue the correction of M2 hexapod.

        Parameters
        ----------
        undo : bool
            If `True` apply the negative value of each correction.

        """

        x, y, z, u, v, w = self.model.getM2HexCorr()

        if undo:
            x, y, z, u, v, w = -x, -y, -z, -u, -v, -w

        try:
            await self.remotes["m2hex"].cmd_move.set_start(
                timeout=self.DEFAULT_TIMEOUT, x=x, y=y, z=z, u=u, v=v, w=w, sync=True
            )

            self.log.debug("Issue the M2 hexapod correction successfully.")

        except Exception as e:
            self.log.exception("M2 hexapod correction command failed.")
            self.pubEvent_rejectedM2HexapodCorrection()
            raise e

    async def issue_camhex_correction(self, undo=False):
        """Issue the correction of camera hexapod.

        Parameters
        ----------
        undo : bool
            If `True` apply the negative value of each correction.

        """

        x, y, z, u, v, w = self.model.getCamHexCorr()

        if undo:
            x, y, z, u, v, w = -x, -y, -z, -u, -v, -w

        try:
            await self.remotes["camhex"].cmd_move.set_start(
                timeout=self.DEFAULT_TIMEOUT, x=x, y=y, z=z, u=u, v=v, w=w, sync=True
            )

            self.log.debug("Issue the camera hexapod correction successfully.")

        except Exception as e:
            self.log.exception("Camera hexapod correction command failed.")
            self.pubEvent_rejectedCameraHexapodCorrection()
            raise e

    async def issue_m1m3_correction(self, undo=False):
        """Issue the correction of M1M3.

        Parameters
        ----------
        undo : bool
            If `True` apply the negative value of each correction.

        """

        z_forces = self.model.getM1M3ActCorr()

        if undo:
            z_forces = np.negative(z_forces)

        try:
            await self.remotes["m1m3"].cmd_applyActiveOpticForces.set_start(
                timeout=self.DEFAULT_TIMEOUT, zForces=z_forces
            )

            self.log.debug("Issue the M1M3 correction successfully.")

        except Exception as e:
            self.log.exception("M1M3 correction command failed.")
            self.pubEvent_rejectedM1M3Correction()
            raise e

    async def issue_m2_correction(self, undo=False):
        """Issue the correction of M2.

        Parameters
        ----------
        undo : bool
            If `True` apply the negative value of each correction.

        """

        z_forces = self.model.getM2ActCorr()

        if undo:
            z_forces = np.negative(z_forces)

        try:
            await self.remotes["m2"].cmd_applyForces.set_start(
                timeout=self.DEFAULT_TIMEOUT, axial=z_forces
            )

            self.log.info("Issue the M2 correction successfully.")

        except Exception as e:
            self.log.exception("M2 correction command failed.")
            self.pubEvent_rejectedM2Correction()
            raise e

    def pubEvent_wavefrontError(self):
        """Publish the calculated wavefront error calculated by WEP.

        WEP: Wavefront estimation pipeline.
        """

        self._logExecFunc()

        listOfWfErr = self.model.getListOfWavefrontError()
        for wavefrontError in listOfWfErr:
            sensorId, zk = self._getIdAndZkFromWavefrontErr(wavefrontError)
            self.evt_wavefrontError.set_put(
                sensorId=sensorId, annularZernikeCoeff=zk, force_output=True,
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

    def pubEvent_rejectedWavefrontError(self):
        """Publish the rejected calculated wavefront error calculated by WEP.

        WEP: Wavefront estimation pipeline.
        """

        self._logExecFunc()

        listOfWfErrRej = self.model.getListOfWavefrontErrorRej()
        for wavefrontError in listOfWfErrRej:
            sensorId, zk = self._getIdAndZkFromWavefrontErr(wavefrontError)
            self.evt_rejectedWavefrontError.set_put(
                sensorId=sensorId, annularZernikeCoeff=zk, force_output=True,
            )

    def pubEvent_degreeOfFreedom(self):
        """Publish the degree of freedom generated by the OFC calculation.

        OFC: Optical feedback control.
        """

        self._logExecFunc()

        dofAggr = self.model.getDofAggr()
        dofVisit = self.model.getDofVisit()
        self.evt_degreeOfFreedom.set_put(
            aggregatedDoF=dofAggr, visitDoF=dofVisit, force_output=True,
        )

    def pubEvent_rejectedDegreeOfFreedom(self):
        """Publish the rejected degree of freedom generated by the OFC
        calculation.

        OFC: Optical feedback control.
        """

        self._logExecFunc()

        dofAggr = self.model.getDofAggr()
        dofVisit = self.model.getDofVisit()
        self.evt_rejectedDegreeOfFreedom.set_put(
            aggregatedDoF=dofAggr, visitDoF=dofVisit, force_output=True,
        )

    def pubEvent_m2HexapodCorrection(self):
        """Publish the M2 hexapod correction that would be commanded if the
        issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        x, y, z, u, v, w = self.model.getM2HexCorr()
        self.evt_m2HexapodCorrection.set_put(
            x=x, y=y, z=z, u=u, v=v, w=w, force_output=True
        )

    def pubEvent_rejectedM2HexapodCorrection(self):
        """Publish the rejected M2 hexapod correction that would be commanded
        if the issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        x, y, z, u, v, w = self.model.getM2HexCorr()
        self.evt_rejectedM2HexapodCorrection.set_put(
            x=x, y=y, z=z, u=u, v=v, w=w, force_output=True
        )

    def pubEvent_cameraHexapodCorrection(self):
        """Publish the camera hexapod correction that would be commanded if the
        issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        x, y, z, u, v, w = self.model.getCamHexCorr()
        self.evt_cameraHexapodCorrection.set_put(
            x=x, y=y, z=z, u=u, v=v, w=w, force_output=True
        )

    def pubEvent_rejectedCameraHexapodCorrection(self):
        """Publish the rejected camera hexapod correction that would be
        commanded if the issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        x, y, z, u, v, w = self.model.getCamHexCorr()
        self.evt_rejectedCameraHexapodCorrection.set_put(
            x=x, y=y, z=z, u=u, v=v, w=w, force_output=True
        )

    def pubEvent_m1m3Correction(self):
        """Publish the M1M3 correction that would be commanded if the
        issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        zForces = self.model.getM1M3ActCorr()
        self.evt_m1m3Correction.set_put(zForces=zForces, force_output=True)

    def pubEvent_rejectedM1M3Correction(self):
        """Publish the rejected M1M3 correction that would be commanded if the
        issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        zForces = self.model.getM1M3ActCorr()
        self.evt_rejectedM1M3Correction.set_put(zForces=zForces, force_output=True)

    def pubEvent_m2Correction(self):
        """Publish the M2 correction that would be commanded if the
        issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        zForces = self.model.getM2ActCorr()
        self.evt_m2Correction.set_put(zForces=zForces, force_output=True)

    def pubEvent_rejectedM2Correction(self):
        """Publish the rejected M2 correction that would be commanded if the
        issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        zForces = self.model.getM2ActCorr()
        self.evt_rejectedM2Correction.set_put(zForces=zForces, force_output=True)

    def pubTel_wepDuration(self):
        """Publish the duration of the WEP calculation as telemetry.
        """

        self._logExecFunc()

        duration = self.model.getAvgCalcTimeWep()
        self.tel_wepDuration.set_put(calcTime=duration)

    def pubTel_ofcDuration(self):
        """Publish the duration of the OFC calculation as telemetry.
        """

        self._logExecFunc()

        duration = self.model.getAvgCalcTimeOfc()
        self.tel_ofcDuration.set_put(calcTime=duration)

    @classmethod
    def add_arguments(cls, parser):
        super(MtaosCsc, cls).add_arguments(parser)
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
        kwargs["log_to_file"] = args.logToFile
        kwargs["debug_level"] = args.debugLevel
