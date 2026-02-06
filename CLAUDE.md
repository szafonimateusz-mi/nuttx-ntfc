# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

NTFC (NuttX Test Framework for Community) is a Python-based testing framework for automating tests of the NuttX RTOS on various platforms and hardware targets. It acts as a bridge between pytest and NuttX devices/simulators using Click CLI, YAML configuration, and dynamic test discovery via ELF symbol parsing.

## Common Commands

### Development Setup

```bash
# Install dependencies (requires Python 3.10+)
pip install -e .

# Install tox (highly recommended for development)
pip install --user tox
```

### Running Tests and Linting

The project uses `tox` to automate development tasks. Run all checks before submitting:

```bash
# Run all checks (tox targets from tox.ini)
tox

# Run tests with coverage report (100% coverage required for CI)
tox -e py

# Run tests without coverage (parallel execution with 4 workers)
tox -e test

# Run single test file
pytest tests/test_report.py -v

# Run single test function
pytest tests/test_report.py::test_function_name -v

# Format code (isort + black)
tox -e format

# Run type checking (mypy with strict mode)
tox -e type

# Run flake8 linting
tox -e flake8

# Run pylint (informational, not blocking CI)
tox -e pylint

# Run code style checks without formatting
tox -e lint
```

### Important Notes on Quality Standards

- **Type annotations required**: Untyped function definitions are disallowed (`mypy --disallow-untyped-defs`). All functions must have type hints.
- **Coverage requirement**: CI requires 100% test coverage. Use `#pragma: no cover` for code that can't be easily tested.
- **Code style**: Black line length is 79 characters. isort is configured for profile "black".
- **CI will fail if linters fail**: Ensure all formatters and type checkers pass locally before pushing.

### CLI Usage

```bash
# Main entry point
ntfc --help

# Build NuttX configuration
ntfc build --help

# Collect available tests for a configuration
ntfc collect --help

# Run tests
ntfc test --help
```

## Architecture Overview

### High-Level Component Structure

1. **CLI Layer** (`src/ntfc/cli/`): Click-based command-line interface with environment context management
   - `main.py`: Main CLI entry point with dynamic command loading
   - `environment.py`: Persistent context passed between CLI commands
   - `clitypes.py`: Shared Click option definitions

2. **Command Layer** (`src/ntfc/commands/`): Specialized CLI commands
   - `cmd_build.py`: Build NuttX images
   - `cmd_test.py`: Execute tests
   - `cmd_collect.py`: Collect and list available tests

3. **Configuration System**: Three-tier configuration hierarchy
   - `envconfig.py:EnvConfig`: Environment-level config (global settings)
   - `productconfig.py:ProductConfig`: Product/target config
   - `coreconfig.py:CoreConfig`: Core/instance-specific config
   - Loaded from YAML files (supports directory of YAML files that merge together)

4. **Product & Core Management**:
   - `product.py:Product`: Represents a product under test
   - `cores.py:CoresHandler`: Manages multiple cores/instances of a product (parallel execution)
   - `core.py:ProductCore`: Individual core representing a running NuttX instance

5. **Device Abstraction Layer** (`src/ntfc/device/`): OS and transport-specific implementations
   - `nuttx.py:DeviceNuttx`: NuttX OS commands and detection
   - `qemu.py:DeviceQemu`: QEMU simulator management
   - `sim.py:DeviceSim`: NuttX simulator
   - `serial.py:DeviceSerial`: Serial port communication
   - `oscommon.py:OSCommon`: Base class for OS implementations
   - Device selection happens at runtime in `getdev.py:get_device()`

6. **Pytest Integration** (`src/ntfc/pytest/`): Custom pytest plugins
   - `mypytest.py:MyPytest`: Main pytest orchestrator using custom plugins
   - `collector.py:CollectorPlugin`: Discovers available tests based on NuttX ELF symbols
   - `runner.py:RunnerPlugin`: Executes tests and validates output
   - `configure.py:PytestConfigPlugin`: Configures pytest session
   - `collected.py:Collected`: Stores collection results
   - Tests are discovered dynamically from ELF symbols when `CONFIG_DEBUG_SYMBOLS` is enabled

7. **Supporting Libraries**:
   - `lib/elf/elf_parser.py`: Parses ELF symbols from NuttX binaries
   - `lib/performance/`: Performance monitoring and data processing
   - `report.py`: Test result summary generation
   - `builder.py`: CMake-based NuttX building
   - `plugins_loader.py`: Dynamic plugin discovery and loading

### Workflow Flow

1. **Configuration Loading**: YAML files define target device, build parameters, and test settings
2. **Optional Build Phase**: NuttX can be built/rebuilt if config indicates new build needed
3. **Test Discovery**: Pytest collector inspects NuttX ELF binary for available test symbols
4. **Test Filtering**: Tests are filtered based on configuration and ELF symbols
5. **Test Execution**: Tests run by sending NSH commands to NuttX instance
6. **Output Validation**: Pytest monitors for crashes, busy loops, and validates command output
7. **Result Reporting**: Test results aggregated and reports generated (HTML, JSON optional)

### Configuration-Driven Architecture

The entire system is driven by YAML configuration. Key configuration sections:

- `config`: Global test execution settings (loops, timeouts, etc.)
- Products (top-level keys): Each product represents a testable system
  - `cores`: List of cores/instances to run tests on
    - Device type (serial, qemu, sim)
    - Device parameters (port, image path, etc.)
    - Environment variables and build settings
  - `tests`: Test discovery patterns and filtering

Configurations can reference environment variable placeholders like `$IMAGE_BIN` and `$IMAGE_HEX`.

## Key Development Areas

### Adding New Tests

Tests are standard pytest test functions but must be in modules that pytest discovers. Test cases are discovered from NuttX ELF symbols using debug symbols. See `docs/writing-test-cases.rst` for detailed guidance.

### Extending Device Support

New device types implement the `OSCommon` interface in `src/ntfc/device/`. The device abstraction handles:
- Command execution and output reading
- OS-specific prompt detection
- Crash/failure detection
- System state monitoring

Add new device type in `src/ntfc/device/` and register in `getdev.py:get_device()`.

### Test Collection and Filtering

Collection happens in `src/ntfc/pytest/collector.py`. Tests are filtered based on:
- Configuration matching
- ELF symbol availability (requires `CONFIG_DEBUG_SYMBOLS`)
- User-specified test patterns

Modify `CollectorPlugin` to change collection behavior.

### Parallel Execution

Multi-core/multi-device execution is handled by `CoresHandler` which uses thread pools. The `run_parallel()` function in `parallel.py` coordinates execution across multiple instances. Performance metrics can be stored in SQLite via `lib/performance/sqllite_lib.py`.

## Project Structure

```
src/ntfc/
├── cli/                    # Click CLI interface
├── commands/               # Individual CLI commands
├── device/                 # Device abstraction layer
├── lib/                    # Support libraries (ELF parsing, performance)
├── pytest/                 # Pytest plugins and integration
├── builder.py              # NuttX build management
├── cores.py                # Multi-core coordination
├── core.py                 # Single core implementation
├── product.py              # Product under test
├── coreconfig.py           # Configuration classes
├── productconfig.py        #
├── envconfig.py            #
├── plugins_loader.py       # Dynamic plugin discovery
├── report.py               # Result reporting
├── parallel.py             # Parallel execution
└── logger.py               # Logging setup

tests/                      # Test suite for NTFC itself
├── resources/              # Test fixtures and resources
├── device/                 # Device tests
├── lib/                    # Library tests
├── pytest/                 # Pytest plugin tests
└── cli/                    # CLI tests
```

## Important Configuration Points

- **Type System**: All new code must use type hints. mypy runs in strict mode with `--disallow-untyped-defs`.
- **Error Handling**: Code should detect NuttX crashes (via `CONFIG_DEBUG_ASSERTIONS`) and busy loops (via timeout monitoring).
- **Performance**: Multi-core tests use thread-based parallelism for concurrent device access.
- **Plugin System**: Commands and plugins are dynamically loaded via `plugins_loader.py`. New commands should be auto-registered.

## Testing This Codebase

The test suite (`tests/`) tests NTFC itself, not NuttX applications:

- `test_core.py`, `test_cores.py`: Core functionality
- `test_coreconfig.py`, `test_productconfig.py`: Configuration handling
- `test_device/`: Device abstraction tests
- `test_pytest/`: Pytest integration tests
- `test_report.py`: Report generation (currently being improved)

All must pass with 100% coverage for CI to pass.
