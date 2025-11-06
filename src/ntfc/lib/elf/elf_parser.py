############################################################################
# SPDX-License-Identifier: Apache-2.0
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.  The
# ASF licenses this file to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance with the
# License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations
# under the License.
#
############################################################################

"""ELF file parser for LTP test case extraction.

Used during test collection phase without fixture dependencies
"""

import logging
import os
import re
import subprocess
from typing import List, Union


class Symbol:
    """ELF symbol representation."""

    def __init__(self, name: str, address: str = "", symbol_type: str = ""):
        """Initialize ELF symbol representation."""
        self.name = name
        self.address = address
        self.type = symbol_type


class ElfParser:
    """ELF file parser for extracting symbols."""

    def __init__(self, elf_path: str):
        """Initialize ELF file parser."""
        if not os.path.exists(elf_path) and not self._is_elf_file(elf_path):
            raise AttributeError

        self.elf_path = elf_path
        self._symbols: List[Symbol] = []

    def _is_elf_file(self, path: str) -> bool:
        """Check if this is ELF file."""
        try:
            with open(path, "rb") as f:
                magic = f.read(4)
            return magic == b"\x7fELF"
        except Exception:
            return False

    @property
    def symbols(self) -> List[Symbol]:
        """Get all symbols from ELF file."""
        if not self._symbols:
            self._symbols = self._extract_symbols()
        return self._symbols

    def _extract_symbols(self) -> List[Symbol]:
        """Extract symbols using nm command."""
        if not os.path.exists(self.elf_path):
            logging.error(f"ELF file not found: {self.elf_path}")
            return []

        try:
            result = subprocess.run(
                ["nm", "--defined-only", self.elf_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

            symbols = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) >= 3:
                    address, symbol_type, name = parts[0], parts[1], parts[2]
                    symbols.append(Symbol(name, address, symbol_type))
                elif len(parts) >= 2:
                    symbol_type, name = parts[0], parts[1]
                    symbols.append(Symbol(name, symbol_type=symbol_type))
                elif len(parts) == 1:
                    name = parts[0]
                    symbols.append(Symbol(name))

            return symbols

        except subprocess.CalledProcessError as e:
            logging.error(
                f"Failed to extract symbols from {self.elf_path}: {e}"
            )
            return []
        except Exception as e:
            logging.error(f"Unexpected error parsing ELF symbols: {e}")
            return []

    def get_symbols_by_pattern(
        self, prefix: str = "", suffix: str = ""
    ) -> List[Symbol]:
        """Filter symbols by prefix and suffix."""
        return [
            s
            for s in self.symbols
            if s.name.startswith(prefix) and s.name.endswith(suffix)
        ]

    def has_symbol(self, symbol_name: Union[str, re.Pattern]) -> bool:
        """Check if symbol exists."""
        if isinstance(symbol_name, str):
            return any(symbol.name == symbol_name for symbol in self.symbols)
        elif isinstance(symbol_name, re.Pattern):
            return any(
                symbol_name.search(symbol.name) for symbol in self.symbols
            )
        else:
            raise ValueError("symbol_name must be either str or re.Pattern")
