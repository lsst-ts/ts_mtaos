# Main Telescope Active Optical System (MTAOS)

*MTAOS is a component of LSST Telescope and Site software. It is responsible for making the closed-loop optical system with the data distribution system (DDS).*

## 1. Platform

- *CentOS 7*
- *python: 3.7.2*
- *scientific pipeline (newinstall.sh from master branch)*

## 2. Needed Package

- *[ts_wep](https://github.com/lsst-ts/ts_wep)*
- *[ts_ofc](https://github.com/lsst-ts/ts_ofc)*
- *[ts_sal](https://github.com/lsst-ts/ts_sal)*
- *[ts_xml](https://github.com/lsst-ts/ts_xml)*
- *[ts_opensplice](https://github.com/lsst-ts/ts_opensplice)*
- *[ts_config_mttcs](https://github.com/lsst-ts/ts_config_mttcs)*
- *[ts_salobj](https://github.com/lsst-ts/ts_salobj)*
- *[ts_phosim](https://github.com/lsst-ts/ts_phosim) (optional)*
- *[documenteer](https://github.com/lsst-sqre/documenteer) (optional)*
- *[plantuml](http://plantuml.com) (optional)*
- *[sphinxcontrib-plantuml](https://pypi.org/project/sphinxcontrib-plantuml/) (optional)*

## 3. Pull the Built Develop Image from Docker Hub

*Pull the built develop docker image by `docker pull lsstts/aos_aoclc:w_2020_06_sal`. The scientific pipeline and lsst packages are installed already (except `ts_MTAOS` and `ts_config_mttcs`). For the details of docker image, please follow the [docker aos_aoclc image](https://hub.docker.com/r/lsstts/aos_aoclc).*

## 4. Generate the IDL Files

*1. Generate the IDL files for subsystems:*

```bash
make_idl_files.py MTAOS Hexapod MTM1M3 MTM2
```

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

- **run_mtaos.py**: Run the MTAOS as a control server. Use `-h` to get the further information.

## 7. Build the Document

*The user can use `package-docs build` to build the documentation. The packages of documenteer, plantuml, and sphinxcontrib-plantuml are needed. The path of plantuml.jar in doc/conf.py needs to be updated to the correct path. To clean the built documents, use `package-docs clean`. See [Building single-package documentation locally](https://developer.lsst.io/stack/building-single-package-docs.html) for further details.*
