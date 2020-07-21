# Main Telescope Active Optical System (MTAOS)

MTAOS is a component of LSST Telescope and Site software. It processes images taken by the wavefront sensor, computes corrections and sends them to M2 and camera hexapods, and M1M3 and M2 support systems.

## Supported OS + Packages

- CentOS 7
- python: 3.7.6
- [black](https://github.com/psf/black) (optional)

## Required LSST Packages

- [ts_wep](https://github.com/lsst-ts/ts_wep)
- [ts_ofc](https://github.com/lsst-ts/ts_ofc)
- [ts_config_mttcs](https://github.com/lsst-ts/ts_config_mttcs)
- [ts_salobj](https://github.com/lsst-ts/ts_salobj)

## Usage

The usage can follow [here](https://ts-mtaos.lsst.io).

## Code Format

This code is automatically formatted by `black` using a git pre-commit hook.
To enable this:

1. Install the `black` Python package.
2. Run `git config core.hooksPath .githooks` once in this repository.

## Building Documentation

### Additional Requirements

The followings are the needed packages:

- [documenteer](https://github.com/lsst-sqre/documenteer)
- [plantuml](https://newcontinuum.dl.sourceforge.net/project/plantuml/plantuml.jar)
- [sphinxcontrib-plantuml](https://pypi.org/project/sphinxcontrib-plantuml/)

You can update `plantuml.jar` path in [doc/conf.py](doc/conf.py).

To build the documentation, run:

```bash
package-docs build
```

To remove the documents, do:

```bash
package-docs clean
```

See ["Building single-package documentation locally"](https://developer.lsst.io/stack/building-single-package-docs.html) for further details.
