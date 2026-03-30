from dataclasses import fields

from nsjail.config import NsJailConfig, MountPt, IdMap, Exe, TrafficRule, UserNet
from nsjail.enums import Mode, LogLevel, RLimitType


class TestMountPt:
    def test_defaults(self):
        m = MountPt()
        assert m.src is None
        assert m.dst is None
        assert m.fstype is None
        assert m.is_bind is False
        assert m.rw is False
        assert m.mandatory is True

    def test_bind_mount(self):
        m = MountPt(src="/lib", dst="/lib", is_bind=True, rw=False)
        assert m.src == "/lib"
        assert m.dst == "/lib"
        assert m.is_bind is True
        assert m.rw is False

    def test_tmpfs_mount(self):
        m = MountPt(dst="/tmp", fstype="tmpfs", rw=True, options="size=50000000")
        assert m.fstype == "tmpfs"
        assert m.rw is True
        assert m.options == "size=50000000"


class TestIdMap:
    def test_defaults(self):
        m = IdMap()
        assert m.inside_id == ""
        assert m.outside_id == ""
        assert m.count == 1
        assert m.use_newidmap is False

    def test_uid_mapping(self):
        m = IdMap(inside_id="0", outside_id="99999", count=1)
        assert m.inside_id == "0"
        assert m.outside_id == "99999"


class TestExe:
    def test_defaults(self):
        e = Exe()
        assert e.path is None
        assert e.arg == []
        assert e.arg0 is None
        assert e.exec_fd is False

    def test_with_args(self):
        e = Exe(path="/bin/bash", arg=["-c", "echo hello"])
        assert e.path == "/bin/bash"
        assert e.arg == ["-c", "echo hello"]

    def test_arg_list_is_independent(self):
        e1 = Exe()
        e2 = Exe()
        e1.arg.append("x")
        assert e2.arg == []


class TestNsJailConfig:
    def test_defaults_match_nsjail(self):
        cfg = NsJailConfig()
        assert cfg.mode == Mode.ONCE
        assert cfg.hostname == "NSJAIL"
        assert cfg.cwd == "/"
        assert cfg.time_limit == 600

    def test_namespace_defaults(self):
        cfg = NsJailConfig()
        assert cfg.clone_newnet is True
        assert cfg.clone_newuser is True
        assert cfg.clone_newns is True
        assert cfg.clone_newpid is True
        assert cfg.clone_newipc is True
        assert cfg.clone_newuts is True
        assert cfg.clone_newcgroup is True
        assert cfg.clone_newtime is False

    def test_cgroup_defaults(self):
        cfg = NsJailConfig()
        assert cfg.cgroup_mem_max == 0
        assert cfg.cgroup_pids_max == 0
        assert cfg.cgroup_cpu_ms_per_sec == 0

    def test_list_fields_independent(self):
        c1 = NsJailConfig()
        c2 = NsJailConfig()
        c1.mount.append(MountPt(dst="/tmp"))
        assert c2.mount == []

    def test_full_construction(self):
        cfg = NsJailConfig(
            name="test",
            mode=Mode.ONCE,
            hostname="sandbox",
            time_limit=30,
            clone_newnet=True,
            mount=[
                MountPt(src="/", dst="/", is_bind=True, rw=False),
                MountPt(dst="/tmp", fstype="tmpfs", rw=True),
            ],
            uidmap=[IdMap(inside_id="0", outside_id="1000")],
            exec_bin=Exe(path="/bin/sh", arg=["-c", "echo hi"]),
        )
        assert cfg.name == "test"
        assert len(cfg.mount) == 2
        assert cfg.exec_bin.path == "/bin/sh"

    def test_rlimit_fields_exist(self):
        cfg = NsJailConfig()
        assert cfg.rlimit_as == 4096
        assert cfg.rlimit_as_type == RLimitType.VALUE
        assert cfg.rlimit_fsize == 1
        assert cfg.rlimit_nofile == 32
        assert cfg.rlimit_nproc_type == RLimitType.SOFT
        assert cfg.rlimit_stack_type == RLimitType.SOFT
