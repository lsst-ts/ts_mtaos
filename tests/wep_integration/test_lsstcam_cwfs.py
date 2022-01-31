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
import yaml
import pytest
import logging
import unittest

from lsst.ts import MTAOS

from lsst.ts.ofc import OFCData

from lsst.daf import butler as dafButler

from lsst.ts.wep.Utility import writeCleanUpRepoCmd, runProgram
from lsst.ts.wep.Utility import getModulePath as getModulePathWep


@pytest.mark.integtest
class TestLsstCamCornerWavefrontSensor(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):

        cls.log = logging.getLogger(__name__)

        cls.dataDir = MTAOS.getModulePath().joinpath("tests", "tmp")
        cls.isrDir = cls.dataDir.joinpath("input")

        # Let the MTAOS to set WEP based on this path variable
        os.environ["ISRDIRPATH"] = cls.isrDir.as_posix()

        ofc_data = OFCData("lsst")

        dof_state0 = yaml.safe_load(
            MTAOS.getModulePath()
            .joinpath("tests", "testData", "state0inDof.yaml")
            .open()
            .read()
        )
        ofc_data.dof_state0 = dof_state0

        data_path = os.path.join(
            getModulePathWep(), "tests", "testData", "gen3TestRepo"
        )
        run_name = "run2"

        # Check that run doesn't already exist due to previous improper cleanup
        butler = dafButler.Butler(data_path)
        registry = butler.registry

        # This is the expected index of the maximum zernike coefficient.
        cls.zernike_coefficient_maximum_expected = {1, 2}

        if run_name in list(registry.queryCollections()):
            cleanUpCmd = writeCleanUpRepoCmd(data_path, run_name)
            runProgram(cleanUpCmd)

        cls.model = MTAOS.Model(
            instrument=ofc_data.name,
            data_path=data_path,
            ofc_data=ofc_data,
            run_name=run_name,
            collections="LSSTCam/calib/unbounded,LSSTCam/raw/all",
            reference_detector=94,
        )

        cls.short_waittime = 1.0

    @classmethod
    def tearDownClass(cls):
        # Check that run doesn't already exist due to previous improper cleanup
        butler = dafButler.Butler(cls.model.data_path)

        if cls.model.run_name in list(butler.registry.queryCollections()):
            runProgram(writeCleanUpRepoCmd(cls.model.data_path, cls.model.run_name))

    async def test_process_lsstcam_corner_wfs(self):

        await self.model.process_lsstcam_corner_wfs(
            visit_id=4021123106000,
            config={
                "tasks": {
                    "generateDonutCatalogWcsTask": {
                        "config": {"donutSelector.fluxField": "g_flux"}
                    }
                }
            },
        )

        self.assertEqual(self.model.wavefront_errors.getNumOfData(), 1)

        data = self.model.wavefront_errors.pop()

        # There should be at 4 sets of data, one for each corner wavefront
        # sensor.
        self.assertEqual(len(data), 4)

        zk_avg = self.model.wavefront_errors.getListOfWavefrontErrorAvgInTakenData()

        # The sensors with data are 191, 195, 199 and 203
        self.assertTrue(191 in zk_avg)
        self.assertTrue(195 in zk_avg)
        self.assertTrue(199 in zk_avg)
        self.assertTrue(203 in zk_avg)


if __name__ == "__main__":
    unittest.main()
