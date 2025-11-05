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

"""Product class implementation."""

import re
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

from ntfc.device.common import CmdStatus
from ntfc.envconfig import EnvConfig
from ntfc.logger import logger

if TYPE_CHECKING:
    from ntfc.device.common import DeviceCommon

###############################################################################
# Class: Product
###############################################################################


class Product:
    """This class implements product under test."""

    def __init__(self, device: "DeviceCommon", conf: "EnvConfig"):
        """Initialize product under test.

        :param device: DeviceCommon instance
        :param conf: EnvConfig instance
        """
        if not device:
            raise TypeError("Device instance is required")

        if not isinstance(conf, EnvConfig):
            raise TypeError("Config instance is required")

        self._device = device
        self._main_prompt = self._device.prompt
        self._cur_prompt = (
            self._main_prompt
            if isinstance(self._main_prompt, str)
            else self._main_prompt.decode("utf-8", errors="ignore")
        )
        self._uptime = conf.core(cpu=0).get("uptime", 3)
        self._kv_conf = conf.kv_conf

        # cores info not ready yet, done in self.init() method called when
        # device is ready
        self._main_core = None
        self._cur_core = None
        self._cores = None

    def _prepare_command(
        self, cmd: str, args: Optional[Union[str, List[str]]]
    ) -> str:
        """Ensure command is valid and include arguments."""
        if not cmd:
            raise ValueError("Command cannot be empty.")
        if args:
            if not isinstance(args, (list, tuple)):
                args = [args]
            cmd = f"{cmd} {' '.join(args)}"
        return cmd

    def _prepare_pattern(
        self,
        cmd: str,
        expects: Optional[Union[str, List[str]]],
        flag: str,
        match_all: bool,
        regexp: bool,
    ) -> str:
        """Build a single regex pattern string."""
        if expects:
            expects_list = (
                expects if isinstance(expects, (list, tuple)) else [expects]
            )
            pattern = self._build_expect_pattern(
                expects_list, match_all, regexp
            )
        else:
            pattern = self._default_prompt_pattern(cmd, flag)

        # Add 'command not found' alternative
        notfound_pattern = re.escape(
            f"{cmd.split(' ')[0]}: {self._device.no_cmd}"
        )
        # Wrap everything and make sure dot matches newlines
        full_pattern = f"(?s)({pattern}|{notfound_pattern})"
        return full_pattern

    def _build_expect_pattern(
        self, expects: List[str], match_all: bool, regexp: bool
    ) -> str:
        """Return a single regex string."""
        items = expects if regexp else [re.escape(e) for e in expects]

        if match_all:
            # Build stacked lookaheads for AND semantics
            return "".join(f"(?=.*{item})" for item in items)

        # OR semantics
        return rf"({'|'.join(items)})"

    def _default_prompt_pattern(self, cmd: str, flag: str = "") -> str:
        """Return prompt-based fallback pattern (string)."""
        prompt = flag if flag else self._cur_prompt
        return (
            f"{re.escape(prompt)}(?!.*{cmd})"
            if cmd not in ["\n"]
            else re.escape(prompt)
        )

    def _encode_for_device(
        self, cmd: str, pattern: Union[str, bytes, List[Union[str, bytes]]]
    ) -> Tuple[bytes, bytes]:
        """Encode command and pattern to bytes, merging lists if needed."""
        cmd_bytes = cmd.encode("utf-8")

        if isinstance(pattern, list):
            # Combine list into one string pattern (mainly for compatibility)
            pattern_str = "".join(
                (
                    p.decode("utf-8")
                    if isinstance(p, (bytes, bytearray))
                    else str(p)
                )
                for p in pattern
            )
            pattern_bytes = pattern_str.encode("utf-8")
        elif isinstance(pattern, (bytes, bytearray)):
            pattern_bytes = bytes(pattern)
        else:
            pattern_bytes = str(pattern).encode("utf-8")

        return cmd_bytes, pattern_bytes

    def _match_not_found(self, rematch: Optional[re.Match]) -> bool:
        """Check for 'command not found' message."""
        if not rematch:
            return False
        matched = rematch.group().strip()
        if isinstance(matched, (bytes, bytearray)):
            matched = matched.decode("utf-8", errors="ignore")
        return self._device.no_cmd in matched

    def init(self) -> None:
        """Finish product initialization."""
        cores = self.get_core_info()
        self._main_core = cores[0] if cores else "ap"
        self._cur_core = self._main_core
        self._cores = cores if cores else ["ap"]
        logger.info(f"Current product support cores: {self._cores}")

    def sendCommand(  # noqa: N802
        self,
        cmd: str,
        expects: Optional[Union[str, List[str]]] = None,
        args: Optional[Union[str, List[str]]] = None,
        timeout: int = 30,
        flag: str = "",
        match_all: bool = True,
        regexp: bool = False,
    ) -> "CmdStatus":
        """Send command and wait for expected response.

        :param cmd: Command to send
        :param expects: List of expected responses or None
        :param args: List of additional arguments to append to the command
         or None
        :param timeout: Timeout in seconds
        :param flag: Default _prompt
        :param match_all: "True" for all responses to match, "False" for any
         response to match
        :param regexp: "False" for str to match, "True" for regular
        expression to match
        :raises ValueError:
        :raises DeviceError: Communication error with device
        :raises TimeoutError: Response timeout

        :return: status : command execution status
        """
        cmd = self._prepare_command(cmd, args)
        pattern = self._prepare_pattern(cmd, expects, flag, match_all, regexp)
        cmd_bytes, pattern_bytes = self._encode_for_device(cmd, pattern)

        logger.debug(
            f"Sending command: {cmd}, expecting: "
            f"{pattern} (timeout={timeout}s)"
        )

        cmdret = self._device.send_cmd_read_until_pattern(
            cmd_bytes, pattern=pattern_bytes, timeout=timeout
        )

        if cmdret.valid_match() and self._match_not_found(cmdret.rematch):
            return CmdStatus.NOTFOUND

        return cmdret.status

    def sendCommandReadUntilPattern(  # noqa: N802
        self,
        cmd: str,
        pattern: Optional[Union[str, bytes, List[Union[str, bytes]]]] = None,
        args: Optional[Union[str, List[str]]] = None,
        timeout: int = 30,
    ) -> Tuple[int, Optional[re.Match], str]:
        """Send command to device and read until a specific pattern.

        :param cmd: (str or list of strs) command to send to device
        :param pattern: (str, bytes, or list of (str, bytes)) String or regex
         pattern to look for. If a list, patterns will be concatenated
         with '.*'. The pattern will be converted to bytes for matching.
        :param args: List of additional arguments to append to the command
         or None
        :param timeout: (int) timeout value in seconds, default 30s.

        :return: CmdReturn : command return data
        """
        cmd = self._prepare_command(cmd, args)
        pattern = self._default_prompt_pattern(cmd) if not pattern else pattern
        cmd_bytes, pattern_bytes = self._encode_for_device(cmd, pattern)

        logger.debug(
            f"Sending command: {cmd}, expecting pattern: {pattern} "
            f"(timeout={timeout}s)"
        )
        return self._device.send_cmd_read_until_pattern(
            cmd_bytes, pattern=pattern_bytes, timeout=timeout
        )

    def sendCtrlCmd(self, ctrl_char: str) -> None:  # noqa: N802
        """Send a control character command (e.g., Ctrl+C).

        :param ctrl_char: Control character to send
        """
        if len(ctrl_char) != 1:
            raise ValueError(
                "ctrl_char must be a single alphabetic character."
            )

        if self._device.send_ctrl_cmd(ctrl_char) == CmdStatus.SUCCESS:
            logger.info(f"Successfully sent Ctrl+{ctrl_char}")
        else:
            logger.warning(f"Failed to send Ctrl+{ctrl_char}")

    # REVISIT: no proc/rpmsg in nuttx/upstream!
    def get_core_info(self) -> Tuple[str, ...]:
        """Retrieve CPU core information from the device.

        :return: Tuple containing Local CPU as first element followed by Remote
                 CPUs. Returns empty tuple on failure.
        """
        cmd_rpmsg = b"cat proc/rpmsg"
        timeout = 5
        nonuttx_core = ["dsp"]  # Non-NuttX core (extend this list as needed)

        # Send command and get raw output
        cmdret = self._device.send_cmd_read_until_pattern(
            cmd_rpmsg, pattern=self._main_prompt, timeout=timeout
        )

        if cmdret.status != 0:
            logger.error(f"Command failed with return code: {cmdret.status}")
            return ()

        # Parse output
        decoded_output = cmdret.output
        lines = [line.strip() for line in decoded_output.splitlines()]

        # Find header location
        header_index = next(
            (
                i
                for i, line in enumerate(lines)
                if "Local CPU" in line and "Remote CPU" in line
            ),
            -1,
        )

        # Early return if header not found
        if header_index == -1:
            logger.warning("CPU information header not found in output")
            return ()

        # Process data rows
        core_data = []
        for line in lines[header_index + 1 :]:
            prompt = self._device.prompt
            if isinstance(prompt, bytes):
                prompt = prompt.decode()
            if line.startswith(prompt):
                break  # Stop at next prompt

            parts = line.split()
            if len(parts) >= 2:
                core_data.append((parts[0], parts[1]))

        # Validate and format results
        if not core_data:
            logger.warning("No valid CPU data found after header")
            return ()

        # Extract unique Local CPU (default single value)
        local_cpu = core_data[0][0]

        # Create result tuple (Local CPU + all Remote CPUs)
        return (
            local_cpu,
            *(cpu[1] for cpu in core_data if cpu[1] not in nonuttx_core),
        )

    def switch_core(self, target_core: str = "") -> int:
        """Switch the target core of the device.

        :param target_core: Core to switch to.

        :return: 0 on success, -1 on failure
        """
        if not self._main_core and not self._cur_core and not self._cores:
            raise ValueError("Product not initialized!")

        if not target_core:
            logger.debug(
                "The target_core has no value and cannot be switched."
            )
            return CmdStatus.NOTFOUND

        if target_core.lower() == self._main_core.lower():
            logger.warning(
                "The target core is the main core, and the core"
                " is not switched."
            )
            return CmdStatus.SUCCESS

        logger.info(f"Attempting to switch to core: {target_core}")

        if target_core.lower() not in self._cores:
            logger.debug(f"There is no {target_core} core in the device")
            return CmdStatus.NOTFOUND

        cmd = f"cu -l /dev/tty{target_core.upper()}\n\n"
        pattern = f"{target_core}>"
        rc = self.sendCommand(cmd, pattern, match_all=False, timeout=5)
        if rc == CmdStatus.SUCCESS:
            logger.info(f"Core switch to {target_core} succeeded")

        return rc

    def get_current_prompt(self) -> str:
        """Dynamically obtain the device current prompt.

        :return: The current prompt (e.g., ap>) (str)
                 or None: If the current prompt cannot be determined
        """
        core_pattern = r"(\S+)>"
        matches = []

        for _ in range(5):
            cmdret = self._device.send_cmd_read_until_pattern(
                "\n", core_pattern
            )

            if cmdret.valid_match():
                # Extract the matched core name
                core_name = (
                    cmdret.rematch.group(1).decode("utf-8", errors="ignore")
                    + ">"
                )
                matches.append(core_name)

        # Check whether two or more of the three results are consistent
        if len(matches) >= 2 and len(set(matches)) == 1:
            logger.info(f"The current prompt is {matches[0]}")
            return matches[0]

        logger.error("Failed to get current prompt, use default prompt.")
        return ">"

    def reboot(self, timeout=30) -> bool:
        """Reboot the device by calling the device's reboot function.

        :param timeout: (int) Timeout in seconds for the reboot operation.
         Default is 30 seconds.

        :return: (bool) True if the reboot was successful, False otherwise.
        """
        logger.info(
            f"Attempting to reboot the device with " f"timeout: {timeout}s"
        )

        success = self._device.reboot(timeout=timeout)

        if success:
            logger.info("Device rebooted successfully.")
        else:
            logger.error("Failed to reboot the device.")

        return success

    @property
    def busyloop(self) -> bool:
        """Check if the device is in busy loop."""
        return self._device.busyloop

    @property
    def crash(self) -> bool:
        """Check if the device is crashed."""
        return self._device.crash

    @property
    def notalive(self) -> bool:
        """Check if the device is dead."""
        return self._device.notalive

    @property
    def cur_core(self) -> str:
        """Get current core."""
        return self._cur_core

    @property
    def device_status(self) -> str:
        """Check device status with all failure mode detection.

        :return: "CRASH", "BUSYLOOP", "NORMAL", "NOTALIVE"
        """
        if self.crash:
            return "CRASH"

        if self.busyloop:
            return "BUSYLOOP"

        if self.notalive:
            return "NOTALIVE"

        return "NORMAL"
