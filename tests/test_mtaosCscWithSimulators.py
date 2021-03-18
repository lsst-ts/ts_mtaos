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

import asyncio
import unittest
import numpy as np
from pathlib import Path
from lsst.ts import salobj
from lsst.ts import MTAOS

# standard command timeout (sec)
STD_TIMEOUT = 60


class CscTestCase(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
    def basic_make_csc(self, initial_state, config_dir, simulation_mode):
        return MTAOS.MtaosCsc(
            config_dir=config_dir, simulation_mode=simulation_mode, log_to_file=True
        )

    def setUp(self):

        # Simulated CSCs
        self.cscM2Hex = None
        self.cscCamHex = None
        self.cscM1M3 = None
        self.cscM2 = None

        self.m2_hex_corrections = []
        self.cam_hex_corrections = []
        self.m1m3_corrections = []
        self.m2_corrections = []

        # Simulated CSC tasks
        self.taskM2Hex = None
        self.taskCamHex = None
        self.taskM1M3 = None
        self.taskM2 = None

    def tearDown(self):

        logFile = Path(MTAOS.getLogDir()).joinpath("MTAOS.log")
        if logFile.exists():
            logFile.unlink()

    @unittest.skip("Skip until commands implementation.")
    async def testIssueCorrection(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=1
        ):

            await self._simulateCSCs()

            await self._startCsc()

            # Set the timeout > 20 seconds for the long calculation time
            remote = self._getRemote()
            await remote.cmd_runWEP.set_start()

            await remote.cmd_runOFC.set_start()

            await remote.cmd_issueCorrection.set_start(timeout=10.0, value=True)

            await self._cancelCSCs()

    async def test_addAberration(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=0
        ):

            await self._simulateCSCs()

            await self._startCsc()

            # Set the timeout > 20 seconds for the long calculation time
            remote = self._getRemote()

            await remote.cmd_addAberration.set_start(wf=np.zeros(19), timeout=10.0)

            # There must be 1 correction for each component

            self.assertEqual(len(self.m2_hex_corrections), 1)
            self.assertEqual(len(self.cam_hex_corrections), 1)
            self.assertEqual(len(self.m1m3_corrections), 1)
            self.assertEqual(len(self.m2_corrections), 1)

            # Check values. They should all be zeros.

            for axis in "xyzuvw":
                self.assertEqual(getattr(self.m2_hex_corrections[0], axis), 0)
                self.assertEqual(getattr(self.cam_hex_corrections[0], axis), 0)

            # Check sync flag
            self.assertTrue(self.m2_hex_corrections[0].sync)
            self.assertTrue(self.cam_hex_corrections[0].sync)

            self.assertTrue(
                np.allclose(self.m1m3_corrections[0].zForces, 0.0),
                f"Not all M1M3 forces are close to zero {self.m1m3_corrections[0].zForces}",
            )
            self.assertTrue(
                np.allclose(self.m2_corrections[0].axial, 0.0),
                f"Not all M2 forces are close to zero {self.m2_corrections[0].axial}",
            )

            # Test it works if one of the forces get rejected
            self.cscM1M3.cmd_applyActiveOpticForces.callback = (
                self.m1m3_apply_forces_fail_callbck
            )

            with self.assertRaises(salobj.AckError):
                await remote.cmd_addAberration.set_start(wf=np.zeros(19), timeout=10.0)

            # There must be 3 corrections for each component except for m1m3
            # which got rejected. The corrections are 1 from the previous test,
            # 1 from trying to apply correction and 1 for removing the
            # correction

            self.assertEqual(len(self.m2_hex_corrections), 3)
            self.assertEqual(len(self.cam_hex_corrections), 3)
            self.assertEqual(len(self.m1m3_corrections), 1)
            self.assertEqual(len(self.m2_corrections), 3)

            await self._cancelCSCs()

    async def _simulateCSCs(self):

        # Mock controller that uses callback functions defined below
        # to handle the expected commands
        self.taskM2Hex = asyncio.create_task(self._simulateM2Hex())
        self.taskCamHex = asyncio.create_task(self._simulateCamHex())
        self.taskM1M3 = asyncio.create_task(self._simulateM1M3())
        self.taskM2 = asyncio.create_task(self._simulateM2())

    async def _simulateM2Hex(self):

        self.cscM2Hex = salobj.Controller(
            "MTHexapod", index=MTAOS.Utility.MTHexapodIndex.M2.value
        )
        self.cscM2Hex.cmd_move.callback = self.hexapod_move_callbck

    def hexapod_move_callbck(self, data):

        if data.MTHexapodID == MTAOS.Utility.MTHexapodIndex.M2.value:
            self.m2_hex_corrections.append(data)
        else:
            self.cam_hex_corrections.append(data)

    async def _simulateCamHex(self):

        self.cscCamHex = salobj.Controller(
            "MTHexapod", index=MTAOS.Utility.MTHexapodIndex.Camera.value
        )
        self.cscCamHex.cmd_move.callback = self.hexapod_move_callbck

    async def _simulateM1M3(self):

        self.cscM1M3 = salobj.Controller("MTM1M3")
        self.cscM1M3.cmd_applyActiveOpticForces.callback = (
            self.m1m3_apply_forces_callbck
        )

    def m1m3_apply_forces_callbck(self, data):

        self.m1m3_corrections.append(data)

    def m1m3_apply_forces_fail_callbck(self, data):

        raise RuntimeError("This is a test.")

    async def _simulateM2(self):

        self.cscM2 = salobj.Controller("MTM2")
        self.cscM2.cmd_applyForces.callback = self.m2_apply_forces_callbck

    def m2_apply_forces_callbck(self, data):

        self.m2_corrections.append(data)

    async def _startCsc(self):
        remote = self._getRemote()
        await salobj.set_summary_state(remote, salobj.State.ENABLED)

    def _getRemote(self):
        # This is instantiated after calling self.make_csc().
        return self.remote

    async def _cancelCSCs(self):

        await self.cscM2Hex.close()
        await self.cscCamHex.close()
        await self.cscM1M3.close()
        await self.cscM2.close()

        self.taskM2Hex.cancel()
        self.taskCamHex.cancel()
        self.taskM1M3.cancel()
        self.taskM2.cancel()


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
