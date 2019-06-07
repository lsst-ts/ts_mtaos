#!/usr/bin/env python

import os
import asyncio
import time
import argparse
import numpy as np
from pathlib import Path

from lsst.ts import salobj
import SALPY_MTAOS

from lsst.ts.MTAOS.Utility import getIsrDirPath

from lsst.ts.wep.Utility import FilterType, runProgram

from lsst.ts.phosim.telescope.TeleFacade import TeleFacade
from lsst.ts.phosim.PhosimCmpt import PhosimCmpt
from lsst.ts.phosim.SkySim import SkySim
from lsst.ts.phosim.Utility import getPhoSimPath, getAoclcOutputPath
from lsst.ts.phosim.PlotUtil import plotFwhmOfIters


def main(phosimDir, numPro, iterNum, baseOutputDir):

    # Prepate the calibration products
    sensorNameList = _getComCamSensorNameList()
    fakeFlatDir = _makeCalibs(baseOutputDir, sensorNameList)

    # Make the ISR directory, need to check the directory authority issue here
    # if the docker image is used and the container has the mount volumn with
    # the outside.
    # I put this with 'export ISRDIRPATH=/home/lsst/output/input' in the
    # container for the server and controller sides
    _makeDir(getIsrDirPath())

    # Test star magnitude
    starMag = 15

    # Survey parameters
    filterType = FilterType.REF
    raInDeg = 0.0
    decInDeg = 0.0
    rotAngInDeg = 0.0

    # Prepare the components
    phosimCmpt = _preparePhosimCmpt(phosimDir, filterType, raInDeg, decInDeg,
                                    rotAngInDeg, numPro)
    mtaos = _prepareRemoteMtaos()

    # Ingest the calibration products
    data = mtaos.cmd_processCalibrationProducts.DataType()
    data.directoryPath = fakeFlatDir.as_posix()
    asyncio.get_event_loop().run_until_complete(
        mtaos.cmd_processCalibrationProducts.start(data, timeout=60.0))

    # Set the telescope state to be the same as the OFC
    state0 = np.zeros(50)
    phosimCmpt.setDofInUm(state0)

    # Do the iteration
    obsId = 9006000
    opdZkFileName = "opd.zer"
    opdPssnFileName = "PSSN.txt"
    outputDirName = "pert"
    outputImgDirName = "img"
    iterDefaultDirName = "iter"
    dofInUmFileName = "dofPertInNextIter.mat"
    skyInfoFileName = "skyComCamInfo.txt"
    userGain = 0.4
    for iterCount in range(iterNum):

        # Set the observation Id
        phosimCmpt.setSurveyParam(obsId=obsId)

        # The iteration directory
        iterDirName = "%s%d" % (iterDefaultDirName, iterCount)

        # Set the output directory
        outputDir = os.path.join(baseOutputDir, iterDirName, outputDirName)
        phosimCmpt.setOutputDir(outputDir)

        # Set the output image directory
        outputImgDir = os.path.join(baseOutputDir, iterDirName,
                                    outputImgDirName)
        phosimCmpt.setOutputImgDir(outputImgDir)

        # Generate the OPD image
        argString = phosimCmpt.getComCamOpdArgsAndFilesForPhoSim()
        phosimCmpt.runPhoSim(argString)

        # Analyze the OPD data
        phosimCmpt.analyzeComCamOpdData(zkFileName=opdZkFileName,
                                        pssnFileName=opdPssnFileName)

        # Get the PSSN from file
        pssn = phosimCmpt.getOpdPssnFromFile(opdPssnFileName)
        print("Calculated PSSN is %s." % pssn)

        # Get the GQ effective FWHM from file
        gqEffFwhm = phosimCmpt.getOpdGqEffFwhmFromFile(opdPssnFileName)
        print("GQ effective FWHM is %.4f." % gqEffFwhm)

        # Prepare the faked sky according to the OPD field positions
        metr = phosimCmpt.getOpdMetr()
        skySim = _prepareSkySim(metr, starMag)

        # Output the sky information.
        outputSkyInfoFilePath = os.path.join(outputDir, skyInfoFileName)
        skySim.exportSkyToFile(outputSkyInfoFilePath)

        # Assign the entra- and intra-focal observation Id
        extraObsId = obsId + 1
        intraObsId = obsId + 2

        # Generate the defocal images
        simSeed = 1000
        argStringList = phosimCmpt.getComCamStarArgsAndFilesForPhoSim(
            extraObsId, intraObsId, skySim, simSeed=simSeed,
            cmdSettingFileName="starDefault.cmd",
            instSettingFileName="starSingleExp.inst")
        for argString in argStringList:
            phosimCmpt.runPhoSim(argString)

        # Repackage the images
        phosimCmpt.repackageComCamImgFromPhoSim()

        # Directory of the defocal images
        intraRawExpDir = os.path.join(outputImgDir,
                                      phosimCmpt.getIntraFocalDirName())

        extraRawExpDir = os.path.join(outputImgDir,
                                      phosimCmpt.getExtraFocalDirName())

        data = mtaos.cmd_processIntraExtraWavefrontError.DataType()
        data.intraVisit = intraObsId
        data.extraVisit = extraObsId
        data.intraDirectoryPath = intraRawExpDir
        data.extraDirectoryPath = extraRawExpDir
        data.fieldRA = raInDeg
        data.fieldDEC = decInDeg
        data.filter = filterType.value
        data.cameraRotation = rotAngInDeg
        data.userGain = userGain
        asyncio.get_event_loop().run_until_complete(
            mtaos.cmd_processIntraExtraWavefrontError.start(data, timeout=3600.0))

        # Set the new aggregated DOF to phosimCmpt
        degreeOfFreedom = mtaos.evt_degreeOfFreedom.get()
        dofInUm = degreeOfFreedom.aggregatedDoF
        phosimCmpt.setDofInUm(dofInUm)

        # Save the DOF file
        phosimCmpt.saveDofInUmFileForNextIter(
            dofInUm, dofInUmFileName=dofInUmFileName)

        # Add the observation ID by 10 for the next iteration
        obsId += 10

    # Exit the MTAOS control
    data = mtaos.cmd_exitControl.DataType()
    asyncio.get_event_loop().run_until_complete(
        mtaos.cmd_exitControl.start(data, timeout=1.0))

    # Summarize the FWHM
    pssnFiles = [os.path.join(baseOutputDir, "%s%d" % (iterDefaultDirName, num),
                 outputImgDirName, opdPssnFileName) for num in range(iterNum)]
    saveToFilePath = os.path.join(baseOutputDir, "fwhmIters.png")
    plotFwhmOfIters(pssnFiles, saveToFilePath=saveToFilePath)


def _getComCamSensorNameList():

    sensorNameList = ["R22_S00", "R22_S01", "R22_S02", "R22_S10", "R22_S11",
                      "R22_S12", "R22_S20", "R22_S21", "R22_S22"]
    return sensorNameList


def _makeCalibs(outputDir, sensorNameList):

    fakeFlatDirName = "fake_flats"
    fakeFlatDir = Path(outputDir).joinpath(fakeFlatDirName)
    _makeDir(fakeFlatDir)

    detector = " ".join(sensorNameList)
    _genFakeFlat(fakeFlatDir, detector)

    return fakeFlatDir


def _makeDir(directory):

    Path(directory).mkdir(parents=True, exist_ok=True)


def _genFakeFlat(fakeFlatDir, detector):

    currWorkDir = os.getcwd()

    os.chdir(fakeFlatDir)
    _makeFakeFlat(detector)
    os.chdir(currWorkDir)


def _makeFakeFlat(detector):

    command = "makeGainImages.py"
    argstring = "--detector_list %s" % detector
    runProgram(command, argstring=argstring)


def _preparePhosimCmpt(phosimDir, filterType, raInDeg, decInDeg, rotAngInDeg,
                       numPro):

    # Set the Telescope facade class
    tele = TeleFacade()
    tele.addSubSys(addCam=True, addM1M3=True, addM2=True)
    tele.setPhoSimDir(phosimDir)

    # Prepare the phosim component
    phosimCmpt = PhosimCmpt(tele)

    # Set the telescope survey parameters
    boresight = (raInDeg, decInDeg)
    zAngleInDeg = 27.0912
    phosimCmpt.setSurveyParam(filterType=filterType, boresight=boresight,
                              zAngleInDeg=zAngleInDeg, rotAngInDeg=rotAngInDeg)

    # Set the PhoSim parameters
    phosimCmpt.setPhosimParam(numPro, 1)

    # Set the seed number for M1M3 surface
    seedNum = 6
    phosimCmpt.setSeedNum(seedNum)

    return phosimCmpt


def _prepareRemoteMtaos():

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

    return mtaos


def _prepareSkySim(opdMetr, starMag):

    skySim = SkySim()

    starId = 0
    raInDegList, declInDegList = opdMetr.getFieldXY()
    for raInDeg, declInDeg in zip(raInDegList, declInDegList):
        # It is noted that the field position might be < 0. But it is not the
        # same case for ra (0 <= ra <= 360).
        if (raInDeg < 0):
            raInDeg += 360.0
        skySim.addStarByRaDecInDeg(starId, raInDeg, declInDeg, starMag)
        starId += 1

    return skySim


if __name__ == "__main__":

    # Set the parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--numOfProc", type=int, default=1,
                        help="number of processor to run PhoSim")
    parser.add_argument("--iterNum", type=int, default=5,
                        help="number of closed-loop iteration")
    parser.add_argument("--output", type=str, default="",
                        help="output directory")
    args = parser.parse_args()

    # Run the simulation
    phosimDir = getPhoSimPath()

    if (args.output == ""):
        outputDir = getAoclcOutputPath()
    else:
        outputDir = args.output
    _makeDir(outputDir)

    main(phosimDir, args.numOfProc, args.iterNum, outputDir)
