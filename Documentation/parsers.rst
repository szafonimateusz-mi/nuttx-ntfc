=======
Parsers
=======

NTFC provides built-in parsers for test frameworks running directly on the
target. Each test case is automatically discovered and mapped to an individual
parametrized pytest item, so pass/fail status is reported per test, not per
binary.

Supported Frameworks
====================

.. list-table::
   :header-rows: 1

   * - Fixture
     - Framework
     - Discovery command
     - Run-single command
   * - ``cmocka_parser``
     - `cmocka <https://cmocka.org/>`_
     - ``<binary> --list``
     - ``<binary> --test <name>``
   * - ``gtest_parser``
     - `Google Test <https://google.github.io/googletest/>`_
     - ``<binary> --gtest_list_tests``
     - ``<binary> --gtest_filter=<name>``
   * - ``custom_parser``
     - Any framework (user-defined)
     - Configurable via ``list_args``
     - Configurable via ``run_args``

``TestResult`` Object
=====================

:meth:`~ntfc.parsers.base.AbstractTestParser.run_single` returns a
:class:`~ntfc.parsers.base.TestResult` dataclass:

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``name``
     - ``str``
     - Full test name (e.g. ``test_foo``)
   * - ``passed``
     - ``bool``
     - ``True`` if the test passed
   * - ``output``
     - ``str``
     - Raw device output from the test run
   * - ``duration``
     - ``Optional[float]``
     - Elapsed seconds (if reported by the framework)

Discovery Mechanism
===================

NTFC tries to resolve test names at collection time in two stages:

1. **ELF symbol scan** — if ``elf_path`` is configured and a valid ELF file
   is found, :class:`~ntfc.lib.elf.elf_parser.ElfParser` is used.  ``cmocka``
   currently returns an empty list here (symbols are not reliably named), so
   the fallback below is always used.

2. **Device discovery** — the binary is run on the target with the
   framework's list command.  The output is parsed into a list of test names.

cmocka Parser
=============

The ``cmocka_parser`` fixture supports the
`cmocka <https://cmocka.org/>`_ unit testing framework.  Test cases are
discovered by running ``<binary> --list`` on the target and executed
individually with ``<binary> --test <name>``.

Basic Usage
-----------

Add ``@pytest.mark.parser_binary`` and request the ``cmocka_parser`` fixture.
The marker takes the **NuttX shell command name** of the binary — the same
name you would type at the ``nsh>`` prompt.  NTFC discovers all tests at
collection time and parametrizes the Python test function automatically.

.. code-block:: python

   import pytest

   @pytest.mark.parser_binary("cmocka_bin")
   def test_cmocka_suite(cmocka_parser):
       result = cmocka_parser.run_single()
       assert result.passed, result.output

Pytest output for a binary with three tests:

.. code-block:: text

   PASSED  test_cmocka_suite[test_foo]
   FAILED  test_cmocka_suite[test_bar]
   PASSED  test_cmocka_suite[test_baz]

Filtered Discovery
------------------

Pass an optional ``filter`` kwarg to limit discovered tests to names
matching a shell-style wildcard pattern (applied via :func:`fnmatch.fnmatch`):

.. code-block:: python

   @pytest.mark.parser_binary("cmocka_bin", filter="test_audio_*")
   def test_audio_only(cmocka_parser):
       result = cmocka_parser.run_single()
       assert result.passed, result.output

Running All or Filtered Tests Programmatically
----------------------------------------------

.. code-block:: python

   @pytest.mark.parser_binary("cmocka_bin")
   def test_run_all(cmocka_parser):
       results = cmocka_parser.run_all()   # Dict[str, TestResult]

   @pytest.mark.parser_binary("cmocka_bin")
   def test_run_filtered(cmocka_parser):
       results = cmocka_parser.run_filtered("test_audio_*")

gtest Parser
============

The ``gtest_parser`` fixture supports the
`Google Test <https://google.github.io/googletest/>`_ framework.  Test cases
are discovered by running ``<binary> --gtest_list_tests`` on the target and
executed with ``<binary> --gtest_filter=<Suite.TestName>``.

Because gtest registers tests at runtime (not via ELF symbols), discovery
always uses the device command.  All tests for a given binary are run in a
single invocation and results are cached; each parametrized pytest item reads
its outcome from the cache without issuing a second device command.

Basic Usage
-----------

Add ``@pytest.mark.parser_binary`` and request the ``gtest_parser`` fixture.
The marker takes the **NuttX shell command name** of the binary.  NTFC
discovers all test cases at collection time and parametrizes the Python test
function automatically.  Test names use the ``Suite.TestName`` format produced
by gtest.

.. code-block:: python

   import pytest

   @pytest.mark.parser_binary("gtest_bin")
   def test_gtest_suite(gtest_parser):
       result = gtest_parser.run_single()
       assert result.passed, result.output

Pytest output for a binary with three tests:

.. code-block:: text

   PASSED  test_gtest_suite[MathTest.AddTwoNumbers]
   FAILED  test_gtest_suite[MathTest.DivByZero]
   PASSED  test_gtest_suite[StringTest.EmptyString]

Filtered Discovery
------------------

Pass an optional ``filter`` kwarg to limit discovered tests to names matching
a shell-style wildcard pattern (applied via :func:`fnmatch.fnmatch`):

.. code-block:: python

   @pytest.mark.parser_binary("gtest_bin", filter="MathTest.*")
   def test_math_only(gtest_parser):
       result = gtest_parser.run_single()
       assert result.passed, result.output

Running All or Filtered Tests Programmatically
----------------------------------------------

.. code-block:: python

   @pytest.mark.parser_binary("gtest_bin")
   def test_run_all(gtest_parser):
       results = gtest_parser.run_all()   # Dict[str, TestResult]

   @pytest.mark.parser_binary("gtest_bin")
   def test_run_filtered(gtest_parser):
       results = gtest_parser.run_filtered("MathTest.*")

Custom Parser
=============

The ``custom_parser`` fixture supports any test framework by letting you
describe its output format with regex patterns.  Pass ``list_pattern`` and
``result_pattern`` directly to ``@pytest.mark.parser_binary`` and request
the ``custom_parser`` fixture.

Configuration
-------------

.. list-table::
   :header-rows: 1

   * - Parameter
     - Default
     - Description
   * - ``list_pattern``
     - *(required)*
     - Regex applied to each line of list output. Must contain a ``name``
       group; ``suite`` is optional.
   * - ``result_pattern``
     - *(required)*
     - Regex applied to run output. Must contain ``name`` and ``status``
       groups.
   * - ``success_value``
     - ``"PASS"``
     - Value of ``status`` that means the test passed.
   * - ``list_args``
     - ``"--list"``
     - Arguments passed to the binary to enumerate tests.
   * - ``run_args``
     - ``"{name}"``
     - Argument template for running one test (``{name}`` is substituted).
   * - ``filter_args``
     - ``"{filter}"``
     - Argument template for ``run_filtered`` (``{filter}`` is substituted).

Usage
-----

Suppose the binary prints this when listing tests::

   TEST: test_encode
   TEST: test_decode
   TEST: test_roundtrip

And this when running a single test::

   PASS test_encode

Map these formats to the parser with named regex groups:

.. code-block:: python

   @pytest.mark.parser_binary(
       "mybin",
       list_pattern=r"TEST:\s+(?P<name>\w+)",
       result_pattern=r"(?P<status>PASS|FAIL)\s+(?P<name>\w+)",
   )
   def test_mybin(custom_parser):
       result = custom_parser.run_single()
       assert result.passed, result.output

NTFC runs ``mybin --list``, matches every line against ``list_pattern`` to
build the test list, then runs ``mybin <name>`` for each test and matches
the output against ``result_pattern``.  The ``status`` group is compared
against ``success_value`` (default ``"PASS"``) to decide pass/fail.

With suite grouping — when the binary groups tests by suite in its list
output, add an optional ``suite`` named group to ``list_pattern``::

   [audio] test_encode
   [audio] test_decode
   [video] test_render

Run output::

   OK test_encode
   ERROR test_decode

.. code-block:: python

   @pytest.mark.parser_binary(
       "mybin",
       list_pattern=r"\[(?P<suite>\w+)\]\s+(?P<name>\w+)",
       result_pattern=r"(?P<status>OK|ERROR)\s+(?P<name>\w+)",
       success_value="OK",
   )
   def test_mybin(custom_parser):
       result = custom_parser.run_single()
       assert result.passed, result.output

With custom CLI arguments — when the binary uses non-standard subcommands
instead of ``--list`` / ``<name>``::

   # list command:  mybin list
   CASE: test_encode
   CASE: test_decode

   # run command:   mybin run test_encode
   [PASSED] test_encode

.. code-block:: python

   @pytest.mark.parser_binary(
       "mybin",
       list_pattern=r"CASE:\s+(?P<name>\w+)",
       result_pattern=r"\[(?P<status>PASSED|FAILED)\]\s+(?P<name>\w+)",
       list_args="list",
       run_args="run {name}",
       filter_args="run {filter}",
       success_value="PASSED",
   )
   def test_mybin(custom_parser):
       result = custom_parser.run_single()
       assert result.passed

Direct API
----------

:class:`~ntfc.parsers.custom.CustomParser` can also be used without the
pytest fixture:

.. code-block:: python

   from ntfc.parsers.custom import CustomParser, CustomParserConfig

   cfg = CustomParserConfig(
       list_pattern=r"TEST:\s+(?P<name>\w+)",
       result_pattern=r"(?P<status>PASS|FAIL)\s+(?P<name>\w+)",
   )
   parser = CustomParser(core, "mybin", cfg)

   # discover tests
   items = parser.get_tests()                    # List[TestItem]
   items = parser.get_tests(filter="test_enc*")  # filtered by fnmatch

   # run tests
   result = parser.run_single("test_encode")     # TestResult
   results = parser.run_all()                    # Dict[str, TestResult]
   results = parser.run_filtered("test_enc*")    # Dict[str, TestResult]
