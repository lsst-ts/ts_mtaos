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

import time
import numpy as np

from lsst.ts.MTAOS.Model import Model

from lsst.ts.wep.ctrlIntf.WEPCalculationOfComCam import WEPCalculationOfComCam
from lsst.ts.wep.ctrlIntf.SensorWavefrontData import SensorWavefrontData
from lsst.ts.wep.Utility import FilterType


class ModelSim(Model):
    """Simulation Model class"""

    def procCalibProducts(self, calibsDir):
        """Process new calibration products.

        Parameters
        ----------
        calibsDir : str
            Calibration products directory.
        """

        # Fake the ingestion time
        time.sleep(3)

    def procIntraExtraWavefrontError(self, raInDeg, decInDeg, aFilter,
                                     rotAngInDeg, priVisit, priDir, secVisit,
                                     secDir, userGain):
        """Process the intra- and extra-focal wavefront error.

        Parameters
        ----------
        raInDeg : float
            Right ascension in degree. The value should be in (0, 360).
        decInDeg : float
            Declination in degree. The value should be in (-90, 90).
        aFilter : int
            Filter used while collecting the images (1: u, 2: g, 3: r, 4: i,
            5: z, 6: y, 7: ref).
        rotAngInDeg : float
            The camera rotation angle in degree (-90 to 90).
        priVisit : int
            Primary visit number (intra-focal visit number).
        priDir : str
            Primary directory of image data (intra-focal images).
        secVisit : int
            Secondary visit number (extra-focal visit number).
        secDir : str
            Secondary directory of image data (extra-focal images).
        userGain : float
            The gain requested by the user. A value of -1 means don't use user
            gain.
        """

        # Simulate WEP and record time
        self.calcTimeWep.evalCalcTimeAndPutRecord(self._fakeWavefrontError)

        # Do OFC and record time
        filterType = FilterType(aFilter)
        self.calcTimeOfc.evalCalcTimeAndPutRecord(
            self._calcCorrection, filterType, rotAngInDeg, userGain)

    def _fakeWavefrontError(self):
        """Fake the wavefront error.

        Raises
        ------
        NotImplementedError
            Only ComCam is supported at this moment.
        """

        # Assign the sensor Id
        # Sensor Id is defined in sensorNameToId.yaml of ts_wep module
        if isinstance(self.wep, WEPCalculationOfComCam):
            sensorIdList = range(96, 105)
        else:
            raise NotImplementedError("Only ComCam is supported at this moment.")

        # Fake the calculation time
        time.sleep(14)

        listOfWfErr = []
        for sensorId in sensorIdList:
            sensorWavefrontData = SensorWavefrontData()
            sensorWavefrontData.setSensorId(sensorId)

            avgErrInUm = np.random.rand(19) * 1e-2
            sensorWavefrontData.setAnnularZernikePoly(avgErrInUm)

            listOfWfErr.append(sensorWavefrontData)

        # Keep this function here for the future's test of rejection of WEP
        self._rejWavefrontErrorUnreasonable(listOfWfErr)


if __name__ == "__main__":
    pass
