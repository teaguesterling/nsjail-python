import copy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nsjail.config import Exe, MountPt, NsJailConfig
from nsjail.exceptions import NsjailNotFound
from nsjail.runner import NsJailResult, Runner, merge_configs, resolve_nsjail_path


class TestResolveNsjailPath:
    def test_explicit_path(self):
        assert resolve_nsjail_path("/custom/nsjail") == Path("/custom/nsjail")

    def test_system_nsjail(self):
        with patch("shutil.which", return_value="/usr/bin/nsjail"):
            assert resolve_nsjail_path(None) == Path("/usr/bin/nsjail")

    def test_bundled_binary(self):
        mock_module = MagicMock()
        mock_module.binary_path.return_value = Path("/site-packages/nsjail_bin/_bin/nsjail")
        with (
            patch("shutil.which", return_value=None),
            patch("nsjail.runner._try_companion_binary", return_value=Path("/site-packages/nsjail_bin/_bin/nsjail")),
        ):
            result = resolve_nsjail_path(None)
            assert result == Path("/site-packages/nsjail_bin/_bin/nsjail")

    def test_not_found_raises(self):
        with (
            patch("shutil.which", return_value=None),
            patch("nsjail.runner._try_companion_binary", return_value=None),
        ):
            with pytest.raises(NsjailNotFound):
                resolve_nsjail_path(None)


class TestMergeConfigs:
    def test_scalar_override(self):
        base = NsJailConfig(hostname="base", time_limit=60)
        override = NsJailConfig(time_limit=120)
        merged = merge_configs(base, override, override_fields={"time_limit"})
        assert merged.hostname == "base"
        assert merged.time_limit == 120

    def test_list_append(self):
        base = NsJailConfig(envar=["A=1"])
        override = NsJailConfig(envar=["B=2"])
        merged = merge_configs(base, override, override_fields={"envar"})
        assert merged.envar == ["A=1", "B=2"]

    def test_mount_append(self):
        base = NsJailConfig(mount=[MountPt(dst="/")])
        override = NsJailConfig(mount=[MountPt(dst="/tmp")])
        merged = merge_configs(base, override, override_fields={"mount"})
        assert len(merged.mount) == 2

    def test_extra_args_appended(self):
        base = NsJailConfig(exec_bin=Exe(path="python", arg=["main.py"]))
        merged = merge_configs(base, NsJailConfig(), override_fields=set(), extra_args=["--verbose"])
        assert merged.exec_bin.arg == ["main.py", "--verbose"]

    def test_merge_does_not_mutate_base(self):
        base = NsJailConfig(hostname="base", envar=["A=1"])
        override = NsJailConfig(envar=["B=2"])
        merge_configs(base, override, override_fields={"envar"})
        assert base.envar == ["A=1"]  # Original unchanged


class TestNsJailResult:
    def test_result_fields(self):
        result = NsJailResult(
            returncode=0,
            stdout=b"hello",
            stderr=b"",
            config_path=Path("/tmp/test.cfg"),
            nsjail_args=["nsjail", "--config", "/tmp/test.cfg"],
            timed_out=False,
            oom_killed=False,
            signaled=False,
            inner_returncode=0,
        )
        assert result.returncode == 0
        assert result.stdout == b"hello"


class TestRunner:
    def test_runner_creation(self):
        runner = Runner(nsjail_path="/usr/bin/nsjail")
        assert runner._nsjail_path == "/usr/bin/nsjail"

    def test_runner_with_base_config(self):
        base = NsJailConfig(hostname="test", time_limit=30)
        runner = Runner(base_config=base)
        assert runner._base_config.hostname == "test"

    def test_fork_creates_new_runner(self):
        base = NsJailConfig(hostname="base", time_limit=60)
        runner = Runner(base_config=base)
        forked = runner.fork(
            overrides=NsJailConfig(time_limit=120),
            override_fields={"time_limit"},
        )
        assert forked._base_config.time_limit == 120
        assert forked._base_config.hostname == "base"
        # Original unchanged
        assert runner._base_config.time_limit == 60

    def test_fork_without_overrides(self):
        base = NsJailConfig(hostname="base")
        runner = Runner(base_config=base)
        forked = runner.fork()
        assert forked._base_config.hostname == "base"
        # Independent copy
        forked._base_config.hostname = "changed"
        assert runner._base_config.hostname == "base"
