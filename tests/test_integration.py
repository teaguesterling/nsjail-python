"""End-to-end tests for nsjail-python.

These tests verify the full workflow from builder to serialized config.
They do NOT require nsjail to be installed.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch

from nsjail import Jail, NsJailConfig, MountPt, Exe, sandbox, Runner
from nsjail.runner import NsJailResult
from nsjail.serializers import to_textproto, to_cli_args, to_file
from nsjail.seccomp import SeccompPolicy, MINIMAL, READONLY
from nsjail.cgroup import CgroupStats


class TestBuilderToTextproto:
    def test_full_pipeline(self):
        cfg = (
            Jail()
            .sh("echo hello")
            .timeout(30)
            .memory(256, "MB")
            .no_network()
            .readonly_root()
            .writable("/tmp", tmpfs=True, size="32M")
            .env("HOME=/root")
            .build()
        )

        text = to_textproto(cfg)

        assert "time_limit: 30" in text
        assert 'envar: "HOME=/root"' in text
        assert "exec_bin {" in text
        assert 'path: "/bin/sh"' in text
        assert "mount {" in text
        assert text.count("{") == text.count("}")

    def test_sandbox_to_textproto(self):
        cfg = sandbox(
            command=["python", "script.py"],
            cwd="/workspace",
            timeout_sec=60,
            memory_mb=512,
            writable_dirs=["/workspace", "/tmp"],
        )

        text = to_textproto(cfg)

        assert "time_limit: 60" in text
        assert 'cwd: "/workspace"' in text
        assert "cgroup_mem_max:" in text


class TestBuilderToCliArgs:
    def test_simple_config(self):
        cfg = NsJailConfig(
            hostname="test",
            time_limit=30,
            keep_env=True,
            envar=["A=1"],
        )
        args = to_cli_args(cfg, on_unsupported="skip")
        assert "--hostname" in args
        assert "--time_limit" in args
        assert "--keep_env" in args
        assert "--env" in args


class TestTextprotoToFile:
    def test_write_and_read(self, tmp_path):
        cfg = (
            Jail()
            .sh("true")
            .timeout(10)
            .build()
        )
        path = tmp_path / "test.cfg"
        to_file(cfg, path)

        content = path.read_text()
        assert "time_limit: 10" in content
        assert "exec_bin {" in content


class TestBuilderRunIntegration:
    def test_builder_run_with_mock(self):
        mock_result = NsJailResult(
            returncode=0, stdout=b"hello", stderr=b"",
            config_path=None, nsjail_args=[], timed_out=False,
            oom_killed=False, signaled=False, inner_returncode=0,
        )
        with patch.object(Runner, "run", return_value=mock_result):
            result = (
                Jail()
                .sh("echo hello")
                .timeout(10)
                .memory(256, "MB")
                .run()
            )
        assert result.returncode == 0
        assert result.stdout == b"hello"


class TestProtobufIntegration:
    def test_protobuf_round_trip(self):
        pytest.importorskip("google.protobuf")
        from nsjail.serializers.protobuf import to_protobuf

        cfg = (
            Jail()
            .sh("echo hello")
            .timeout(30)
            .memory(256, "MB")
            .build()
        )
        msg = to_protobuf(cfg)
        assert msg.time_limit == 30


class TestSeccompIntegration:
    def test_builder_with_seccomp_to_textproto(self):
        cfg = (
            Jail()
            .sh("echo hi")
            .seccomp(MINIMAL)
            .build()
        )
        text = to_textproto(cfg)
        assert "seccomp_string:" in text
        assert "read" in text

    def test_custom_policy_to_textproto(self):
        policy = (
            SeccompPolicy("custom")
            .allow("read", "write")
            .deny("execve")
            .default_kill()
        )
        cfg = Jail().sh("echo hi").seccomp(policy).build()
        text = to_textproto(cfg)
        assert "seccomp_string:" in text


class TestCgroupStatsIntegration:
    def test_result_with_cgroup_stats(self):
        stats = CgroupStats(
            memory_peak_bytes=512 * 1024 * 1024,
            cpu_usage_ns=2_500_000_000,
            pids_current=12,
        )
        result = NsJailResult(
            returncode=0, stdout=b"", stderr=b"",
            config_path=None, nsjail_args=[], timed_out=False,
            oom_killed=False, signaled=False, inner_returncode=0,
            cgroup_stats=stats,
        )
        assert result.cgroup_stats.memory_peak_bytes == 512 * 1024 * 1024
        assert result.cgroup_stats.cpu_usage_ns == 2_500_000_000
