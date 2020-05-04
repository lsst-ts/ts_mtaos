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

__all__ = ["CollOfListOfWfErr"]

import numpy as np
from collections import deque


class CollOfListOfWfErr(object):

    def __init__(self, maxLeng):
        """Collection of list of wavefront sensor data.

        Parameters
        ----------
        maxLeng : int
            Maximum length of collection.
        """

        # Collection of list of wavefront error data
        self._collectionData = deque(maxlen=int(maxLeng))

        # Collection of taken data of list of wavefront error data
        # This is designed for the MtaosCsc to publish the event of wavefront
        # error. The published data will be in this collection.
        self._collectionDataTaken = []

    def getNumOfData(self):
        """Get the number of data.

        Returns
        -------
        int
            Number of data.
        """

        return len(self._collectionData)

    def getNumOfDataTaken(self):
        """Get the number of taken data.

        Returns
        -------
        int
            Number of taken data.
        """

        return len(self._collectionDataTaken)

    def append(self, listOfWfErr):
        """Add the list of wavefront error data to collection.

        Parameters
        ----------
        listOfWfErr : list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of wavefront error data.
        """

        self._collectionData.append(listOfWfErr)

    def pop(self):
        """Pop the list of wavefront error data from collection.

        Returns
        -------
        listOfWfErr : list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of wavefront error data.
        """

        try:
            data = self._collectionData.popleft()
            self._collectionDataTaken.append(data)
        except IndexError:
            data = []

        return data

    def clear(self):
        """Clear the collection."""

        self._collectionData.clear()
        self._collectionDataTaken = []

    def getListOfWavefrontErrorAvgInTakenData(self):
        """Get the list of average wavefront error in taken data.

        Returns
        -------
        list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of average wavefront error data.

        Raises
        ------
        RuntimeError
            No data in the collection of taken data.
        """

        # Check there is the wavefront error data in collection or not
        numOfElements = len(self._collectionDataTaken)
        if (numOfElements == 0):
            raise RuntimeError("No data in the collection of taken data.")

        # Do the average of wavefont error
        listOfWfErrAvg = self._collectionDataTaken.pop()

        for wfErr in listOfWfErrAvg:
            zk = wfErr.getAnnularZernikePoly()
            wfErr.setAnnularZernikePoly(zk/numOfElements)

        idxWfErrMiss = []
        while self._collectionDataTaken:

            listOfWfErrNext = self._collectionDataTaken.pop()
            for idx, wfErr in enumerate(listOfWfErrAvg):
                sensorId = wfErr.getSensorId()
                wfErrNext = self._getSensorWavefrontDataInList(listOfWfErrNext,
                                                               sensorId)

                if (wfErrNext is not None):
                    zk = wfErr.getAnnularZernikePoly()
                    zkNext = wfErrNext.getAnnularZernikePoly()
                    wfErr.setAnnularZernikePoly(zk + zkNext/numOfElements)
                else:
                    # Collect the index of wavefront error data if there is the
                    # data missing
                    idxWfErrMiss.append(idx)

        # Get the unique list of index of wavefront error data that has the
        # missing data.
        idxWfErrMissUnique = np.unique(np.array(idxWfErrMiss)).tolist()

        # Only return the value that is not in the above list
        return [listOfWfErrAvg[idx] for idx in range(len(listOfWfErrAvg))
                if idx not in idxWfErrMissUnique]

    def _getSensorWavefrontDataInList(self, listOfWfErr, sensorId):
        """Get the sensor wavefront data in the list.

        Parameters
        ----------
        listOfWfErr : list[lsst.ts.wep.ctrlIntf.SensorWavefrontData]
            List of wavefront error data.
        sensorId : int
            Sensor Id.

        Returns
        -------
        lsst.ts.wep.ctrlIntf.SensorWavefrontData
            Sensor wavefront data. Return None if not find.
        """

        for wfErr in listOfWfErr:
            if wfErr.getSensorId() == sensorId:
                return wfErr
            else:
                continue

        # Return None if not find
        return None


if __name__ == "__main__":
    pass
