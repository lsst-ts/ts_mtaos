# Main Telescope Active Optical System (MTAOS)

MTAOS is a component of LSST Telescope and Site software. It process images taken by camera corner raft (wavefront sensors), computes corrections and sends them to M2 and camera hexapods and M1M3 support system.

## Supported OS + packages

- CentOS 7
- python: 3.7.6
- scientific pipeline (`newinstall.sh` from master branch)

## Required LSST packages

- [ts_wep](https://github.com/lsst-ts/ts_wep)
- [ts_ofc](https://github.com/lsst-ts/ts_ofc)
- [ts_sal](https://github.com/lsst-ts/ts_sal)
- [ts_xml](https://github.com/lsst-ts/ts_xml)
- [ts_opensplice](https://github.com/lsst-ts/ts_opensplice)
- [ts_config_mttcs](https://github.com/lsst-ts/ts_config_mttcs)
- [ts_salobj](https://github.com/lsst-ts/ts_salobj)
- [ts_phosim](https://github.com/lsst-ts/ts_phosim) (optional)

## Docker images

All required packages are available in [lsst/aos_aoclc](https://hub.docker.com/r/lsstts/aos_aoclc) container. [lsstts/mtaos_sim](https://hub.docker.com/r/lsstts/mtaos_sim) runs MTAOS CsC as simulator.

## Client IDL files

To generate IDL files for clients, run:

```bash
make_idl_files.py MTAOS Hexapod MTM1M3 MTM2
```

## Usage

1. Call SAL `.setup.sh` to setup MTAOS environment:

```bash
source /home/saluser/.setup.sh
cd $path_to_ts_MTAOS
setup -k -r .
```

2. Set the ISR (instrument signature removal) path variable:

```bash
export ISRDIRPATH=$path_to_isr_directory
```

3. Run MTAOS

```bash
run_mtaos.py
```

or (for simulator):

```bash
run_mtaos.py -s
```

See `run_mtaos.py -h` for details.

## Logging

Python logging packages is used, with default log level set to DEBUG. You can change the level with `--debugLevel` argument. Add the `--logToFile` argument to log messages to a log file.

## Building documentation

### Additional requirements

_Provided in `lsstts/mtaos_sim` container._

- [documenteer](https://github.com/lsst-sqre/documenteer)
- [plantuml](https://newcontinuum.dl.sourceforge.net/project/plantuml/plantuml.jar)
- [sphinxcontrib-plantuml](https://pypi.org/project/sphinxcontrib-plantuml/)

You can update plantuml.jar path in [doc/conf.py](doc/conf.py).

To build the documentation, run 

```bash
package-docs build
```

See ["Building single-package documentation locally"](https://developer.lsst.io/stack/building-single-package-docs.html) for further details.
