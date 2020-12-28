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
import asyncio
import asynctest
import numpy as np
from pathlib import Path
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

        # Simulated CSCs
        self.cscM2Hex = None
        self.cscCamHex = None
        self.cscM1M3 = None
        self.cscM2 = None

        # Simulated CSC tasks
        self.taskM2Hex = None
        self.taskCamHex = None
        self.taskM1M3 = None
        self.taskM2 = None

    def tearDown(self):

        try:
            os.environ.pop("ISRDIRPATH")
        except KeyError:
            pass

        logFile = Path(MTAOS.getLogDir()).joinpath("MTAOS.log")
        if logFile.exists():
            logFile.unlink()

    async def testIssueWavefrontCorrection(self):
        async with self.make_csc(
            initial_state=salobj.State.STANDBY, config_dir=None, simulation_mode=1
        ):

            await self._simulateCSCs()

            await self._startCsc()

            # Set the timeout > 20 seconds for the long calculation time
            remote = self._getRemote()
            await remote.cmd_processIntraExtraWavefrontError.set_start(
                timeout=2 * STD_TIMEOUT,
                intraVisit=0,
                extraVisit=1,
                intraDirectoryPath="intraDir",
                extraDirectoryPath="extraDir",
                fieldRA=0.0,
                fieldDEC=0.0,
                filter=7,
                cameraRotation=0.0,
                userGain=1,
            )

            await remote.cmd_issueWavefrontCorrection.set_start(
                timeout=10.0, value=True
            )

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
        self.cscM2Hex.cmd_move.callback = self._checkDataHex

    def _checkDataHex(self, data):

        self.assertNotEqual(data.x, 0)
        self.assertNotEqual(data.y, 0)
        self.assertNotEqual(data.z, 0)
        self.assertNotEqual(data.u, 0)
        self.assertNotEqual(data.v, 0)

        self.assertEqual(data.w, 0)
        self.assertEqual(data.sync, True)

    async def _simulateCamHex(self):

        self.cscCamHex = salobj.Controller(
            "MTHexapod", index=MTAOS.Utility.MTHexapodIndex.Camera.value
        )
        self.cscCamHex.cmd_move.callback = self._checkDataHex

    async def _simulateM1M3(self):

        self.cscM1M3 = salobj.Controller("MTM1M3")
        self.cscM1M3.cmd_applyActiveOpticForces.callback = self._callbackM1M3

    def _callbackM1M3(self, data):

        self._checkActForce(data.zForces)

    def _checkActForce(self, forceData):

        self.assertNotEqual(np.sum(np.abs(forceData)), 0)

    async def _simulateM2(self):

        self.cscM2 = salobj.Controller("MTM2")
        self.cscM2.cmd_applyForces.callback = self._callbackM2

    def _callbackM2(self, data):

        self._checkActForce(data.axial)

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
    asynctest.main()
