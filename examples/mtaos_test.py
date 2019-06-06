# This file is part of MTAOS.
#
# Developed for the LSST.
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
import asyncio
import time

from lsst.ts.wep.Utility import runProgram
from lsst.ts.MTAOS.Utility import getModulePath, getIsrDirPath

from lsst.ts import salobj
import SALPY_MTAOS

# Notes:
# Filters:
#   U = 1
#   G = 2
#   R = 3
#   I = 4
#   Z = 5
#   Y = 6
#   REF = 7


def main():

    mtaos = salobj.Remote(SALPY_MTAOS, index=0)
    mtaos.salinfo.manager.setDebugLevel(0)

    mtaos.evt_wavefrontError.flush()
    mtaos.evt_degreeOfFreedom.flush()
    mtaos.evt_m1m3Correction.flush()
    mtaos.evt_m2Correction.flush()
    mtaos.evt_cameraHexapodCorrection.flush()
    mtaos.evt_m2HexapodCorrection.flush()

    data = mtaos.cmd_resetWavefrontCorrection.DataType()
    data.value = False
    asyncio.get_event_loop().run_until_complete(
        mtaos.cmd_resetWavefrontCorrection.start(data, timeout=1.0))

    time.sleep(0.5)

    # wavefrontError = mtaos.evt_wavefrontError.get()
    # sensorId
    # annularZernikePoly

    degreeOfFreedom = mtaos.evt_degreeOfFreedom.get()
    print("MTAOS_logevent_degreeOfFreedom")
    for idx in range(50):
        print(f"\taggregatedDoF[{idx}] ({degreeOfFreedom.aggregatedDoF[idx]})")
    for idx in range(50):
        print(f"\tvisitDoF[{idx}] ({degreeOfFreedom.visitDoF[idx]})")

    m1m3Correction = mtaos.evt_m1m3Correction.get()
    print("MTAOS_logevent_m1m3Correction")
    for idx in range(156):
        print(f"\tzForces[{idx}] ({m1m3Correction.zForces[idx]})")

    m2Correction = mtaos.evt_m2Correction.get()
    print("MTAOS_logevent_m2Correction")
    for idx in range(72):
        print(f"\tzForces[{idx}] ({m2Correction.zForces[idx]})")

    cameraHexapodCorrection = mtaos.evt_cameraHexapodCorrection.get()
    print("MTAOS_logevent_cameraHexapodCorrection")
    print(f"\tx ({cameraHexapodCorrection.x})")
    print(f"\ty ({cameraHexapodCorrection.y})")
    print(f"\tz ({cameraHexapodCorrection.z})")
    print(f"\tu ({cameraHexapodCorrection.u})")
    print(f"\tv ({cameraHexapodCorrection.v})")
    print(f"\tw ({cameraHexapodCorrection.w})")

    m2HexapodCorrection = mtaos.evt_m2HexapodCorrection.get()
    print("MTAOS_logevent_m2HexapodCorrection")
    print(f"\tx ({m2HexapodCorrection.x})")
    print(f"\ty ({m2HexapodCorrection.y})")
    print(f"\tz ({m2HexapodCorrection.z})")
    print(f"\tu ({m2HexapodCorrection.u})")
    print(f"\tv ({m2HexapodCorrection.v})")
    print(f"\tw ({m2HexapodCorrection.w})")

    time.sleep(0.5)

    # Flush the event data
    mtaos.evt_wavefrontError.flush()
    mtaos.evt_degreeOfFreedom.flush()
    mtaos.evt_m1m3Correction.flush()
    mtaos.evt_m2Correction.flush()
    mtaos.evt_cameraHexapodCorrection.flush()
    mtaos.evt_m2HexapodCorrection.flush()

    # Make the calibration products
    sensorNameList = _getComCamSensorNameList()
    testDataDir = os.path.split(getIsrDirPath())[0]
    fakeFlatDir = _makeCalibs(testDataDir, sensorNameList)

    data = mtaos.cmd_processCalibrationProducts.DataType()
    data.directoryPath = fakeFlatDir
    asyncio.get_event_loop().run_until_complete(
        mtaos.cmd_processCalibrationProducts.start(data, timeout=60.0))

    rawImgDir = os.path.join(getModulePath(), "tests", "testData",
                             "phosimOutput", "realComCam")
    data = mtaos.cmd_processIntraExtraWavefrontError.DataType()
    data.intraVisit = 9006002
    data.extraVisit = 9006001
    data.intraDirectoryPath = os.path.join(rawImgDir, "intra")
    data.extraDirectoryPath = os.path.join(rawImgDir, "extra")
    data.fieldRA = 0.0
    data.fieldDEC = 0.0
    data.filter = 7
    data.cameraRotation = 0.0
    data.userGain = 1.0
    asyncio.get_event_loop().run_until_complete(
        mtaos.cmd_processIntraExtraWavefrontError.start(data, timeout=3600.0))

    time.sleep(0.5)

    for idx in range(9):
        wavefrontError = mtaos.evt_wavefrontError.get_oldest()
        if (wavefrontError.sensorId == 96):
            print("MTAOS_logevent_wavefrontError")
            print(f"\tsensorId ({wavefrontError.sensorId})")
            print("Sensor is R22_S00")
            for counter, zk in enumerate(wavefrontError.annularZernikePoly):
                print("z[%d] = %.3f" % (counter, zk))

    degreeOfFreedom = mtaos.evt_degreeOfFreedom.get()
    print("MTAOS_logevent_degreeOfFreedom")

    print("Aggregated DOF:")
    for counter, dof in enumerate(degreeOfFreedom.aggregatedDoF):
        print("dof[%d] = %.6f" % (counter, dof))

    cameraHexapodCorrection = mtaos.evt_cameraHexapodCorrection.get()
    print("MTAOS_logevent_cameraHexapodCorrection (change degree to arcsec)")
    print(f"\tx ({round(cameraHexapodCorrection.x, 4)})")
    print(f"\ty ({round(cameraHexapodCorrection.y, 4)})")
    print(f"\tz ({round(cameraHexapodCorrection.z, 4)})")
    print(f"\tu ({round(cameraHexapodCorrection.u * 3600, 4)})")
    print(f"\tv ({round(cameraHexapodCorrection.v * 3600, 4)})")
    print(f"\tw ({round(cameraHexapodCorrection.w * 3600, 4)})")

    m2HexapodCorrection = mtaos.evt_m2HexapodCorrection.get()
    print("MTAOS_logevent_m2HexapodCorrection (change degree to arcsec)")
    print(f"\tx ({round(m2HexapodCorrection.x, 4)})")
    print(f"\ty ({round(m2HexapodCorrection.y, 4)})")
    print(f"\tz ({round(m2HexapodCorrection.z, 4)})")
    print(f"\tu ({round(m2HexapodCorrection.u * 3600, 4)})")
    print(f"\tv ({round(m2HexapodCorrection.v * 3600, 4)})")
    print(f"\tw ({round(m2HexapodCorrection.w * 3600, 4)})")


def _getComCamSensorNameList():

    sensorNameList = ["R22_S00", "R22_S01", "R22_S02", "R22_S10", "R22_S11",
                      "R22_S12", "R22_S20", "R22_S21", "R22_S22"]
    return sensorNameList


def _makeCalibs(outputDir, sensorNameList):

    fakeFlatDirName = "fake_flats"
    fakeFlatDir = os.path.join(outputDir, fakeFlatDirName)
    _makeDir(fakeFlatDir)

    detector = " ".join(sensorNameList)
    _genFakeFlat(fakeFlatDir, detector)

    return fakeFlatDir


def _makeDir(directory):

    if (not os.path.exists(directory)):
        os.makedirs(directory)


def _genFakeFlat(fakeFlatDir, detector):

    currWorkDir = os.getcwd()

    os.chdir(fakeFlatDir)
    _makeFakeFlat(detector)
    os.chdir(currWorkDir)


def _makeFakeFlat(detector):

    command = "makeGainImages.py"
    argstring = "--detector_list %s" % detector
    runProgram(command, argstring=argstring)


if __name__ == "__main__":

    # Make the ISR directory
    _makeDir(getIsrDirPath())

    # Run the test script
    main()
