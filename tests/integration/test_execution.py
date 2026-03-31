"""Integration tests for nsjail command execution."""

from __future__ import annotations

import time

import pytest

from nsjail.config import Exe, NsJailConfig
from nsjail.runner import Runner

pytestmark = pytest.mark.integration


class TestCommandExecution:
    def test_echo_stdout(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/echo", arg=["hello"]),
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        assert result.stdout.strip() == b"hello"

    def test_exit_code_zero(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/true"),
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        assert result.returncode == 0

    def test_exit_code_nonzero(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/false"),
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        assert result.returncode != 0

    def test_exit_code_specific(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "exit 42"]),
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        assert result.inner_returncode == 42

    def test_time_limit_kills(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sleep", arg=["60"]),
            time_limit=2,
        )
        start = time.monotonic()
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        elapsed = time.monotonic() - start
        assert result.timed_out is True
        assert elapsed < 10

    def test_env_vars_set(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "echo $MYVAR"]),
            envar=["MYVAR=hello_from_nsjail"],
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "envar", "time_limit",
        })
        assert b"hello_from_nsjail" in result.stdout

    def test_working_directory(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "pwd"]),
            cwd="/tmp",
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "cwd", "time_limit",
        })
        assert b"/tmp" in result.stdout

    def test_stderr_captured(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "echo err >&2"]),
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        assert b"err" in result.stderr
