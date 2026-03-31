from nsjail.config import MountPt
from nsjail.mounts import bind_tree, bind_paths, tmpfs_mount, proc_mount


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
