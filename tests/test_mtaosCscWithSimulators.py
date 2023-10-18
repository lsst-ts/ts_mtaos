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
from pathlib import Path

import numpy as np
import yaml
from lsst.ts import mtaos, salobj

# standard command timeout (sec)
SHORT_TIMEOUT = 5
STD_TIMEOUT = 60


class CscTestCase(salobj.BaseCscTestCase, unittest.IsolatedAsyncioTestCase):
    def basic_make_csc(self, initial_state, config_dir, simulation_mode):
        return mtaos.MTAOS(config_dir=config_dir, simulation_mode=simulation_mode)

    @classmethod
    def setUpClass(cls):
        cls._randomize_topic_subname = False

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
        logFile = Path(mtaos.getLogDir()).joinpath("mtaos.log")
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

            # Use the addAberration to have something to issue.
            wfe = np.zeros(19)
            # Add 0.1 um of defocus
            wfe[0] = 0.1

            # Flush event before correction is issued
            remote.evt_m2HexapodCorrection.flush()
            remote.evt_cameraHexapodCorrection.flush()
            remote.evt_m1m3Correction.flush()
            remote.evt_m2Correction.flush()

            await remote.cmd_addAberration.set_start(wf=wfe, timeout=STD_TIMEOUT)

            # Get the expected corrections.
            m2_hex_corrections = await remote.evt_m2HexapodCorrection.next(
                flush=False, timeout=STD_TIMEOUT
            )
            cam_hex_corrections = await remote.evt_cameraHexapodCorrection.next(
                flush=False, timeout=STD_TIMEOUT
            )
            m1m3_corrections = await remote.evt_m1m3Correction.next(
                flush=False, timeout=STD_TIMEOUT
            )
            m2_corrections = await remote.evt_m2Correction.next(
                flush=False, timeout=STD_TIMEOUT
            )

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

            # Check values. They should match what was published by the events
            for axis in "xyzuvw":
                self.assertEqual(
                    getattr(self.m2_hex_corrections[0], axis),
                    getattr(m2_hex_corrections, axis),
                )
                self.assertEqual(
                    getattr(self.cam_hex_corrections[0], axis),
                    getattr(cam_hex_corrections, axis),
                )

            # Check sync flag
            self.assertTrue(self.m2_hex_corrections[0].sync)
            self.assertTrue(self.cam_hex_corrections[0].sync)

            self.assertTrue(
                np.allclose(self.m1m3_corrections[0].zForces, m1m3_corrections.zForces),
                f"Commanded M1M3 z-forces {self.m1m3_corrections[0].zForces} "
                f"different than expected {m1m3_corrections.zForces}",
            )
            self.assertTrue(
                np.allclose(self.m2_corrections[0].axial, m2_corrections.zForces),
                f"Commanded M2 axial forces {self.m2_corrections[0].axial} "
                f"different than expected {m2_corrections.zForces}",
            )

            # add random values for aberrations
            wf = np.random.rand(19) * 0.1

            dof_add_aberration_before = await remote.evt_degreeOfFreedom.aget(
                timeout=SHORT_TIMEOUT
            )

            remote.evt_degreeOfFreedom.flush()

            await remote.cmd_addAberration.set_start(wf=wf, timeout=10.0)

            dof_add_aberration_after = await remote.evt_degreeOfFreedom.next(
                flush=False, timeout=SHORT_TIMEOUT
            )

            # DoF after addAberration should NOT be similar to DoF before
            # applying addAberration.

            self.assertFalse(
                np.allclose(
                    dof_add_aberration_before.aggregatedDoF,
                    dof_add_aberration_after.aggregatedDoF,
                ),
                f"Expected {dof_add_aberration_before.aggregatedDoF} vs "
                f"Received {dof_add_aberration_after.aggregatedDoF}.",
            )
            self.assertFalse(
                np.allclose(
                    dof_add_aberration_before.visitDoF,
                    dof_add_aberration_after.visitDoF,
                ),
                f"Expected {dof_add_aberration_before.visitDoF} vs "
                f"Received {dof_add_aberration_after.visitDoF}.",
            )

            # Test it works if one of the forces get rejected
            self.cscM1M3.cmd_applyActiveOpticForces.callback = (
                self.m1m3_apply_forces_fail_callbck
            )

            remote.evt_degreeOfFreedom.flush()

            with self.assertRaises(salobj.AckError):
                await remote.cmd_issueCorrection.start(timeout=STD_TIMEOUT)

            dof_issue_correction_after = await remote.evt_degreeOfFreedom.next(
                flush=False, timeout=SHORT_TIMEOUT
            )

            # DoF after issueCorrection is rejected should be similar to DoF
            # before applying addAberration.
            self.assertTrue(
                np.allclose(
                    dof_add_aberration_before.aggregatedDoF,
                    dof_issue_correction_after.aggregatedDoF,
                ),
                f"Expected {dof_add_aberration_before.aggregatedDoF} vs "
                f"Received {dof_issue_correction_after.aggregatedDoF}.",
            )
            self.assertTrue(
                np.allclose(
                    dof_add_aberration_before.visitDoF,
                    dof_issue_correction_after.visitDoF,
                ),
                f"Expected {dof_add_aberration_before.visitDoF} vs "
                f"Received {dof_issue_correction_after.visitDoF}.",
            )

            # There must be 3 corrections for each component except for m1m3
            # which got rejected. The corrections are 1 from the previous test,
            # 1 from trying to apply correction and 1 for removing the
            # correction

            self.assertEqual(len(self.m2_hex_corrections), 3)
            self.assertEqual(len(self.cam_hex_corrections), 3)
            self.assertEqual(len(self.m1m3_corrections), 1)
            self.assertEqual(len(self.m2_corrections), 3)

            # Check values. When the correction fails the system should apply
            # the last successful correction. Therefore the last correction
            # must be equal to the first.
            for axis in "xyzuvw":
                self.assertAlmostEqual(
                    getattr(self.m2_hex_corrections[0], axis),
                    getattr(self.m2_hex_corrections[2], axis),
                )
                self.assertAlmostEqual(
                    getattr(self.cam_hex_corrections[0], axis),
                    getattr(self.cam_hex_corrections[2], axis),
                )

            self.assertTrue(
                np.allclose(
                    np.array(self.m2_corrections[0].axial),
                    np.array(self.m2_corrections[2].axial),
                )
            )

    async def test_addAberration_issueCorrection_xref_x0(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=0
        ):
            await self._simulateCSCs()

            await self._startCsc()

            # Set the timeout > 20 seconds for the long calculation time
            remote = self._getRemote()

            # Flush event before correction is issued
            remote.evt_m2HexapodCorrection.flush()
            remote.evt_cameraHexapodCorrection.flush()
            remote.evt_m1m3Correction.flush()
            remote.evt_m2Correction.flush()

            # Use the addAberration to have something to issue.
            wfe = np.zeros(19)

            # Add 1um of z7
            wfe[7 - 4] = 1

            # set control algorithm
            config = dict(xref="x0")

            # Calculate the DOF and issue the correction for first time
            await remote.cmd_addAberration.set_start(
                wf=wfe, config=yaml.safe_dump(config), timeout=STD_TIMEOUT
            )
            await remote.cmd_issueCorrection.start(timeout=STD_TIMEOUT)

            dof_first = await remote.evt_degreeOfFreedom.next(
                flush=False, timeout=STD_TIMEOUT
            )

            # Calculate the DOF and issue the correction for second time
            await remote.cmd_addAberration.set_start(
                wf=wfe, config=yaml.safe_dump(config), timeout=STD_TIMEOUT
            )
            await remote.cmd_issueCorrection.start(timeout=STD_TIMEOUT)

            dof_second = await remote.evt_degreeOfFreedom.next(
                flush=False, timeout=STD_TIMEOUT
            )

            # The two times calculation of visit DOF should be eqaul under "x0"
            np.testing.assert_array_equal(dof_first.visitDoF, dof_second.visitDoF)

    async def asyncTearDown(self):
        await self._cancelCSCs()

    async def _simulateCSCs(self):
        self.cscM2Hex = salobj.Controller(
            "MTHexapod", index=mtaos.utility.MTHexapodIndex.M2.value
        )
        self.cscCamHex = salobj.Controller(
            "MTHexapod", index=mtaos.utility.MTHexapodIndex.Camera.value
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
        if data.salIndex == mtaos.utility.MTHexapodIndex.M2.value:
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
