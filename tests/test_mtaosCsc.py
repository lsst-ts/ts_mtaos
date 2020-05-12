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

import os
import asynctest
from pathlib import Path
import numpy as np

from lsst.utils import getPackageDir

from lsst.ts import salobj
from lsst.ts import MTAOS

# standard command timeout (sec)
STD_TIMEOUT = 60


class CscTestCase(salobj.BaseCscTestCase, asynctest.TestCase):

    def basic_make_csc(self, initial_state, config_dir, simulation_mode):
        return MTAOS.MtaosCsc(
            config_dir=config_dir,
            simulation_mode=simulation_mode,
            log_to_file=True
        )

    def setUp(self):

        self.dataDir = MTAOS.getModulePath().joinpath("tests", "tmp")
        self.isrDir = self.dataDir.joinpath("input")

        # Let the MTAOS to set WEP based on this path variable
        os.environ["ISRDIRPATH"] = self.isrDir.as_posix()

    def tearDown(self):

        try:
            os.environ.pop("ISRDIRPATH")
        except KeyError:
            pass

        logFile = Path(MTAOS.getLogDir()).joinpath("MTAOS.log")
        if logFile.exists():
            logFile.unlink()

    def _getCsc(self):
        # This is instantiated after calling self.make_csc().
        return self.csc

    def _getRemote(self):
        # This is instantiated after calling self.make_csc().
        return self.remote

    async def testBinScript(self):
        cmdline_args = ["--simulate", "--logToFile"]
        await self.check_bin_script("MTAOS", 0, "run_mtaos.py",
                                    cmdline_args)

    async def testInitWithoutConfigDir(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None,
            simulation_mode=1
        ):

            configDir = Path(getPackageDir("ts_config_mttcs"))
            configDir = configDir.joinpath(MTAOS.getCscName(), "v1")

            csc = self._getCsc()
            self.assertEqual(csc.config_dir, configDir)

    async def testInitWithConfigDir(self):
        configDir = MTAOS.getModulePath().joinpath("tests", "testData")
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=configDir,
            simulation_mode=1
        ):

            csc = self._getCsc()
            self.assertEqual(csc.config_dir, configDir)

    async def testConfiguration(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None,
            simulation_mode=1
        ):
            await self._startCsc()

            csc = self._getCsc()
            model = csc.getModel()
            self.assertTrue(isinstance(model, MTAOS.ModelSim))

    async def _startCsc(self):
        remote = self._getRemote()
        await salobj.set_summary_state(remote, salobj.State.ENABLED)

    async def testCommandsWrongState(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None,
            simulation_mode=1
        ):

            remote = self._getRemote()

            funcNames = ["resetWavefrontCorrection", "issueWavefrontCorrection",
                         "processCalibrationProducts",
                         "processIntraExtraWavefrontError"]
            for funcName in funcNames:
                cmdObj = getattr(remote, f"cmd_{funcName}")
                with self.assertRaises(salobj.AckError):
                    await cmdObj.set_start(timeout=5)

    @asynctest.skip("Need timeout support of check_standard_state_transitions()")
    async def testStandardStateTransitions(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None,
            simulation_mode=1
        ):
            enabled_commands = ("resetWavefrontCorrection",
                                "issueWavefrontCorrection",
                                "processCalibrationProducts",
                                "processIntraExtraWavefrontError")
            skip_commands = ("processWavefrontError",
                             "processShWavefrontError",
                             "processCmosWavefrontError")
            await self.check_standard_state_transitions(
                enabled_commands=enabled_commands,
                skip_commands=skip_commands)

    async def testResetWavefrontCorrection(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None,
            simulation_mode=1
        ):
            await self._startCsc()

            remote = self._getRemote()
            await remote.cmd_resetWavefrontCorrection.set_start(
                timeout=STD_TIMEOUT, value=True)

            dof = await remote.evt_degreeOfFreedom.next(
                flush=False, timeout=STD_TIMEOUT)
            dofAggr = dof.aggregatedDoF
            dofVisit = dof.visitDoF
            self.assertEqual(len(dofAggr), 50)
            self.assertEqual(len(dofVisit), 50)
            self.assertEqual(np.sum(np.abs(dofAggr)), 0)
            self.assertEqual(np.sum(np.abs(dofVisit)), 0)

            await self._checkCorrIsZero(remote)

    async def _checkCorrIsZero(self, remote):

        corrM2Hex = await remote.evt_m2HexapodCorrection.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertEqual(corrM2Hex.x, 0)
        self.assertEqual(corrM2Hex.y, 0)
        self.assertEqual(corrM2Hex.z, 0)
        self.assertEqual(corrM2Hex.u, 0)
        self.assertEqual(corrM2Hex.v, 0)
        self.assertEqual(corrM2Hex.w, 0)

        corrCamHex = await remote.evt_cameraHexapodCorrection.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertEqual(corrCamHex.x, 0)
        self.assertEqual(corrCamHex.y, 0)
        self.assertEqual(corrCamHex.z, 0)
        self.assertEqual(corrCamHex.u, 0)
        self.assertEqual(corrCamHex.v, 0)
        self.assertEqual(corrCamHex.w, 0)

        corrM1M3 = await remote.evt_m1m3Correction.next(
            flush=False, timeout=STD_TIMEOUT)
        actForcesM1M3 = corrM1M3.zForces
        self.assertEqual(len(actForcesM1M3), 156)
        self.assertEqual(np.sum(np.abs(actForcesM1M3)), 0)

        corrM2 = await remote.evt_m2Correction.next(
            flush=False, timeout=STD_TIMEOUT)
        actForcesM2 = corrM2.zForces
        self.assertEqual(len(actForcesM2), 72)
        self.assertEqual(np.sum(np.abs(actForcesM2)), 0)

    async def testIssueWavefrontCorrection(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None,
            simulation_mode=1
        ):
            await self._startCsc()

            remote = self._getRemote()
            with self.assertRaises(salobj.AckTimeoutError):
                with self.assertWarns(UserWarning):
                    # timeout value here can not be longer than the default
                    # value in the Model. Otherwise, the salobj.AckTimeoutError
                    # will not be raised.
                    await remote.cmd_issueWavefrontCorrection.set_start(
                        timeout=10.0, value=True)

            dof = await remote.evt_rejectedDegreeOfFreedom.next(
                flush=False, timeout=STD_TIMEOUT)
            dofAggr = dof.aggregatedDoF
            dofVisit = dof.visitDoF
            self.assertEqual(len(dofAggr), 50)
            self.assertEqual(len(dofVisit), 50)
            self.assertEqual(np.sum(np.abs(dofAggr)), 0)
            self.assertEqual(np.sum(np.abs(dofVisit)), 0)

            corrM2Hex = await remote.evt_rejectedM2HexapodCorrection.next(
                flush=False, timeout=STD_TIMEOUT)
            self.assertEqual(corrM2Hex.x, 0)
            self.assertEqual(corrM2Hex.y, 0)
            self.assertEqual(corrM2Hex.z, 0)
            self.assertEqual(corrM2Hex.u, 0)
            self.assertEqual(corrM2Hex.v, 0)
            self.assertEqual(corrM2Hex.w, 0)

    async def testIssueWavefrontCorrectionWithWfErr(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None,
            simulation_mode=1
        ):
            await self._startCsc()

            # Set the timeout > 20 seconds for the long calculation time
            remote = self._getRemote()
            await remote.cmd_processIntraExtraWavefrontError.set_start(
                timeout=2*STD_TIMEOUT, intraVisit=0, extraVisit=1,
                intraDirectoryPath="intraDir", extraDirectoryPath="extraDir",
                fieldRA=0.0, fieldDEC=0.0, filter=7, cameraRotation=0.0,
                userGain=1)

            with self.assertRaises(salobj.AckTimeoutError):
                with self.assertWarns(UserWarning):
                    # timeout value here can not be longer than the default
                    # value in the Model. Otherwise, the salobj.AckTimeoutError
                    # will not be raised.
                    await remote.cmd_issueWavefrontCorrection.set_start(
                        timeout=10.0, value=True)

            await self._checkOfcTopicsFromProcImg(remote)

    async def _checkOfcTopicsFromProcImg(self, remote):

        warningOfc = await remote.evt_ofcWarning.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertEqual(warningOfc.warning, 0)

        dof = await remote.evt_degreeOfFreedom.next(
            flush=False, timeout=STD_TIMEOUT)
        dofAggr = dof.aggregatedDoF
        dofVisit = dof.visitDoF
        self.assertEqual(len(dofAggr), 50)
        self.assertEqual(len(dofVisit), 50)
        self.assertNotEqual(np.sum(np.abs(dofAggr)), 0)
        self.assertNotEqual(np.sum(np.abs(dofVisit)), 0)

        await self._checkCorrNotZero(remote)

        durationOfc = await remote.tel_ofcDuration.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertGreater(durationOfc.calcTime, 0)

    async def _checkCorrNotZero(self, remote):

        corrM2Hex = await remote.evt_m2HexapodCorrection.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertNotEqual(corrM2Hex.x, 0)
        self.assertNotEqual(corrM2Hex.y, 0)
        self.assertNotEqual(corrM2Hex.z, 0)
        self.assertNotEqual(corrM2Hex.u, 0)
        self.assertNotEqual(corrM2Hex.v, 0)
        self.assertEqual(corrM2Hex.w, 0)

        corrCamHex = await remote.evt_cameraHexapodCorrection.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertNotEqual(corrCamHex.x, 0)
        self.assertNotEqual(corrCamHex.y, 0)
        self.assertNotEqual(corrCamHex.z, 0)
        self.assertNotEqual(corrCamHex.u, 0)
        self.assertNotEqual(corrCamHex.v, 0)
        self.assertEqual(corrCamHex.w, 0)

        corrM1M3 = await remote.evt_m1m3Correction.next(
            flush=False, timeout=STD_TIMEOUT)
        actForcesM1M3 = corrM1M3.zForces
        self.assertEqual(len(actForcesM1M3), 156)
        self.assertNotEqual(np.sum(np.abs(actForcesM1M3)), 0)

        corrM2 = await remote.evt_m2Correction.next(
            flush=False, timeout=STD_TIMEOUT)
        actForcesM2 = corrM2.zForces
        self.assertEqual(len(actForcesM2), 72)
        self.assertNotEqual(np.sum(np.abs(actForcesM2)), 0)

    async def testProcessCalibrationProducts(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None,
            simulation_mode=1
        ):
            await self._startCsc()

            remote = self._getRemote()
            await remote.cmd_processCalibrationProducts.set_start(
                timeout=STD_TIMEOUT, directoryPath="calibsDir")

    async def testProcessIntraExtraWavefrontError(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None,
            simulation_mode=1
        ):
            await self._startCsc()

            # Set the timeout > 20 seconds for the long calculation time
            remote = self._getRemote()
            await remote.cmd_processIntraExtraWavefrontError.set_start(
                timeout=2*STD_TIMEOUT, intraVisit=0, extraVisit=1,
                intraDirectoryPath="intraDir", extraDirectoryPath="extraDir",
                fieldRA=0.0, fieldDEC=0.0, filter=7, cameraRotation=0.0,
                userGain=1)

            csc = self._getCsc()
            await self._checkWepTopicsFromProcImg(remote, csc)

    async def _checkWepTopicsFromProcImg(self, remote, csc):

        warningWep = await remote.evt_wepWarning.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertEqual(warningWep.warning, 0)

        # The value here should be 0 because the wavefront error is published
        # already
        numOfWfErr = len(csc.getModel().getListOfWavefrontError())
        self.assertEqual(numOfWfErr, 0)

        # Check the published wavefront error
        for counter in range(9):
            wfErr = await remote.evt_wavefrontError.next(
                flush=False, timeout=STD_TIMEOUT)
            self.assertNotEqual(wfErr.sensorId, 0)

            zk = wfErr.annularZernikePoly
            self.assertEqual(len(zk), 19)
            self.assertNotEqual(np.sum(np.abs(zk)), 0)

        numOfWfErrRej = len(csc.getModel().getListOfWavefrontErrorRej())
        for counter in range(numOfWfErrRej):
            wfErr = await remote.evt_rejectedWavefrontError.next(
                flush=False, timeout=STD_TIMEOUT)
            self.assertNotEqual(wfErr.sensorId, 0)

            zk = wfErr.annularZernikePoly
            self.assertEqual(len(zk), 19)
            self.assertNotEqual(np.sum(np.abs(zk)), 0)

        durationWep = await remote.tel_wepDuration.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertGreater(durationWep.calcTime, 14)


if __name__ == "__main__":

    # Do the unit test
    asynctest.main()
