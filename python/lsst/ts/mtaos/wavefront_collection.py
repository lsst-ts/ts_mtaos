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

__all__ = ["WavefrontCollection"]

from collections import deque

import numpy as np


class WavefrontCollection(object):
    def __init__(self, maxLeng):
        """Collection of list of wavefront sensor data.

        Parameters
        ----------
        maxLeng : `int`
            Maximum length of collection.
        """

        # Collection of list of wavefront error data
        self._collectionData = deque(maxlen=int(maxLeng))

        # Collection of taken data of list of wavefront error data.
        # This is designed for the MtaosCsc to publish the event of wavefront
        # error. The published data will be in this collection.
        # This is a list of tuples with (sensor_id, np.ndarray)
        self._collectionDataTaken = dict()
        # Number of data taken from collectionData into collectionDataTaken
        self._numDataTaken = 0

    def getNumOfData(self):
        """Get the number of data.

        Returns
        -------
        `int`
            Number of data.
        """

        return len(self._collectionData)

    def getNumOfDataTaken(self):
        """Get the number of taken data.

        Returns
        -------
        `int`
            Number of taken data.
        """

        return self._numDataTaken

    def append(self, listOfWfErr):
        """Add the list of wavefront error data to collection.

        Parameters
        ----------
        listOfWfErr : `list` of `tuple` with [`int`, `np.ndarray`]
            List of wavefront error data. Each element contains tuple which the
            first elements specify the sensor id and the second is an array
            with the zernike coeffients.
        """

        self._collectionData.append(listOfWfErr)

    def pop(self):
        """Pop the list of wavefront error data from collection.

        Returns
        -------
        listOfWfErr : `tuple` with [`int`, `np.ndarray`]
            List of wavefront error data.
        """

        try:
            data = self._collectionData.popleft()
            for sensor_id, zk in data:
                if sensor_id in self._collectionDataTaken:
                    self._collectionDataTaken[sensor_id] = np.vstack(
                        (self._collectionDataTaken[sensor_id], zk)
                    )
                else:
                    self._collectionDataTaken[sensor_id] = np.array(zk, ndmin=2)
            self._numDataTaken += 1
        except IndexError:
            data = []

        return data

    def clear(self):
        """Clear the collection."""

        self._collectionData.clear()
        self._collectionDataTaken = dict()
        self._numDataTaken = 0

    def getListOfWavefrontErrorAvgInTakenData(self):
        """Get the list of average wavefront error in taken data.

        Returns
        -------
        wfe_avg : `dict`
            Dictionary with average wavefront errors for each sensor.

        Raises
        ------
        RuntimeError
            No data in the collection of taken data.
        """

        # Check there is the wavefront error data in collection or not
        if len(self._collectionDataTaken) == 0:
            raise RuntimeError("No data in the collection of taken data.")

        wfe_avg = dict(
            [
                (
                    sensor_id,
                    np.mean(np.array(self._collectionDataTaken[sensor_id]), axis=0),
                )
                for sensor_id in self._collectionDataTaken
            ]
        )

        self._collectionDataTaken = dict()
        self._numDataTaken = 0

        return wfe_avg


if __name__ == "__main__":
    pass
