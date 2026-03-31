from unittest.mock import MagicMock, patch

from nsjail.builder import Jail
from nsjail.config import NsJailConfig
from nsjail.enums import Mode
from nsjail.mounts import bind_tree, system_libs, dev_minimal, tmpfs_mount
from nsjail.runner import NsJailResult, Runner
from nsjail.seccomp import SeccompPolicy, MINIMAL


class TestBuilderCommand:
    def test_command(self):
        cfg = Jail().command("python", "script.py").build()
        assert cfg.exec_bin.path == "python"
        assert cfg.exec_bin.arg == ["script.py"]

    def test_sh(self):
        cfg = Jail().sh("echo hello && ls").build()
        assert cfg.exec_bin.path == "/bin/sh"
        assert cfg.exec_bin.arg == ["-c", "echo hello && ls"]

    def test_python(self):
        cfg = Jail().python("script.py").build()
        assert cfg.exec_bin.path == "/usr/bin/python3"
        assert cfg.exec_bin.arg == ["script.py"]

    def test_bash(self):
        cfg = Jail().bash("-c", "echo hi").build()
        assert cfg.exec_bin.path == "/bin/bash"
        assert cfg.exec_bin.arg == ["-c", "echo hi"]


class TestBuilderResources:
    def test_timeout(self):
        cfg = Jail().sh("true").timeout(30).build()
        assert cfg.time_limit == 30

    def test_memory_mb(self):
        cfg = Jail().sh("true").memory(512, "MB").build()
        assert cfg.cgroup_mem_max == 512 * 1024 * 1024

    def test_memory_gb(self):
        cfg = Jail().sh("true").memory(2, "GB").build()
        assert cfg.cgroup_mem_max == 2 * 1024 * 1024 * 1024

    def test_cpu(self):
        cfg = Jail().sh("true").cpu(500).build()
        assert cfg.cgroup_cpu_ms_per_sec == 500

    def test_pids(self):
        cfg = Jail().sh("true").pids(64).build()
        assert cfg.cgroup_pids_max == 64


class TestBuilderNamespace:
    def test_no_network(self):
        cfg = Jail().sh("true").no_network().build()
        assert cfg.clone_newnet is True

    def test_network(self):
        cfg = Jail().sh("true").network().build()
        assert cfg.clone_newnet is False


class TestBuilderFilesystem:
    def test_readonly_root(self):
        cfg = Jail().sh("true").readonly_root().build()
        root = [m for m in cfg.mount if m.dst == "/"]
        assert len(root) == 1
        assert root[0].rw is False

    def test_writable(self):
        cfg = Jail().sh("true").readonly_root().writable("/workspace").build()
        ws = [m for m in cfg.mount if m.dst == "/workspace"]
        assert len(ws) == 1
        assert ws[0].rw is True

    def test_writable_tmpfs(self):
        cfg = Jail().sh("true").writable("/tmp", tmpfs=True, size="64M").build()
        tmp = [m for m in cfg.mount if m.dst == "/tmp"]
        assert len(tmp) == 1
        assert tmp[0].fstype == "tmpfs"
        assert "64M" in (tmp[0].options or "")

    def test_mount(self):
        cfg = Jail().sh("true").mount("/data", "/data", readonly=True).build()
        data = [m for m in cfg.mount if m.dst == "/data"]
        assert len(data) == 1
        assert data[0].rw is False


class TestBuilderEnvironment:
    def test_env(self):
        cfg = Jail().sh("true").env("HOME=/home/user").env("CI=1").build()
        assert "HOME=/home/user" in cfg.envar
        assert "CI=1" in cfg.envar

    def test_cwd(self):
        cfg = Jail().sh("true").cwd("/workspace").build()
        assert cfg.cwd == "/workspace"


class TestBuilderSecurity:
    def test_seccomp_log(self):
        cfg = Jail().sh("true").seccomp_log().build()
        assert cfg.seccomp_log is True

    def test_uid_map(self):
        cfg = Jail().sh("true").uid_map(inside=0, outside=1000).build()
        assert len(cfg.uidmap) == 1
        assert cfg.uidmap[0].inside_id == "0"
        assert cfg.uidmap[0].outside_id == "1000"


class TestBuilderChaining:
    def test_full_chain(self):
        cfg = (
            Jail()
            .sh("pytest tests/ -v")
            .cwd("/workspace")
            .timeout(60)
            .memory(512, "MB")
            .cpu(500)
            .pids(64)
            .no_network()
            .readonly_root()
            .writable("/workspace")
            .writable("/tmp", tmpfs=True, size="64M")
            .env("HOME=/home/user")
            .env("CI=1")
            .seccomp_log()
            .uid_map(inside=0, outside=1000)
            .build()
        )
        assert isinstance(cfg, NsJailConfig)
        assert cfg.exec_bin.path == "/bin/sh"
        assert cfg.time_limit == 60
        assert cfg.cgroup_mem_max == 512 * 1024 * 1024
        assert cfg.seccomp_log is True
        assert len(cfg.envar) == 2

    def test_build_returns_nsjailconfig(self):
        cfg = Jail().sh("true").build()
        assert isinstance(cfg, NsJailConfig)


class TestBuilderRun:
    def test_run_with_default_runner(self):
        mock_result = NsJailResult(
            returncode=0, stdout=b"ok", stderr=b"",
            config_path=None, nsjail_args=[], timed_out=False,
            oom_killed=False, signaled=False, inner_returncode=0,
        )
        with patch.object(Runner, "run", return_value=mock_result):
            result = Jail().sh("echo hi").timeout(10).run()
        assert result.returncode == 0

    def test_run_with_explicit_runner(self):
        runner = Runner(nsjail_path="/custom/nsjail", render_mode="cli")
        mock_result = NsJailResult(
            returncode=0, stdout=b"", stderr=b"",
            config_path=None, nsjail_args=[], timed_out=False,
            oom_killed=False, signaled=False, inner_returncode=0,
        )
        with patch.object(Runner, "run", return_value=mock_result):
            result = Jail().sh("true").run(runner=runner)
        assert result.returncode == 0

    def test_run_passes_kwargs(self):
        mock_result = NsJailResult(
            returncode=0, stdout=b"", stderr=b"",
            config_path=None, nsjail_args=[], timed_out=False,
            oom_killed=False, signaled=False, inner_returncode=0,
        )
        with patch.object(Runner, "run", return_value=mock_result) as mock_run:
            Jail().sh("true").run(extra_args=["--verbose"])
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs.get("extra_args") == ["--verbose"]


class TestBuilderSeccomp:
    def test_seccomp_with_policy(self):
        policy = SeccompPolicy("test").allow("read").default_kill()
        cfg = Jail().sh("true").seccomp(policy).build()
        assert len(cfg.seccomp_string) == 1
        assert "ALLOW { read }" in cfg.seccomp_string[0]

    def test_seccomp_with_preset(self):
        cfg = Jail().sh("true").seccomp(MINIMAL).build()
        assert len(cfg.seccomp_string) == 1
        assert "read" in cfg.seccomp_string[0]

    def test_seccomp_with_raw_string(self):
        raw = "POLICY p { ALLOW { read } } USE p DEFAULT KILL"
        cfg = Jail().sh("true").seccomp(raw).build()
        assert len(cfg.seccomp_string) == 1
        assert cfg.seccomp_string[0] == raw

    def test_seccomp_multiple(self):
        cfg = (
            Jail()
            .sh("true")
            .seccomp(MINIMAL)
            .seccomp("POLICY extra { ALLOW { openat } } USE extra DEFAULT KILL")
            .build()
        )
        assert len(cfg.seccomp_string) == 2


class TestBuilderMounts:
    def test_mounts_extends_list(self):
        cfg = (
            Jail()
            .sh("true")
            .mounts(bind_tree("/usr"))
            .build()
        )
        usr_mounts = [m for m in cfg.mount if m.dst == "/usr"]
        assert len(usr_mounts) == 1
        assert usr_mounts[0].is_bind is True

    def test_mounts_chaining(self):
        cfg = (
            Jail()
            .sh("true")
            .mounts(bind_tree("/usr"))
            .mounts(tmpfs_mount("/tmp"))
            .build()
        )
        assert len(cfg.mount) == 2

    def test_mounts_with_system_libs(self):
        cfg = (
            Jail()
            .sh("true")
            .mounts(system_libs())
            .build()
        )
        assert len(cfg.mount) >= 1
        assert all(m.rw is False for m in cfg.mount)

    def test_mounts_combined_with_writable(self):
        cfg = (
            Jail()
            .sh("true")
            .readonly_root()
            .mounts(dev_minimal())
            .writable("/workspace")
            .build()
        )
        assert len(cfg.mount) >= 3

    def test_mounts_returns_self(self):
        builder = Jail().sh("true")
        result = builder.mounts(bind_tree("/usr"))
        assert result is builder
