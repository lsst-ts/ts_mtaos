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
import numpy as np
from pathlib import Path

from lsst.utils import getPackageDir

from lsst.ts import salobj
from lsst.ts import MTAOS

# standard command timeout (sec)
STD_TIMEOUT = 60


class Harness(object):

    def __init__(self, config_dir=None):
        self.csc = MTAOS.MtaosCsc(
            config_dir=config_dir,
            initial_simulation_mode=1)
        self.remote = salobj.Remote(self.csc.domain, MTAOS.getCscName(), index=0)

    async def __aenter__(self):
        await self.csc.start_task
        await self.remote.start_task
        return self

    async def __aexit__(self, *args):
        await self.remote.close()
        await self.csc.close()


class TestMtaosCsc(asynctest.TestCase):
    """Test the MtaosCsc class."""

    def setUp(self):

        self.dataDir = MTAOS.getModulePath().joinpath("tests", "tmp")
        self.isrDir = self.dataDir.joinpath("input")

        # Let the MTAOS to set WEP based on this path variable
        os.environ["ISRDIRPATH"] = self.isrDir.as_posix()

        salobj.set_random_lsst_dds_domain()

    def tearDown(self):

        try:
            os.environ.pop("ISRDIRPATH")
        except KeyError:
            pass

    async def testInitWithoutConfigDir(self):
        async with Harness() as harness:

            configDir = Path(getPackageDir("ts_config_mttcs"))
            configDir = configDir.joinpath(MTAOS.getCscName(), "v1")
            self.assertEqual(harness.csc.config_dir, configDir)

    async def testInitWithConfigDir(self):

        configDir = MTAOS.getModulePath().joinpath("tests", "testData")
        async with Harness(config_dir=configDir) as harness:

            self.assertEqual(harness.csc.config_dir, configDir)

    async def testConfiguration(self):
        async with Harness() as harness:

            await self._startCsc(harness)

            model = harness.csc.getModel()
            self.assertTrue(isinstance(model, MTAOS.ModelSim))

    async def _startCsc(self, harness):
        await harness.remote.cmd_start.set_start(
            timeout=STD_TIMEOUT, settingsToApply="default")
        await harness.remote.cmd_enable.set_start(
            timeout=STD_TIMEOUT)

    async def testCommandsWrongState(self):
        async with Harness() as harness:

            funcNames = ["resetWavefrontCorrection", "issueWavefrontCorrection",
                         "processCalibrationProducts",
                         "processIntraExtraWavefrontError"]

            for funcName in funcNames:
                cmdObj = getattr(harness.remote, f"cmd_{funcName}")
                with self.assertRaises(salobj.AckError):
                    await cmdObj.set_start(timeout=5)

    async def testDo_resetWavefrontCorrection(self):
        async with Harness() as harness:

            await self._startCsc(harness)
            await harness.remote.cmd_resetWavefrontCorrection.set_start(
                timeout=STD_TIMEOUT, value=True)

            dof = await harness.remote.evt_degreeOfFreedom.next(
                flush=False, timeout=STD_TIMEOUT)
            dofAggr = dof.aggregatedDoF
            dofVisit = dof.visitDoF
            self.assertEqual(len(dofAggr), 50)
            self.assertEqual(len(dofVisit), 50)
            self.assertEqual(np.sum(np.abs(dofAggr)), 0)
            self.assertEqual(np.sum(np.abs(dofVisit)), 0)

            await self._checkCorrIsZero(harness)

    async def _checkCorrIsZero(self, harness):

        corrM2Hex = await harness.remote.evt_m2HexapodCorrection.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertEqual(corrM2Hex.x, 0)
        self.assertEqual(corrM2Hex.y, 0)
        self.assertEqual(corrM2Hex.z, 0)
        self.assertEqual(corrM2Hex.u, 0)
        self.assertEqual(corrM2Hex.v, 0)
        self.assertEqual(corrM2Hex.w, 0)

        corrCamHex = await harness.remote.evt_cameraHexapodCorrection.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertEqual(corrCamHex.x, 0)
        self.assertEqual(corrCamHex.y, 0)
        self.assertEqual(corrCamHex.z, 0)
        self.assertEqual(corrCamHex.u, 0)
        self.assertEqual(corrCamHex.v, 0)
        self.assertEqual(corrCamHex.w, 0)

        corrM1M3 = await harness.remote.evt_m1m3Correction.next(
            flush=False, timeout=STD_TIMEOUT)
        actForcesM1M3 = corrM1M3.zForces
        self.assertEqual(len(actForcesM1M3), 156)
        self.assertEqual(np.sum(np.abs(actForcesM1M3)), 0)

        corrM2 = await harness.remote.evt_m2Correction.next(
            flush=False, timeout=STD_TIMEOUT)
        actForcesM2 = corrM2.zForces
        self.assertEqual(len(actForcesM2), 72)
        self.assertEqual(np.sum(np.abs(actForcesM2)), 0)

    async def testDo_issueWavefrontCorrection(self):
        async with Harness() as harness:

            await self._startCsc(harness)

            with self.assertRaises(salobj.AckTimeoutError):
                with self.assertWarns(UserWarning):
                    # timeout value here can not be longer than the default
                    # value in the Model. Otherwise, the salobj.AckTimeoutError
                    # will not be raised.
                    await harness.remote.cmd_issueWavefrontCorrection.set_start(
                        timeout=10.0, value=True)

            dof = await harness.remote.evt_rejectedDegreeOfFreedom.next(
                flush=False, timeout=STD_TIMEOUT)
            dofAggr = dof.aggregatedDoF
            dofVisit = dof.visitDoF
            self.assertEqual(len(dofAggr), 50)
            self.assertEqual(len(dofVisit), 50)
            self.assertEqual(np.sum(np.abs(dofAggr)), 0)
            self.assertEqual(np.sum(np.abs(dofVisit)), 0)

            corrM2Hex = await harness.remote.evt_rejectedM2HexapodCorrection.next(
                flush=False, timeout=STD_TIMEOUT)
            self.assertEqual(corrM2Hex.x, 0)
            self.assertEqual(corrM2Hex.y, 0)
            self.assertEqual(corrM2Hex.z, 0)
            self.assertEqual(corrM2Hex.u, 0)
            self.assertEqual(corrM2Hex.v, 0)
            self.assertEqual(corrM2Hex.w, 0)

    async def testDo_processCalibrationProducts(self):
        async with Harness() as harness:

            await self._startCsc(harness)
            await harness.remote.cmd_processCalibrationProducts.set_start(
                timeout=STD_TIMEOUT, directoryPath="calibsDir")

    async def testDo_processIntraExtraWavefrontError(self):
        async with Harness() as harness:

            await self._startCsc(harness)
            # Set the timeout > 20 seconds for the long calculation time
            await harness.remote.cmd_processIntraExtraWavefrontError.set_start(
                timeout=2*STD_TIMEOUT, intraVisit=0, extraVisit=1,
                intraDirectoryPath="intraDir", extraDirectoryPath="extraDir",
                fieldRA=0.0, fieldDEC=0.0, filter=7, cameraRotation=0.0,
                userGain=1)

            await self._checkWepTopicsFromProcImg(harness)
            await self._checkOfcTopicsFromProcImg(harness)

    async def _checkWepTopicsFromProcImg(self, harness):

        warningWep = await harness.remote.evt_wepWarning.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertEqual(warningWep.warning, 0)

        numOfWfErr = len(harness.csc.getModel().getListOfWavefrontError())
        self.assertEqual(numOfWfErr, 9)

        for counter in range(numOfWfErr):
            wfErr = await harness.remote.evt_wavefrontError.next(
                flush=False, timeout=STD_TIMEOUT)
            self.assertNotEqual(wfErr.sensorId, 0)

            zk = wfErr.annularZernikePoly
            self.assertEqual(len(zk), 19)
            self.assertNotEqual(np.sum(np.abs(zk)), 0)

        numOfWfErrRej = len(harness.csc.getModel().getListOfWavefrontErrorRej())
        for counter in range(numOfWfErrRej):
            wfErr = await harness.remote.evt_rejectedWavefrontError.next(
                flush=False, timeout=STD_TIMEOUT)
            self.assertNotEqual(wfErr.sensorId, 0)

            zk = wfErr.annularZernikePoly
            self.assertEqual(len(zk), 19)
            self.assertNotEqual(np.sum(np.abs(zk)), 0)

        durationWep = await harness.remote.tel_wepDuration.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertGreater(durationWep.duration, 14)

    async def _checkOfcTopicsFromProcImg(self, harness):

        warningOfc = await harness.remote.evt_ofcWarning.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertEqual(warningOfc.warning, 0)

        dof = await harness.remote.evt_degreeOfFreedom.next(
            flush=False, timeout=STD_TIMEOUT)
        dofAggr = dof.aggregatedDoF
        dofVisit = dof.visitDoF
        self.assertEqual(len(dofAggr), 50)
        self.assertEqual(len(dofVisit), 50)
        self.assertNotEqual(np.sum(np.abs(dofAggr)), 0)
        self.assertNotEqual(np.sum(np.abs(dofVisit)), 0)

        await self._checkCorrNotZero(harness)

        durationOfc = await harness.remote.tel_ofcDuration.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertGreater(durationOfc.duration, 0)

    async def _checkCorrNotZero(self, harness):

        corrM2Hex = await harness.remote.evt_m2HexapodCorrection.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertNotEqual(corrM2Hex.x, 0)
        self.assertNotEqual(corrM2Hex.y, 0)
        self.assertNotEqual(corrM2Hex.z, 0)
        self.assertNotEqual(corrM2Hex.u, 0)
        self.assertNotEqual(corrM2Hex.v, 0)
        self.assertEqual(corrM2Hex.w, 0)

        corrCamHex = await harness.remote.evt_cameraHexapodCorrection.next(
            flush=False, timeout=STD_TIMEOUT)
        self.assertNotEqual(corrCamHex.x, 0)
        self.assertNotEqual(corrCamHex.y, 0)
        self.assertNotEqual(corrCamHex.z, 0)
        self.assertNotEqual(corrCamHex.u, 0)
        self.assertNotEqual(corrCamHex.v, 0)
        self.assertEqual(corrCamHex.w, 0)

        corrM1M3 = await harness.remote.evt_m1m3Correction.next(
            flush=False, timeout=STD_TIMEOUT)
        actForcesM1M3 = corrM1M3.zForces
        self.assertEqual(len(actForcesM1M3), 156)
        self.assertNotEqual(np.sum(np.abs(actForcesM1M3)), 0)

        corrM2 = await harness.remote.evt_m2Correction.next(
            flush=False, timeout=STD_TIMEOUT)
        actForcesM2 = corrM2.zForces
        self.assertEqual(len(actForcesM2), 72)
        self.assertNotEqual(np.sum(np.abs(actForcesM2)), 0)


if __name__ == "__main__":

    # Do the unit test
    asynctest.main()
