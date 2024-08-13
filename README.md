![eodata](./docs/images/header.svg)

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Cirras_eodata&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Cirras_eodata)
[![Lint](https://github.com/Cirras/eodata/actions/workflows/lint.yml/badge.svg?event=push)](https://github.com/Cirras/eodata/actions/workflows/lint.yml)
[![Build](https://github.com/Cirras/eodata/actions/workflows/build.yml/badge.svg?event=push)](https://github.com/Cirras/eodata/actions/workflows/build.yml)

A tool for creating and modifying the EDF data files from Endless Online.

## Screenshots

![Main window](./docs/images/main_window.png)

## Development

### Requirements

- [Python](https://www.python.org/downloads/) 3.10+
- [Hatch](https://hatch.pypa.io/latest/install/)

### Available Commands

| Command                     | Description                                            |
| --------------------------- | ------------------------------------------------------ |
| `hatch build`               | Build package                                          |
| `hatch clean`               | Remove build artifacts                                 |
| `hatch run lint:format`     | Format source files using `black`                      |
| `hatch run lint:style`      | Check formatting using `black`                         |
| `hatch run lint:typing`     | Check typing using `mypy`                              |
| `hatch run lint:all`        | Check formatting using `black` and typing using `mypy` |
| `hatch run release:prepare` | Prepare and tag a new release                          |
| `hatch run release:deploy`  | Build and deploy the application                       |
