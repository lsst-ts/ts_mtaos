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
import shutil
import unittest
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import yaml
from lsst.afw.image import VisitInfo
from lsst.geom import SpherePoint, degrees
from lsst.ts import mtaos
from lsst.ts.ofc import OFC, OFCData
from lsst.ts.ofc.utils import CorrectionType

# A short wait time in seconds
SHORT_WAIT_TIME = 1.0


class TestModel(unittest.IsolatedAsyncioTestCase):
    """Test the Model class."""

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

        cls.model = mtaos.Model(
            instrument=ofc_data.name, data_path=None, ofc_data=ofc_data
        )

        # patch _get_visit_info for unit testing
        cls.model._get_visit_info = Mock(side_effect=cls._get_visit_info_mock)

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

    @staticmethod
    def _get_visit_info_mock(instrument: str, exposure: int) -> VisitInfo:
        """Mock the _get_visit_info method from mtaos Model class.

        Parameters
        ----------
        instrument : `str`
            Name of the instrument.
        exposure : `int`
            exposure id of data to retrieve information from.

        Returns
        -------
        `VisitInfo`
            Object with information about a single exposure of an imaging
            camera.
        """
        return VisitInfo(
            exposureId=exposure,
            instrumentLabel=instrument,
            boresightRaDec=SpherePoint(
                0.0 * degrees,
                -80.0 * degrees,
            ),
            boresightRotAngle=45.0 * degrees,
        )

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

    def test_generate_wep_configuration(self):
        wep_configuration = self.model.generate_wep_configuration(
            instrument="comcam",
            config=dict(),
        )

        expected_donut_catalog_wcs_config = dict()

        expected_isr_config = {
            "connections.outputExposure": "postISRCCD",
            "doBias": False,
            "doVariance": False,
            "doLinearize": False,
            "doCrosstalk": False,
            "doDefect": False,
            "doNanMasking": False,
            "doInterpolate": False,
            "doBrighterFatter": False,
            "doDark": False,
            "doFlat": False,
            "doApplyGains": True,
            "doFringe": False,
            "doOverscan": True,
        }
        expected_zernike_science_sensor_config = {
            "donutTemplateSize": 160,
            "donutStampSize": 160,
            "initialCutoutPadding": 40,
        }

        self.assert_wep_configuration(
            wep_configuration=wep_configuration,
            expected_donut_catalog_wcs_task_config=expected_donut_catalog_wcs_config,
            expected_isr_config=expected_isr_config,
            expected_zernike_science_sensor_config=expected_zernike_science_sensor_config,
        )

    def test_generate_wep_configuration_custom_donut_catalog_online(self):
        wep_configuration = self.model.generate_wep_configuration(
            instrument="comcam",
            config=dict(
                tasks=dict(
                    generateDonutCatalogWcsTask=dict(
                        config={
                            "filterName": "g",
                            "connections.refCatalogs": "cal_ref_cat",
                        }
                    )
                )
            ),
        )

        expected_donut_catalog_cwfs_config = dict(
            filterName="g",
        )
        expected_donut_catalog_cwfs_config["connections.refCatalogs"] = "cal_ref_cat"

        expected_isr_config = {
            "connections.outputExposure": "postISRCCD",
            "doBias": False,
            "doVariance": False,
            "doLinearize": False,
            "doCrosstalk": False,
            "doDefect": False,
            "doNanMasking": False,
            "doInterpolate": False,
            "doBrighterFatter": False,
            "doDark": False,
            "doFlat": False,
            "doApplyGains": True,
            "doFringe": False,
            "doOverscan": True,
        }

        expected_zernike_science_sensor_config = {
            "donutTemplateSize": 160,
            "donutStampSize": 160,
            "initialCutoutPadding": 40,
        }

        self.assert_wep_configuration(
            wep_configuration=wep_configuration,
            expected_donut_catalog_wcs_task_config=expected_donut_catalog_cwfs_config,
            expected_isr_config=expected_isr_config,
            expected_zernike_science_sensor_config=expected_zernike_science_sensor_config,
        )

    def test_generate_wep_configuration_custom_isr(self):
        wep_configuration = self.model.generate_wep_configuration(
            instrument="comcam",
            config=dict(
                tasks=dict(
                    isr=dict(
                        config=dict(
                            doBias=True,
                            doDefect=True,
                        )
                    )
                )
            ),
        )

        expected_donut_catalog_cwfs_config = dict()
        expected_isr_config = {
            "connections.outputExposure": "postISRCCD",
            "doBias": True,
            "doVariance": False,
            "doLinearize": False,
            "doCrosstalk": False,
            "doDefect": True,
            "doNanMasking": False,
            "doInterpolate": False,
            "doBrighterFatter": False,
            "doDark": False,
            "doFlat": False,
            "doApplyGains": True,
            "doFringe": False,
            "doOverscan": True,
        }
        expected_zernike_science_sensor_config = {
            "donutTemplateSize": 160,
            "donutStampSize": 160,
            "initialCutoutPadding": 40,
        }

        self.assert_wep_configuration(
            wep_configuration=wep_configuration,
            expected_donut_catalog_wcs_task_config=expected_donut_catalog_cwfs_config,
            expected_isr_config=expected_isr_config,
            expected_zernike_science_sensor_config=expected_zernike_science_sensor_config,
        )

    def test_generate_wep_configuration_custom_zernike_science_sensor(self):
        wep_configuration = self.model.generate_wep_configuration(
            instrument="comcam",
            config=dict(
                tasks=dict(
                    CutOutDonutsScienceSensorTask=dict(
                        config=dict(
                            initialCutoutPadding=80,
                        )
                    )
                )
            ),
        )

        expected_donut_catalog_cwfs_config = dict()
        expected_isr_config = {
            "connections.outputExposure": "postISRCCD",
            "doBias": False,
            "doVariance": False,
            "doLinearize": False,
            "doCrosstalk": False,
            "doDefect": False,
            "doNanMasking": False,
            "doInterpolate": False,
            "doBrighterFatter": False,
            "doDark": False,
            "doFlat": False,
            "doApplyGains": True,
            "doFringe": False,
            "doOverscan": True,
        }
        expected_zernike_science_sensor_config = {
            "donutTemplateSize": 160,
            "donutStampSize": 160,
            "initialCutoutPadding": 80,
        }

        self.assert_wep_configuration(
            wep_configuration=wep_configuration,
            expected_donut_catalog_wcs_task_config=expected_donut_catalog_cwfs_config,
            expected_isr_config=expected_isr_config,
            expected_zernike_science_sensor_config=expected_zernike_science_sensor_config,
        )

    def assert_wep_configuration(
        self,
        wep_configuration,
        expected_donut_catalog_wcs_task_config,
        expected_isr_config,
        expected_zernike_science_sensor_config,
    ):
        assert "tasks" in wep_configuration

        self.assert_generate_donut_catalog_wcs_task_config(
            wep_configuration, expected_donut_catalog_wcs_task_config
        )

        self.assert_isr_config(wep_configuration, expected_isr_config)

        self.assert_estimate_zernikes_science_sensor_task(
            wep_configuration, expected_zernike_science_sensor_config
        )

    def assert_generate_donut_catalog_wcs_task_config(
        self, wep_configuration, expected_donut_catalog_wcs_task_config
    ):
        assert "generateDonutCatalogWcsTask" in wep_configuration["tasks"]
        if len(expected_donut_catalog_wcs_task_config) > 0:
            assert "config" in wep_configuration["tasks"]["generateDonutCatalogWcsTask"]
            for config in expected_donut_catalog_wcs_task_config:
                assert (
                    config
                    in wep_configuration["tasks"]["generateDonutCatalogWcsTask"][
                        "config"
                    ]
                )

                assert (
                    wep_configuration["tasks"]["generateDonutCatalogWcsTask"]["config"][
                        config
                    ]
                    == expected_donut_catalog_wcs_task_config[config]
                )

    def assert_isr_config(self, wep_configuration, expected_isr_config):
        assert "isr" in wep_configuration["tasks"]
        assert "config" in wep_configuration["tasks"]["isr"]
        for config in set(
            (
                "connections.outputExposure",
                "doBias",
                "doVariance",
                "doLinearize",
                "doCrosstalk",
                "doDefect",
                "doNanMasking",
                "doInterpolate",
                "doBrighterFatter",
                "doDark",
                "doFlat",
                "doApplyGains",
                "doFringe",
                "doOverscan",
            )
        ).union(expected_isr_config.keys()):
            assert config in wep_configuration["tasks"]["isr"]["config"]

            assert (
                wep_configuration["tasks"]["isr"]["config"][config]
                == expected_isr_config[config]
            ), f"Expected {config}"

    def assert_estimate_zernikes_science_sensor_task(
        self, wep_configuration, expected_zernike_science_sensor_config
    ):
        assert "CutOutDonutsScienceSensorTask" in wep_configuration["tasks"]
        assert "calcZernikesTask" in wep_configuration["tasks"]
        assert "config" in wep_configuration["tasks"]["CutOutDonutsScienceSensorTask"]
        for config in set(
            ("donutTemplateSize", "donutStampSize", "initialCutoutPadding")
        ).union(expected_zernike_science_sensor_config):
            assert (
                config
                in wep_configuration["tasks"]["CutOutDonutsScienceSensorTask"]["config"]
            )

            assert (
                wep_configuration["tasks"]["CutOutDonutsScienceSensorTask"]["config"][
                    config
                ]
                == expected_zernike_science_sensor_config[config]
            )

    async def test_log_stream(self):
        task = await asyncio.create_subprocess_shell(
            f"echo THIS IS A TEST; sleep {SHORT_WAIT_TIME};echo THIS IS A TEST",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        with self.assertLogs("Model", level="DEBUG") as model_log:
            log_task = asyncio.create_task(self.model.log_stream(task.stdout))

            await asyncio.wait_for(
                log_task,
                timeout=SHORT_WAIT_TIME * 2.0,
            )

            self.assertEqual(
                model_log.output,
                [
                    "DEBUG:Model:THIS IS A TEST",
                    "DEBUG:Model:THIS IS A TEST",
                ],
            )


if __name__ == "__main__":
    # Do the unit test
    unittest.main()
