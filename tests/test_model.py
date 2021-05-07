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

from lsst.ts.ofc import OFC, OFCData
from lsst.ts.ofc.utils import CorrectionType

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

        ofc_data = OFCData("comcam")

        config = MTAOS.Config(str(settingFilePath))
        dof_state0 = yaml.safe_load(
            MTAOS.getModulePath()
            .joinpath("tests", "testData", "state0inDof.yaml")
            .open()
            .read()
        )
        ofc_data.dof_state0 = dof_state0

        cls.model = MTAOS.Model(config, ofc_data)

    def setUp(self):
        os.environ["ISRDIRPATH"] = self.isrDir.as_posix()
        self._makeDir(self.isrDir)

    def _makeDir(self, directory):

        Path(directory).mkdir(parents=True, exist_ok=True)

    def tearDown(self):

        self.model.reset_fwhm_data()
        self.model.reset_wfe_correction()

        shutil.rmtree(self.dataDir)
        try:
            os.environ.pop("ISRDIRPATH")
        except KeyError:
            pass

    def test_init(self):

        self.assertTrue(isinstance(self.model.ofc, OFC))
        self.assertEqual(self.model.ofc.ofc_data.name, "comcam")

    def test_user_gain(self):

        self.assertTrue(self.model.user_gain is not None)

        self.model.user_gain = 0.0
        self.assertEqual(self.model.user_gain, 0.0)

        self.model.user_gain = 0.5
        self.assertEqual(self.model.user_gain, 0.5)

        self.model.user_gain = 1.0
        self.assertEqual(self.model.user_gain, 1.0)

        with self.assertRaises(ValueError):
            self.model.user_gain = -0.1

        with self.assertRaises(ValueError):
            self.model.user_gain = 1.1

    def test_get_wfe(self):

        self.assertEqual(self.model.get_wfe(), [])

    def test_get_rejected_wfe(self):

        self.assertEqual(self.model.get_rejected_wfe(), [])

    def test_get_fwhm_sensors(self):

        self.assertEqual(self.model.get_fwhm_sensors(), [])

        self.model.set_fwhm_data(5, np.zeros(2))
        self.assertEqual(len(self.model.get_fwhm_sensors()), 1)
        self.assertEqual(self.model.get_fwhm_sensors()[0], 5)

    def test_set_fwhm_data(self):

        self.model.set_fwhm_data(1, np.zeros(2))

        fwhm_data = self.model.get_fwhm_data()
        self.assertEqual(len(fwhm_data), 1)

        self.model.set_fwhm_data(2, np.zeros(3))
        self.model.set_fwhm_data(3, np.zeros(4))

        fwhm_data = self.model.get_fwhm_data()
        self.assertEqual(len(fwhm_data), 3)

    def test_set_fwhm_data_repeat_sensor(self):

        self.model.set_fwhm_data(1, np.zeros(2))

        new_fwhm_values = np.array([1, 2, 3])
        self.model.set_fwhm_data(1, new_fwhm_values)

        fwhm_data = self.model.get_fwhm_data()

        self.assertEqual(len(fwhm_data), 1)

        fwhm_values_in_list = fwhm_data[0]
        self.assertTrue(np.all(fwhm_values_in_list == new_fwhm_values))

    def test_reset_fwhm_data(self):

        self.model.set_fwhm_data(1, np.zeros(2))
        self.model.reset_fwhm_data()

        fwhm_data = self.model.get_fwhm_data()
        self.assertEqual(len(fwhm_data), 0)

    def test_get_dof_aggr(self):

        self.assertEqual(len(self.model.get_dof_aggr()), 50)

    def test_get_dof(self):

        self.assertEqual(len(self.model.get_dof_lv()), 50)

    def test_add_correction(self):

        wavefront_erros = np.zeros(19)

        # Passing in zeros for wavefront_errors should return 0 in correction
        self.model.add_correction(wavefront_erros)

        x, y, z, u, v, w = self.model.m2_hexapod_correction()

        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(z, 0)
        self.assertEqual(u, 0)
        self.assertEqual(v, 0)
        self.assertEqual(w, 0)

        x, y, z, u, v, w = self.model.cam_hexapod_correction()
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(z, 0)
        self.assertEqual(u, 0)
        self.assertEqual(v, 0)
        self.assertEqual(w, 0)

        actCorr = self.model.m1m3_correction()
        self.assertListEqual(actCorr.tolist(), np.zeros_like(actCorr).tolist())

        actCorr = self.model.m2_correction()
        self.assertListEqual(actCorr.tolist(), np.zeros_like(actCorr).tolist())

        # Give 0.1 um of focus correction. All values must be close to zero
        # except z correction.

        wavefront_erros[0] = 0.1
        self.model.add_correction(wavefront_erros)

        x, y, z_m2hex, u, v, w = self.model.m2_hexapod_correction()

        self.assertAlmostEqual(x, 0, 3)
        self.assertAlmostEqual(y, 0, 3)
        self.assertAlmostEqual(u, 0, 3)
        self.assertAlmostEqual(v, 0, 3)
        self.assertAlmostEqual(w, 0, 3)

        x, y, z_camhex, u, v, w = self.model.cam_hexapod_correction()

        self.assertAlmostEqual(x, 0, 3)
        self.assertAlmostEqual(y, 0, 3)
        self.assertAlmostEqual(u, 0, 3)
        self.assertAlmostEqual(v, 0, 3)
        self.assertAlmostEqual(w, 0, 3)

        # Expected total hexapod offset
        self.assertAlmostEqual(z_m2hex + z_camhex, 4.16211, 3)

        actCorr = self.model.m1m3_correction()
        self.assertTrue(
            np.allclose(actCorr, np.zeros_like(actCorr), rtol=0.1, atol=0.1),
            f"{actCorr} not almost close to 0.",
        )

        actCorr = self.model.m2_correction()
        self.assertTrue(
            np.allclose(actCorr, np.zeros_like(actCorr), rtol=0.1, atol=0.1),
            f"{actCorr} not almost close to 0.",
        )

    def test_m2_hexapod_correction(self):

        x, y, z, u, v, w = self.model.m2_hexapod_correction()
        self.assertEqual(
            self.model.m2_hexapod_correction.correction_type, CorrectionType.POSITION
        )
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(z, 0)
        self.assertEqual(u, 0)
        self.assertEqual(v, 0)
        self.assertEqual(w, 0)

    def test_cam_hexapod_correction(self):

        self.assertEqual(
            self.model.cam_hexapod_correction.correction_type, CorrectionType.POSITION
        )
        x, y, z, u, v, w = self.model.cam_hexapod_correction()
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)
        self.assertEqual(z, 0)
        self.assertEqual(u, 0)
        self.assertEqual(v, 0)
        self.assertEqual(w, 0)

    def test_m1m3_correction(self):

        self.assertEqual(
            self.model.m1m3_correction.correction_type, CorrectionType.FORCE
        )
        self.assertEqual(len(self.model.m1m3_correction()), 156)

    def test_m2_correction(self):

        self.assertEqual(self.model.m2_correction.correction_type, CorrectionType.FORCE)
        self.assertEqual(len(self.model.m2_correction()), 72)

    def test_reset_wfe_correction(self):

        data = [1, 2, 3]
        self.model.wavefront_errors.append(data)
        self.model.rejected_wavefront_errors.append(data)

        self.model.reset_wfe_correction()

        self.assertEqual(self.model.get_wfe(), [])
        self.assertEqual(self.model.get_rejected_wfe(), [])

    def test_reject_unreasonable_wfe(self):

        self.assertEqual(self.model.reject_unreasonable_wfe([]), [])


if __name__ == "__main__":

    # Do the unit test
    unittest.main()
