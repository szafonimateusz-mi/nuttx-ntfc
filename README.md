# NTFC

NuttX Test Framework for Community.

## What is NTFC?

NTFC is a Python-based testing framework designed to automate the
testing of [NuttX RTOS](https://nuttx.apache.org/) on various
platforms. It provides a structured way to develop, discover,
and execute test cases against NuttX configurations.

## Purpose

NTFC enables developers to:

- **Validate NuttX functionality** across different configurations
  and hardware targets

- **Automate test execution** on NuttX devices for real hardware and
  host-based target

- **Detect system failures** including OS crashes and busy loop
  conditions

- **Dynamically discover applicable tests** based on the NuttX
  image configuration

- **Standardize testing workflows** using pytest, a widely-adopted
  Python testing framework

## How It Works

NTFC acts as a bridge between pytest and NuttX devices/simulators:

1. Loads a NuttX YAML configuration specifying the target device
   and build parameters

2. Builds or prepares the NuttX image (optionally flashing to
   hardware)

3. Discovers which test cases are applicable based on the NuttX
   configuration and ELF symbols

4. Executes tests by sending NSH commands to the running NuttX
   instance

5. Validates command output and monitors for system failures

This tool requires at least Python 3.10. Not tested with earlier
versions of Python.

## Features

- NuttX simulator, QEMU and devices with serial port are supported

- Run the command from NSH and compare with the expected output

- OS crash detection and busy loop detection

- Detection of supported test cases for a given NuttX image based on
  the configuration and image ELF file

## Installation

NTFC can be installed from source using pip. PyPI package release
is planned for future versions.

```bash
git clone <PATH_TO_NTFC_REPO>
cd ntfc
pip install -e .
```

NTFC requires Python 3.10 or later (not tested with older Python).

## Optional dependencies

- pytest-html - for HTML test reports
- pytest-json - for JSON test reports

## Usage

See [Documentation/quickstart](Documentation/quickstart.rst) for a quick start guide
and [Documentation/usage](Documentation/usage.rst) for detailed usage information.

### Preparing the Image for Testing

- ``CONFIG_DEBUG_SYMBOLS`` is required for automatic command
  detection
- ``CONFIG_DEBUG_FEATURES=y`` and ``CONFIG_DEBUG_ASSERTIONS=y`` are
  recommended for better error detection

### Test Cases

Currently available test case repositories:

- https://github.com/szafonimateusz-mi/nuttx-testing - NuttX RTOS
  functionality tests

For guidance on writing your own test cases, see
[Documentation/writing-test-cases](Documentation/writing-test-cases.rst).

## Contributing

To get started with developing NTFC, see
[CONTRIBUTING.md](CONTRIBUTING.md).

The roadmpa for the project can be found in [ROADMAP](Documentation/roadmap.rst).
