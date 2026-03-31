"""Integration tests for end-to-end nsjail-python pipelines."""

from __future__ import annotations

from pathlib import Path

import pytest

from nsjail import Jail, NsJailConfig, sandbox
from nsjail.runner import Runner
from nsjail.serializers import to_textproto, to_file

pytestmark = pytest.mark.integration


class TestBuilderPipeline:
    def test_builder_sh_run(self, runner: Runner):
        result = (
            Jail()
            .sh("echo builder_works")
            .timeout(10)
            .run(runner=runner)
        )
        assert b"builder_works" in result.stdout
        assert result.returncode == 0

    def test_builder_command_run(self, runner: Runner):
        result = (
            Jail()
            .command("/bin/echo", "command_works")
            .timeout(10)
            .run(runner=runner)
        )
        assert b"command_works" in result.stdout


class TestSandboxPreset:
    def test_sandbox_preset(self, runner: Runner):
        cfg = sandbox(
            command=["/bin/echo", "preset_works"],
            timeout_sec=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit", "mode", "cwd", "clone_newnet", "mount",
        })
        assert b"preset_works" in result.stdout


class TestConfigFilePipeline:
    def test_textproto_to_file_to_nsjail(self, runner: Runner, tmp_path: Path):
        cfg = NsJailConfig(
            exec_bin=Jail().sh("echo config_file_works").build().exec_bin,
            time_limit=10,
        )
        config_path = tmp_path / "test.cfg"
        to_file(cfg, config_path)

        content = config_path.read_text()
        assert "exec_bin" in content

        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "time_limit",
        })
        assert b"config_file_works" in result.stdout


class TestFullFeatureBuilder:
    def test_builder_with_all_features(self, runner: Runner):
        cfg = (
            Jail()
            .sh('echo "host=$(hostname) cwd=$(pwd) var=$TESTVAR"')
            .timeout(10)
            .cwd("/tmp")
            .env("TESTVAR=integration_test")
            .build()
        )
        run_result = runner.run(
            overrides=cfg,
            override_fields={
                "exec_bin", "time_limit", "cwd", "envar", "hostname",
            },
        )
        assert b"cwd=/tmp" in run_result.stdout
        assert b"var=integration_test" in run_result.stdout
