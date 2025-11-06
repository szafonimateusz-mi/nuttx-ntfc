# TODO

This is a to-do list for the NTFC project.

## Package

- [ ] More unit tests, we want 100% coverage result.
- [ ] Release package (PyPI).
- [ ] (SOMEDAY) Fix pylint issues.
- [ ] (SOMEDAY) Fix mypy issues (typing).

## Documentation

- [ ] Details on what exactly NFC does
- [ ] Guide on how to write your own test cases
- [ ] Guide on how to support your own boards (YAML config)

## Features

- [ ] Support for serial port communication with the device.
- [ ] Support for hardware reset if the device support this feature.
      Required for real HW testing, for QEMU we can use QEMU monitor.
- [ ] Support for ELF building from the tool level.
- [ ] Support for ELF flashing from the tool level (HW testing)
- [ ] Better workflow with CMake - handle many NuttX images at once.
- [ ] Support for AMP test cases for host-based simulations (rpmsg).
- [ ] Running test cases on multiple threads in parallel for host-based configuration.
      Pytest-xdist won't help here.
- [ ] Get rid of the dependency on NSH.
      At this point, a shell is required and NSH must be the entry point.
- [ ] List of test cases to be executed from the text file.
- [ ] Test configuration entirely from CLI, without the need for YAML configuration?
      Which option is better? Maybe support for both?
- [ ] (SOMEDAY) Create a sample external plugin for the tool.

## Misc

- [ ] Unit test cases depends now on pre-build NuttX sim image.
