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

__all__ = ["MTAOSCsc"]

import asyncio
import enum
import numpy as np
import time
import traceback

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

data = mtaos.cmd_processIntraExtraWavefrontError.DataType()
data.intraDirectoryPath = ""
data.extraDirectoryPath = ""
data.fieldRA = 0.0
data.fieldDEC = 0.0
data.filter = 7
data.cameraRotation = 0.0
data.userGain = 1.0
asyncio.get_event_loop().run_until_complete(mtaos.cmd_processIntraExtraWavefrontError.start(data, timeout=1.0))

time.sleep(0.5)

wavefrontError = mtaos.evt_wavefrontError.get_oldest()
print("MTAOS_logevent_wavefrontError")
print(f"\tsensorId ({wavefrontError.sensorId}) = 198 : {wavefrontError.sensorId == 198}")
expectedAnnularZernikePoly = np.asarray([-6.153917390910894625e-01,6.800721617519535078e-01,7.156367199512111421e-01,-1.160736861912169682e-01,-5.102712621247364189e-02,1.543248524492320806e-01,2.937848549762492670e-02,-3.797015954213123212e-02,-3.099129598642007266e-02,-6.330189569219045118e-03,1.454797898400303213e-01,4.730209733706434994e-02,1.040252378444658440e-02,2.339768113271831554e-02,1.101866708804799533e-02,-3.515152035538683661e-02,5.674920993267872776e-02,4.062308183947008211e-02,-2.706689685617463814e-03])
for i in range(19):
    print(f"\tannularZernikePoly[{i}] ({round(wavefrontError.annularZernikePoly[i],6)}) == {round(expectedAnnularZernikePoly[i],6)} : {round(wavefrontError.annularZernikePoly[i],6) == round(expectedAnnularZernikePoly[i],6)}")

wavefrontError = mtaos.evt_wavefrontError.get_oldest()
print("MTAOS_logevent_wavefrontError")
print(f"\tsensorId ({wavefrontError.sensorId}) = 31 : {wavefrontError.sensorId == 31}")
expectedAnnularZernikePoly = np.asarray([-6.508025658456179086e-01,1.077484851406983246e+00,6.619831230825762303e-01,-5.280921416422450915e-02,1.195858978531248555e-02,6.224911738783732440e-02,5.997471924534075738e-02,-3.412540804053735416e-02,-2.458755478845710274e-02,-6.695443423383920512e-02,9.813334757580062517e-02,4.944647631600296300e-02,-6.907523554670066436e-03,2.340636456000866686e-02,-4.869086883414252415e-02,-2.918418017494414998e-02,4.201074469237146836e-02,2.951184764628276419e-02,-2.161628407805408006e-03])
for i in range(19):
    print(f"\tannularZernikePoly[{i}] ({round(wavefrontError.annularZernikePoly[i],6)}) == {round(expectedAnnularZernikePoly[i],6)} : {round(wavefrontError.annularZernikePoly[i],6) == round(expectedAnnularZernikePoly[i],6)}")

wavefrontError = mtaos.evt_wavefrontError.get_oldest()
print("MTAOS_logevent_wavefrontError")
print(f"\tsensorId ({wavefrontError.sensorId}) = 2 : {wavefrontError.sensorId == 2}")
expectedAnnularZernikePoly = np.asarray([-5.364835666589059526e-01,7.834904898482739632e-01,4.580432878801197760e-01,1.322239860081102919e-02,2.717302077193928245e-02,1.320376479551270688e-01,1.354213134433924492e-01,-3.796888614780912635e-02,-4.863708304767278695e-02,2.025441640237930600e-03,1.188792620929283866e-01,-7.423205235517253697e-02,-1.590907144014760966e-02,-1.500990401179183240e-02,-1.711300292664839212e-02,1.653917968798911467e-02,-6.635913889407275834e-02,4.454640570529196791e-02,-3.382080575084947961e-03])
for i in range(19):
    print(f"\tannularZernikePoly[{i}] ({round(wavefrontError.annularZernikePoly[i],6)}) == {round(expectedAnnularZernikePoly[i],6)} : {round(wavefrontError.annularZernikePoly[i],6) == round(expectedAnnularZernikePoly[i],6)}")

wavefrontError = mtaos.evt_wavefrontError.get_oldest()
print("MTAOS_logevent_wavefrontError")
print(f"\tsensorId ({wavefrontError.sensorId}) = 169 : {wavefrontError.sensorId == 169}")
expectedAnnularZernikePoly = np.asarray([-5.731407802472003876e-01,1.120233673138077091e+00,5.497975405958508421e-01,-8.879783186066200762e-02,-1.043655677029090012e-01,1.212888514877605989e-01,1.346889615803068159e-02,-4.229652934813449283e-02,-1.233579508301714360e-02,-7.258821002407078726e-02,1.047862248292259768e-01,3.050152051017651460e-03,2.390182037902876047e-02,5.975219894465437845e-03,2.965160596788523652e-03,2.820190845764394914e-03,4.733646843564373596e-02,1.460241530850708153e-02,-1.900365060864501153e-03])
for i in range(19):
    print(f"\tannularZernikePoly[{i}] ({round(wavefrontError.annularZernikePoly[i],6)}) == {round(expectedAnnularZernikePoly[i],6)} : {round(wavefrontError.annularZernikePoly[i],6) == round(expectedAnnularZernikePoly[i],6)}")

degreeOfFreedom = mtaos.evt_degreeOfFreedom.get()
print("MTAOS_logevent_degreeOfFreedom")
expectedDoF = np.asarray([-16.0367,-1.3495,2.6511,0.2607,0.7057,-36.3131,3.9930,0.6636,-1.2466,0.2791,0.2779,0.1655,0.0471,-0.0215,0.0246,0.0166,0.0389,0.0015,-0.0080,0.0001,-0.0023,-0.0219,-0.0039,0.0047,-0.0010,0.0007,-0.0081,-0.0080,-0.0007,0.0010,-0.0097,0.1448,0.0633,-0.0357,-0.0832,-0.0470,0.0062,-0.0038,-0.0076,-0.0001,-0.0011,0.0074,-0.0012,0.0112,-0.0106,-0.0019,0.0019,0.0017,-0.0007,0.0021])
for i in range(50):
    print(f"\taggregatedDoF[{i}] ({round(degreeOfFreedom.aggregatedDoF[i],4)}) == {round(expectedDoF[i],4)} : {round(degreeOfFreedom.aggregatedDoF[i],4) == round(expectedDoF[i],4)}")
for i in range(50):
    print(f"\tvisitDoF[{i}] ({round(degreeOfFreedom.visitDoF[i],4)}) == {round(expectedDoF[i],4)} : {round(degreeOfFreedom.visitDoF[i],4) == round(expectedDoF[i],4)}")

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
print(f"\tx ({round(cameraHexapodCorrection.x,4)}) ==  -3.9930 : {round(cameraHexapodCorrection.x,4) == -3.9930}")
print(f"\ty ({round(cameraHexapodCorrection.y,4)}) ==   0.6636 : {round(cameraHexapodCorrection.y,4) == 0.6636}")
print(f"\tz ({round(cameraHexapodCorrection.z,4)}) ==  36.3131 : {round(cameraHexapodCorrection.z,4) == 36.3131}")
print(f"\tu ({round(cameraHexapodCorrection.u*3600,4)}) ==   1.2466 : {round(cameraHexapodCorrection.u*3600,4) == 1.2466}")
print(f"\tv ({round(cameraHexapodCorrection.v*3600,4)}) ==   0.2791 : {round(cameraHexapodCorrection.v*3600,4) == 0.2791}")
print(f"\tw ({round(cameraHexapodCorrection.w*3600,4)}) ==   0.0000 : {round(cameraHexapodCorrection.w*3600,4) == 0.0}")

m2HexapodCorrection = mtaos.evt_m2HexapodCorrection.get()
print("MTAOS_logevent_m2HexapodCorrection")
print(f"\tx ({round(m2HexapodCorrection.x,4)}) ==   1.3495 : {round(m2HexapodCorrection.x,4) == 1.3495}")
print(f"\ty ({round(m2HexapodCorrection.y,4)}) ==   2.6511 : {round(m2HexapodCorrection.y,4) == 2.6511}")
print(f"\tz ({round(m2HexapodCorrection.z,4)}) ==  16.0367 : {round(m2HexapodCorrection.z,4) == 16.0367}")
print(f"\tu ({round(m2HexapodCorrection.u*3600,4)}) ==  -0.2607 : {round(m2HexapodCorrection.u*3600,4) == -0.2607}")
print(f"\tv ({round(m2HexapodCorrection.v*3600,4)}) ==   0.7057 : {round(m2HexapodCorrection.v*3600,4) == 0.7057}")
print(f"\tw ({round(m2HexapodCorrection.w*3600,4)}) ==   0.0000 : {round(m2HexapodCorrection.w*3600,4) == 0.0}")