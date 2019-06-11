# Main Telescope Active Optics System (MTAOS)

*MTAOS is a component of LSST Telescope and Site software. It is responsible for making the closed-loop optical system with the service abstraction layer (SAL) middleware.*

## 1. Platform

- *CentOS 7*
- *python: 3.7.2*
- *scientific pipeline (newinstall.sh from master branch)*
- *phosim_syseng4 (branch: aos, tag: firstdonuts) (optional)*

## 2. Needed Package

- *jsonschema*
- *[ts_wep](https://github.com/lsst-ts/ts_wep) - master branch (commit: b0d90ce)*
- *[ts_ofc](https://github.com/lsst-ts/ts_ofc) - master branch (commit: 8b2f74b)*
- *[ts_sal](https://github.com/lsst-ts/ts_sal) - master branch (commit: ac2ca6b)*
- *[ts_xml](https://github.com/lsst-ts/ts_xml) - develop branch (commit: 994918f)*
- *[ts_opensplice](https://github.com/lsst-ts/ts_opensplice) - master branch (commit: dba3466) (DDS v.6.9.0 is used.)*
- *[ts_config_ocs](https://github.com/lsst-ts/ts_config_ocs) - develop branch (commit: 0da9278)*
- *[ts_config_mttcs](https://github.com/lsst-ts/ts_config_mttcs) - develop branch (commit: 0efe216)*
- *[ts_salobj](https://github.com/lsst-ts/ts_salobj) - master branch (commit: 4fea586)*
- *[ts_phosim](https://github.com/lsst-ts/ts_phosim) - master branch (commit: 9078901) (optional)*
- *[documenteer](https://github.com/lsst-sqre/documenteer) (optional)*
- *[plantuml](http://plantuml.com) (optional)*
- *[sphinxcontrib-plantuml](https://pypi.org/project/sphinxcontrib-plantuml/) (optional)*

## 3. Setup the SAL Environment and Build the Subsystem Library

*1. Export the SAL needed environment varibales as the following:*

```bash
export LSST_SDK_INSTALL=$path_to_ts_sal
export OSPL_HOME=$path_to_ts_opensplice/OpenSpliceDDS/V6.9.0/HDE/x86_64.linux-debug
export PYTHON_BUILD_VERSION=3.7m
export PYTHON_BUILD_LOCATION=$path_to_python_build_in_scientific_pipeline
export LSST_DDS_DOMAIN=mtaos
```

*2. Build the subsystem SAL libraries (Test, Hexapod, MTAOS, MTM1M3, and MTM2) as the following ($subsystem is the CSC such as MTAOS):*

```bash
cd $path_to_ts_sal/test
source $path_to_ts_sal/setup.env
cp $path_to_ts_xml/sal_interfaces/SAL*.xml .
cp $path_to_ts_xml/sal_interfaces/$subsystem/*.xml .
salgenerator $subsystem validate
salgenerator $subsystem html
salgenerator $subsystem sal cpp
salgenerator $subsystem sal python
salgenerator $subsystem lib
```

*3. Build the ts_salobj with the move of SAL library:*

```bash
source $path_to_sal_directory/setup.env
cd $path_to_ts_xml
setup -k -r .
cd $path_to_ts_sal
setup -k -r .
cd $path_to_ts_config_ocs
setup -k -r .
cd $path_to_ts_config_mttcs
setup -k -r .
cd $path_to_ts_salobj
setup -k -r .
scons
```

## 4. Use of Module

*1. Setup the ts_wep, ts_ofc, ts_xml, ts_sal, ts_config_ocs, ts_config_mttcs, and ts_salobj environments first, and then, setup the MTAOS environment by eups:*

```bash
cd $path_to_ts_MTAOS
setup -k -r .
scons
```

*2. Set the path variable:*

```bash
export ISRDIRPATH=$path_to_isr_directory
```

## 5. Pull the Built Image from Docker Hub

*Pull the built docker image by `docker pull lsstts/mtaos_dev:v0.3`. The scientific pipeline and lsst packages are installed already. For the details of docker image, please follow the [docker mtaos_dev image](https://hub.docker.com/r/lsstts/mtaos_dev).*

## 6. Example Script

- **mtaos_test.py**: Test the commissioning camera (ComCam) images with one iteration.

## 7. Command Line Task

- **run_mtaos.py**: Run the MTAOS as a control server.

*The following part needs to have the ts_phosim package with the related environment varibales.*

- **comcamCloseLoopMtaos.py**: Close-loop simulation of commissioning camera with MTAOS. There are 9 stars on the center of each CCD.

## 8. Build the Document

*The user can use `package-docs build` to build the documentation. The packages of documenteer, plantuml, and sphinxcontrib-plantuml are needed. The path of plantuml.jar in doc/conf.py needs to be updated to the correct path. To clean the built documents, use `package-docs clean`. See [Building single-package documentation locally](https://developer.lsst.io/stack/building-single-package-docs.html) for further details.*
