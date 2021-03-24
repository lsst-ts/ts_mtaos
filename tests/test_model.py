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
from pathlib import Path
import shutil
import unittest
import numpy as np
import yaml

from lsst.ts.ofc.ctrlIntf.OFCCalculationOfComCam import OFCCalculationOfComCam
from lsst.ts.ofc.ctrlIntf.M1M3Correction import M1M3Correction
from lsst.ts.ofc.ctrlIntf.M2Correction import M2Correction

from lsst.ts import MTAOS


class TestModel(unittest.TestCase):
    """Test the Model class."""

    @classmethod
    def setUpClass(cls):

        cls.dataDir = MTAOS.getModulePath().joinpath("tests", "tmp")
        cls.isrDir = cls.dataDir.joinpath("input")

        # Let the MTAOS to set WEP based on this path variable
        os.environ["ISRDIRPATH"] = cls.isrDir.as_posix()

        settingFilePath = MTAOS.getModulePath().joinpath(
            "tests", "testData", "default.yaml"
        )
        config = MTAOS.Config(str(settingFilePath))
        state0Dof = yaml.safe_load(
            MTAOS.getModulePath()
            .joinpath("tests", "testData", "state0inDof.yaml")
            .open()
            .read()
        )
        cls.model = MTAOS.Model(config, state0Dof)

    def setUp(self):
        os.environ["ISRDIRPATH"] = self.isrDir.as_posix()
        self._makeDir(self.isrDir)

    def _makeDir(self, directory):

        Path(directory).mkdir(parents=True, exist_ok=True)

    def tearDown(self):

        self.model.resetFWHMSensorData()
        self.model.resetWavefrontCorrection()

        shutil.rmtree(self.dataDir)
        try:
            os.environ.pop("ISRDIRPATH")
        except KeyError:
            pass

    def testInitOfModelMTAOS(self):

        ofc = self.model.ofc
        self.assertTrue(isinstance(ofc, OFCCalculationOfComCam))

    def testGetListOfWavefrontError(self):

        self.assertEqual(self.model.getListOfWavefrontError(), [])

    def testGetListOfWavefrontErrorRej(self):

        self.assertEqual(self.model.getListOfWavefrontErrorRej(), [])

    def testGetListOfFWHMSensorData(self):

        self.assertEqual(self.model.getListOfFWHMSensorData(), [])

    def testSetFWHMSensorData(self):

        self.model.setFWHMSensorData(1, np.zeros(2))

        listOfFWHMSensorData = self.model.getListOfFWHMSensorData()
        self.assertEqual(len(listOfFWHMSensorData), 1)

        self.model.setFWHMSensorData(2, np.zeros(2))
        self.assertEqual(len(listOfFWHMSensorData), 2)

    def testSetFWHMSensorDataRepeatSensorId(self):

        self.model.setFWHMSensorData(1, np.zeros(2))

        newFwhmValues = np.array([1, 2, 3])
        self.model.setFWHMSensorData(1, newFwhmValues)

        listOfFWHMSensorData = self.model.getListOfFWHMSensorData()
        self.assertEqual(len(listOfFWHMSensorData), 1)

        fwhmValuesInList = listOfFWHMSensorData[0].getFwhmValues()
        self.assertTrue((fwhmValuesInList == newFwhmValues).all())

    def testResetFWHMSensorData(self):

        self.model.setFWHMSensorData(1, np.zeros(2))
        self.model.resetFWHMSensorData()

        listOfFWHMSensorData = self.model.getListOfFWHMSensorData()
        self.assertEqual(listOfFWHMSensorData, [])

    def testGetDofAggr(self):

        dofAggr = self._getDofAggr()
        self.assertEqual(len(dofAggr), 50)

    def _getDofAggr(self):

        return self.model.getDofAggr()

    def testGetDofVisit(self):

        dofVisit = self._getDofVisit()
        self.assertEqual(len(dofVisit), 50)

    def _getDofVisit(self):

        return self.model.getDofVisit()

    def test_add_correction(self):

        wavefront_erros = np.zeros(19)

        # Passing in zeros for wavefront_errors should return 0 in correction
        self.model.add_correction(wavefront_erros)

        x, y, z, u, v, w = self.model.getM2HexCorr()

        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(z, 0)
        self.assertEqual(u, 0)
        self.assertEqual(v, 0)
        self.assertEqual(w, 0)

        x, y, z, u, v, w = self.model.getCamHexCorr()
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(z, 0)
        self.assertEqual(u, 0)
        self.assertEqual(v, 0)
        self.assertEqual(w, 0)

        actCorr = self.model.getM1M3ActCorr()
        self.assertListEqual(actCorr.tolist(), np.zeros_like(actCorr).tolist())

        actCorr = self.model.getM2ActCorr()
        self.assertListEqual(actCorr.tolist(), np.zeros_like(actCorr).tolist())

        # Give 0.1 um of focus correction. All values must be close to zero
        # except z correction.

        wavefront_erros[0] = 0.1
        self.model.add_correction(wavefront_erros)

        x, y, z_m2hex, u, v, w = self.model.getM2HexCorr()

        self.assertAlmostEqual(x, 0, 3)
        self.assertAlmostEqual(y, 0, 3)
        self.assertAlmostEqual(u, 0, 3)
        self.assertAlmostEqual(v, 0, 3)
        self.assertAlmostEqual(w, 0, 3)

        x, y, z_camhex, u, v, w = self.model.getCamHexCorr()

        self.assertAlmostEqual(x, 0, 3)
        self.assertAlmostEqual(y, 0, 3)
        self.assertAlmostEqual(u, 0, 3)
        self.assertAlmostEqual(v, 0, 3)
        self.assertAlmostEqual(w, 0, 3)

        # Expected total hexapod offset
        self.assertAlmostEqual(z_m2hex + z_camhex, 4.16211, 3)

        actCorr = self.model.getM1M3ActCorr()
        self.assertTrue(
            np.allclose(actCorr, np.zeros_like(actCorr), rtol=0.1, atol=0.1),
            f"{actCorr} not almost close to 0.",
        )

        actCorr = self.model.getM2ActCorr()
        self.assertTrue(
            np.allclose(actCorr, np.zeros_like(actCorr), rtol=0.1, atol=0.1),
            f"{actCorr} not almost close to 0.",
        )

    def testGetM2HexCorr(self):

        x, y, z, u, v, w = self.model.getM2HexCorr()
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(z, 0)
        self.assertEqual(u, 0)
        self.assertEqual(v, 0)
        self.assertEqual(w, 0)

    def testGetCamHexCorr(self):

        x, y, z, u, v, w = self.model.getCamHexCorr()
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(z, 0)
        self.assertEqual(u, 0)
        self.assertEqual(v, 0)
        self.assertEqual(w, 0)

    def testGetM1M3ActCorr(self):

        actCorr = self.model.getM1M3ActCorr()
        self.assertEqual(len(actCorr), M1M3Correction.NUM_OF_ACT)

    def testGetM2ActCorr(self):

        actCorr = self.model.getM2ActCorr()
        self.assertEqual(len(actCorr), M2Correction.NUM_OF_ACT)

    def testResetWavefrontCorrection(self):

        data = [1, 2, 3]
        self.model.wavefront_errors.append(data)
        self.model.rejected_wavefront_errors.append(data)

        self.model.resetWavefrontCorrection()

        self._checkWfsErrAndWfsErrRejClear()

    def _checkWfsErrAndWfsErrRejClear(self):

        self.assertEqual(self.model.getListOfWavefrontError(), [])
        self.assertEqual(self.model.getListOfWavefrontErrorRej(), [])

    def testRejWavefrontErrorUnreasonable(self):

        self.assertEqual(self.model.rejWavefrontErrorUnreasonable([]), [])


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
