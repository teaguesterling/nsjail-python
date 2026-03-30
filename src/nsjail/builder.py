"""Fluent builder for NsJailConfig."""

from __future__ import annotations

from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from nsjail.runner import Runner, NsJailResult

from nsjail.config import Exe, IdMap, MountPt, NsJailConfig
from nsjail.presets import (
    apply_cgroup_limits,
    apply_readonly_root,
    apply_seccomp_log,
)


class Jail:
    """Fluent builder for NsJailConfig."""

    def __init__(self) -> None:
        self._cfg = NsJailConfig()

    def build(self) -> NsJailConfig:
        return self._cfg

    # --- Command builders ---

    def command(self, *args: str) -> Jail:
        self._cfg.exec_bin = Exe(path=args[0], arg=list(args[1:]))
        return self

    def sh(self, script: str) -> Jail:
        self._cfg.exec_bin = Exe(path="/bin/sh", arg=["-c", script])
        return self

    def python(self, *args: str) -> Jail:
        self._cfg.exec_bin = Exe(path="/usr/bin/python3", arg=list(args))
        return self

    def bash(self, *args: str) -> Jail:
        self._cfg.exec_bin = Exe(path="/bin/bash", arg=list(args))
        return self

    # --- Resource limits ---

    def timeout(self, seconds: int) -> Jail:
        self._cfg.time_limit = seconds
        return self

    def memory(self, amount: int, unit: Literal["MB", "GB"] = "MB") -> Jail:
        if unit == "GB":
            memory_mb = amount * 1024
        else:
            memory_mb = amount
        apply_cgroup_limits(self._cfg, memory_mb=memory_mb)
        return self

    def cpu(self, ms_per_sec: int) -> Jail:
        apply_cgroup_limits(self._cfg, cpu_ms_per_sec=ms_per_sec)
        return self

    def pids(self, max_pids: int) -> Jail:
        apply_cgroup_limits(self._cfg, pids_max=max_pids)
        return self

    # --- Namespace control ---

    def no_network(self) -> Jail:
        self._cfg.clone_newnet = True
        return self

    def network(self) -> Jail:
        self._cfg.clone_newnet = False
        return self

    # --- Filesystem ---

    def readonly_root(self) -> Jail:
        apply_readonly_root(self._cfg)
        return self

    def writable(self, path: str, *, tmpfs: bool = False, size: str | None = None) -> Jail:
        if tmpfs:
            options = f"size={size}" if size else None
            self._cfg.mount.append(
                MountPt(dst=path, fstype="tmpfs", rw=True, is_dir=True, options=options)
            )
        else:
            self._cfg.mount.append(
                MountPt(src=path, dst=path, is_bind=True, rw=True)
            )
        return self

    def mount(self, src: str, dst: str, *, readonly: bool = False) -> Jail:
        self._cfg.mount.append(
            MountPt(src=src, dst=dst, is_bind=True, rw=not readonly)
        )
        return self

    # --- Environment ---

    def env(self, var: str) -> Jail:
        self._cfg.envar.append(var)
        return self

    def cwd(self, path: str) -> Jail:
        self._cfg.cwd = path
        return self

    # --- Security ---

    def seccomp_log(self) -> Jail:
        apply_seccomp_log(self._cfg)
        return self

    def uid_map(self, *, inside: int = 0, outside: int = 1000, count: int = 1) -> Jail:
        self._cfg.uidmap.append(
            IdMap(inside_id=str(inside), outside_id=str(outside), count=count)
        )
        return self

    # --- Execution ---

    def run(self, *, runner: Runner | None = None, **run_kwargs: object) -> NsJailResult:
        """Execute the built config via a Runner."""
        from nsjail.runner import Runner as _Runner

        r = runner or _Runner()
        temp = _Runner(
            base_config=self._cfg,
            nsjail_path=r._nsjail_path,
            render_mode=r._render_mode,
            capture_output=r._capture_output,
            keep_config=r._keep_config,
        )
        return temp.run(**run_kwargs)

    async def async_run(self, *, runner: Runner | None = None, **run_kwargs: object) -> NsJailResult:
        """Execute the built config asynchronously via a Runner."""
        from nsjail.runner import Runner as _Runner

        r = runner or _Runner()
        temp = _Runner(
            base_config=self._cfg,
            nsjail_path=r._nsjail_path,
            render_mode=r._render_mode,
            capture_output=r._capture_output,
            keep_config=r._keep_config,
        )
        return await temp.async_run(**run_kwargs)
