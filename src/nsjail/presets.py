"""Opinionated preset configurations and composable modifiers."""

from __future__ import annotations

from nsjail.config import Exe, MountPt, NsJailConfig
from nsjail.enums import Mode


def apply_readonly_root(
    cfg: NsJailConfig,
    *,
    writable: list[str] | None = None,
) -> None:
    cfg.mount.append(MountPt(src="/", dst="/", is_bind=True, rw=False))

    for path in writable or []:
        if path == "/tmp":
            cfg.mount.append(
                MountPt(dst="/tmp", fstype="tmpfs", rw=True, is_dir=True)
            )
        else:
            cfg.mount.append(
                MountPt(src=path, dst=path, is_bind=True, rw=True)
            )


def apply_cgroup_limits(
    cfg: NsJailConfig,
    *,
    memory_mb: int | None = None,
    cpu_ms_per_sec: int | None = None,
    pids_max: int | None = None,
) -> None:
    if memory_mb is not None:
        cfg.cgroup_mem_max = memory_mb * 1024 * 1024
    if cpu_ms_per_sec is not None:
        cfg.cgroup_cpu_ms_per_sec = cpu_ms_per_sec
    if pids_max is not None:
        cfg.cgroup_pids_max = pids_max


def apply_seccomp_log(cfg: NsJailConfig) -> None:
    cfg.seccomp_log = True


def sandbox(
    *,
    command: list[str],
    cwd: str = "/",
    timeout_sec: int = 600,
    memory_mb: int | None = None,
    cpu_ms_per_sec: int | None = None,
    pids_max: int | None = None,
    network: bool = False,
    writable_dirs: list[str] | None = None,
) -> NsJailConfig:
    cfg = NsJailConfig(
        mode=Mode.ONCE,
        cwd=cwd,
        time_limit=timeout_sec,
        clone_newnet=not network,
    )

    cfg.exec_bin = Exe(path=command[0], arg=command[1:])

    apply_readonly_root(cfg, writable=writable_dirs)
    apply_cgroup_limits(
        cfg,
        memory_mb=memory_mb,
        cpu_ms_per_sec=cpu_ms_per_sec,
        pids_max=pids_max,
    )

    return cfg
