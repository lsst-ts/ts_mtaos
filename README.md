# Main Telescope Active Optical System (MTAOS)

*MTAOS is a component of LSST Telescope and Site software. It is responsible for making the closed-loop optical system with the data distribution system (DDS).*

## 1. Platform

- *CentOS 7*
- *python: 3.7.2*
- *scientific pipeline (newinstall.sh from master branch)*

## 2. Needed Package

- *[ts_wep](https://github.com/lsst-ts/ts_wep) - master branch (commit: 5d20039)*
- *[ts_ofc](https://github.com/lsst-ts/ts_ofc) - master branch (commit: e38c4e1)*
- *[ts_sal](https://github.com/lsst-ts/ts_sal) - develop branch (commit: f330832)*
- *[ts_xml](https://github.com/lsst-ts/ts_xml) - develop branch (commit: 22e2500)*
- *[ts_opensplice](https://github.com/lsst-ts/ts_opensplice) - master branch (DDS v.6.9.0 is used)*
- *[ts_config_mttcs](https://github.com/lsst-ts/ts_config_mttcs) - develop branch*
- *[ts_salobj](https://github.com/lsst-ts/ts_salobj) - develop branch (commit: 82fa683)*
- *[ts_phosim](https://github.com/lsst-ts/ts_phosim) - master branch (commit: a2a42f3) (optional)*
- *[documenteer](https://github.com/lsst-sqre/documenteer) (optional)*
- *[plantuml](http://plantuml.com) (optional)*
- *[sphinxcontrib-plantuml](https://pypi.org/project/sphinxcontrib-plantuml/) (optional)*

## 3. Pull the Built Develop Image from Docker Hub

*Pull the built develop docker image by `docker pull lsstts/aos_aoclc:w_2019_38_sal`. The scientific pipeline and lsst packages are installed already (except `ts_MTAOS` and `ts_config_mttcs`). For the details of docker image, please follow the [docker aos_aoclc image](https://hub.docker.com/r/lsstts/aos_aoclc).*

## 4. Generate the IDL Files

*1. Generate the IDL files for subsystems:*

```bash
make_idl_files.py MTAOS Hexapod MTM1M3 MTM2
```

*2. Unset the LSST IP by `unset LSST_DDS_IP`. This is a bug in `ts_salobj` v5.0.0_RC2.*

## 5. Use of Module

*1. Setup `ts_config_mttcs` first, and then, setup `ts_MTAOS`. `.setup.sh` is an environment setup script in docker container.*

```bash
source /home/saluser/.setup.sh
cd $path_to_ts_config_mttcs
setup -k -r .
cd $path_to_ts_MTAOS
setup -k -r .
scons
```

*2. Set the path variable of ISR (instrument signature removal) data for the butler to use:*

```bash
export ISRDIRPATH=$path_to_isr_directory
```

## 6. Command Line Task

- **run_mtaos.py**: Run the MTAOS as a control server. User can pass `-s` as the argument to run the simulation mode.

## 7. Build the Document

*The user can use `package-docs build` to build the documentation. The packages of documenteer, plantuml, and sphinxcontrib-plantuml are needed. The path of plantuml.jar in doc/conf.py needs to be updated to the correct path. To clean the built documents, use `package-docs clean`. See [Building single-package documentation locally](https://developer.lsst.io/stack/building-single-package-docs.html) for further details.*
