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
import numpy as np
import time

from lsst.ts.wep.Utility import runProgram

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


def main(testDataDir):

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
    asyncio.get_event_loop().run_until_complete(mtaos.cmd_resetWavefrontCorrection.start(data, timeout=1.0))

    time.sleep(0.5)

    # wavefrontError = mtaos.evt_wavefrontError.get()
    # sensorId
    # annularZernikePoly

    degreeOfFreedom = mtaos.evt_degreeOfFreedom.get()
    print("MTAOS_logevent_degreeOfFreedom")
    for i in range(50):
        print(f"\taggregatedDoF[{i}] ({degreeOfFreedom.aggregatedDoF[i]}) == 0 : {degreeOfFreedom.aggregatedDoF[i] == 0.0}")
    for i in range(50):
        print(f"\tvisitDoF[{i}] ({degreeOfFreedom.visitDoF[i]}) == 0 : {degreeOfFreedom.visitDoF[i] == 0.0}")

    m1m3Correction = mtaos.evt_m1m3Correction.get()
    print("MTAOS_logevent_m1m3Correction")
    for i in range(156):
        print(f"\tzForces[{i}] ({m1m3Correction.zForces[i]}) == 0 : {m1m3Correction.zForces[i] == 0.0}")

    m2Correction = mtaos.evt_m2Correction.get()
    print("MTAOS_logevent_m2Correction")
    for i in range(72):
        print(f"\tzForces[{i}] ({m2Correction.zForces[i]}) == 0 : {m2Correction.zForces[i] == 0.0}")

    cameraHexapodCorrection = mtaos.evt_cameraHexapodCorrection.get()
    print("MTAOS_logevent_cameraHexapodCorrection")
    print(f"\tx ({cameraHexapodCorrection.x}) == 0 : {cameraHexapodCorrection.x == 0.0}")
    print(f"\ty ({cameraHexapodCorrection.y}) == 0 : {cameraHexapodCorrection.y == 0.0}")
    print(f"\tz ({cameraHexapodCorrection.z}) == 0 : {cameraHexapodCorrection.z == 0.0}")
    print(f"\tu ({cameraHexapodCorrection.u}) == 0 : {cameraHexapodCorrection.u == 0.0}")
    print(f"\tv ({cameraHexapodCorrection.v}) == 0 : {cameraHexapodCorrection.v == 0.0}")
    print(f"\tw ({cameraHexapodCorrection.w}) == 0 : {cameraHexapodCorrection.w == 0.0}")

    m2HexapodCorrection = mtaos.evt_m2HexapodCorrection.get()
    print("MTAOS_logevent_m2HexapodCorrection")
    print(f"\tx ({m2HexapodCorrection.x}) == 0 : {m2HexapodCorrection.x == 0.0}")
    print(f"\ty ({m2HexapodCorrection.y}) == 0 : {m2HexapodCorrection.y == 0.0}")
    print(f"\tz ({m2HexapodCorrection.z}) == 0 : {m2HexapodCorrection.z == 0.0}")
    print(f"\tu ({m2HexapodCorrection.u}) == 0 : {m2HexapodCorrection.u == 0.0}")
    print(f"\tv ({m2HexapodCorrection.v}) == 0 : {m2HexapodCorrection.v == 0.0}")
    print(f"\tw ({m2HexapodCorrection.w}) == 0 : {m2HexapodCorrection.w == 0.0}")

    time.sleep(0.5)

    mtaos.evt_wavefrontError.flush()
    mtaos.evt_degreeOfFreedom.flush()
    mtaos.evt_m1m3Correction.flush()
    mtaos.evt_m2Correction.flush()
    mtaos.evt_cameraHexapodCorrection.flush()
    mtaos.evt_m2HexapodCorrection.flush()

    # Make the calibration products
    sensorNameList = _getComCamSensorNameList()
    calibPath = os.path.join(testDataDir, "calibrationProducts")
    fakeFlatDir = _makeCalibs(calibPath, sensorNameList)

    data = mtaos.cmd_processCalibrationProducts.DataType()
    data.directoryPath = fakeFlatDir
    asyncio.get_event_loop().run_until_complete(
        mtaos.cmd_processCalibrationProducts.start(data, timeout=60.0))

    data = mtaos.cmd_processIntraExtraWavefrontError.DataType()
    data.intraVisit = 9005001
    data.extraVisit = 9005000
    data.intraDirectoryPath = "/home/lsst/testData/rawImages/intra"
    data.extraDirectoryPath = "/home/lsst/testData/rawImages/extra"
    data.fieldRA = 0.0
    data.fieldDEC = 0.0
    data.filter = 7
    data.cameraRotation = 0.0
    data.userGain = 1.0
    asyncio.get_event_loop().run_until_complete(
        mtaos.cmd_processIntraExtraWavefrontError.start(data, timeout=300.0))

    time.sleep(0.5)

    for i in range(2):
        wavefrontError = mtaos.evt_wavefrontError.get_oldest()
        if wavefrontError.sensorId == 100:
            print("MTAOS_logevent_wavefrontError")
            print(f"\tsensorId ({wavefrontError.sensorId}) = 100 : {wavefrontError.sensorId == 100}")
            expectedAnnularZernikePoly = np.asarray(
                [-0.003132, 0.008869, 0.232299, 0.008724, -0.002694, -0.068149,
                 -0.01733, 0.038938, -0.014419, -0.001669, 0.015322, 3.1e-05,
                 0.001045, -0.006121, 0.002829, 0.032297, -0.003703, -0.04533,
                 -0.013229])
            for i in range(19):
                print(f"\tannularZernikePoly[{i}] ({round(wavefrontError.annularZernikePoly[i],3)}) == {round(expectedAnnularZernikePoly[i],3)} : {round(wavefrontError.annularZernikePoly[i],3) == round(expectedAnnularZernikePoly[i],3)}")
        elif wavefrontError.sensorId == 99:
            print("MTAOS_logevent_wavefrontError")
            print(f"\tsensorId ({wavefrontError.sensorId}) = 99 : {wavefrontError.sensorId == 99}")
            expectedAnnularZernikePoly = np.asarray(
                [0.005894, 0.037559, 0.164951, 0.004442, -0.004069, -0.032041,
                 0.006704, 0.036877, 0.009101, -0.002455, -0.008421, -0.004067,
                 -0.001783, -0.014688, -0.009204, 0.031468, -0.007014, -0.035128,
                 -0.013208])
            for i in range(19):
                print(f"\tannularZernikePoly[{i}] ({round(wavefrontError.annularZernikePoly[i],3)}) == {round(expectedAnnularZernikePoly[i],3)} : {round(wavefrontError.annularZernikePoly[i],3) == round(expectedAnnularZernikePoly[i],3)}")
        else:
            print("MTAOS_logevent_wavefrontError")
            print("\tUNEXPECTED WAVEFRONT SENSOR")

    degreeOfFreedom = mtaos.evt_degreeOfFreedom.get()
    print("MTAOS_logevent_degreeOfFreedom")
    expectedDoF = np.asarray(
        [0.4793, -0.2487, 3.833, 0.5388, 0.0315, 6.3908, 0.0805, -1.5978,
         -0.7501, -0.0021, -0.0215, 0.1853, -0.0777, 0.0, 0.0, 0.0, 0.0, 0.0,
         0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0081,
         -0.2135, -0.0024, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
         0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    for i in range(50):
        print(f"\taggregatedDoF[{i}] ({round(degreeOfFreedom.aggregatedDoF[i],1)}) == {round(expectedDoF[i],1)} : {round(degreeOfFreedom.aggregatedDoF[i],1) == round(expectedDoF[i],1)}")
    for i in range(50):
        print(f"\tvisitDoF[{i}] ({round(degreeOfFreedom.visitDoF[i],1)}) == {round(expectedDoF[i],1)} : {round(degreeOfFreedom.visitDoF[i],1) == round(expectedDoF[i],1)}")

    # m1m3Correction = mtaos.evt_m1m3Correction.get()
    # print("MTAOS_logevent_m1m3Correction")
    # for i in range(156):
    #     print(f"\tzForces[{i}] ({m1m3Correction.zForces[i]}) == 0 : {m1m3Correction.zForces[i] == 0.0}")

    # m2Correction = mtaos.evt_m2Correction.get()
    # print("MTAOS_logevent_m2Correction")
    # for i in range(72):
    #     print(f"\tzForces[{i}] ({m2Correction.zForces[i]}) == 0 : {m2Correction.zForces[i] == 0.0}")

    cameraHexapodCorrection = mtaos.evt_cameraHexapodCorrection.get()
    print("MTAOS_logevent_cameraHexapodCorrection")
    print(f"\tx ({round(cameraHexapodCorrection.x,4)}) ==  -0.0805 : {round(cameraHexapodCorrection.x,4) == -0.0805}")
    print(f"\ty ({round(cameraHexapodCorrection.y,4)}) ==  -1.5978 : {round(cameraHexapodCorrection.y,4) == -1.5978}")
    print(f"\tz ({round(cameraHexapodCorrection.z,4)}) ==  -6.3908 : {round(cameraHexapodCorrection.z,4) == -6.3908}")
    print(f"\tu ({round(cameraHexapodCorrection.u*3600,4)}) ==   0.7501 : {round(cameraHexapodCorrection.u*3600,4) == 0.7501}")
    print(f"\tv ({round(cameraHexapodCorrection.v*3600,4)}) ==  -0.0021 : {round(cameraHexapodCorrection.v*3600,4) == -0.0021}")
    print(f"\tw ({round(cameraHexapodCorrection.w*3600,4)}) ==   0.0000 : {round(cameraHexapodCorrection.w*3600,4) == 0.0}")

    m2HexapodCorrection = mtaos.evt_m2HexapodCorrection.get()
    print("MTAOS_logevent_m2HexapodCorrection")
    print(f"\tx ({round(m2HexapodCorrection.x,4)}) ==   0.2487 : {round(m2HexapodCorrection.x,4) == 0.2487}")
    print(f"\ty ({round(m2HexapodCorrection.y,4)}) ==   3.8330 : {round(m2HexapodCorrection.y,4) == 3.8330}")
    print(f"\tz ({round(m2HexapodCorrection.z,4)}) ==  -0.4793 : {round(m2HexapodCorrection.z,4) == -0.4793}")
    print(f"\tu ({round(m2HexapodCorrection.u*3600,4)}) ==  -0.5388 : {round(m2HexapodCorrection.u*3600,4) == -0.5388}")
    print(f"\tv ({round(m2HexapodCorrection.v*3600,4)}) ==   0.0315 : {round(m2HexapodCorrection.v*3600,4) == 0.0315}")
    print(f"\tw ({round(m2HexapodCorrection.w*3600,4)}) ==   0.0000 : {round(m2HexapodCorrection.w*3600,4) == 0.0}")


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

    testDataDir = os.path.join(os.sep, "home", "lsst", "testData")
    main(testDataDir)
