====================================
Products Configuration (config.yaml)
====================================

This file defines device-under-test (DUT) setup and global configuration.

**Structure for single DUT:**

.. code-block:: yaml

   config:
     # global configuration

   product:
     name: "product-name"     # Product identifier
     cores:                   # List of product cores
       core0:                 # Core0 entry
         name: 'core0-name'
         device: 'sim|qemu|serial'
         # Device-specific configuration

       core1:                 # Core1 entry
         name: 'core1-name'
         device: 'sim|qemu|serial'
         # Device-specific configuration


**Structure for many DUT:**

.. code-block:: yaml

   config:
     # global configuration

   product0:
     name: "product0-name"    # Product 0 identifier
     cores:
       core0:
         name: 'core-name'
         device: 'sim|qemu|serial'
         # Device-specific configuration

   product1:
     name: "product1-name"    # Product 1 identifier
     cores:
       core0:
         name: 'core-name'
         device: 'sim|qemu|serial'
         # Device-specific configuration


Platform Types
==============

NTFC supports two multi-core platform types:

**AMP (Asymmetric Multi-Processing)** - Default mode

In AMP mode, each core has its own device instance. This is managed by
the :class:`ntfc.cores.CoresHandler`. Tests are executed on
specific cores based on the core configuration. Each core operates independently
with its own memory space and execution context.

.. code-block:: yaml

   product:
     name: "product-name"
     platform: "amp"              # Optional, defaults to "amp"
     cores:
       core0:
         name: 'main'
         device: 'qemu'
         # ... core0 configuration
       core1:
         name: 'cpu1'
         device: 'qemu'
         # ... core1 configuration

Use AMP when:

- Each core has its own device/serial interface
- Cores run independently
- Testing different firmware images on each core

**SMP (Symmetric Multi-Processing)**

In SMP mode, all cores share the same device instance, coordinated by
the :class:`ntfc.cores.CoresHandler`. NTFC automatically
switches between cores during test execution using the NuttX ``cu`` (call up)
command. Tests are parametrized to run on each core sequentially.

.. code-block:: yaml

   product:
     name: "product-name"
     platform: "smp"              # Enable SMP mode
     cores:
       core0:
         name: 'main'
         device: 'serial'
         exec_path: '/dev/ttyUSB0'
         exec_args: '115200,n,8,1'
         # ... core0 configuration
       core1:
         name: 'cpu1'
         # core1 shares the same device in SMP mode
       core2:
         name: 'cpu2'
         # core2 shares the same device in SMP mode

Use SMP when:

- Multiple cores share the same device/serial interface
- Testing SMP NuttX configuration
- Need to run tests on different cores through a single interface

**Running tests on specific cores (SMP):**

When SMP mode is enabled, you can specify which cores to run tests on using
the ``--run_in_cores`` option:

.. code-block:: bash

   python -m ntfc test --run_in_cores=main,cpu1,cpu2

This will parametrize tests to run on each specified core. NTFC automatically
handles core switching before and after each test execution.

Device Types
============

Simulator (sim)
---------------

This device type is implemented in :class:`ntfc.device.sim.DeviceSim`.

.. code-block:: yaml

   cores:
     core0:
       name: 'main'
       device: 'sim'
       exec_path: ''   # empty for sim
       exec_args: ''   # empty for sim

QEMU
----

This device type is implemented in :class:`ntfc.device.qemu.DeviceQemu`.

.. code-block:: yaml

   cores:
     core0:
       name: 'main'
       device: 'qemu'
       exec_path: 'qemu-system-arm'
       exec_args: '-cpu cortex-a7 -nographic -machine virt'

Common QEMU executables: ``qemu-system-arm``, ``qemu-system-aarch64``,
``qemu-system-i386``, ``qemu-system-x86_64``, ``qemu-system-riscv64``

At default NTFC automatically add the ``-kernel path_to_elf_image`` option
to ``exec_args``. You can also add your custom boot parameter with
``$IMAGE_ELF``, where ``$IMAGE_ELF`` will be replaced with the path to the ELF.

Serial Device
-------------

This device type is implemented in :class:`ntfc.device.serial.DeviceSerial`.
For real hardware with UART communication:

.. code-block:: yaml

   cores:
     core0:
       name: 'main'
       device: 'serial'
       exec_path: '/dev/ttyACM0'
       exec_args: '115200,n,8,1'
       defconfig: 'boards/arm/stm32h7/nucleo-h743zi/configs/ntfc'
       flash: 'st-flash write $IMAGE_BIN 0x08000000'
       reboot: 'st-flash reset'

**Serial Settings Format:** ``BAUDRATE,PARITY,DATABITS,STOPBITS``

- BAUDRATE: 9600, 19200, 38400, 57600, 115200, etc.
- PARITY: 'n' (None), 'e' (Even), 'o' (Odd), 'm' (Mark), 's' (Space)
- DATABITS: 5, 6, 7, or 8
- STOPBITS: 1, 1.5, or 2

Configuration Approaches
========================

**Auto-build:**

NTFC can automatically builds NuttX with CMake when core configuration has:

.. code-block:: yaml

   defconfig: 'path/to/nuttx/defconfig'

You can specify additional defines passed to CMake with:

.. code-block:: yaml

   dcmake:
     DEFINE1: "VALUE1"
     DEFINE2: "VALUE2"

``dcmake`` uses the same YAML mapping style as ``build_env`` (``KEY: VALUE``).

You can also pass environment variables to the build process (CMake configure
and ``cmake --build``), for example to select a specific compiler version:

.. code-block:: yaml

   config:
     cwd: './external'
     build_dir: './build'
     build_env:
       CC: gcc-14
       CXX: g++-14

   product:
     name: "product"
     cores:
       core0:
         name: 'main'
         device: 'serial'
         defconfig: 'boards/arm/stm32h7/nucleo-h743zi/configs/ntfc'
         build_env:              # optional per-core override
           CXX: g++-14

Build directory and path to NuttX repositories must be specified in global
configuration section:

.. code-block:: yaml

  config:
    cwd: './external'
    build_dir: './build'     # Build output directory
    build_env:               # Optional env vars for cmake configure/build
      CC: gcc-14
      CXX: g++-14

Use when:

- Fresh build needed for each test run
- Development/testing workflow
- Easier to use

**Pre-compiled ELF:**

Use existing NuttX binary and skip build step when product configuration has:

.. code-block:: yaml

   elf_path: './external/nuttx/nuttx'
   conf_path: './external/nuttx/.config'

Use when:

- Faster repeated test runs
- Pre-built test images available
- CI environments with cached binaries

**Flash and Reboot (real hardware):**

Automate firmware deployment and device reset is handled with two parameters:

- ``flash``: System command executed before tests
- ``reboot``: System command to reset device between test runs

Flash command can use special tags that are handled by NTFC:

- ``$IMAGE_BIN`` is replaced by path to ``nuttx.bin``.
- ``$IMAGE_HEX`` is replaced by path to ``nuttx.hex``.

Example usage with ``st-flash`` tool:

.. code-block:: yaml

   flash: 'st-flash write $IMAGE_BIN 0x08000000'
   reboot: 'st-flash reset'

Product Configuration Fields
============================

These fields are parsed by :class:`ntfc.productconfig.ProductConfig`.

.. list-table::
   :header-rows: 1

   * - Field
     - Description
   * - ``name``
     - Product identifier
   * - ``platform``
     - Platform type: ``amp`` (default) or ``smp``.
       See `Platform Types`_ section
   * - ``cores``
     - List of product cores (core0, core1, etc.)

Core Configuration Fields
=========================

These fields are parsed by :class:`ntfc.coreconfig.CoreConfig`.

.. list-table::
   :header-rows: 1

   * - Field
     - Description
   * - ``name``
     - Human-readable core name
   * - ``device``
     - Device type: ``sim``, ``qemu``, or ``serial``
   * - ``exec_path``
     - QEMU executable name or serial port device (``/dev/ttyACM0``, ``COM1``,
       etc.)
   * - ``exec_args``
     - QEMU arguments or serial settings
   * - ``defconfig``
     - Path to NuttX defconfig (auto-build)
   * - ``elf_path``
     - Path to ELF binary (pre-compiled)
   * - ``conf_path``
     - Path to NuttX ``.config`` file (pre-compiled)
   * - ``flash``
     - System command to flash firmware (work in progress)
   * - ``reboot``
     - System command to reboot device
   * - ``dcmake``
     - Defines passed to CMake build (YAML mapping syntax, e.g.
       ``FEATURE_X: ON``)
   * - ``build_env``
     - Environment variables passed to CMake configure/build for this core.
       Overrides ``config.build_env`` keys when both are set
