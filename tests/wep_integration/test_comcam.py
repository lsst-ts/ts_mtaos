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
import os
import unittest

import numpy as np
import pytest
import yaml
from lsst.daf import butler as dafButler
from lsst.ts import mtaos
from lsst.ts.ofc import OFCData
from lsst.ts.wep.utils import getModulePath as getModulePathWep
from lsst.ts.wep.utils import runProgram, writeCleanUpRepoCmd


@pytest.mark.integtest
class TestComCam(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataDir = mtaos.getModulePath().joinpath("tests", "tmp")
        cls.isrDir = cls.dataDir.joinpath("input")

        # Let the mtaos to set WEP based on this path variable
        os.environ["ISRDIRPATH"] = cls.isrDir.as_posix()

        ofc_data = OFCData("comcam")

        dof_state0 = yaml.safe_load(
            mtaos.getModulePath()
            .joinpath("tests", "testData", "state0inDof.yaml")
            .open()
            .read()
        )
        ofc_data.dof_state0 = dof_state0

        data_path = os.path.join(
            getModulePathWep(), "tests", "testData", "gen3TestRepo"
        )
        run_name = "run1"

        # Check that run doesn't already exist due to previous improper cleanup
        butler = dafButler.Butler(data_path)
        registry = butler.registry

        # This is the expected index of the maximum zernike coefficient.
        cls.zernike_coefficient_maximum_expected = {1, 2}

        if run_name in list(registry.queryCollections()):
            cleanUpCmd = writeCleanUpRepoCmd(data_path, run_name)
            runProgram(cleanUpCmd)

        cls.model = mtaos.Model(
            instrument=ofc_data.name,
            data_path=data_path,
            ofc_data=ofc_data,
            run_name=run_name,
            collections="refcats/gen2,LSSTCam/calib,LSSTCam/raw/all",
            pipeline_instrument=dict(comcam="lsst.obs.lsst.LsstCam"),
            data_instrument_name=dict(comcam="LSSTCam"),
            reference_detector=94,
        )

        cls.short_waittime = 1.0

    @classmethod
    def tearDownClass(cls):
        # Check that run doesn't already exist due to previous improper cleanup
        butler = dafButler.Butler(cls.model.data_path)

        if cls.model.run_name in list(butler.registry.queryCollections()):
            runProgram(writeCleanUpRepoCmd(cls.model.data_path, cls.model.run_name))

    async def test_process_comcam(self):
        await self.model.process_comcam(
            4021123106001,
            4021123106002,
            dict(),
        )

        self.assertEqual(self.model.wavefront_errors.getNumOfData(), 1)

        data = self.model.wavefront_errors.pop()

        # There is one element for each sensor, 2 sensors have data.
        self.assertEqual(len(data), 2)

        zk_avg = self.model.wavefront_errors.getListOfWavefrontErrorAvgInTakenData()

        # The sensors with data are 93 and 94
        self.assertTrue(93 in zk_avg)
        self.assertTrue(94 in zk_avg)

        # It is not possible to guaranteee here that the values of the zernike
        # coefficients will always be the same. Instead of trying to chase our
        # tails here, let's check that the returning arrays has the expected
        # dimensions and that the maximum absolute value of all zernike
        # coefficients is always the same.
        self.assertEqual(
            len(zk_avg[93]),
            len(self.model.ofc.ofc_data.zn3_idx),
            msg="Wrong size of zernike coefficients in sensor 93.",
        )
        self.assertTrue(
            np.argmax(np.abs(zk_avg[93])) in self.zernike_coefficient_maximum_expected
        )
        self.assertEqual(
            len(zk_avg[94]),
            len(self.model.ofc.ofc_data.zn3_idx),
            msg="Wrong size of zernike coefficients in sensor 94.",
        )
        self.assertTrue(
            np.argmax(np.abs(zk_avg[94])) in self.zernike_coefficient_maximum_expected
        )

    async def test_interrupt_wep_process(self):
        task = asyncio.create_task(
            self.model.process_comcam(
                4021123106001,
                4021123106002,
                dict(),
            )
        )

        await asyncio.sleep(self.short_waittime)

        await self.model.interrupt_wep_process()

        with self.assertRaises(RuntimeError):
            await task

    async def test_process_comcam_fail_if_ongoing(self):
        """If two process_comcam tasks are scheduled concurrently, one should
        fail.
        """
        with self.assertRaises(RuntimeError):
            await asyncio.gather(
                self.model.process_comcam(
                    4021123106001,
                    4021123106002,
                    dict(),
                ),
                self.model.process_comcam(
                    4021123106001,
                    4021123106002,
                    dict(),
                ),
            )

    async def test_wep_process_fail_bad_config(self):
        task = asyncio.create_task(
            self.model.process_comcam(
                4021123106001,
                4021123106002,
                dict(),
            )
        )

        with self.assertRaises(RuntimeError):
            await task


if __name__ == "__main__":
    unittest.main()
