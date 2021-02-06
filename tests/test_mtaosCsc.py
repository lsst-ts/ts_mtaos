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
            config_dir=config_dir, simulation_mode=simulation_mode, log_to_file=True
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
        cmdline_args = ["--simulate", "--logToFile", "--debugLevel", "20"]
        await self.check_bin_script(
            "MTAOS", 0, "run_mtaos.py", cmdline_args=cmdline_args
        )

    async def testInitWithoutConfigDir(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=1
        ):

            configDir = Path(getPackageDir("ts_config_mttcs"))
            configDir = configDir.joinpath(MTAOS.getCscName(), "v1")

            csc = self._getCsc()
            self.assertEqual(csc.config_dir, configDir)

    async def testInitWithConfigDir(self):
        configDir = MTAOS.getModulePath().joinpath("tests", "testData")
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=configDir, simulation_mode=1
        ):

            csc = self._getCsc()
            self.assertEqual(csc.config_dir, configDir)

    async def testConfiguration(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=1
        ):
            await self._startCsc()

            csc = self._getCsc()
            model = csc.getModel()
            self.assertTrue(isinstance(model, MTAOS.ModelSim))

    async def _startCsc(self):
        remote = self._getRemote()
        await salobj.set_summary_state(remote, salobj.State.ENABLED)

    async def testStandardStateTransitions(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=1
        ):
            enabled_commands = (
                "resetCorrection",
                "issueCorrection",
                "rejectCorrection",
                "selectSources",
                "preProcess",
                "runWEP",
                "runOFC",
                "addAberration",
            )
            await self.check_standard_state_transitions(
                enabled_commands=enabled_commands, timeout=STD_TIMEOUT,
            )

    async def testResetCorrection(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=1
        ):
            await self._startCsc()

            remote = self._getRemote()
            await remote.cmd_resetCorrection.set_start(timeout=STD_TIMEOUT)

            dof = await remote.evt_degreeOfFreedom.next(
                flush=False, timeout=STD_TIMEOUT
            )
            dofAggr = dof.aggregatedDoF
            dofVisit = dof.visitDoF
            self.assertEqual(len(dofAggr), 50)
            self.assertEqual(len(dofVisit), 50)
            self.assertEqual(np.sum(np.abs(dofAggr)), 0)
            self.assertEqual(np.sum(np.abs(dofVisit)), 0)

            await self._checkCorrIsZero(remote)

    async def _checkCorrIsZero(self, remote):

        await self.assert_next_sample(
            remote.evt_m2HexapodCorrection,
            flush=False,
            timeout=STD_TIMEOUT,
            x=0,
            y=0,
            z=0,
            u=0,
            v=0,
            w=0,
        )

        await self.assert_next_sample(
            remote.evt_cameraHexapodCorrection,
            flush=False,
            timeout=STD_TIMEOUT,
            x=0,
            y=0,
            z=0,
            u=0,
            v=0,
            w=0,
        )

        corrM1M3 = await remote.evt_m1m3Correction.next(
            flush=False, timeout=STD_TIMEOUT
        )
        actForcesM1M3 = corrM1M3.zForces
        self.assertEqual(len(actForcesM1M3), 156)
        self.assertEqual(np.sum(np.abs(actForcesM1M3)), 0)

        corrM2 = await remote.evt_m2Correction.next(flush=False, timeout=STD_TIMEOUT)
        actForcesM2 = corrM2.zForces
        self.assertEqual(len(actForcesM2), 72)
        self.assertEqual(np.sum(np.abs(actForcesM2)), 0)

    async def testIssueCorrectionError(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=1
        ):
            await self._startCsc()

            remote = self._getRemote()
            with self.assertRaises(salobj.AckError):
                await remote.cmd_issueCorrection.set_start(timeout=10.0)

            dof = await remote.evt_rejectedDegreeOfFreedom.next(
                flush=False, timeout=STD_TIMEOUT
            )
            dofAggr = dof.aggregatedDoF
            dofVisit = dof.visitDoF
            self.assertEqual(len(dofAggr), 50)
            self.assertEqual(len(dofVisit), 50)
            self.assertEqual(np.sum(np.abs(dofAggr)), 0)
            self.assertEqual(np.sum(np.abs(dofVisit)), 0)

            await self.assert_next_sample(
                remote.evt_rejectedM2HexapodCorrection,
                flush=False,
                timeout=STD_TIMEOUT,
                x=0,
                y=0,
                z=0,
                u=0,
                v=0,
                w=0,
            )


if __name__ == "__main__":

    # Do the unit test
    asynctest.main()
