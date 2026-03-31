import sys
from pathlib import Path

from nsjail.config import MountPt
from nsjail.mounts import bind_tree, bind_paths, tmpfs_mount, proc_mount
from nsjail.mounts import overlay_mount
from nsjail.mounts import system_libs, dev_minimal, python_env


class TestBindTree:
    def test_readonly_bind(self):
        mounts = bind_tree("/usr")
        assert len(mounts) == 1
        assert mounts[0].src == "/usr"
        assert mounts[0].dst == "/usr"
        assert mounts[0].is_bind is True
        assert mounts[0].rw is False

    def test_readwrite_bind(self):
        mounts = bind_tree("/data", readonly=False)
        assert mounts[0].rw is True

    def test_custom_dst(self):
        mounts = bind_tree("/host/data", dst="/sandbox/data")
        assert mounts[0].src == "/host/data"
        assert mounts[0].dst == "/sandbox/data"

    def test_returns_list_of_mountpt(self):
        mounts = bind_tree("/usr")
        assert isinstance(mounts, list)
        assert isinstance(mounts[0], MountPt)


class TestBindPaths:
    def test_multiple_paths(self):
        mounts = bind_paths(["/usr", "/lib", "/lib64"])
        assert len(mounts) == 3
        assert all(m.is_bind for m in mounts)
        assert all(m.rw is False for m in mounts)

    def test_readwrite(self):
        mounts = bind_paths(["/data", "/workspace"], readonly=False)
        assert all(m.rw is True for m in mounts)

    def test_empty_list(self):
        mounts = bind_paths([])
        assert mounts == []

    def test_each_mount_matches_path(self):
        paths = ["/usr", "/lib"]
        mounts = bind_paths(paths)
        for path, mount in zip(paths, mounts):
            assert mount.src == path
            assert mount.dst == path


class TestTmpfsMount:
    def test_basic_tmpfs(self):
        mounts = tmpfs_mount("/tmp")
        assert len(mounts) == 1
        assert mounts[0].dst == "/tmp"
        assert mounts[0].fstype == "tmpfs"
        assert mounts[0].rw is True
        assert mounts[0].is_dir is True

    def test_with_size(self):
        mounts = tmpfs_mount("/tmp", size="64M")
        assert mounts[0].options == "size=64M"

    def test_without_size(self):
        mounts = tmpfs_mount("/tmp")
        assert mounts[0].options is None


class TestProcMount:
    def test_proc_mount(self):
        mounts = proc_mount()
        assert len(mounts) == 1
        assert mounts[0].dst == "/proc"
        assert mounts[0].fstype == "proc"


class TestOverlayMount:
    def test_basic_overlay(self):
        mounts = overlay_mount(
            lower="/workspace",
            upper="/tmp/overlay/upper",
            work="/tmp/overlay/work",
            dst="/workspace",
        )
        assert len(mounts) == 1
        m = mounts[0]
        assert m.dst == "/workspace"
        assert m.fstype == "overlay"
        assert m.rw is True
        assert "lowerdir=/workspace" in m.options
        assert "upperdir=/tmp/overlay/upper" in m.options
        assert "workdir=/tmp/overlay/work" in m.options

    def test_overlay_options_format(self):
        mounts = overlay_mount(
            lower="/base",
            upper="/scratch/upper",
            work="/scratch/work",
            dst="/merged",
        )
        expected = "lowerdir=/base,upperdir=/scratch/upper,workdir=/scratch/work"
        assert mounts[0].options == expected

    def test_returns_list_of_mountpt(self):
        mounts = overlay_mount(lower="/a", upper="/b", work="/c", dst="/d")
        assert isinstance(mounts, list)
        assert isinstance(mounts[0], MountPt)


class TestSystemLibs:
    def test_returns_list(self):
        mounts = system_libs()
        assert isinstance(mounts, list)

    def test_all_readonly(self):
        mounts = system_libs()
        assert all(m.rw is False for m in mounts)

    def test_all_bind_mounts(self):
        mounts = system_libs()
        assert all(m.is_bind is True for m in mounts)

    def test_only_existing_paths(self):
        mounts = system_libs()
        for m in mounts:
            assert Path(m.src).exists(), f"{m.src} does not exist"

    def test_includes_usr(self):
        mounts = system_libs()
        dsts = {m.dst for m in mounts}
        assert "/usr/lib" in dsts or "/usr/bin" in dsts


class TestDevMinimal:
    def test_returns_list(self):
        mounts = dev_minimal()
        assert isinstance(mounts, list)

    def test_includes_dev_null(self):
        dsts = {m.dst for m in dev_minimal()}
        assert "/dev/null" in dsts

    def test_includes_dev_urandom(self):
        dsts = {m.dst for m in dev_minimal()}
        assert "/dev/urandom" in dsts

    def test_all_readonly(self):
        mounts = dev_minimal()
        assert all(m.rw is False for m in mounts)

    def test_only_existing_devices(self):
        mounts = dev_minimal()
        for m in mounts:
            assert Path(m.src).exists(), f"{m.src} does not exist"


class TestPythonEnv:
    def test_returns_list(self):
        mounts = python_env()
        assert isinstance(mounts, list)
        assert len(mounts) >= 1

    def test_all_readonly(self):
        mounts = python_env()
        assert all(m.rw is False for m in mounts)

    def test_includes_python_prefix(self):
        mounts = python_env()
        dsts = {m.dst for m in mounts}
        assert any(sys.prefix in d or d in sys.prefix for d in dsts)
