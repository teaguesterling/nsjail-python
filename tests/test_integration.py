"""End-to-end tests for nsjail-python.

These tests verify the full workflow from builder to serialized config.
They do NOT require nsjail to be installed.
"""

from nsjail import Jail, NsJailConfig, MountPt, Exe, sandbox, Runner
from nsjail.serializers import to_textproto, to_cli_args, to_file


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
