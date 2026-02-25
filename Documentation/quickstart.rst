===========
Quick start
===========

Common initialization
=====================

1. Clone the NTFC repository::

     git clone <PATH_TO_NTFC_REPO>
     cd nuttx-ntfc

2. Create and activate a virtual environment::

     virtualenv venv
     source venv/bin/activate

3. Install the project in editable mode::

     pip install -e .

4. Prepare the test environment::

     git clone https://github.com/apache/nuttx.git external/nuttx
     git clone https://github.com/apache/nuttx-apps.git external/nuttx-apps
     git clone https://github.com/szafonimateusz-mi/nuttx-testing \
     external/nuttx-testing

5. Cherry-pick NTFC configurations::

     git fetch https://github.com/raiden00pl/nuttx.git vtfc_configs
     git rebase FETCH_HEAD

Automatically build DUT images
==============================

The tool allows you to automatically build configurations and run tests on
the created NuttX image.

Then run the ``test`` command that build which will build the image
and start testing.

For ``SIMULATOR``::

     python -m ntfc test --confpath config/nuttx-sim.yaml

For ``QEMU-X86_64``::

     python -m ntfc test --confpath config/nuttx-qemu-x86_64.yaml

For ``QEMU-ARMV7A``::

     python -m ntfc test --confpath config/nuttx-qemu-armv7a.yaml

For ``QEMU-ARMV7R``::

     python -m ntfc test --confpath config/nuttx-qemu-armv7r.yaml

For ``QEMU-ARMV8A``::

     python -m ntfc test --confpath config/nuttx-qemu-armv8a.yaml

For ``QEMU-RISCV64``::

     python -m ntfc test --confpath config/nuttx-qemu-riscv-rv-virt-64.yaml

There is also a configuration available that builds the all available
QEMU and SIM targets and runs parallel tests on all DUTs::

  python -m ntfc test --confpath=./config/nuttx-build-qemu-sim-ntfc.yaml

You can also run ``build`` command that only build image without starting tests.

Automatic build and Flash
=========================

For ``NUCLEO-H743ZI`` there is availalbe configuration that automatically
build, flash and test image:

1. Build image and flash::

     python -m ntfc build --confpath config/nuttx-nucleo-h743zi.yaml

2. Collect test cases without running tests::

     python -m ntfc collect --confpath config/nuttx-nucleo-h743zi.yaml

3. Run test cases::

     python -m ntfc test --confpath config/nuttx-nucleo-h743zi.yaml

Creating a DUT image manually
=============================

You can always manually build the NuttX image. Currently, such an example
is available in ``config/nuttx-custom-sim.yaml`` and
``config/nuttx-custom-serial.yaml``. Commands are the same like before:

1. Collect test cases without running tests::

     python -m ntfc collect --confpath config/nuttx-custom-sim.yaml

2. Run test cases::

     python -m ntfc test --confpath config/nuttx-custom-sim.yaml

Running specific test cases
===========================

You can narrow down the tests you run by specifying the exact path to the test
cases with the ``--testpath`` option. In the example below, we only run tests
dedicated to NSH::

     python -m ntfc test --confpath=./config/nuttx-build-qemu-sim-ntfc.yaml \
     --testpath ./external/nuttx-testing/arch/nsh

