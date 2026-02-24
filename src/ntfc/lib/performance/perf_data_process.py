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

"""Process performance data."""

import csv
import json
import os
import re
import time
from typing import TYPE_CHECKING, Any, List, Tuple

from ntfc.lib.performance.sqllite_lib import DBLib
from ntfc.log.logger import logger

if TYPE_CHECKING:
    from pathlib import Path


class ProcessPerfData:
    """Process performance data."""

    def read_json_file(self, jsonfilepath: str) -> Any:
        """Read json file."""
        with open(jsonfilepath, "r", encoding="utf-8") as file:
            data = file.read()
        json_data = json.loads(data)
        return json_data

    def _wait_for_file(
        self, file_path: str, max_retries: int = 10, retry_interval: int = 5
    ) -> bool:
        """Check if the file exists.

        If not, it will retry for a maximum of max_retries times with a retry
        interval of retry_interval seconds.
        If the file is not found after max_retries, it will return False.
        """
        retries = 0
        while retries < max_retries:
            if os.path.exists(file_path):
                logger.info(f"File: <{file_path}> already exists")
                return True
            logger.info(
                f"Search for files <{file_path}>..."
                f" (retry {retries + 1}/{max_retries})"
            )
            time.sleep(retry_interval)
            retries += 1
        logger.info(
            f"Reached maximum retry count {max_retries}，"
            f"file <{file_path}> still not found"
        )
        return False

    def __create_performance_folder(self, resultdir: str) -> Tuple[bool, str]:
        """Create performance folder."""
        try:
            report_path = resultdir
            folder_path = os.path.join(report_path, "performance")

            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)
                logger.info(f"Create performance-folder: {folder_path}")
            return (True, folder_path)
        except Exception as e:
            logger.error(f"Failed to create performance-folder: {e}")
            return (False, "")

    def __get_perf_data_from_log_file(
        self,
        output: List[str],
        board: str = "",
        core: str = "",
        branch: str = "",
    ) -> Tuple[List[str], List[List[str]]]:
        """Get performance data from log file."""
        raw_data_list = [line for line in output if not line.startswith("ap>")]
        head = ["board", "core", "branch"]
        processed_data = []
        flag = True
        for line in raw_data_list:
            j = line.split()
            if len(j) == 4 and flag:
                head.extend(j)
                flag = False
            elif len(j) == 4 and not flag:
                data_row = [board, core, branch] + j
                processed_data.append(data_row)
        return head, processed_data

    def generate_csv_in_the_specified_dir(
        self,
        resultdir: "Path",
        domain: str,
        metricname: str,
        csvheadlist: List[str],
        csvdatalist: List[List[str]],
    ) -> bool:
        """Generate CSV file."""
        create_res = self.__create_performance_folder(str(resultdir))
        if create_res[0]:
            try:
                head = [
                    x.lower() if isinstance(x, str) else x for x in csvheadlist
                ]
                required_items = {"board", "core", "branch"}
                contains_all = all(item in head for item in required_items)
                if contains_all:
                    csvfp = os.path.join(
                        create_res[1], domain + "-" + metricname + ".csv"
                    )
                    with open(csvfp, "w", encoding="UTF8", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(head)
                        writer.writerows(csvdatalist)
                        logger.info(
                            f"Write performance data to csv file Successfully."
                            f" Csv fp: {csvfp}"
                        )
                    return True
                logger.error(
                    "The csvheadlist must contain three fields: board, "
                    "core, and branch.Please check your csvheadlist field."
                )
                return False
            except Exception as e:
                logger.error(f"Writing CSV file failed: {str(e)}")
                return False
        return False

    def generate_csv_of_simple_scene(
        self,
        output: List[str],
        board: str,
        core: str,
        branch: str,
        reportdir: "Path",
        domain: str,
        metricname: str,
    ) -> None:
        """Generate CSV file."""
        perf_data = self.__get_perf_data_from_log_file(
            output, board, core, branch
        )
        self.generate_csv_in_the_specified_dir(
            reportdir,
            domain,
            metricname,
            csvheadlist=perf_data[0],
            csvdatalist=perf_data[1],
        )


class DataProcess(DBLib):
    """Process data."""

    def __init__(self, dbpath: str) -> None:
        """Initialize data process handler."""
        super().__init__(dbpath)
        self.db_path = dbpath

    def __clean_sql(self, sql: str) -> str:
        """Clean sql command."""
        sql = re.sub(r"--.*", "", sql)
        sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
        sql = re.sub(r"\s+", " ", sql)
        return sql.strip()

    def __split_columns(self, body: str) -> List[str]:
        """Split columds."""
        columns: List[str] = []
        current: List[str] = []
        depth = 0
        for char in body:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            if char == "," and depth == 0:
                columns.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        if current:
            columns.append("".join(current).strip())
        return columns

    def step_1_mysql_to_sqlitesql(self, mysqlfp: str) -> Any:  # noqa: C901
        """Translate MySQL statements into SQLite statements."""
        logger.info(
            "step-1: translate MySQL statements into SQLite statements"
        )
        time.sleep(3)
        with open(mysqlfp, "r", encoding="utf-8") as file:
            sql_commands = file.read()

        cleaned_sql = self.__clean_sql(sql_commands)
        table_match = re.search(r"CREATE TABLE `([^`]+)`", cleaned_sql)
        if not table_match:
            raise ValueError("Unable to extract table name")
        table_name = table_match.group(1)
        body_match = re.search(r"\((.*)\)", cleaned_sql, re.DOTALL)
        if not body_match:
            raise ValueError("Unable to extract table definition subject")
        table_body = body_match.group(1)

        column_defs = self.__split_columns(table_body)
        processed_columns = []
        indexes = []
        for col_def in column_defs:
            if col_def.startswith("`"):
                col_name_match = re.match(r"`([^`]+)`", col_def)
                if not col_name_match:
                    continue
                col_name = col_name_match.group(1)
                remaining = col_def[len(col_name_match.group(0)) :].strip()

                type_match = re.match(
                    r"([a-z]+)(?:\([^)]+\))?", remaining, re.IGNORECASE
                )
                if not type_match:
                    continue
                mysql_type = type_match.group(1).lower()

                type_map = {
                    "bigint": "INTEGER",
                    "int": "INTEGER",
                    "varchar": "TEXT",
                    "char": "TEXT",
                    "datetime": "TEXT",
                }
                sqlite_type = type_map.get(mysql_type, mysql_type.upper())

                constraints = []
                if col_name == "id" and "NOT NULL" in remaining:
                    remaining = remaining.replace("NOT NULL", "").strip()
                if "NOT NULL" in remaining and col_name != "id":
                    constraints.append("NOT NULL")
                default_match = re.search(
                    r"DEFAULT\s+([^\s,]+)", remaining, re.IGNORECASE
                )
                if default_match:
                    default_value = default_match.group(1)
                    if default_value.startswith(
                        "'"
                    ) and default_value.endswith("'"):
                        default_value = f"'{default_value[1:-1]}'"
                    constraints.append(f"DEFAULT {default_value}")

                if "AUTO_INCREMENT" in remaining:
                    constraints.append("PRIMARY KEY AUTOINCREMENT")

                if (
                    col_name == "update_time"
                    and "ON UPDATE CURRENT_TIMESTAMP" in remaining
                ):
                    remaining = remaining.replace(
                        "ON UPDATE CURRENT_TIMESTAMP", ""
                    ).strip()

                new_col_def = f"{col_name} {sqlite_type}"
                if constraints:
                    new_col_def += " " + " ".join(constraints)

                processed_columns.append(new_col_def)

            elif "PRIMARY KEY" in col_def and "`id`" in col_def:
                continue

            elif "KEY" in col_def:
                key_match = re.search(
                    r"KEY\s+`([^`]+)`\s*\(`([^`]+)`\)", col_def
                )
                if key_match:
                    indexes.append((key_match.group(1), key_match.group(2)))

        create_table_sql = f"CREATE TABLE {table_name} (\n  "
        create_table_sql += ",\n  ".join(processed_columns)
        create_table_sql += "\n);\n"
        for index_name, column in indexes:
            create_table_sql += (
                f"CREATE INDEX {index_name} ON {table_name} ({column});\n"
            )

        return create_table_sql.strip(), table_name

    def step_2_create_new_table(self, sqlcmd: str) -> None:
        """Create new table for sqlite."""
        logger.info("step-2: create new table")
        time.sleep(1)
        super()._create_table(sqlcmd)

    def setp_3_insert_csv_data_from_csv(
        self, csvfp: str, tabname: Any
    ) -> None:
        """Read data from CSV file and insert it into database."""
        logger.info("step-3: insert performance data from csv")
        time.sleep(1)
        try:
            with open(csvfp, "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                headers = next(reader)
                lowercase_headers = [
                    header[0].lower() + header[1:] for header in headers
                ]
                data_to_insert = []
                for row in reader:
                    board = row[0]
                    core = row[1].strip("[]'")
                    description = row[2]
                    max_val = int(row[3])
                    min_val = int(row[4])
                    avg_val = int(row[5])
                    data_to_insert.append(
                        tuple(
                            [
                                board,
                                core,
                                description,
                                max_val,
                                min_val,
                                avg_val,
                            ]
                        )
                    )
                super()._insert_data(
                    tablename=tabname,
                    lowercaseheaders=lowercase_headers,
                    data=data_to_insert,
                )
        except Exception as e:
            logger.info(f"Error: fail to insert performance data: {e}")

    def performance_indicator_data_storage_verification(
        self, mysqlfp: str, csvfp: str
    ) -> None:
        """Verify the data storage of performance indicators."""
        data_tup = self.step_1_mysql_to_sqlitesql(mysqlfp)
        self.step_2_create_new_table(data_tup[0])
        self.setp_3_insert_csv_data_from_csv(csvfp, data_tup[1])
