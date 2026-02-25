============
NTFC Roadmap
============

This is the general roadmap for the project.

Python Package
==============

* Release package (PyPI).

  How to release Python package under Apache Foundation?

* Support for Windows and Mac. So far NTFC has only been tested with Linux.

Code Quality
============

* Unit test cases depends now on pre-build NuttX sim image.

  Build simulator image used in test cases in an initial phase of testing.

* Revisit all "pragma: no cover" and "type: ignore".

* Fix pylint issues.

Documentation
=============

* Build documentation to HTML so it can be hosted online.

NuttX CI
========

* enable more tests for citest configurations

* enable more architectures

Parallel executuon for host-based tests
=======================================

* Run tests for all configured products.

* Running test cases on multiple threads in parallel for host-based configuration.
  Pytest-xdist won't help here.

AMP test cases
==============

* Support for AMP test cases for host-based simulations (rpmsg).

Devices
=======

* Support for SSH/TELNET communication with the device.

* Support for ADB communication with the device.

Failure detection
=================

* Compare ``free`` and ``ps`` before and after command call.

Debugging features
==================

* Support for GDB debugging.

* Parse coredump.

* Integration with ``tools/pynuttx``

Other improvements
==================

* Custom path to NuttX repositories.

* Improve ntfc.yaml handling:

  - Detect module configuration in parent dir

* Migrate session.json to yaml file so we can drop json dependency.

* Get rid of the dependency on NSH.
  At this point, a shell is required and NSH must be the entry point.

* Test configuration entirely from CLI, without the need for YAML configuration?
  Does it make sense now? Which option is better? Maybe support for both approach?

Plugins
=======

* (SOMEDAY) Create a sample external plugin for the tool.
