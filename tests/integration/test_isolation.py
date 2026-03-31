"""Integration tests for nsjail namespace and filesystem isolation."""

from __future__ import annotations

import pytest

from nsjail.config import Exe, MountPt, NsJailConfig
from nsjail.runner import Runner

pytestmark = pytest.mark.integration


class TestPidNamespace:
    def test_pid_is_one_inside(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "echo $$"]),
            clone_newpid=True,
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "clone_newpid", "time_limit",
        })
        assert result.stdout.strip() == b"1"


class TestFilesystem:
    def test_readonly_root_blocks_writes(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "touch /testfile_readonly"]),
            mount=[MountPt(src="/", dst="/", is_bind=True, rw=False)],
            mount_proc=True,
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "mount", "mount_proc", "time_limit",
        })
        assert result.returncode != 0

    def test_writable_directory(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "touch /tmp/testfile_rw && echo ok"]),
            mount=[
                MountPt(src="/", dst="/", is_bind=True, rw=False),
                MountPt(src="/tmp", dst="/tmp", is_bind=True, rw=True),
            ],
            mount_proc=True,
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "mount", "mount_proc", "time_limit",
        })
        assert b"ok" in result.stdout

    def test_tmpfs_mount(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "touch /tmp/test && df -T /tmp | tail -1"]),
            mount=[
                MountPt(src="/", dst="/", is_bind=True, rw=False),
                MountPt(dst="/tmp", fstype="tmpfs", rw=True, is_dir=True),
            ],
            mount_proc=True,
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "mount", "mount_proc", "time_limit",
        })
        assert b"tmpfs" in result.stdout

    def test_mount_proc(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/sh", arg=["-c", "head -1 /proc/self/status"]),
            mount=[MountPt(src="/", dst="/", is_bind=True, rw=False)],
            mount_proc=True,
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "mount", "mount_proc", "time_limit",
        })
        assert b"Name:" in result.stdout


class TestHostname:
    def test_custom_hostname(self, runner: Runner):
        cfg = NsJailConfig(
            exec_bin=Exe(path="/bin/hostname"),
            hostname="testjail",
            time_limit=10,
        )
        result = runner.run(overrides=cfg, override_fields={
            "exec_bin", "hostname", "time_limit",
        })
        assert b"testjail" in result.stdout
