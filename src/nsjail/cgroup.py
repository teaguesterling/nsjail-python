"""Cgroup stats monitoring for nsjail sandboxes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CgroupStats:
    """Resource usage stats captured from cgroup stat files."""

    memory_peak_bytes: int | None = None
    memory_current_bytes: int | None = None
    cpu_usage_ns: int | None = None
    cpu_user_ns: int | None = None
    cpu_system_ns: int | None = None
    pids_current: int | None = None


def _read_int(path: Path) -> int | None:
    """Read an integer from a cgroup stat file."""
    try:
        return int(path.read_text().strip())
    except (FileNotFoundError, ValueError, PermissionError):
        return None


def parse_v1_stats(
    *,
    memory_path: Path | None = None,
    cpu_path: Path | None = None,
    pids_path: Path | None = None,
) -> CgroupStats:
    """Parse cgroup v1 stat files."""
    stats = CgroupStats()

    if memory_path:
        stats.memory_peak_bytes = _read_int(memory_path / "memory.max_usage_in_bytes")
        stats.memory_current_bytes = _read_int(memory_path / "memory.usage_in_bytes")

    if cpu_path:
        stats.cpu_usage_ns = _read_int(cpu_path / "cpuacct.usage")

    if pids_path:
        stats.pids_current = _read_int(pids_path / "pids.current")

    return stats


def parse_v2_stats(cgroup_path: Path) -> CgroupStats:
    """Parse cgroup v2 stat files from a unified cgroup directory."""
    stats = CgroupStats()

    stats.memory_peak_bytes = _read_int(cgroup_path / "memory.peak")
    stats.memory_current_bytes = _read_int(cgroup_path / "memory.current")
    stats.pids_current = _read_int(cgroup_path / "pids.current")

    cpu_stat_path = cgroup_path / "cpu.stat"
    try:
        text = cpu_stat_path.read_text()
        cpu_values: dict[str, int] = {}
        for line in text.strip().splitlines():
            parts = line.split()
            if len(parts) == 2:
                cpu_values[parts[0]] = int(parts[1])
        if "usage_usec" in cpu_values:
            stats.cpu_usage_ns = cpu_values["usage_usec"] * 1000
        if "user_usec" in cpu_values:
            stats.cpu_user_ns = cpu_values["user_usec"] * 1000
        if "system_usec" in cpu_values:
            stats.cpu_system_ns = cpu_values["system_usec"] * 1000
    except (FileNotFoundError, ValueError, PermissionError):
        pass

    return stats
