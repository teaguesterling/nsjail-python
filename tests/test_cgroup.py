import time
import threading

from nsjail.cgroup import CgroupStats, parse_v1_stats, parse_v2_stats
from nsjail.cgroup import CgroupMonitor


class TestCgroupStats:
    def test_defaults_are_none(self):
        stats = CgroupStats()
        assert stats.memory_peak_bytes is None
        assert stats.memory_current_bytes is None
        assert stats.cpu_usage_ns is None
        assert stats.cpu_user_ns is None
        assert stats.cpu_system_ns is None
        assert stats.pids_current is None

    def test_with_values(self):
        stats = CgroupStats(
            memory_peak_bytes=1024 * 1024,
            memory_current_bytes=512 * 1024,
            cpu_usage_ns=1_000_000_000,
            pids_current=5,
        )
        assert stats.memory_peak_bytes == 1024 * 1024
        assert stats.cpu_usage_ns == 1_000_000_000
        assert stats.pids_current == 5


class TestParseV1Stats:
    def test_memory_stats(self, tmp_path):
        (tmp_path / "memory.max_usage_in_bytes").write_text("1048576\n")
        (tmp_path / "memory.usage_in_bytes").write_text("524288\n")
        stats = parse_v1_stats(memory_path=tmp_path)
        assert stats.memory_peak_bytes == 1048576
        assert stats.memory_current_bytes == 524288

    def test_cpu_stats(self, tmp_path):
        (tmp_path / "cpuacct.usage").write_text("5000000000\n")
        stats = parse_v1_stats(cpu_path=tmp_path)
        assert stats.cpu_usage_ns == 5000000000

    def test_pids_stats(self, tmp_path):
        (tmp_path / "pids.current").write_text("7\n")
        stats = parse_v1_stats(pids_path=tmp_path)
        assert stats.pids_current == 7

    def test_missing_files(self, tmp_path):
        stats = parse_v1_stats(memory_path=tmp_path)
        assert stats.memory_peak_bytes is None

    def test_all_none_when_no_paths(self):
        stats = parse_v1_stats()
        assert stats == CgroupStats()


class TestParseV2Stats:
    def test_memory_stats(self, tmp_path):
        (tmp_path / "memory.peak").write_text("2097152\n")
        (tmp_path / "memory.current").write_text("1048576\n")
        stats = parse_v2_stats(tmp_path)
        assert stats.memory_peak_bytes == 2097152
        assert stats.memory_current_bytes == 1048576

    def test_cpu_stats(self, tmp_path):
        (tmp_path / "cpu.stat").write_text(
            "usage_usec 5000000\n"
            "user_usec 3000000\n"
            "system_usec 2000000\n"
        )
        stats = parse_v2_stats(tmp_path)
        assert stats.cpu_usage_ns == 5000000000
        assert stats.cpu_user_ns == 3000000000
        assert stats.cpu_system_ns == 2000000000

    def test_pids_stats(self, tmp_path):
        (tmp_path / "pids.current").write_text("3\n")
        stats = parse_v2_stats(tmp_path)
        assert stats.pids_current == 3

    def test_missing_files(self, tmp_path):
        stats = parse_v2_stats(tmp_path)
        assert stats == CgroupStats()


class TestCgroupMonitor:
    def test_monitor_captures_stats(self, tmp_path):
        (tmp_path / "memory.peak").write_text("1048576\n")
        (tmp_path / "memory.current").write_text("524288\n")
        (tmp_path / "pids.current").write_text("3\n")

        monitor = CgroupMonitor(cgroup_path=tmp_path, poll_interval=0.05, use_v2=True)
        monitor.start()
        time.sleep(0.15)
        stats = monitor.stop()

        assert stats.memory_peak_bytes == 1048576
        assert stats.memory_current_bytes == 524288
        assert stats.pids_current == 3

    def test_monitor_survives_missing_files(self, tmp_path):
        monitor = CgroupMonitor(cgroup_path=tmp_path, poll_interval=0.05, use_v2=True)
        monitor.start()
        time.sleep(0.1)
        stats = monitor.stop()
        assert stats == CgroupStats()

    def test_monitor_captures_changing_values(self, tmp_path):
        (tmp_path / "memory.current").write_text("100\n")
        (tmp_path / "memory.peak").write_text("100\n")

        monitor = CgroupMonitor(cgroup_path=tmp_path, poll_interval=0.05, use_v2=True)
        monitor.start()
        time.sleep(0.1)

        (tmp_path / "memory.current").write_text("200\n")
        (tmp_path / "memory.peak").write_text("200\n")
        time.sleep(0.1)

        stats = monitor.stop()
        assert stats.memory_peak_bytes == 200

    def test_monitor_stops_cleanly(self, tmp_path):
        (tmp_path / "memory.peak").write_text("1000\n")
        monitor = CgroupMonitor(cgroup_path=tmp_path, poll_interval=0.05, use_v2=True)
        monitor.start()
        time.sleep(0.1)
        stats = monitor.stop()
        assert stats is not None
