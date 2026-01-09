=====
Usage
=====

Commands
========

You can run NTFC as a Python module:

.. code-block:: bash

   python -m ntfc [OPTIONS] COMMAND [ARGS]...

For commands details use ``--help`` option.

``collect`` command
-------------------

Collect-only test cases.

.. code-block:: bash

   python -m ntfc collect [OPTIONS] [COLLECT]


The ``COLLECT`` argument specify what data to print:

* ``collected`` - print collected items only.

* ``skipped`` - print skipped items only.

* ``all``-  (DEFAULT) print all possible data.

* ``silent`` - don't print any additional data.

Options:

* ``--testpath PATH`` - Path to test cases.
  Can be also set with environment variable ``NTFC_TESTPATH``.
  Default: ``./external/nuttx-testing``.

  With this option you can also narrow down the tests
  to run by specifying the path to the test sub-module,
  example: ``--testpath ./external/nuttx-testing/arch/nsh``

* ``--confpath PATH`` - Path to test configuration file.
  Can be also set with environmentvariable ``NTFC_CONFPATH``.
  Default: ``./external/config.yaml``

* ``--rebuild`` - Always rebuild configuration. Default: True.

``test`` command
----------------

Run test cases.

.. code-block:: bash

   python -m ntfc test [OPTIONS]

Test Filtering Options:

* ``-c, --modules TEXT`` - Execute specific test module(s).
  Use quotes for multiple modules: ``-c "module1 module2"`` or comma-separated: ``-c module1,module2``.
  Example: ``-c "Nuttx_System_Arch_Nsh Nuttx_System_Arch_Example"``

* ``-i, --index INTEGER`` - Select and execute individual tests by index.
  Use with ``-l`` to see available indexes. Can be specified multiple times.
  Example: ``-i 1 -i 5 -i 10``

* ``--loops INTEGER`` - Number of times to run each test case.
  Default: 1.
  Example: ``--loops 3`` will run each test 3 times

* ``-l, --list-tests`` - List all available test cases with their indexes.
  Displays test index, name, file location, and line number in a formatted table.
  Use with ``-c`` to filter by module.

* ``--list-modules`` - List all available test modules.
  Displays module name, number of tests, and directory in a formatted table.

Report Options:

* ``--xml`` - Store the XML report.

* ``--resdir PATH`` - Where to store the test results.
  Default: ./result

Test Execution Options:

* ``--testpath PATH`` - Path to test cases.
  Can be also set with environment variable ``NTFC_TESTPATH``.
  Default: ``./external/nuttx-testing``

* ``--confpath PATH`` - Path to test configuration file.
  Can be also set with environmentvariable ``NTFC_CONFPATH``.
  Default: ``./external/config.yaml``
  For details look at ``docs/config.yaml``.

* ``--jsonconf PATH`` - Path to test session configuration file.
  Default: None.
  For details look at ``docs/session.json``.

* ``--nologs`` - When set, test logs are not saved locally

* ``--exitonfail / --no-exitonfail`` - Stop test execution on first failure.
  Default: False (continue on failure).

* ``--rebuild`` - Always rebuild configuration. Default: True.

* ``--flash`` - Flash image. Default: False.

``build`` command
----------------

Build NuttX test image from YAML configuration and try to flash.
Build command always rebuild configuration and at default try to
flash image to DUT.

.. code-block:: bash

   python -m ntfc build [OPTIONS]

Options:

* ``--confpath PATH`` - Path to test configuration file.
  Can be also set with environmentvariable ``NTFC_CONFPATH``.
  Default: ``./external/config.yaml``

* ``--flash / --no-flash``  Flash image. Default: True.
