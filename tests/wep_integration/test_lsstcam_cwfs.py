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
import unittest
from pathlib import Path

import pytest
import yaml

from lsst.daf import butler as dafButler
from lsst.ts import mtaos
from lsst.ts.ofc import OFCData
from lsst.ts.wep.utils import getModulePath as getModulePathWep
from lsst.ts.wep.utils import runProgram, writeCleanUpRepoCmd


@pytest.mark.integtest
class TestLsstCamCornerWavefrontSensor(unittest.IsolatedAsyncioTestCase):
    dataDir: Path
    isrDir: Path
    model: mtaos.Model
    short_waittime: float
    zernike_coefficient_maximum_expected: set[int]

    @classmethod
    def setUpClass(cls) -> None:
        cls.dataDir = mtaos.getModulePath().joinpath("tests", "tmp")
        cls.isrDir = cls.dataDir.joinpath("input")

        # Let the mtaos to set WEP based on this path variable
        os.environ["ISRDIRPATH"] = cls.isrDir.as_posix()

        ofc_data = OFCData("lsstfam")

        dof_state0 = yaml.safe_load(
            mtaos.getModulePath().joinpath("tests", "testData", "state0inDof.yaml").open().read()
        )
        ofc_data.dof_state0 = dof_state0

        data_path = os.path.join(getModulePathWep(), "tests", "testData", "gen3TestRepo")
        run_name = "run2"

        # Check that run doesn't already exist due to previous improper cleanup
        butler = dafButler.Butler(data_path)  # type: ignore
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
            collections="refcats/gen2,LSSTCam/calib,LSSTCam/raw/all,LSSTCam/aos/intrinsic",
            reference_detector=94,
        )

        cls.short_waittime = 1.0

    def setUp(self) -> None:
        self.model = self.__class__.model

        self.model.set_visit_ids(
            intra_id=4021123106000,
            extra_id=None,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        # Check that run doesn't already exist due to previous improper cleanup
        butler = dafButler.Butler(cls.model.data_path)  # type: ignore

        if cls.model.run_name in list(butler.registry.queryCollections()):
            runProgram(writeCleanUpRepoCmd(cls.model.data_path, cls.model.run_name))

    async def test_process_lsstcam_corner_wfs(self) -> None:
        await self.model.process_lsstcam_corner_wfs(
            config=dict(),
        )

        self.assertEqual(self.model.wavefront_errors.getNumOfData(), 1)

        data = self.model.wavefront_errors.pop()

        # There should be at 4 sets of data, one for each corner wavefront
        # sensor.
        self.assertEqual(len(data), 1)

        zk_avg = self.model.wavefront_errors.getListOfWavefrontErrorAvgInTakenData()

        # The sensors with data are 191, 195, 199 and 203
        self.assertTrue(191 in zk_avg)


if __name__ == "__main__":
    unittest.main()
