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
        return MTAOS.MtaosCsc(config_dir=config_dir, simulation_mode=simulation_mode)

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

    def tearDown(self):

        logFile = Path(MTAOS.getLogDir()).joinpath("MTAOS.log")
        if logFile.exists():
            logFile.unlink()

    async def test_addAberration_issueCorrection(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=0
        ):
            await self._simulateCSCs()

            await self._startCsc()

            # Set the timeout > 20 seconds for the long calculation time
            remote = self._getRemote()

            # User the addAberration to have something to issue
            wfe = np.zeros(19)
            await remote.cmd_addAberration.set_start(wf=wfe, timeout=STD_TIMEOUT)

            # Add aberration does not send the corrections, we need to send
            # run issueCorrections
            self.assertEqual(len(self.m2_hex_corrections), 0)
            self.assertEqual(len(self.cam_hex_corrections), 0)
            self.assertEqual(len(self.m1m3_corrections), 0)
            self.assertEqual(len(self.m2_corrections), 0)

            await remote.cmd_issueCorrection.start(timeout=STD_TIMEOUT)

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

            wf = np.random.rand(19) * 0.1

            await remote.cmd_addAberration.set_start(wf=wf, timeout=10.0)

            with self.assertRaises(salobj.AckError):
                await remote.cmd_issueCorrection.start(timeout=STD_TIMEOUT)

            # There must be 3 corrections for each component except for m1m3
            # which got rejected. The corrections are 1 from the previous test,
            # 1 from trying to apply correction and 1 for removing the
            # correction

            self.assertEqual(len(self.m2_hex_corrections), 3)
            self.assertEqual(len(self.cam_hex_corrections), 3)
            self.assertEqual(len(self.m1m3_corrections), 1)
            self.assertEqual(len(self.m2_corrections), 3)

            # Check values. The last 2 corrections should have same values with
            # different sign.
            for axis in "xyzuvw":
                self.assertEqual(
                    getattr(self.m2_hex_corrections[1], axis),
                    -getattr(self.m2_hex_corrections[2], axis),
                )
                self.assertEqual(
                    getattr(self.cam_hex_corrections[1], axis),
                    -getattr(self.cam_hex_corrections[2], axis),
                )

            self.assertTrue(
                np.all(
                    np.array(self.m2_corrections[1].axial)
                    == -np.array(self.m2_corrections[2].axial)
                )
            )

    async def asyncTearDown(self):
        await self._cancelCSCs()

    async def _simulateCSCs(self):

        self.cscM2Hex = salobj.Controller(
            "MTHexapod", index=MTAOS.utility.MTHexapodIndex.M2.value
        )
        self.cscCamHex = salobj.Controller(
            "MTHexapod", index=MTAOS.utility.MTHexapodIndex.Camera.value
        )
        self.cscM1M3 = salobj.Controller("MTM1M3")
        self.cscM2 = salobj.Controller("MTM2")

        await asyncio.gather(
            *[
                controller.start_task
                for controller in {
                    self.cscM2Hex,
                    self.cscCamHex,
                    self.cscM1M3,
                    self.cscM2,
                }
            ]
        )

        self.cscM2Hex.cmd_move.callback = self.hexapod_move_callbck
        self.cscCamHex.cmd_move.callback = self.hexapod_move_callbck
        self.cscM1M3.cmd_applyActiveOpticForces.callback = (
            self.m1m3_apply_forces_callbck
        )
        self.cscM2.cmd_applyForces.callback = self.m2_apply_forces_callbck

    def hexapod_move_callbck(self, data):

        if data.MTHexapodID == MTAOS.utility.MTHexapodIndex.M2.value:
            self.m2_hex_corrections.append(data)
        else:
            self.cam_hex_corrections.append(data)

    def m1m3_apply_forces_callbck(self, data):

        self.m1m3_corrections.append(data)

    def m1m3_apply_forces_fail_callbck(self, data):

        raise RuntimeError("This is a test.")

    def m2_apply_forces_callbck(self, data):

        self.m2_corrections.append(data)

    async def _startCsc(self):
        remote = self._getRemote()
        await salobj.set_summary_state(remote, salobj.State.ENABLED)

    def _getRemote(self):
        # This is instantiated after calling self.make_csc().
        return self.remote

    async def _cancelCSCs(self):

        await asyncio.gather(
            self.cscM2Hex.close(),
            self.cscCamHex.close(),
            self.cscM1M3.close(),
            self.cscM2.close(),
        )


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
