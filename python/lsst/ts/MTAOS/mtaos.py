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

__all__ = ["MTAOS"]

import inspect
import asyncio
import logging
import yaml

from astropy import units as u

import numpy as np

from lsst.ts import salobj
from lsst.ts.idl.enums.MTAOS import FilterType
from lsst.ts.ofc import OFCData

from . import CONFIG_SCHEMA, TELESCOPE_DOF_SCHEMA
from . import Config
from . import Model
from . import utility
from . import __version__


class MTAOS(salobj.ConfigurableCsc):

    # Class attribute comes from the upstream BaseCsc class
    valid_simulation_modes = (0,)
    version = __version__

    DEFAULT_TIMEOUT = 10.0
    LONG_TIMEOUT = 60.0
    LOG_FILE_NAME = "MTAOS.log"
    MAX_TIME_SAMPLE = 100

    def __init__(
        self, config_dir=None, log_to_file=False, log_level=None, simulation_mode=0
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
        log_level : int or str, optional
            Logging level of file handler. It can be "DEBUG" (10), "INFO" (20),
            "WARNING" (30), "ERROR" (40), or "CRITICAL" (50). (the default is
            None.)
        simulation_mode : int, optional
            Simulation mode. (the default is 0: do not simulate.)

        Attributes
        ----------
        log : `logging.Logger`
            A logger.
        state0DofValidator : `salobj.DefaultingValidator`
            Validator for the telescopedof configuration file.
        visit_id_offset: `int`
            Offset applied to visit id. TODO (DM-31365): Remove workaround to
            visitId being of type long in MTAOS runWEP command.
        remotes : `dict`
            A dictionary with `salobj.Remote` for each component the MTAOS
            communicates with.
        issue_correction_to : `set`
            Set with the name of the component in self.remote that also makes
            the name of the method to issue the correction, e.g.,
            `m2hex` -> `issue_m2hex_correction`.
        model : `None` or `lsst.ts.MTAOS.Model`
            MTAOS Model class. This attribute is initialized during
            configuration.
        issue_correction_lock : `asyncio.Lock`
            A lock used to synchronize sending corrections to the components.
        execution_times : `dict`
            Dictionary to store cricital execution times.
        DEFAULT_TIMEOUT : `float`
            Default timeout (in seconds). Used on normal operations, e.g.
            issuing corrections to the CSCs.
        LONG_TIMEOUT : `float`
            Long timeout (in seconds). Used in operations that will take longer
            than normal operations, e.g. running OFC.
        LOG_FILE_NAME : `str`
            Name of the log file.
        MAX_TIME_SAMPLE : `int`
            Maximum samples of execution times to store.
        """

        cscName = utility.getCscName()

        super().__init__(
            cscName,
            index=0,
            config_schema=CONFIG_SCHEMA,
            config_dir=config_dir,
            initial_state=salobj.State.STANDBY,
            simulation_mode=int(simulation_mode),
        )

        # Logger attribute comes from the upstream Controller class
        if log_to_file:
            log_dir = utility.getLogDir()
            log_path = log_dir.joinpath(self.LOG_FILE_NAME)
            utility.addRotFileHandler(
                self.log, log_path, logging.DEBUG if log_level is None else log_level
            )

        self.log.info("Prepare MTAOS CSC.")

        self.state0DofValidator = salobj.DefaultingValidator(
            schema=TELESCOPE_DOF_SCHEMA
        )

        # TODO (DM-31365): Remove workaround to visitId being of type long in
        # MTAOS runWEP command.
        #
        # Offset applied to the visit ids when getting images from butler. This
        # is mainly to work around an issue with xml < 9.2 where the visit id
        # is defined as a a long which allows values from -2147483648 to
        # 2147483647
        self.visit_id_offset = 0

        # Dictionary with remotes for M2 Hexapod, Camera Hexapod, M1M3 and M2
        # components. Note the use of include=[] in all remotes. This prevents
        # the remote from subscribing to events and telemetry from those
        # systems that we do not need, helping to solve resources.
        self.remotes = {
            "m2hex": salobj.Remote(
                self.domain,
                "MTHexapod",
                index=utility.MTHexapodIndex.M2.value,
                include=[],
            ),
            "camhex": salobj.Remote(
                self.domain,
                "MTHexapod",
                index=utility.MTHexapodIndex.Camera.value,
                include=[],
            ),
            "m1m3": salobj.Remote(self.domain, "MTM1M3", include=[]),
            "m2": salobj.Remote(self.domain, "MTM2", include=[]),
        }

        self.execution_times = {}

        # Set with the name of the component in self.remote that also makes the
        # name of the method to issue the correction, e.g.
        # m2hex -> issue_m2hex_correction
        self.issue_correction_to = {
            "m2hex",
            "camhex",
            "m1m3",
            "m2",
        }

        # Model class to do the real data processing
        self.model = None

        # Lock to prevent multiple issueCorrection commands to execute at the
        # same time.
        self.issue_correction_lock = asyncio.Lock()

        self.log.info("MTAOS CSC is ready.")

    async def configure(self, config):

        self._logExecFunc()
        self.log.debug("MTAOS configuration started.")

        # TODO (DM-31365): Remove workaround to visitId being of type long in
        # MTAOS runWEP command.
        self.visit_id_offset = config.visit_id_offset

        config_obj = Config(config)
        state0_dof_file = config_obj.getState0DofFile()
        dof_state0 = None

        if state0_dof_file is not None:
            with open(state0_dof_file) as fp:
                dof_state0 = self.state0DofValidator.validate(yaml.safe_load(fp))

        ofc_config_dir = self.config_dir / "ofc"
        if ofc_config_dir.exists():
            self.log.debug(f"Setting OFC configuration directory to {ofc_config_dir!r}")
        else:
            self.log.debug("Using default OFC configuration directory.")
            ofc_config_dir = None

        ofc_data = OFCData(
            config_dir=ofc_config_dir,
            log=self.log,
        )

        await ofc_data.configure_instrument(config.instrument)

        self.log.debug("ofc data ready. Creating model")

        self.model = Model(
            instrument=config.instrument,
            data_path=config.data_path,
            ofc_data=ofc_data,
            log=self.log,
            run_name=config.run_name,
            collections=config.collections,
            pipeline_instrument=config.pipeline_instrument,
            pipeline_n_processes=config.pipeline_n_processes,
            zernike_table_name=config.zernike_table_name,
        )

        if dof_state0 is not None:
            self.model.ofc_data.dof_state0 = dof_state0

        self.log.debug("MTAOS configuration completed.")

    def _logExecFunc(self):
        """Log the executed function."""

        funcName = inspect.stack()[1].function
        self.log.info(f"Execute {funcName}().")

    @staticmethod
    def get_config_pkg():

        return "ts_config_mttcs"

    async def start(self):

        self._logExecFunc()

        await super().start()

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
        self.model.reset_wfe_correction()

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
            timeout=self.DEFAULT_TIMEOUT,
            result="issueCorrection started.",
        )

        # We don't want multiple commands to be executed at the same time.
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

        Parameters
        ----------
        data : object
            Data for the command being executed.
        """

        self._logExecFunc()
        self.assert_enabled()

        self.pubEvent_rejectedDegreeOfFreedom()
        self.model.reject_correction()

    async def do_selectSources(self, data):
        """Run source selection algorithm for a specific field and visit
        configuration.

        Parameters
        ----------
        data : object
            Data for the command being executed.

        """
        self.assert_enabled()

        # This command may take some time to execute, so will send
        # ack_in_progress with estimated timeout.
        self.cmd_issueCorrection.ack_in_progress(
            data,
            timeout=self.LONG_TIMEOUT,
            result="selectSources started.",
        )

        await self.model.select_sources(
            ra=data.ra * u.hourangle.to(u.deg),
            dec=data.decl,
            sky_angle=data.pa,
            obs_filter=FilterType(data.filter),
            mode=data.mode,
        )

    async def do_preProcess(self, data):
        """Pre-process image for WEP.

        Parameters
        ----------
        data : object
            Data for the command being executed.
        """
        self.assert_enabled()

        # This command may take some time to execute, so will send
        # ack_in_progress with estimated timeout.
        self.cmd_issueCorrection.ack_in_progress(
            data,
            timeout=self.LONG_TIMEOUT,
            result="preProcess started.",
        )

        if data.useOCPS:
            raise NotImplementedError("Use OCPS not implemented.")
        else:
            # TODO (DM-31365): Remove workaround to visitId being of type long in
            # MTAOS runWEP command.
            await self.model.pre_process(
                visit_id=self.visit_id_offset + data.visitId,
                config=yaml.safe_load(data.config),
            )

    async def do_runWEP(self, data):
        """Process wavefront data.

        Parameters
        ----------
        data : object
            Data for the command being executed.
        """
        self.assert_enabled()

        # This command may take some time to execute, so will send
        # ack_in_progress with estimated timeout.
        self.cmd_issueCorrection.ack_in_progress(
            data,
            timeout=self.LONG_TIMEOUT,
            result="runWEP started.",
        )

        if data.useOCPS:
            raise NotImplementedError("Use OCPS not implemented.")
        else:
            # TODO (DM-31365): Remove workaround to visitId being of type long in
            # MTAOS runWEP command.
            await self.model.run_wep(
                visit_id=self.visit_id_offset + data.visitId,
                extra_id=self.visit_id_offset + data.extraId
                if data.extraId > 0
                else None,
                config=yaml.safe_dump(data.config) if len(data.config) > 0 else {},
                log_time=self.execution_times,
            )

            self.pubEvent_wavefrontError()
            self.pubEvent_rejectedWavefrontError()

            while len(self.execution_times["RUN_WEP"]) > self.MAX_TIME_SAMPLE:
                self.execution_times["RUN_WEP"].pop(0)

    async def do_runOFC(self, data):
        """Run OFC on the latest wavefront errors data. Before running this
        command, you must have ran runWEP at least once.

        This command will run OFC to compute corrections but won't apply them.
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
            data,
            timeout=self.LONG_TIMEOUT,
            result="runOFC started.",
        )

        if len(data.config) > 0:
            raise NotImplementedError(
                "User provided configuration overrides not supported yet."
            )

        async with self.issue_correction_lock:

            # Need to set user gain before computing corrections.
            self.model.user_gain = data.userGain
            # If this call fails (raise an exeception), command will be
            # rejected.
            # This is not a coroutine so it will block the event loop. Need
            # to think about how to fix it, maybe run in executor?
            self.model.calculate_corrections(log_time=self.execution_times)
            while (
                len(self.execution_times["CALCULATE_CORRECTIONS"])
                > self.MAX_TIME_SAMPLE
            ):
                self.execution_times["CALCULATE_CORRECTIONS"].pop(0)

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

        Parameters
        ----------
        data : object
            Data for the command being executed.
        """
        self.assert_enabled()

        # This command may take some time to execute, so will send
        # ack_in_progress with estimated timeout.
        self.cmd_addAberration.ack_in_progress(
            data,
            timeout=self.LONG_TIMEOUT,
            result="addAberration started.",
        )

        # We don't want multiple commands to be executed at the same time.
        # This lock will block any subsequent command from being executed until
        # this one is done.
        async with self.issue_correction_lock:

            config = yaml.safe_load(data.config)

            if config is not None:
                self.log.debug("Customizing OFC parameters.")
                original_ofc_data_values = await self.model.set_ofc_data_values(
                    **config
                )
            else:
                original_ofc_data_values = dict()

            try:
                self.model.add_correction(wavefront_errors=data.wf, config=config)
            finally:
                if len(original_ofc_data_values) > 0:
                    self.log.debug("Restoring ofc_data values.")
                    await self.model.set_ofc_data_values(**original_ofc_data_values)

            self.pubEvent_degreeOfFreedom()
            self.pubEvent_m2HexapodCorrection()
            self.pubEvent_cameraHexapodCorrection()
            self.pubEvent_m1m3Correction()
            self.pubEvent_m2Correction()

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
                (comp, asyncio.create_task(getattr(self, f"issue_{comp}_correction")()))
                for comp in self.issue_correction_to
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
            self.model.reject_correction()

            # Undo corrections that completed.
            error_repor = await self.handle_undo_corrections(issue_corrections_tasks)

            raise RuntimeError(error_repor)

    async def handle_undo_corrections(self, issued_corrections):
        """Handle undoing corrections.

        The method will inspect the `issued_corrections` list of tasks, will
        undo all the successful corrections and log the unsuccesful. If any
        successful correction fail to be undone, it will log the issue and skip
        the error.

        At the end return a report with the activities performed.

        Parameters
        ----------
        issued_corrections : `list` of `asyncio.Task`
            List with all the tasks that executed corrections.

        Returns
        -------
        error_report : `str`
            String with error report.
        """

        failed_to_do = []
        failed_to_undo = []

        # Loop through all the components
        for comp in self.issue_correction_to:
            if issued_corrections[comp].exception() is None:
                # If the task exception is None it means the task completed
                # successfully and the correction needs to be undone. If it
                # fails to undo the exception log the error and continue.
                self.log.warning(f"Undoing {comp} correction.")
                try:
                    await getattr(self, f"issue_{comp}_correction")()
                except Exception:
                    self.log.exception(
                        f"Failed to undo successful correction in {comp}."
                    )
                    failed_to_undo.append(comp)
            else:
                # Correction failed, store it as failed and continue.
                failed_to_do.append(comp)
        # Generate a report about the issue.
        error_report = f"Failed to apply correction to: {failed_to_do}. "
        if len(failed_to_undo) > 0:
            error_report += f"Failed to undo correction to: {failed_to_undo}"

        return error_report

    async def issue_m2hex_correction(self, undo=False):
        """Issue the correction of M2 hexapod.

        Parameters
        ----------
        undo : bool
            If `True` apply the negative value of each correction.
        """

        x, y, z, u, v, w = self.model.m2_hexapod_correction()

        if undo:
            x, y, z, u, v, w = -x, -y, -z, -u, -v, -w

        try:
            await self.remotes["m2hex"].cmd_move.set_start(
                timeout=self.DEFAULT_TIMEOUT, x=x, y=y, z=z, u=u, v=v, w=w, sync=True
            )

            self.log.debug("Issue the M2 hexapod correction successfully.")

        except Exception:
            self.log.exception("M2 hexapod correction command failed.")
            self.pubEvent_rejectedM2HexapodCorrection()
            raise

    async def issue_camhex_correction(self, undo=False):
        """Issue the correction of camera hexapod.

        Parameters
        ----------
        undo : bool
            If `True` apply the negative value of each correction.
        """

        x, y, z, u, v, w = self.model.cam_hexapod_correction()

        if undo:
            x, y, z, u, v, w = -x, -y, -z, -u, -v, -w

        try:
            await self.remotes["camhex"].cmd_move.set_start(
                timeout=self.DEFAULT_TIMEOUT, x=x, y=y, z=z, u=u, v=v, w=w, sync=True
            )

            self.log.debug("Issue the camera hexapod correction successfully.")

        except Exception:
            self.log.exception("Camera hexapod correction command failed.")
            self.pubEvent_rejectedCameraHexapodCorrection()
            raise

    async def issue_m1m3_correction(self, undo=False):
        """Issue the correction of M1M3.

        Parameters
        ----------
        undo : bool
            If `True` apply the negative value of each correction.

        """

        z_forces = self.model.m1m3_correction()

        if undo:
            z_forces = np.negative(z_forces)

        try:
            await self.remotes["m1m3"].cmd_applyActiveOpticForces.set_start(
                timeout=self.DEFAULT_TIMEOUT, zForces=z_forces
            )

            self.log.debug("Issue the M1M3 correction successfully.")

        except Exception:
            self.log.exception("M1M3 correction command failed.")
            self.pubEvent_rejectedM1M3Correction()
            raise

    async def issue_m2_correction(self, undo=False):
        """Issue the correction of M2.

        Parameters
        ----------
        undo : bool
            If `True` apply the negative value of each correction.

        """

        z_forces = self.model.m2_correction()

        if undo:
            z_forces = np.negative(z_forces)

        try:
            await self.remotes["m2"].cmd_applyForces.set_start(
                timeout=self.DEFAULT_TIMEOUT, axial=z_forces
            )

            self.log.debug("Issue the M2 correction successfully.")

        except Exception:
            self.log.exception("M2 correction command failed.")
            self.pubEvent_rejectedM2Correction()
            raise

    def pubEvent_wavefrontError(self):
        """Publish the calculated wavefront error calculated by WEP.

        WEP: Wavefront estimation pipeline.
        """

        self._logExecFunc()

        listOfWfErr = self.model.getListOfWavefrontError()
        for wavefrontError in listOfWfErr:
            sensorId, zk = self._getIdAndZkFromWavefrontErr(wavefrontError)
            self.evt_wavefrontError.set_put(
                sensorId=sensorId,
                annularZernikeCoeff=zk,
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

    def pubEvent_rejectedWavefrontError(self):
        """Publish the rejected calculated wavefront error calculated by WEP.

        WEP: Wavefront estimation pipeline.
        """

        self._logExecFunc()

        listOfWfErrRej = self.model.getListOfWavefrontErrorRej()
        for wavefrontError in listOfWfErrRej:
            sensorId, zk = self._getIdAndZkFromWavefrontErr(wavefrontError)
            self.evt_rejectedWavefrontError.set_put(
                sensorId=sensorId,
                annularZernikeCoeff=zk,
                force_output=True,
            )

    def pubEvent_degreeOfFreedom(self):
        """Publish the degree of freedom generated by the OFC calculation.

        OFC: Optical feedback control.
        """

        self._logExecFunc()

        dofAggr = self.model.get_dof_aggr()
        dofVisit = self.model.get_dof_lv()
        self.evt_degreeOfFreedom.set_put(
            aggregatedDoF=dofAggr,
            visitDoF=dofVisit,
            force_output=True,
        )

    def pubEvent_rejectedDegreeOfFreedom(self):
        """Publish the rejected degree of freedom generated by the OFC
        calculation.

        OFC: Optical feedback control.
        """

        self._logExecFunc()

        dofAggr = self.model.get_dof_aggr()
        dofVisit = self.model.get_dof_lv()
        self.evt_rejectedDegreeOfFreedom.set_put(
            aggregatedDoF=dofAggr,
            visitDoF=dofVisit,
            force_output=True,
        )

    def pubEvent_m2HexapodCorrection(self):
        """Publish the M2 hexapod correction that would be commanded if the
        issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        x, y, z, u, v, w = self.model.m2_hexapod_correction()
        self.evt_m2HexapodCorrection.set_put(
            x=x, y=y, z=z, u=u, v=v, w=w, force_output=True
        )

    def pubEvent_rejectedM2HexapodCorrection(self):
        """Publish the rejected M2 hexapod correction that would be commanded
        if the issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        x, y, z, u, v, w = self.model.m2_hexapod_correction()
        self.evt_rejectedM2HexapodCorrection.set_put(
            x=x, y=y, z=z, u=u, v=v, w=w, force_output=True
        )

    def pubEvent_cameraHexapodCorrection(self):
        """Publish the camera hexapod correction that would be commanded if the
        issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        x, y, z, u, v, w = self.model.cam_hexapod_correction()
        self.evt_cameraHexapodCorrection.set_put(
            x=x, y=y, z=z, u=u, v=v, w=w, force_output=True
        )

    def pubEvent_rejectedCameraHexapodCorrection(self):
        """Publish the rejected camera hexapod correction that would be
        commanded if the issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        x, y, z, u, v, w = self.model.cam_hexapod_correction()
        self.evt_rejectedCameraHexapodCorrection.set_put(
            x=x, y=y, z=z, u=u, v=v, w=w, force_output=True
        )

    def pubEvent_m1m3Correction(self):
        """Publish the M1M3 correction that would be commanded if the
        issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        zForces = self.model.m1m3_correction()
        self.evt_m1m3Correction.set_put(zForces=zForces, force_output=True)

    def pubEvent_rejectedM1M3Correction(self):
        """Publish the rejected M1M3 correction that would be commanded if the
        issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        zForces = self.model.m1m3_correction()
        self.evt_rejectedM1M3Correction.set_put(zForces=zForces, force_output=True)

    def pubEvent_m2Correction(self):
        """Publish the M2 correction that would be commanded if the
        issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        zForces = self.model.m2_correction()
        self.evt_m2Correction.set_put(zForces=zForces, force_output=True)

    def pubEvent_rejectedM2Correction(self):
        """Publish the rejected M2 correction that would be commanded if the
        issueWavefrontCorrection command was sent.
        """

        self._logExecFunc()

        zForces = self.model.m2_correction()
        self.evt_rejectedM2Correction.set_put(zForces=zForces, force_output=True)

    def pubTel_wepDuration(self):
        """Publish the duration of the WEP calculation as telemetry."""

        self._logExecFunc()

        duration = (
            np.mean(self.execution_times["RUN_WEP"])
            if "RUN_WEP" in self.execution_times
            and len(self.execution_times["RUN_WEP"]) > 0
            else 0.0
        )
        self.tel_wepDuration.set_put(calcTime=duration)

    def pubTel_ofcDuration(self):
        """Publish the duration of the OFC calculation as telemetry."""

        self._logExecFunc()

        duration = (
            np.mean(self.execution_times["CALCULATE_CORRECTIONS"])
            if "CALCULATE_CORRECTIONS" in self.execution_times
            and len(self.execution_times["CALCULATE_CORRECTIONS"]) > 0
            else 0.0
        )
        self.tel_ofcDuration.set_put(calcTime=duration)

    @classmethod
    def add_arguments(cls, parser):
        super(MTAOS, cls).add_arguments(parser)
        parser.add_argument(
            "--log-to-file",
            action="store_true",
            default=False,
            help="Output the log to files. The files will be in logs directory. "
            "The default log level is DEBUG.",
        )
        parser.add_argument(
            "--log-level",
            type=int,
            help="Debug level of log files. It can be DEBUG (10), INFO (20), "
            "WARNING (30), ERROR (40), or CRITICAL (50).",
        )

    @classmethod
    def add_kwargs_from_args(cls, args, kwargs):
        super(MTAOS, cls).add_kwargs_from_args(args, kwargs)
        kwargs["log_to_file"] = args.log_to_file
        kwargs["log_level"] = args.log_level
