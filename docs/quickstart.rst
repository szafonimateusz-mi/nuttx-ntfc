===========
Quick start
===========

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
     git clone https://github.com/szafonimateusz-mi/nuttx-testing external/nuttx-testing

5. Configure and build NuttX in ``external/nuttx``.

   A sample configuration for ``SIMULATOR``, QEMU targets can
   be found at ``docs/boards``. There is also a configuration for ``nucleo-h743zi``
   that demonstrating the use of the serial port to communicate with the DTU.

   For ``SIMULATOR``::

     cd external/nuttx
     mkdir boards/sim/sim/sim/configs/ntfc
     cp ../../docs/boards/sim/defconfig boards/sim/sim/sim/configs/ntfc
     ./tools/configure.sh sim/ntfc
     make -j
     cd ../..

   For ``QEMU-X86_64``::

     mkdir boards/x86_64/intel64/qemu-intel64/configs/ntfc
     cp ../../docs/boards/qemu-intel64/defconfig boards/x86_64/intel64/qemu-intel64/configs/ntfc
     ./tools/configure.sh qemu-intel64/ntfc
     make -j
     cd ../..

   For ``QEMU-ARMV7A``::

     mkdir boards/arm/qemu/qemu-armv7a/configs/ntfc
     cp ../../docs/boards/qemu-armv7a/defconfig boards/arm/qemu/qemu-armv7a/configs/ntfc
     ./tools/configure.sh qemu-armv7a/ntfc
     make -j
     cd ../..

   For ``QEMU-ARMV7R``::

     mkdir boards/arm/qemu/qemu-armv7r/configs/ntfc
     cp ../../docs/boards/qemu-armv7r/defconfig boards/arm/qemu/qemu-armv7r/configs/ntfc
     ./tools/configure.sh qemu-armv7r/ntfc
     make -j
     cd ../..

   For ``QEMU-ARMV8A``::

     mkdir boards/arm64/qemu/qemu-armv8a/configs/ntfc
     cp ../../docs/boards/qemu-armv8a/defconfig boards/arm64/qemu/qemu-armv8a/configs/ntfc
     ./tools/configure.sh qemu-armv8a/ntfc
     make -j
     cd ../..

   For ``QEMU-RISCV64``::

     mkdir boards/risc-v/qemu-rv/rv-virt/configs/ntfc64
     cp ../../docs/boards/qemu-riscv-rv-virt-64/defconfig boards/risc-v/qemu-rv/rv-virt/configs/ntfc64
     ./tools/configure.sh rv-virt/ntfc64
     make -j
     cd ../..

   For ``NUCLEO-H743ZI``::

     mkdir boards/arm/stm32h7/nucleo-h743zi/configs/ntfc
     cp ../../docs/boards/nucleo-h743zi/defconfig boards/arm/stm32h7/nucleo-h743zi/configs/ntfc
     ./tools/configure.sh nucleo-h743zi/ntfc
     make -j
     cd ../..

6. Collect test cases without running tests.

   For ``SIMULATOR``::

     python -m ntfc collect --confpath config/nuttx-sim.yaml

   For ``QEMU-X86_64``::

     python -m ntfc collect --confpath config/nuttx-qemu-x86_64.yaml

   For ``QEMU-ARMV7A``::

     python -m ntfc collect --confpath config/nuttx-qemu-armv7a.yaml

   For ``QEMU-ARMV7R``::

     python -m ntfc collect --confpath config/nuttx-qemu-armv7r.yaml

   For ``QEMU-ARMV8A``::

     python -m ntfc collect --confpath config/nuttx-qemu-armv8a.yaml

   For ``QEMU-RISCV64``::

     python -m ntfc collect --confpath config/nuttx-qemu-riscv-rv-virt-64.yaml

   For ``NUCLEO-H743ZI``::

     python -m ntfc collect --confpath config/nuttx-qemu-serial-stlink.yaml

   When you run NTFC with ``--debug`` option, tests that were detected but
   the conditions for running them are not met will also be listed.

7. Run test cases.

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

   For ``NUCLEO-H743ZI``::

     python -m ntfc test --confpath config/nuttx-qemu-serial-stlink.yaml
