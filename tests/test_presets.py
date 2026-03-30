from nsjail.config import NsJailConfig, MountPt, Exe
from nsjail.enums import Mode
from nsjail.presets import (
    apply_readonly_root,
    apply_cgroup_limits,
    apply_seccomp_log,
    sandbox,
)


class TestApplyReadonlyRoot:
    def test_adds_root_bind_mount(self):
        cfg = NsJailConfig()
        apply_readonly_root(cfg)
        root_mounts = [m for m in cfg.mount if m.dst == "/"]
        assert len(root_mounts) == 1
        assert root_mounts[0].is_bind is True
        assert root_mounts[0].rw is False

    def test_adds_writable_dirs(self):
        cfg = NsJailConfig()
        apply_readonly_root(cfg, writable=["/workspace", "/home"])
        writable = [m for m in cfg.mount if m.rw is True]
        dsts = {m.dst for m in writable}
        assert "/workspace" in dsts
        assert "/home" in dsts

    def test_writable_as_tmpfs(self):
        cfg = NsJailConfig()
        apply_readonly_root(cfg, writable=["/tmp"])
        tmp_mounts = [m for m in cfg.mount if m.dst == "/tmp"]
        assert len(tmp_mounts) == 1
        assert tmp_mounts[0].fstype == "tmpfs"
        assert tmp_mounts[0].rw is True


class TestApplyCgroupLimits:
    def test_memory_limit(self):
        cfg = NsJailConfig()
        apply_cgroup_limits(cfg, memory_mb=512)
        assert cfg.cgroup_mem_max == 512 * 1024 * 1024

    def test_cpu_limit(self):
        cfg = NsJailConfig()
        apply_cgroup_limits(cfg, cpu_ms_per_sec=500)
        assert cfg.cgroup_cpu_ms_per_sec == 500

    def test_pids_limit(self):
        cfg = NsJailConfig()
        apply_cgroup_limits(cfg, pids_max=64)
        assert cfg.cgroup_pids_max == 64

    def test_no_args_does_nothing(self):
        cfg = NsJailConfig()
        apply_cgroup_limits(cfg)
        assert cfg.cgroup_mem_max == 0
        assert cfg.cgroup_cpu_ms_per_sec == 0
        assert cfg.cgroup_pids_max == 0


class TestApplySeccompLog:
    def test_enables_seccomp_log(self):
        cfg = NsJailConfig()
        apply_seccomp_log(cfg)
        assert cfg.seccomp_log is True


class TestSandbox:
    def test_basic_sandbox(self):
        cfg = sandbox(
            command=["python", "script.py"],
            timeout_sec=60,
        )
        assert cfg.mode == Mode.ONCE
        assert cfg.time_limit == 60
        assert cfg.exec_bin is not None
        assert cfg.exec_bin.path == "python"
        assert cfg.exec_bin.arg == ["script.py"]

    def test_sandbox_with_memory(self):
        cfg = sandbox(command=["echo", "hi"], memory_mb=256)
        assert cfg.cgroup_mem_max == 256 * 1024 * 1024

    def test_sandbox_no_network(self):
        cfg = sandbox(command=["echo"], network=False)
        assert cfg.clone_newnet is True

    def test_sandbox_with_network(self):
        cfg = sandbox(command=["echo"], network=True)
        assert cfg.clone_newnet is False

    def test_sandbox_with_writable_dirs(self):
        cfg = sandbox(
            command=["echo"],
            writable_dirs=["/workspace"],
        )
        writable = [m for m in cfg.mount if m.rw is True and m.dst == "/workspace"]
        assert len(writable) == 1

    def test_sandbox_sets_cwd(self):
        cfg = sandbox(command=["echo"], cwd="/workspace")
        assert cfg.cwd == "/workspace"
