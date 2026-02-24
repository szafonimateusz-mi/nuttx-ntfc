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

"""Sqlite database handler."""

import sqlite3
import time
from typing import Any, List, Tuple

from ntfc.log.logger import logger


class DBLib:
    """This class implements Sqlite database handler."""

    def __init__(self, dbpath: str) -> None:
        """Initialize database handler."""
        self.timestamp = int(time.time())
        self.conn = sqlite3.connect(dbpath)
        self.cursor = self.conn.cursor()

    def _close_db(self) -> None:
        """Close database."""
        self.cursor.close()
        self.conn.close()

    def _create_table(self, sqlcmd: str) -> None:
        """Create table."""
        try:
            sql_commands = [
                cmd.strip() for cmd in sqlcmd.split(";") if cmd.strip()
            ]
            for command in sql_commands:
                try:
                    self.cursor.execute(command)
                    logger.info("Create new table for sqlite Successfully")
                except sqlite3.Error as e:
                    logger.info(f"Error executing SQL command: {command}")
                    logger.info(f"Error message: {e}")
                    continue
            self.conn.commit()
        except sqlite3.Error as e:
            logger.info(f"Error creating table, error message: {e}")

    def _insert_data(
        self,
        tablename: str,
        lowercaseheaders: List[str],
        data: List[Tuple[Any, ...]],
    ) -> None:
        """Insert data."""
        try:
            insert_sql = (
                f"INSERT INTO {tablename} {tuple(lowercaseheaders)} "
                f"VALUES (?, ?, ?, ?, ?, ?)"
            )

            self.cursor.executemany(insert_sql, data)
            self.conn.commit()
            logger.info("Insert performance data from csv Successfully")
        except sqlite3.Error as e:
            logger.info(f"Error executing insert sql, error message: {e}")
